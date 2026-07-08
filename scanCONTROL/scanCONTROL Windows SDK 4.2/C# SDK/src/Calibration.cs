/*
 * scanCONTROL C# SDK - C# wrapper for LLT.dll
 *
 * MIT License
 *
 * Copyright © 2017-2018 Micro-Epsilon Messtechnik GmbH & Co. KG
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:

 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.

 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */

using System;
using System.Text;

namespace MEScanControl
{
    class CScanCONTROLSample
    {
        /* Global variables */
        public const int MAX_INTERFACE_COUNT = 5;
        public const int MAX_RESOULUTIONS = 6;

        static public uint m_toggle = 0;

        static public uint uiResolution = 0;
        static public uint hLLT = 0;
        static public TScannerType tscanCONTROLType;

        [STAThread]
        static void Main(string[] args)
        {
            scanCONTROL_Sample();
        }

        static void scanCONTROL_Sample()
        {
            uint[] auiInterfaces = new uint[MAX_INTERFACE_COUNT];
            uint[] auiResolutions = new uint[MAX_RESOULUTIONS];

            StringBuilder sbDevName = new StringBuilder(100);
            StringBuilder sbVenName = new StringBuilder(100);          

            int iInterfaceCount = 0;
            uint uiExposureTime = 100;
            uint uiIdleTime = 3900;
            int iRetValue;
            bool bOK = true;
            bool bConnected = false;
            ConsoleKeyInfo cki;

            hLLT = 0;
            uiResolution = 0;

            Console.WriteLine("----- Connect to scanCONTROL -----\n");

            //Create a Ethernet Device -> returns handle to LLT device
            hLLT = CLLTI.CreateLLTDevice(TInterfaceType.INTF_TYPE_ETHERNET);
            if (hLLT != 0)
                Console.WriteLine("CreateLLTDevice OK");
            else
                Console.WriteLine("Error during CreateLLTDevice\n");

            //Gets the available interfaces from the scanCONTROL-device
            iInterfaceCount = CLLTI.GetDeviceInterfacesFast(hLLT, auiInterfaces, auiInterfaces.GetLength(0));
            if (iInterfaceCount <= 0)
                Console.WriteLine("FAST: There is no scanCONTROL connected");
            else if (iInterfaceCount == 1)
                Console.WriteLine("FAST: There is 1 scanCONTROL connected ");
            else
                Console.WriteLine("FAST: There are " + iInterfaceCount + " scanCONTROL's connected");

            if (iInterfaceCount >= 1)
            {
                uint target4 = auiInterfaces[0] & 0x000000FF;
                uint target3 = (auiInterfaces[0] & 0x0000FF00) >> 8;
                uint target2 = (auiInterfaces[0] & 0x00FF0000) >> 16;
                uint target1 = (auiInterfaces[0] & 0xFF000000) >> 24;

                // Set the first IP address detected by GetDeviceInterfacesFast to handle
                Console.WriteLine("Select the device interface: " + target1 + "." + target2 + "." + target3 + "." + target4);
                if ((iRetValue = CLLTI.SetDeviceInterface(hLLT, auiInterfaces[0], 0)) < CLLTI.GENERAL_FUNCTION_OK)
                {
                    OnError("Error during SetDeviceInterface", iRetValue);
                    bOK = false;
                }

                if (bOK)
                {
                    // Connect to sensor with the device interface set before
                    Console.WriteLine("Connecting to scanCONTROL");
                    if ((iRetValue = CLLTI.Connect(hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during Connect", iRetValue);
                        bOK = false;
                    }
                    else
                        bConnected = true;
                }

                if (bOK)
                {
                    Console.WriteLine("\n----- Get scanCONTROL Info -----\n");

                    // Read the device name and vendor from scanner
                    Console.WriteLine("Get Device Name");
                    if ((iRetValue = CLLTI.GetDeviceName(hLLT, sbDevName, sbDevName.Capacity, sbVenName, sbVenName.Capacity)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during GetDevName", iRetValue);
                        bOK = false;
                    }
                    else
                    {
                        Console.WriteLine(" - Devname: " + sbDevName + "\n - Venname: " + sbVenName);
                    }
                }

                if (bOK)
                {
                    // Get the scanCONTROL type and check if it is valid
                    Console.WriteLine("Get scanCONTROL type");
                    if ((iRetValue = CLLTI.GetLLTType(hLLT, ref tscanCONTROLType)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during GetLLTType", iRetValue);
                        bOK = false;
                    }

                    if (iRetValue == CLLTI.GENERAL_FUNCTION_DEVICE_NAME_NOT_SUPPORTED)
                    {
                        Console.WriteLine(" - Can't decode scanCONTROL type. Please contact Micro-Epsilon for a newer version of the LLT.dll.");
                    }

                    if (tscanCONTROLType >= TScannerType.scanCONTROL27xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL27xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL27xx");
                    }
                    else if (tscanCONTROLType >= TScannerType.scanCONTROL25xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL25xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL25xx");
                    }
                    else if (tscanCONTROLType >= TScannerType.scanCONTROL26xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL26xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL26xx");
                    }
                    else if (tscanCONTROLType >= TScannerType.scanCONTROL29xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL29xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL29xx");
                    }
                    else if (tscanCONTROLType >= TScannerType.scanCONTROL30xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL30xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL30xx");
                    }
                    else
                    {
                        Console.WriteLine(" - The scanCONTROL is a undefined type\nPlease contact Micro-Epsilon for a newer SDK");
                    }

                    // Get all possible resolutions for connected sensor and save them in array
                    Console.WriteLine("Get all possible resolutions");
                    if ((iRetValue = CLLTI.GetResolutions(hLLT, auiResolutions, auiResolutions.GetLength(0))) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during GetResolutions", iRetValue);
                        bOK = false;
                    }

                    // Set the max. possible resolution
                    uiResolution = auiResolutions[0];
                }

                // Set scanner settings to valid parameters for this example

                if (bOK)
                {
                    Console.WriteLine("\n----- Set scanCONTROL Parameters -----\n");

                    Console.WriteLine("Set resolution to " + uiResolution);
                    if ((iRetValue = CLLTI.SetResolution(hLLT, uiResolution)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetResolution", iRetValue);
                        bOK = false;
                    }
                }
                
                if (bOK)
                {
                    Console.WriteLine("Set Profile config to PROFILE");
                    if ((iRetValue = CLLTI.SetProfileConfig(hLLT, TProfileConfig.PROFILE)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetProfileConfig", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set trigger to internal");
                    if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_TRIGGER, CLLTI.TRIG_INTERNAL)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetFeature(FEATURE_FUNCTION_TRIGGER)", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set exposure time to " + uiExposureTime);
                    if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXPOSURE_TIME, uiExposureTime)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME)", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set idle time to " + uiIdleTime);
                    if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_IDLE_TIME, uiIdleTime)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetFeature(FEATURE_FUNCTION_IDLE_TIME)", iRetValue);
                        bOK = false;
                    }
                }

                // Main tasks in this example
                if (bOK)
                {
                    Console.WriteLine("\n----- Set Calibration -----\n");

                    Calibration();
                }

                Console.WriteLine("\n----- Disconnect from scanCONTROL -----\n");

                if (bConnected)
                {
                    // Disconnect from the sensor
                    Console.WriteLine("Disconnect the scanCONTROL");
                    if ((iRetValue = CLLTI.Disconnect(hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during Disconnect", iRetValue);
                    }
                }

                if (bConnected)
                {
                    // Free ressources
                    Console.WriteLine("Delete the scanCONTROL instance");
                    if ((iRetValue = CLLTI.DelDevice(hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during Delete", iRetValue);
                    }
                }
            }

            //Wait for a keyboard hit
            while (true)
            {
                cki = Console.ReadKey();
                if (cki.KeyChar != 0)
                {
                    break;
                }
            }
        }

        /*
        * Set Calibration
        */
        static void Calibration()
        {   
            /* Sensor parameters have to adjusted for sensor type - see Config Tools Manual */
            double offset = 95.0; // e.g. 65.0 mm;
            double scaling = 0.002; // e.g.0.001 mm;

            Console.WriteLine("Offset: " + offset);
            Console.WriteLine("Scaling: " + scaling);

            // Center of rotation and angle
            double center_x = 0.0; // usually x = 0.0mm
            double center_z = offset; // usually z = offset
            double angle = -2.0; // degree
            
            // Coordinate system is shifted by
            double shift_x = -2.0; // mm
            double shift_z = -2.0; // mm

            Console.WriteLine("Read Calibration");
            ReadCalibration(offset, scaling);
            
            Console.WriteLine("Reset Calibration 1");
            ResetCustomCalibration();

            Console.WriteLine("Read Calibration");
            ReadCalibration(offset, scaling);

            Console.WriteLine("Set Calibration 1");
            SetCustomCalibration(center_x, center_z, angle, shift_x, shift_z, offset, scaling);

            Console.WriteLine("Read Calibration");
            ReadCalibration(offset, scaling);

            Console.WriteLine("Reset Calibration 2");
            ResetCustomCalibration2();

            Console.WriteLine("Read Calibration");
            ReadCalibration(offset, scaling);

            Console.WriteLine("Set Calibration 2");
            SetCustomCalibration2(center_x, center_z, angle, shift_x, shift_z, offset, scaling);

            Console.WriteLine("Read Calibration");
            ReadCalibration(offset, scaling);

            Console.WriteLine("Save calibration permanently");
            CLLTI.SaveGlobalParameter(hLLT);
        }

        // Function to be used for sensors with Firmware < v43
        static void SetCustomCalibration(double cX, double cZ, double angle, double sX, double sZ, double offset, double scaling)
        {
            int iRetValue;
            uint tmp = 0;
            double rotate_angle = angle;
            double PI = Math.PI;
            double xTrans = -sX;
            double zTrans = offset - sZ;

            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0000)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0100)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0420)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0305)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0204)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0308)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0280)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }

            // Read current state of invert_x and invert_z from sensor
	        if ((iRetValue = CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_PROFILE_PROCESSING, ref tmp)) < CLLTI.GENERAL_FUNCTION_OK)
	        {
		        OnError("Error during GetFeature(FEATURE_FUNCTION_PROFILE_PROCESSING)", iRetValue);
	        }
	        
            uint uiInvertX = (tmp & CLLTI.PROC_FLIP_POSITION) >> 7;
	        uint uiInvertZ = (tmp & CLLTI.PROC_FLIP_DISTANCE) >> 6;

	        // invert angle if necessary
	        if (uiInvertX != uiInvertZ)
	        {
		        rotate_angle = -angle;
	        }
	        double sinus = Math.Sin(rotate_angle * PI / 180);
	        double cosinus = Math.Cos(rotate_angle * PI / 180);

	        // Rotation angle
	        if (rotate_angle < 0)
	        {
		        rotate_angle = Math.Floor(65536 + rotate_angle / 0.01 + 0.5);
	        }
	        else
	        {
		        rotate_angle = Math.Floor(rotate_angle / 0.01 + 0.5);
	        }

	        // Rotation center 1 for rotating
	        double x1 = cX / scaling + 32768;
	        double z1 = (cZ - offset) / scaling + 32768;

	        // Rotation center 2 for translating
	        double x2 = xTrans / scaling + 32768;
	        double z2 = 65536 - ((zTrans - offset) / scaling + 32768);

	        // Calculate the combined rotation center
	        double x3 = x1 + (x2 - 32768) * cosinus + (z2 - 32768) * sinus;
	        double z3 = z1 + (z2 - 32768) * cosinus - (x2 - 32768) * sinus;
	        xTrans = Math.Floor(x3 + 0.5);
	        zTrans = Math.Floor(z3 + 0.5);

	        // Saturation
	        if (xTrans < 0) xTrans = 0; else if (xTrans > 65535) xTrans = 65535;
	        if (zTrans < 0) zTrans = 0; else if (zTrans > 65535) zTrans = 65535;
	        if (rotate_angle < 0) rotate_angle = 0; else if (rotate_angle > 65535) rotate_angle = 65535;

	        uint a = (uint) xTrans;
            uint b = (uint) zTrans;

            // Ausgabe
            // X High
            tmp = 0x300 | ((a & 0xFF00) >> 8);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            // X Low
            tmp = 0x200 | (a & 0xFF);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            // Z High
            tmp = 0x300 | ((b & 0xFF00) >> 8);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            // Z Low
            tmp = 0x200 | (b & 0xFF);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }

            a = 0;
	        b = (uint) rotate_angle;

            // Ausgabe
            // X High
            tmp = 0x300 | ((a & 0xFF00) >> 8);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            // X Low
            tmp = 0x200 | (a & 0xFF);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            // Z High
            tmp = 0x300 | ((b & 0xFF00) >> 8);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            // Z Low
            tmp = 0x200 | (b & 0xFF);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }

            // Abschluss
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0100)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
        }

        // Function to be used for sensors with Firmware >= v43
        static void SetCustomCalibration2(double cX, double cZ, double angle, double sX, double sZ, double offset, double scaling)
        {
            int iRetValue;
            uint tmp = 0;
            double rotate_angle = angle;
            double PI = Math.PI;
            double xTrans = -sX;
            double zTrans = offset - sZ;
            
            // Read current state of invert_x and invert_z from sensor
            if ((iRetValue = CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_PROFILE_PROCESSING, ref tmp)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetFeature(FEATURE_FUNCTION_PROFILE_PROCESSING)", iRetValue);
            }
            uint uiInvertX = (tmp & CLLTI.PROC_FLIP_POSITION) >> 7;
            uint uiInvertZ = (tmp & CLLTI.PROC_FLIP_DISTANCE) >> 6;
            
            // invert angle if necessary
            if (uiInvertX != uiInvertZ)
            {
                rotate_angle = -angle;
            }
            double sinus = Math.Sin(rotate_angle * PI / 180);
            double cosinus = Math.Cos(rotate_angle * PI / 180);
            
            // Rotation angle
            if (rotate_angle < 0) 
            {
                rotate_angle = Math.Floor(65536 + rotate_angle / 0.01 + 0.5);
            }
            else
            {
                rotate_angle = Math.Floor(rotate_angle / 0.01 + 0.5);
            }

            // Rotation center 1 for rotating
            double x1 = cX / scaling + 32768;
            double z1 = (cZ - offset) / scaling + 32768;

            // Rotation center 2 for translating
            double x2 = xTrans / scaling + 32768;
            double z2 = 65536 - ((zTrans - offset) / scaling + 32768);

            // Calculate the combined rotation center
            double x3 = x1 + (x2 - 32768) * cosinus + (z2 - 32768) * sinus;
            double z3 = z1 + (z2 - 32768) * cosinus - (x2 - 32768) * sinus;
            xTrans = Math.Floor(x3 + 0.5);
            zTrans = Math.Floor(z3 + 0.5);

            // Saturation
            if (xTrans < 0) xTrans = 0; else if (xTrans > 65535) xTrans = 65535;
            if (zTrans < 0) zTrans = 0; else if (zTrans > 65535) zTrans = 65535;
            if (rotate_angle < 0) rotate_angle = 0; else if (rotate_angle > 65535) rotate_angle = 65535;

            // Compute register values
            uint calib2 = ((uint)xTrans << 16) + (uint)zTrans;
            uint calib3 = (uint)rotate_angle;

            // Write calibration to sensor
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_0, 0x05000004)) < CLLTI.GENERAL_FUNCTION_OK)
                OnError("Error during Activation 0", iRetValue);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_1, 0x08000080)) < CLLTI.GENERAL_FUNCTION_OK)
                OnError("Error during Activation 1", iRetValue);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_2, calib2)) < CLLTI.GENERAL_FUNCTION_OK)
                OnError("Error during Calibration 2", iRetValue);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_3, calib3)) < CLLTI.GENERAL_FUNCTION_OK)
                OnError("Error during Calibration 3", iRetValue);
        }

        static void ReadCalibration(double offset, double scaling)
        {
            uint tmp = 0;
            CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_0, ref tmp);
            Console.WriteLine("FEATURE_FUNCTION_CALIBRATION_0: {0:X8}", tmp);
            CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_1, ref tmp);
            Console.WriteLine("FEATURE_FUNCTION_CALIBRATION_1: {0:X8}", tmp);
            CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_2, ref tmp);
            Console.WriteLine("FEATURE_FUNCTION_CALIBRATION_2: {0:X8}", tmp);
            CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_3, ref tmp);
            Console.WriteLine("FEATURE_FUNCTION_CALIBRATION_3: {0:X8}", tmp);
            CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_4, ref tmp);
            Console.WriteLine("FEATURE_FUNCTION_CALIBRATION_4: {0:X8}", tmp);
            CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_5, ref tmp);
            Console.WriteLine("FEATURE_FUNCTION_CALIBRATION_5: {0:X8}", tmp);
            CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_6, ref tmp);
            Console.WriteLine("FEATURE_FUNCTION_CALIBRATION_6: {0:X8}", tmp);
            CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_7, ref tmp);
            Console.WriteLine("FEATURE_FUNCTION_CALIBRATION_7: {0:X8}", tmp);
            Console.WriteLine("");
        }

        static void ResetCustomCalibration()
        {
            int iRetValue;

            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0000)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0100)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0420)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0100)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
            }            
        }

        static void ResetCustomCalibration2()
        {
            int iRetValue;

            //Deactivate calibration
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_0, 0x00000000)) < CLLTI.GENERAL_FUNCTION_OK)
                OnError("Error during Activation 0", iRetValue);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_1, 0x00000000)) < CLLTI.GENERAL_FUNCTION_OK)
                OnError("Error during Activation 1", iRetValue);
            //Reset calibration registers
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_2, 0x00000000)) < CLLTI.GENERAL_FUNCTION_OK)
                OnError("Error during Calibration 2", iRetValue);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_CALIBRATION_3, 0x00000000)) < CLLTI.GENERAL_FUNCTION_OK)
                OnError("Error during Calibration 3", iRetValue);
        }

        static void OnError(string strErrorTxt, int iErrorValue)
        {
            byte[] acErrorString = new byte[200];

            Console.WriteLine(strErrorTxt);
            if (CLLTI.TranslateErrorValue(hLLT, iErrorValue, acErrorString, acErrorString.GetLength(0))
            >= CLLTI.GENERAL_FUNCTION_OK)
                Console.WriteLine(System.Text.Encoding.ASCII.GetString(acErrorString, 0, acErrorString.GetLength(0)));
        }
    }
}
