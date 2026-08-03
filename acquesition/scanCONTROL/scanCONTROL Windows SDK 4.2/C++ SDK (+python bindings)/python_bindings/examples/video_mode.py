import time
import ctypes as ct
import numpy as np
from matplotlib import pyplot as plt
import pyllt as llt

# Parametrize transmission
scanner_type = ct.c_int(0)

# Init profile buffer and timestamp info
available_resolutions = (ct.c_uint*4)()
available_interfaces = (ct.c_uint*6)()
lost_profiles = ct.c_int()

# Create instance and set IP address
hLLT = llt.create_llt_device(llt.TInterfaceType.INTF_TYPE_ETHERNET)

# Get available interfaces
ret = llt.get_device_interfaces_fast(hLLT, available_interfaces, len(available_interfaces))
if ret < 1:
    raise ValueError("Error getting interfaces : " + str(ret))

ret = llt.set_device_interface(hLLT, available_interfaces[0], 0)
if ret < 1:
    raise ValueError("Error setting device interface: " + str(ret))

# Connect
ret = llt.connect(hLLT)
if ret < 1:
    raise ConnectionError("Error connect: " + str(ret))

# Scanner type
ret = llt.get_llt_type(hLLT, ct.byref(scanner_type))
if ret < 1:
    raise ValueError("Error scanner type: " + str(ret))

# Set profile config
ret = llt.set_profile_config(hLLT, llt.TProfileConfig.VIDEO_IMAGE)
if ret < 1:
    raise ValueError("Error setting profile config: " + str(ret))

# Set trigger
ret = llt.set_feature(hLLT, llt.FEATURE_FUNCTION_TRIGGER, llt.TRIG_INTERNAL)
if ret < 1:
    raise ValueError("Error setting trigger: " + str(ret))

# Set exposure time
ret = llt.set_feature(hLLT, llt.FEATURE_FUNCTION_EXPOSURE_TIME, 100)
if ret < 1:
    raise ValueError("Error setting exposure time: " + str(ret))

# Set idle time
ret = llt.set_feature(hLLT, llt.FEATURE_FUNCTION_IDLE_TIME, 3900)
if ret < 1:
    raise ValueError("Error idle time: " + str(ret))

height = ct.c_uint(0)
width = ct.c_uint(0)

# use VIDEO_MODE_0 for scanCONTROL 30xx series, to save bandwidth
video_type = llt.TTransferVideoType.VIDEO_MODE_1
if llt.TScannerType.scanCONTROL30xx_25 <= scanner_type.value <= llt.TScannerType.scanCONTROL30xx_xxx:
    video_type = llt.TTransferVideoType.VIDEO_MODE_0

# Start transfer
ret = llt.transfer_video_stream(hLLT, video_type, 1, ct.byref(height), ct.byref(width))
if ret < 1:
    raise ValueError("Error starting transfer profiles: " + str(ret))

# Allocate profile buffer
profile_buffer = (ct.c_ubyte * (height.value * width.value))()

# Warm-up time
time.sleep(0.2)

ret = llt.get_actual_profile(hLLT, profile_buffer, len(profile_buffer), llt.TProfileConfig.VIDEO_IMAGE,
                             ct.byref(lost_profiles))
if ret != len(profile_buffer):
    raise ValueError("Error get profile buffer data: " + str(ret))

# Stop Video Stream
ret = llt.transfer_video_stream(hLLT, video_type, 0, ct.byref(height), ct.byref(width))
if ret < 1:
    raise ValueError("Error stopping transfer profiles: " + str(ret))

# Disconnect
ret = llt.disconnect(hLLT)
if ret < 1:
    raise ConnectionAbortedError("Error while disconnect: "  + str(ret))

# Disconnect
ret = llt.del_device(hLLT)
if ret < 1:
    raise ConnectionAbortedError("Error while delete: " + str(ret))

image = np.frombuffer(profile_buffer, dtype='uint8').reshape((width.value, height.value))
plt.figure()
plt.imshow(image, 'gray', origin='lower')
plt.show()
