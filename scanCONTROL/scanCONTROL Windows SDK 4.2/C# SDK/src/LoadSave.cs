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

        static public uint uiResolution = 0;
        static public uint hLLT = 0;
        static public TScannerType tscanCONTROLType;

        // Set file name for avi file
        static StringBuilder sbAviFilename = new StringBuilder("LoadSaveSample.avi");

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

            uint uiBufferCount = 20, uiMainReflection = 0, uiPacketSize = 1024;

            int iInterfaceCount = 0;
            uint uiExposureTime = 100;
            uint uiIdleTime = 900;
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
            if (iInterfaceCount == 0)
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
                if ((iRetValue = CLLTI.SetDeviceInterface(hLLT, auiInterfaces[0], 0))
                    < CLLTI.GENERAL_FUNCTION_OK)
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
                    Console.WriteLine("Set BufferCount to " + uiBufferCount);
                    if ((iRetValue = CLLTI.SetBufferCount(hLLT, uiBufferCount)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetBufferCount", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set MainReflection to " + uiMainReflection);
                    if ((iRetValue = CLLTI.SetMainReflection(hLLT, uiMainReflection)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetMainReflection", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set Packetsize to " + uiPacketSize);
                    if ((iRetValue = CLLTI.SetPacketSize(hLLT, uiPacketSize)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetPacketSize", iRetValue);
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
                    Console.WriteLine("\n----- Save profiles from scanCONTROL -----\n");
                    bOK = Save();
                }
                if (bOK)
                {
                    Console.WriteLine("\n----- Load profiles from saved avi -----\n");
                    Load();
                }

                if (bConnected)
                {
                    Console.WriteLine("\n----- Disconnect from scanCONTROL -----\n");

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
         * Save a received profile sequence to a .avi file 
         */
        static bool Save()
        {
            int iRetValue;


            // Start continous profile transmission
            Console.WriteLine("Enable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 1)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return false;
            }

            // Start saving profiles to avi file
            Console.WriteLine("Enable the save process");
            if ((iRetValue = CLLTI.SaveProfiles(hLLT, sbAviFilename, TFileType.AVI)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during Saving", iRetValue);
                return false;
            }

            // Sleep for the time you want to save
            System.Threading.Thread.Sleep(1000);

            // Stop saving profiles to avi file
            Console.WriteLine("Disable the save process");
            if ((iRetValue = CLLTI.SaveProfiles(hLLT, null, TFileType.AVI)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during Saving", iRetValue);
                return false;
            }

            // Stop saving profiles to avi file
            Console.WriteLine("Disable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return false;
            }

            return true;
        }

        /*
         * Load a saved profile sequence from a .avi file 
         */
        static bool Load()
        {
            int iRetValue;

            // Create struct instances for parameters
            TPartialProfile tPartialProfile = new TPartialProfile();
            TProfileConfig tProfileConfig = new TProfileConfig();
            TScannerType tScannerType = new TScannerType();

            uint uiRearrangement = 0;
            uint uiProfileCount = 0;
            uint uiLostProfiles = 0;

            // Enable the load process for specified avi file
            Console.WriteLine("Enable the load process");
            if ((iRetValue = CLLTI.LoadProfiles(hLLT, sbAviFilename, ref tPartialProfile, ref tProfileConfig, ref tScannerType, ref uiRearrangement)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during Loading", iRetValue);
                return false;
            }

            Console.WriteLine("Loaded data:\n - PartialProfile:" + tPartialProfile + "\n - tScannerType: " + tScannerType + "\n - uiRearrangement: " + uiRearrangement);

            // Allocate buffer for loading profiles into
            byte[] abyProfileBuffer = new byte[tPartialProfile.nPointCount * 64];

            //Reading of the saved profiles
            while ((iRetValue = CLLTI.GetActualProfile(hLLT, abyProfileBuffer, abyProfileBuffer.GetLength(0), TProfileConfig.PROFILE, ref uiLostProfiles)) == tPartialProfile.nPointCount * 64)
            {
                uiProfileCount++;
                Console.Write("\rRead Profil: " + uiProfileCount);
            }
            Console.WriteLine("\n" + uiProfileCount + " profiles read from the saved file\n");

            return true;
        }

        //Displaying the error text
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
