import ctypes as ct
import numpy as np
from scipy.optimize import leastsq
import time as t
from matplotlib import pyplot as plt
import matplotlib.patches as patches
import pyllt as llt
import os
def calc_radius(x, y, xc, yc):
    """ calculate the distance of each 2D points from the center (xc, yc) """
    return np.sqrt((x-xc)**2 + (y-yc)**2)


def f(c, x, y):
    """ calculate the algebraic distance between the data points and the mean circle centered at c=(xc, yc) """
    r_i = calc_radius(x, y, *c)
    return r_i - r_i.mean()


def leastsq_circle(x,y):
    ''' approximates center coo and radius of a circle '''
    # coordinates of the barycenter
    x_m = np.mean(x)
    y_m = np.mean(y)
    center_estimate = x_m, y_m
    center, _ = leastsq(f, center_estimate, args=(x,y))
    xc, yc = center
    r_i = calc_radius(x, y, *center)
    r = r_i.mean()
    residuals = np.sum((r_i - r)**2)
    return xc, yc, r, residuals

# Circle ROI ---- Important: make sure there are valid points in the ROI
upper_z_limit = 90
lower_z_limit = 85
upper_x_limit = 15
lower_x_limit = -15

# Init animation plot
fig, ax = plt.subplots(facecolor='white')
line1, = ax.plot([], [], 'b-', label="fitted circle", lw=2)
line2, = ax.plot([], [], 'bD', mec='y', mew=1)
line3, = ax.plot([], [], 'g.', label="data", mew=1)
ax.grid()
ax.set_xlim(-25, 25)
ax.set_ylim(65, 110)
ax.add_patch(
    patches.Rectangle(
        (lower_x_limit, lower_z_limit),  # (x,y)
        upper_x_limit - lower_x_limit,  # width
        upper_z_limit - lower_z_limit,  # height
        edgecolor="#0000ff",
        facecolor="#0000ee",
        alpha = 0.1
    )
)

scanner_type = ct.c_uint(0)
profile_config = ct.c_uint(0)
partial_profile_struct = llt.TPartialProfile(0, 0, 0, 0)
rearrangement = ct.c_uint(0)

# ADJUST FILENAME HERE
filename = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + "### insert your file name (file located in same directory as this file) ###"
filename_b = filename.encode('utf-8')
filename_p = ct.c_char_p(filename_b)

# Null pointer if data not necessary
null_ptr_short = ct.POINTER(ct.c_ushort)()
null_ptr_int = ct.POINTER(ct.c_uint)()

hLLT = llt.create_llt_device(llt.TInterfaceType.INTF_TYPE_ETHERNET)

# Load profile data
ret = llt.load_profiles(hLLT, filename_p, ct.byref(partial_profile_struct),
                       ct.byref(profile_config), ct.byref(scanner_type), ct.byref(rearrangement))
if ret < 1:
    raise ValueError("Error loading data: " + str(ret))

resolution = partial_profile_struct.nPointCount
profile_buffer = (ct.c_ubyte*(resolution*partial_profile_struct.nPointDataWidth))()
lost_profiles = ct.c_int()

# Declare measuring data array
x = np.empty(resolution, dtype=float) # (ct.c_double * resolution)()
z = np.empty(resolution, dtype=float) # (ct.c_double * resolution)()
x_p = x.ctypes.data_as(ct.POINTER(ct.c_double))
z_p = z.ctypes.data_as(ct.POINTER(ct.c_double))

ret = llt.load_profiles_set_pos(hLLT, 5)
if ret < 1:
    raise ValueError("Error setting position: " + str(ret))

ret = llt.get_actual_profile(hLLT, profile_buffer, len(profile_buffer), profile_config,
                                ct.byref(lost_profiles))
if ret != len(profile_buffer):
    print("Error get profile buffer data: " + str(ret))

ret = llt.convert_part_profile_2_values(hLLT, profile_buffer, ct.byref(partial_profile_struct), scanner_type, 0, 1,
                                        null_ptr_short, null_ptr_short, null_ptr_short, x_p, z_p, null_ptr_int, null_ptr_int)
if ret & llt.CONVERT_X is 0 or ret & llt.CONVERT_Z is 0:
    raise ValueError("Error converting data: " + str(ret))

# Adjust ROI to area with circle
x_roi = x[(x > lower_x_limit) & (x < upper_x_limit) & (z > lower_z_limit) & (z < upper_z_limit)]
z_roi = z[(x > lower_x_limit) & (x < upper_x_limit) & (z > lower_z_limit) & (z < upper_z_limit)]

# Fitting
xc, zc, r, residuals = leastsq_circle(x_roi, z_roi)
theta_fit = np.linspace(-np.pi, np.pi, 90)

print("Radius[mm]:\t\t",round(r, 3))
print("Center(x|z)[mm]:\t",round(xc, 3), "|", round(zc, 3))
print("Residual:\t\t", round(residuals, 3),"\n")

# Prepare draw data
x_fit = xc + r * np.cos(theta_fit)
z_fit = zc + r * np.sin(theta_fit)

line1.set_data(x_fit, z_fit)
line2.set_data([xc], [zc])
line3.set_data(x, z)

plt.show()