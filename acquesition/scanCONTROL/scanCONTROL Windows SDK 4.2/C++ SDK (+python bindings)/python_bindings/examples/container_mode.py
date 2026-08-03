import time
import ctypes as ct
import math as m
import numpy as np
from matplotlib import pyplot as plt
import pyllt as llt

# Parametrize transmission
container_size = 25
scanner_type = ct.c_int(0)

# Init profile buffer and timestamp info
available_resolutions = (ct.c_uint * 4)()
available_interfaces = (ct.c_uint * 6)()
lost_profiles = ct.c_int(0)

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

# Get available resolutions
ret = llt.get_resolutions(hLLT, available_resolutions, len(available_resolutions))
if ret < 1:
    raise ValueError("Error getting resolutions : " + str(ret))

# Set max. resolution
resolution = available_resolutions[0]
ret = llt.set_resolution(hLLT, resolution)
if ret < 1:
    raise ValueError("Error getting resolutions : " + str(ret))

# Declare measuring data arrays
profile_buffer = (ct.c_ubyte * (resolution * 2 * container_size))()
x = (ct.c_double * resolution)()
z = (ct.c_double * resolution)()
intensities = (ct.c_ushort * resolution)()

# Equidistant ranges
x = np.linspace(0, resolution, resolution)
y = np.linspace(0, container_size, container_size)
X, Y = np.meshgrid(x, y)

# Scanner type
ret = llt.get_llt_type(hLLT, ct.byref(scanner_type))
if ret < 1:
    raise ValueError("Error scanner type: " + str(ret))

# Set container to profile config
ret = llt.set_profile_config(hLLT, llt.TProfileConfig.CONTAINER)
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

# Set rearrangement (z only)
rec_log2 = 1.0 / m.log(2.0)
container_resolution = m.floor((m.log(resolution) * rec_log2) + 0.5)
ret = llt.set_feature(hLLT, llt.FEATURE_FUNCTION_PROFILE_REARRANGEMENT, llt.CONTAINER_DATA_Z | llt.CONTAINER_STRIPE_1 | (container_resolution << 12))
if ret < 1:
    raise ValueError("Error setting rearrangement: " + str(ret))

# Set container size
ret = llt.set_profile_container_size(hLLT, 0, container_size)
if ret < 1:
    raise ValueError("Error setting profile container size: " + str(ret))

# Start transfer
ret = llt.transfer_profiles(hLLT, llt.TTransferProfileType.NORMAL_CONTAINER_MODE, 1)
if ret < 1:
    raise ValueError("Error starting transfer profiles: " + str(ret))

# Wait for container to fill
time.sleep(2.0)

ret = llt.get_actual_profile(hLLT, profile_buffer, len(profile_buffer), llt.TProfileConfig.CONTAINER, ct.byref(lost_profiles))
if ret != len(profile_buffer):
    print("Error get profile buffer data: " + str(ret))

# Stop transmission
ret = llt.transfer_profiles(hLLT, llt.TTransferProfileType.NORMAL_CONTAINER_MODE, 0)
if ret < 1:
    raise ValueError("Error stopping transfer profiles: " + str(ret))

# Disconnect
ret = llt.disconnect(hLLT)
if ret < 1:
    raise ConnectionAbortedError("Error while disconnect: " + str(ret))

ret = llt.del_device(hLLT)
if ret < 1:
    raise ConnectionAbortedError("Error while delete: " + str(ret))

# Convert buffer to big-endian ushort values and reshape them to 2D array
Z = np.frombuffer(profile_buffer, dtype='>H').reshape((container_size, resolution))

fig = plt.figure()
fig.subplots_adjust(wspace=0.3)
plt.pcolormesh(X, Y, Z)
plt.colorbar()
plt.show()
