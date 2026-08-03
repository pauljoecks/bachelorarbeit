/*
 * scanCONTROL C# SDK - C# wrapper for LLT.dll
 *
 * MIT License
 *
 * Copyright � 2017-2018 Micro-Epsilon Messtechnik GmbH & Co. KG
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
        static public uint uiResolution2 = 0;
        static public uint hLLT = 0;
        static public uint hLLT2 = 0;
        static public TScannerType tscanCONTROLType;
        static public TScannerType tscanCONTROLType2;

        static public byte[] abyProfileBuffer = new byte[1];
        static public byte[] abyProfileBuffer2 = new byte[1];  

        static public bool bProfileReceived = false;
        static public bool bProfileReceived2 = false;
        static public uint uiProfileDataSize = 0;
        static public uint uiProfileDataSize2 = 0;


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

            ProfileReceiveMethod fnProfileReceiveMethod = null;            

            uint uiBufferCount = 20, uiMainReflection = 0, uiPacketSize = 1024;

            int iInterfaceCount = 0;
            uint uiExposureTime = 100;
            uint uiIdleTime = 900;
            int iRetValue;
            bool bOK = true;
            bool bConnected = false;
            bool bConnected2 = false;
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

            hLLT2 = CLLTI.CreateLLTDevice(TInterfaceType.INTF_TYPE_ETHERNET);
            if (hLLT != 0)
                Console.WriteLine("CreateLLTDevice OK");
            else
                Console.WriteLine("Error during CreateLLTDevice\n");

            //Gets the available interfaces from the scanCONTROL-device
            iInterfaceCount = CLLTI.GetDeviceInterfacesFast(hLLT, auiInterfaces, auiInterfaces.GetLength(0));
            if (iInterfaceCount <= 0)
                Console.WriteLine("FAST: There is no scanCONTROL connected");
            else if (iInterfaceCount == 1)
                Console.WriteLine("FAST: There is only 1 scanCONTROL connected - please connect a second sensor to run this example!");
            else
                Console.WriteLine("FAST: There are " + iInterfaceCount + " scanCONTROL's connected");

            if (iInterfaceCount >= 2)
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

                target4 = auiInterfaces[1] & 0x000000FF;
                target3 = (auiInterfaces[1] & 0x0000FF00) >> 8;
                target2 = (auiInterfaces[1] & 0x00FF0000) >> 16;
                target1 = (auiInterfaces[1] & 0xFF000000) >> 24;

                // Set the second IP address detected by GetDeviceInterfacesFast to handle
                Console.WriteLine("Select the device interface: " + target1 + "." + target2 + "." + target3 + "." + target4);
                if ((iRetValue = CLLTI.SetDeviceInterface(hLLT2, auiInterfaces[1], 0)) < CLLTI.GENERAL_FUNCTION_OK)
                {
                    OnError("Error during SetDeviceInterface", iRetValue);
                    bOK = false;
                }

                if (bOK)
                {
                    // Connect to sensor with the device interface set before
                    Console.WriteLine("Connecting to scanCONTROL 1");
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
                    // Connect to sensor with the device interface set before
                    Console.WriteLine("Connecting to scanCONTROL 2");
                    if ((iRetValue = CLLTI.Connect(hLLT2)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during Connect", iRetValue);
                        bOK = false;
                    }
                    else
                        bConnected2 = true;
                }  

                if (bOK)
                {
                    Console.WriteLine("\n----- Get scanCONTROL Info -----\n");

                    // Read the device name and vendor from scanner
                    Console.WriteLine("Get Device Name 1");
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
                    // Read the device name and vendor from scanner
                    Console.WriteLine("Get Device Name 2");
                    if ((iRetValue = CLLTI.GetDeviceName(hLLT2, sbDevName, sbDevName.Capacity, sbVenName, sbVenName.Capacity)) < CLLTI.GENERAL_FUNCTION_OK)
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
                    Console.WriteLine("Get scanCONTROL type 1");
                    if ((iRetValue = CLLTI.GetLLTType(hLLT, ref tscanCONTROLType)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during GetLLTType", iRetValue);
                        bOK = false;
                    }

                    if (iRetValue == CLLTI.GENERAL_FUNCTION_DEVICE_NAME_NOT_SUPPORTED)
                    {
                        Console.WriteLine(" - Can't decode scanCONTROL 1 type. Please contact Micro-Epsilon for a newer version of the LLT.dll.");
                    }

                    if (tscanCONTROLType >= TScannerType.scanCONTROL27xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL27xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL 1 is a scanCONTROL27xx");
                    }
                    else if (tscanCONTROLType >= TScannerType.scanCONTROL25xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL25xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL 1 is a scanCONTROL25xx");
                    }
                    else if (tscanCONTROLType >= TScannerType.scanCONTROL26xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL26xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL 1 is a scanCONTROL26xx");
                    }
                    else if (tscanCONTROLType >= TScannerType.scanCONTROL29xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL29xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL 1 is a scanCONTROL29xx");
                    }
                    else if (tscanCONTROLType >= TScannerType.scanCONTROL30xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL30xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL 1 is a scanCONTROL30xx");
                    }
                    else
                    {
                        Console.WriteLine(" - The scanCONTROL 1 is a undefined type\nPlease contact Micro-Epsilon for a newer SDK");
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

                if (bOK)
                {
                    // Get the scanCONTROL type and check if it is valid
                    Console.WriteLine("Get scanCONTROL type 2");
                    if ((iRetValue = CLLTI.GetLLTType(hLLT2, ref tscanCONTROLType2)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during GetLLTType", iRetValue);
                        bOK = false;
                    }

                    if (iRetValue == CLLTI.GENERAL_FUNCTION_DEVICE_NAME_NOT_SUPPORTED)
                    {
                        Console.WriteLine(" - Can't decode scanCONTROL 2 type. Please contact Micro-Epsilon for a newer version of the LLT.dll.");
                    }

                    if (tscanCONTROLType2 >= TScannerType.scanCONTROL27xx_25 && tscanCONTROLType2 <= TScannerType.scanCONTROL27xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL 2 is a scanCONTROL27xx");
                    }
                    else if (tscanCONTROLType2 >= TScannerType.scanCONTROL25xx_25 && tscanCONTROLType2 <= TScannerType.scanCONTROL25xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL 2 is a scanCONTROL25xx");
                    }
                    else if (tscanCONTROLType2 >= TScannerType.scanCONTROL26xx_25 && tscanCONTROLType2 <= TScannerType.scanCONTROL26xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL 2 is a scanCONTROL26xx");
                    }
                    else if (tscanCONTROLType2 >= TScannerType.scanCONTROL29xx_25 && tscanCONTROLType2 <= TScannerType.scanCONTROL29xx_xxx)
                    {
                        Console.WriteLine(" - The scanCONTROL 2 is a scanCONTROL29xx");
                    }
                    else if (tscanCONTROLType2 >= TScannerType.scanCONTROL30xx_25 && tscanCONTROLType2 <= TScannerType.scanCONTROL30xx_xxx)
                    {
                    Console.WriteLine(" - The scanCONTROL 2 is a scanCONTROL30xx");
                    }
                    else
                    {
                        Console.WriteLine(" - The scanCONTROL is a undefined type\nPlease contact Micro-Epsilon for a newer SDK");
                    }

                    // Get all possible resolutions for connected sensor and save them in array 
                    Console.WriteLine("Get all possible resolutions");
                    if ((iRetValue = CLLTI.GetResolutions(hLLT2, auiResolutions, auiResolutions.GetLength(0))) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during GetResolutions", iRetValue);
                        bOK = false;
                    }

                    // Set the max. possible resolution
                    uiResolution2 = auiResolutions[0];
                }

                // Set scanner settings to valid parameters for this example                

                if (bOK)
                {
                    Console.WriteLine("\n----- Set scanCONTROL Parameters -----\n");

                    Console.WriteLine("Set resolution 1 to " + uiResolution);
                    if ((iRetValue = CLLTI.SetResolution(hLLT, uiResolution)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetResolution", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set BufferCount 1 to " + uiBufferCount);
                    if ((iRetValue = CLLTI.SetBufferCount(hLLT, uiBufferCount)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetBufferCount", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set MainReflection 1 to " + uiMainReflection);
                    if ((iRetValue = CLLTI.SetMainReflection(hLLT, uiMainReflection)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetMainReflection", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set Packetsize 1 to " + uiPacketSize);
                    if ((iRetValue = CLLTI.SetPacketSize(hLLT, uiPacketSize)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetPacketSize", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set Profile config 1 to PROFILE");
                    if ((iRetValue = CLLTI.SetProfileConfig(hLLT, TProfileConfig.PROFILE)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetProfileConfig", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set trigger 1 to internal");
                    if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_TRIGGER, CLLTI.TRIG_INTERNAL)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetFeature(FEATURE_FUNCTION_TRIGGER)", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set exposure time 1 to " + uiExposureTime);
                    if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXPOSURE_TIME, uiExposureTime)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME)", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set idle time 1 to " + uiIdleTime);
                    if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_IDLE_TIME, uiIdleTime)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetFeature(FEATURE_FUNCTION_IDLE_TIME)", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {   
                    Console.WriteLine("Set resolution 2 to " + uiResolution2);
                    if ((iRetValue = CLLTI.SetResolution(hLLT2, uiResolution2)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetResolution", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set BufferCount 2 to " + uiBufferCount);
                    if ((iRetValue = CLLTI.SetBufferCount(hLLT2, uiBufferCount)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetBufferCount", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set MainReflection 2 to " + uiMainReflection);
                    if ((iRetValue = CLLTI.SetMainReflection(hLLT2, uiMainReflection)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetMainReflection", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set Packetsize 2 to " + uiPacketSize);
                    if ((iRetValue = CLLTI.SetPacketSize(hLLT2, uiPacketSize)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetPacketSize", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set Profile config 2 to PROFILE");
                    if ((iRetValue = CLLTI.SetProfileConfig(hLLT2, TProfileConfig.PROFILE)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetProfileConfig", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set trigger 2 to internal");
                    if ((iRetValue = CLLTI.SetFeature(hLLT2, CLLTI.FEATURE_FUNCTION_TRIGGER, CLLTI.TRIG_INTERNAL)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetFeature(FEATURE_FUNCTION_TRIGGER)", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set exposure time 2 to " + uiExposureTime);
                    if ((iRetValue = CLLTI.SetFeature(hLLT2, CLLTI.FEATURE_FUNCTION_EXPOSURE_TIME, uiExposureTime)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME)", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set idle time 2 to " + uiIdleTime);
                    if ((iRetValue = CLLTI.SetFeature(hLLT2, CLLTI.FEATURE_FUNCTION_IDLE_TIME, uiIdleTime)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetFeature(FEATURE_FUNCTION_IDLE_TIME)", iRetValue);
                        bOK = false;
                    }
                }

                // Setup callback
                if (bOK)
                {
                    Console.WriteLine("\n----- Setup Callback function and event -----\n");

                    Console.WriteLine("Register the callback 1");
                    // Set the callback function
                    fnProfileReceiveMethod = new ProfileReceiveMethod(ProfileEvent);

                    // Register the callback
                    if ((iRetValue = CLLTI.RegisterCallback(hLLT, TCallbackType.STD_CALL, fnProfileReceiveMethod, hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during RegisterCallback", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Register the callback 2");

                    // Register the callback
                    if ((iRetValue = CLLTI.RegisterCallback(hLLT2, TCallbackType.STD_CALL, fnProfileReceiveMethod, hLLT2)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during RegisterCallback", iRetValue);
                        bOK = false;
                    }
                }

                // Main tasks in this example
                if (bOK)
                {
                    Console.WriteLine("\n----- Get profiles with Callback from scanCONTROL -----\n");

                    GetProfiles_Callback();
                }

                Console.WriteLine("\n----- Disconnect from scanCONTROL -----\n");

                if (bConnected)
                {
                    // Disconnect from the sensor
                    Console.WriteLine("Disconnect the scanCONTROL 1");
                    if ((iRetValue = CLLTI.Disconnect(hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during Disconnect", iRetValue);
                    }
                }

                if (bConnected)
                {
                    // Free ressources
                    Console.WriteLine("Delete the scanCONTROL instance 1");
                    if ((iRetValue = CLLTI.DelDevice(hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during Delete", iRetValue);
                    }
                }

                if (bConnected2)
                {
                    // Disconnect from the sensor
                    Console.WriteLine("Disconnect the scanCONTROL 2");
                    if ((iRetValue = CLLTI.Disconnect(hLLT2)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during Disconnect", iRetValue);
                    }
                }

                if (bConnected2)
                {
                    // Free ressources
                    Console.WriteLine("Delete the scanCONTROL instance 2");
                    if ((iRetValue = CLLTI.DelDevice(hLLT2)) < CLLTI.GENERAL_FUNCTION_OK)
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
         * Evalute reveived profiles via callback function
         */ 
        static void GetProfiles_Callback()
        {
            int iRetValue;
            double[] adValueX = new double[uiResolution];
            double[] adValueZ = new double[uiResolution];
            double[] adValueX2 = new double[uiResolution2];
            double[] adValueZ2 = new double[uiResolution2];

            // Allocate the profile buffer to the maximal profile size times the profile count
            Array.Resize(ref abyProfileBuffer, (int)uiResolution * 64);
            Array.Resize(ref abyProfileBuffer2, (int)uiResolution2 * 64);
            byte[] abyTimestamp = new byte[16];
            byte[] abyTimestamp2 = new byte[16];


            // Start continous profile transmission
            Console.WriteLine("Enable the measurement 1");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 1)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return;
            }

            Console.WriteLine("Enable the measurement 2");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT2, TTransferProfileType.NORMAL_TRANSFER, 1)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return;
            }

            // Wait for profile event (or timeout)
			Console.WriteLine("Wait for needed profiles");
            if (hProfileEvent.WaitOne(1000) != true)
            {
                Console.WriteLine("No profile received");
                return;
            }

            // Test the size of profile
            if (uiProfileDataSize == uiResolution * 64)
                Console.WriteLine("Profile size 1 is OK");
            else
            {
                Console.WriteLine("Profile size 1 is wrong");
                return;
            }

            // Test the size of profile
            if (uiProfileDataSize2 == uiResolution2 * 64)
                Console.WriteLine("Profile size 2 is OK");
            else
            {
                Console.WriteLine("Profile size 2 is wrong");
                return;
            }
            
            // Convert partial profile to x and z values
            Console.WriteLine("Converting of profile data 1 from the first reflection");
            iRetValue = CLLTI.ConvertProfile2Values(hLLT, abyProfileBuffer, uiResolution, TProfileConfig.PROFILE, tscanCONTROLType,
              0, 1, null, null, null, adValueX, adValueZ, null, null);
            if (((iRetValue & CLLTI.CONVERT_X) == 0) || ((iRetValue & CLLTI.CONVERT_Z) == 0))
            {
                OnError("Error during Converting of profile data", iRetValue);
                return;
            }
   
            // Convert partial profile to x and z values
            Console.WriteLine("Converting of profile data 2 from the first reflection");
            
            iRetValue = CLLTI.ConvertProfile2Values(hLLT2, abyProfileBuffer2, uiResolution2, TProfileConfig.PROFILE, tscanCONTROLType2,
              0, 1, null, null, null, adValueX2, adValueZ2, null, null);
            if (((iRetValue & CLLTI.CONVERT_X) == 0) || ((iRetValue & CLLTI.CONVERT_Z) == 0))
            {
                OnError("Error during Converting of profile data", iRetValue);
                return;
            }
         

            // Display x and z values
            Console.WriteLine("Profile data sensor 1");
            DisplayProfile(adValueX, adValueZ, uiResolution);
            Console.WriteLine("\nProfile data sensor 2");
            DisplayProfile(adValueX2, adValueZ2, uiResolution2);

            Console.WriteLine("\nTimestamp sensor 1:");           
            // Extract the 16-byte timestamp from the profile buffer into timestamp buffer and display it           
            Buffer.BlockCopy(abyProfileBuffer, 64 * (int)uiResolution - 16, abyTimestamp, 0, 16);
            DisplayTimestamp(abyTimestamp);

            Console.WriteLine("Timestamp sensor 2:");
            // Extract the 16-byte timestamp from the profile buffer into timestamp buffer and display it
            Buffer.BlockCopy(abyProfileBuffer2, 64 * (int)uiResolution2 - 16, abyTimestamp2, 0, 16);
            DisplayTimestamp(abyTimestamp2);

            // Stop continous profile transmission
            Console.WriteLine("Disable the measurement 1");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return;
            }

            Console.WriteLine("Disable the measurement 2");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT2, TTransferProfileType.NORMAL_TRANSFER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
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
                if (uiUserData == hLLT)
                {
                    //If the needed profile count not arrived: copy the new Profile in the buffer and increase the recived buffer count
                    uiProfileDataSize = uiSize;
                    //Copy the unmanaged data buffer (data) to the application
                    fixed (byte* dst = &abyProfileBuffer[0])
                    {
                        memcpy(dst, data, uiSize);
                    }
                    bProfileReceived = true;
 
                }

                if (uiUserData == hLLT2)
                {
                    //If the needed profile count not arrived: copy the new Profile in the buffer and increase the recived buffer count
                    uiProfileDataSize2 = uiSize;
                    //Copy the unmanaged data buffer (data) to the application
                    fixed (byte* dst = &abyProfileBuffer2[0])
                    {
                        memcpy(dst, data, uiSize);
                    }
                    bProfileReceived2 = true;
                }

                if (bProfileReceived == true && bProfileReceived2 == true)
                {
                    //If the needed profile count is arived: set the event
                    hProfileEvent.Set();                    
                }
            }
        }
    }
}
