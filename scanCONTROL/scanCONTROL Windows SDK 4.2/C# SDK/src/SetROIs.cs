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
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace MEScanControl
{
    class CScanCONTROLSample
    {
        /* Global variables */
        public const int MAX_INTERFACE_COUNT = 5;
        public const int MAX_RESOULUTIONS = 6;
        static public uint uiResolution = 0;
        static public uint hLLT = 0;
        static public TScannerType tscanCONTROLType;

        static public byte[] abyProfileBuffer;

        static public uint bProfileReceived = 0;
        static public uint uiNeededProfileCount = 25;
        static public uint uiProfileDataSize = 0;
        static public double raster_x = 0;
        static public double raster_z = 0;

        // Define an array with two AutoResetEvent WaitHandles. 
        static AutoResetEvent hProfileEvent = new AutoResetEvent(false);

        [STAThread]
        static void Main(string[] args)
        {
            scanCONTROL_Sample();
        }

        static unsafe void scanCONTROL_Sample()
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
                        raster_x = 1.25;
                        raster_z = 100.0 / 480.0;
                    }
                    else if (tscanCONTROLType >= TScannerType.scanCONTROL25xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL25xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL25xx");
                        raster_x = 2.5;
                        raster_z = 100.0 / 1024.0;
                    }
                    else if (tscanCONTROLType >= TScannerType.scanCONTROL26xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL26xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL26xx");
                        raster_x = 1.25;
                        raster_z = 100.0 / 480.0;
                    }
                    else if (tscanCONTROLType >= TScannerType.scanCONTROL29xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL29xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL29xx");
                        raster_x = 2.5;
                        raster_z = 100.0 / 1024.0;
                    }
                    else if (tscanCONTROLType >= TScannerType.scanCONTROL30xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL30xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL30xx");
                        raster_x = 1.5625;
                        raster_z = 200.0 / 1088.0;
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
                    Console.WriteLine("Set idle time to " + uiIdleTime + "\n\n");
                    if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_IDLE_TIME, uiIdleTime)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetFeature(FEATURE_FUNCTION_IDLE_TIME)", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    SetROI1();
                }

                if (bOK)
                {
                    SetROI2();
                }

                if (bOK)
                {
                    SetRONI();
                }

                if (bOK)
                {
                    SetROIAutoExposure();
                }

                if (bOK)
                {

                    GetProfiles_Callback();
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


        static void SetROI1()
        {
            int iRetValue;
            ushort col_start;
            ushort col_size;
            ushort row_start;
            ushort row_size;

            // Percentage X/Z of ROI
            double start_z = 10.0;
            double end_z = 90.0;
            double start_x = 10.0;
            double end_x = 45.0;

            Console.WriteLine("ROI1 Start Z (%): " + start_z);
            Console.WriteLine("ROI1 End Z (%): " + end_z);
            Console.WriteLine("ROI1 Start X (%): " + start_x);
            Console.WriteLine("ROI1 End X (%): " + end_x );

            if (tscanCONTROLType >= TScannerType.scanCONTROL26xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL26xx_xxx)
            {
                col_start = (ushort)(65535 - ((Math.Round(end_x / raster_x) * raster_x) / 100 * 65535));
                col_size = (ushort)(Math.Round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
                row_start = (ushort)(Math.Round(start_z / raster_z) * raster_z / 100 * 65536);
                row_size = (ushort)(Math.Round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);

            }
            else if (tscanCONTROLType >= TScannerType.scanCONTROL25xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL25xx_xxx)
            {
                
                col_start = (ushort)(65535 - ((Math.Round(end_x / raster_x) * raster_x) / 100 * 65535));
                col_size = (ushort)(Math.Round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
                row_start = (ushort)(65535 - ((Math.Round(end_z / raster_z) * raster_z) / 100 * 65535));
                row_size = (ushort)(Math.Round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
            }
            else if (tscanCONTROLType >= TScannerType.scanCONTROL27xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL27xx_xxx)
            {
                col_start = (ushort)(65535 - ((Math.Round(end_x / raster_x) * raster_x) / 100 * 65535));
                col_size = (ushort)(Math.Round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
                row_start = (ushort)(65535 - ((Math.Round(end_z / raster_z) * raster_z) / 100 * 65535));
                row_size = (ushort)(Math.Round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
            }
            else if (tscanCONTROLType >= TScannerType.scanCONTROL29xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL29xx_xxx)
            {
                col_start = (ushort)(65535 - ((Math.Round(end_x / raster_x) * raster_x) / 100 * 65535));
                col_size = (ushort)(Math.Round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
                row_start = (ushort)(65535 - ((Math.Round(end_z / raster_z) * raster_z) / 100 * 65535));
                row_size = (ushort)(Math.Round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
            }
            else if (tscanCONTROLType >= TScannerType.scanCONTROL30xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL30xx_xxx)
            {
                col_start = (ushort)(Math.Round(start_x / raster_x) * raster_x / 100 * 65536);
                col_size = (ushort)(Math.Round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
                row_start = (ushort)(Math.Round(start_z / raster_z) * raster_z / 100 * 65536);
                row_size = (ushort)(Math.Round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
            }
            else
            {
                Console.WriteLine("The scanCONTROL is a undefined type\nPlease contact Micro-Epsilon for a newer SDK\n\n");
                return;
            }

            Console.WriteLine("Enable ROI1 free region");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_ROI1_PRESET, 0x800)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_PRESET)", iRetValue);
            }

            Console.WriteLine("Set ROI1_Position parameter");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_ROI1_POSITION, (uint)(col_start << 16) + col_size)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_POSITION)", iRetValue);
            }

            Console.WriteLine("Set ROI1_Distance parameter");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_ROI1_DISTANCE, (uint)(row_start << 16) + row_size)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_DISTANCE)", iRetValue);
            }

            Console.WriteLine("Activate ROI1 free region\n\n");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER)", iRetValue);
            }
        }

        static void SetROI2()
        {
            int iRetValue;
            UInt32 tmp = 0; 
            ushort col_start;
            ushort col_size;
            ushort row_start;
            ushort row_size;

            // Percentage X/Z of ROI
            double start_z = 10.0;
            double end_z = 90.0;
            double start_x = 55.0;
            double end_x = 90.0;

            Console.WriteLine("ROI2 Start Z (%): " + start_z);
            Console.WriteLine("ROI2 End Z (%): " + end_z);
            Console.WriteLine("ROI2 Start X (%): " + start_x);
            Console.WriteLine("ROI2 End X (%): " + end_x);

            if (tscanCONTROLType >= TScannerType.scanCONTROL30xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL30xx_xxx)
            {
                col_start = (ushort)(Math.Round(start_x / raster_x) * raster_x / 100 * 65536);
                col_size = (ushort)(Math.Round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
                row_start = (ushort)(Math.Round(start_z / raster_z) * raster_z / 100 * 65536);
                row_size = (ushort)(Math.Round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
            }
            else
            {
                Console.WriteLine("ROI 2 cannot be set for this scanCONTROL type");
                return;
            }

            Console.WriteLine("Enable ROI2 free region");
            if ((iRetValue = CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_IMAGE_FEATURES,  ref tmp)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_PRESET)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_IMAGE_FEATURES, tmp | 0x1)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_IMAGE_FEATURES)", iRetValue);
            }

            Console.WriteLine("Set ROI2_Position parameter");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_ROI2_POSITION, (uint)(col_start << 16) + col_size)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_POSITION)", iRetValue);
            }
            Console.WriteLine("Set ROI2_Distance parameter\n\n");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_ROI2_DISTANCE, (uint)(row_start << 16) + row_size)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_DISTANCE)", iRetValue);
            }
        }

        static void SetRONI()
        {
            int iRetValue;
            UInt32 tmp = 0;
            ushort col_start;
            ushort col_size;
            ushort row_start;
            ushort row_size;

            // Percentage X/Z of ROI
            double start_z = 35.0;
            double end_z = 55.0;
            double start_x = 30.0;
            double end_x = 70.0;

            Console.WriteLine("RONI Start Z (%): " + start_z);
            Console.WriteLine("RONI End Z (%): " + end_z);
            Console.WriteLine("RONI Start X (%): " + start_x);
            Console.WriteLine("RONI End X (%): " + end_x);

            if (tscanCONTROLType >= TScannerType.scanCONTROL30xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL30xx_xxx)
            {
                col_start = (ushort)(Math.Round(start_x / raster_x) * raster_x / 100 * 65536);
                col_size = (ushort)(Math.Round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
                row_start = (ushort)(Math.Round(start_z / raster_z) * raster_z / 100 * 65536);
                row_size = (ushort)(Math.Round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
            }
            else
            {
                Console.WriteLine("RONI cannot be set for this scanCONTROL type\n\n");
                return;
            }

            Console.WriteLine("Enable RONI free region");
            if ((iRetValue = CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_IMAGE_FEATURES, ref tmp)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_PRESET)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_IMAGE_FEATURES, tmp | 0x2)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_IMAGE_FEATURES)", iRetValue);
            }

            Console.WriteLine("Set RONI_Position parameter");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_RONI_POSITION, (uint)(col_start << 16) + col_size)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_POSITION)", iRetValue);
            }
            Console.WriteLine("Set RONI_Distance parameter\n\n");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_RONI_DISTANCE, (uint)(row_start << 16) + row_size)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_DISTANCE)", iRetValue);
            }

        }

        static void SetROIAutoExposure()
        {
            int iRetValue;
            UInt32 tmp = 0;
            ushort col_start;
            ushort col_size;
            ushort row_start;
            ushort row_size;

            // Percentage X/Z of ROI
            double start_z = 5.0;
            double end_z = 95.0;
            double start_x = 5.0;
            double end_x = 95.0;

            Console.WriteLine("ROI auto exposure Start Z (%): " + start_z);
            Console.WriteLine("ROI auto exposure End Z (%): " + end_z);
            Console.WriteLine("ROI auto exposure Start X (%): " + start_x);
            Console.WriteLine("ROI auto exposure End X (%): " + end_x);

            if (tscanCONTROLType >= TScannerType.scanCONTROL30xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL30xx_xxx)
            {
                col_start = (ushort)(Math.Round(start_x / raster_x) * raster_x / 100 * 65536);
                col_size = (ushort)(Math.Round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
                row_start = (ushort)(Math.Round(start_z / raster_z) * raster_z / 100 * 65536);
                row_size = (ushort)(Math.Round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
            }
            else
            {
                Console.WriteLine("ROI auto exposure cannot be set for this scanCONTROL type");
                return;
            }

            Console.WriteLine("Enable auto exposure region");
            if ((iRetValue = CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_IMAGE_FEATURES, ref tmp)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_PRESET)", iRetValue);
            }
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_IMAGE_FEATURES, tmp | 0x4)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_IMAGE_FEATURES)", iRetValue);
            }

            Console.WriteLine("Set ROI auto exposure Position parameter");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EA_REFERENCE_REGION_POSITION, (uint)(col_start << 16) + col_size)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_POSITION)", iRetValue);
            }
            Console.WriteLine("Set ROI auto exposure Distance parameter\n\n");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EA_REFERENCE_REGION_DISTANCE, (uint)(row_start << 16) + row_size)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_DISTANCE)", iRetValue);
            }

        }

        /*
         * Evalute reveived profiles via callback function
         */
        static unsafe void GetProfiles_Callback()
        {
        int iRetValue;
        double[] adValueX = new double[uiResolution];
        double[] adValueZ = new double[uiResolution];
        ProfileReceiveMethod fnProfileReceiveMethod = null;

        Console.WriteLine("\n----- Setup Callback function and event -----\n");

        Console.WriteLine("Register the callback");
        // Set the callback function
        fnProfileReceiveMethod = new ProfileReceiveMethod(ProfileEvent);

        // Register the callback
        if ((iRetValue = CLLTI.RegisterCallback(hLLT, TCallbackType.STD_CALL, fnProfileReceiveMethod, hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
        {
            OnError("Error during RegisterCallback", iRetValue);
        }

        // Allocate the profile buffer to the maximal profile size times the profile count
        abyProfileBuffer = new byte[uiResolution * 64 * uiNeededProfileCount];
        byte[] abyTimestamp = new byte[16];

        // Start continous profile transmission
        Console.WriteLine("Enable the measurement");
        if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 1)) < CLLTI.GENERAL_FUNCTION_OK)
        {
            OnError("Error during TransferProfiles", iRetValue);
            return;
        }

        // Wait for profile event (or timeout)
        Console.WriteLine("Wait for needed profiles");
        if (hProfileEvent.WaitOne(2000) != true)
        {
            Console.WriteLine("No profile received");
            return;
        }

        // Test the size of profile
        if (uiProfileDataSize == uiResolution * 64)
            Console.WriteLine("Profile size is OK");
        else
        {
            Console.WriteLine("Profile size is wrong");
            return;
        }

        // Convert partial profile to x and z values
        Console.WriteLine("Converting of profile data from the first reflection");
        iRetValue = CLLTI.ConvertProfile2Values(hLLT, abyProfileBuffer, uiResolution, TProfileConfig.PROFILE, tscanCONTROLType,
            0, 1, null, null, null, adValueX, adValueZ, null, null);
        if (((iRetValue & CLLTI.CONVERT_X) == 0) || ((iRetValue & CLLTI.CONVERT_Z) == 0))
        {
            OnError("Error during Converting of profile data", iRetValue);
            return;
        }

        // Display x and z values
        DisplayProfile(adValueX, adValueZ, uiResolution);

        // Extract the 16-byte timestamp from the profile buffer into timestamp buffer and display it
        Buffer.BlockCopy(abyProfileBuffer, 64 * (int)uiResolution - 16, abyTimestamp, 0, 16);
        DisplayTimestamp(abyTimestamp);

        // Stop continous profile transmission
        Console.WriteLine("Disable the measurement");
        if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
        {
            OnError("Error during TransferProfiles", iRetValue);
            return;
        }
        }

        // Display the X/Z-Data of one profile
        static void DisplayProfile(double[] adValueX, double[] adValueZ, uint uiResolution)
        {
            int iNumberSize = 0;
            for (uint i = 0; i < uiResolution; i++)
            {

                //Prints the X- and Z-values
                iNumberSize = adValueX[i].ToString().Length;
                Console.Write("\r" + "Profiledata: X = " + adValueX[i].ToString());

                for (; iNumberSize < 8; iNumberSize++)
                {
                    Console.Write(" ");
                }

                iNumberSize = adValueZ[i].ToString().Length;
                Console.Write(" Z = " + adValueZ[i].ToString());

                for (; iNumberSize < 8; iNumberSize++)
                {
                    Console.Write(" ");
                }

                // Wait for display
                if (i % 8 == 0)
                {
                    System.Threading.Thread.Sleep(10);
                }
            }
            Console.WriteLine("");
        }

        // Display the timestamp
        static void DisplayTimestamp(byte[] abyTimestamp)
        {
            double dShutterOpen = 0, dShutterClose = 0;
            uint uiProfileCount = 0;

            //Decode the timestamp
            CLLTI.Timestamp2TimeAndCount(abyTimestamp, ref dShutterOpen, ref dShutterClose, ref uiProfileCount);
            Console.WriteLine("ShutterOpen: " + dShutterOpen + " ShutterClose: " + dShutterClose);
            Console.WriteLine("ProfileCount: " + uiProfileCount);
        }

        // Display the error text
        static void OnError(string strErrorTxt, int iErrorValue)
        {
            byte[] acErrorString = new byte[200];

            Console.WriteLine(strErrorTxt);
            if (CLLTI.TranslateErrorValue(hLLT, iErrorValue, acErrorString, acErrorString.GetLength(0))
                                            >= CLLTI.GENERAL_FUNCTION_OK)
                Console.WriteLine(System.Text.Encoding.ASCII.GetString(acErrorString, 0, acErrorString.GetLength(0)));
        }

        [DllImport("msvcrt.dll", EntryPoint = "memcpy", CallingConvention = CallingConvention.Cdecl, SetLastError = false)]
        static unsafe extern IntPtr memcpy(byte* dest, byte* src, uint count);

        /*
         * Callback function which copies the received data into the buffer and sets an event after the specified profiles
         */
        static unsafe void ProfileEvent(byte* data, uint uiSize, uint uiUserData)
        {
            if (uiSize > 0)
            {
                if (bProfileReceived < uiNeededProfileCount)
                {
                    //If the needed profile count not arrived: copy the new Profile in the buffer and increase the recived buffer count
                    uiProfileDataSize = uiSize;
                    //Kopieren des Unmanaged Datenpuffers (data) in die Anwendung
                    fixed (byte* dst = &abyProfileBuffer[bProfileReceived * uiSize])
                    {
                        memcpy(dst, data, uiSize);
                    }
                    bProfileReceived++;
                }

                if (bProfileReceived >= uiNeededProfileCount)
                {
                    //If the needed profile count is arrived: set the event
                    hProfileEvent.Set();
                }
            }
        }
    }
}