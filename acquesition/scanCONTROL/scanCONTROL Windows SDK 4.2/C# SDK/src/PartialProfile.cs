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

        static public uint uiExposureTime = 100;
        static public uint uiIdleTime = 900;

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

            int iRetValue;
            bool bOK = true;
            bool bConnected = false;
            ConsoleKeyInfo cki;

            hLLT = 0;
            uiResolution = 0;

            Console.WriteLine("----- Connect to scanCONTROL -----\n");

            // Create a Ethernet Device -> returns handle to LLT device
            hLLT = CLLTI.CreateLLTDevice(TInterfaceType.INTF_TYPE_ETHERNET);
            if (hLLT != 0)
                Console.WriteLine("CreateLLTDevice OK");
            else
                Console.WriteLine("Error during CreateLLTDevice\n");

            // Get the available interfaces from the scanCONTROL-device
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
                    if ((iRetValue = CLLTI.SetProfileConfig(hLLT, TProfileConfig.PARTIAL_PROFILE)) < CLLTI.GENERAL_FUNCTION_OK)
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
                    Console.WriteLine("\n----- Poll Pure Profile -----\n");

                    bOK = Partial_Profile_Pure(tscanCONTROLType);
                }
                if (bOK)
                {
                    Console.WriteLine("\n----- Poll Quarter Profil -----\n");
                    bOK = Partial_Profile_Quarter(tscanCONTROLType);
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
         * Set the scanner to transmit only a part of the profile - in this case part of the X and Z data of the 1st reflection
         * This reduces the amount of transmitted data significantly 
         */

        static bool Partial_Profile_Pure(TScannerType tscanCONTROLType)
        {
            int iRetValue = 0;
            uint uiLostProfiles = 0;
            bool noProfileReceived = true;

            // Struct necessary for defining the partial profile
            TPartialProfile tPartialProfile;

            double[] adValueX = new double[uiResolution];
            double[] adValueZ = new double[uiResolution];
            byte[] abyTimestamp = new byte[16];

            // Set the partial profile structure
            tPartialProfile.nStartPoint = 20;                 // Offset 20 -> start at the 21th point of the profile
            tPartialProfile.nStartPointData = 4;              // Dataoffset 4 Bytes ->location of X and Z
            tPartialProfile.nPointCount = uiResolution / 2; // transmit half the resolution
            tPartialProfile.nPointDataWidth = 4;              // 4 Bytes -> X and Z (2 bytes each)

            // Allocate buffer for partial profile
            byte[] abyProfileBuffer = new byte[tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth];

            // Set the partial profile stream setting
            Console.WriteLine("Set the partial profile struct");
            if ((iRetValue = CLLTI.SetPartialProfile(hLLT, ref tPartialProfile)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetPartialProfile", iRetValue);
                return false;
            }

            // Wait until all parameters are set before starting the transmission (this can take up to 120ms)
            System.Threading.Thread.Sleep(120);

            // Start continous profile transmission
            Console.WriteLine("Start the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 1)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return false;
            }



            // Get the next transmitted partial profile
            Console.WriteLine("Get Pure Profile");
            while (noProfileReceived)
            {
                if ((iRetValue = CLLTI.GetActualProfile(hLLT, abyProfileBuffer, abyProfileBuffer.GetLength(0), TProfileConfig.PARTIAL_PROFILE, ref uiLostProfiles)) != abyProfileBuffer.GetLength(0))
                {
                    if (iRetValue == CLLTI.ERROR_PROFTRANS_NO_NEW_PROFILE)
                    {
                        System.Threading.Thread.Sleep((int)(uiIdleTime + uiExposureTime) / 100);
                        noProfileReceived = true;
                    }
                    else
                    {
                        OnError("Error during GetActualProfile", iRetValue);
                        return false;
                    }

                }
                else
                {
                    Console.WriteLine("Profile received");
                    noProfileReceived = false;
                }
            }



            // Convert partial profile to x and z values
            Console.WriteLine("Convert Profiles");
            if ((iRetValue = CLLTI.ConvertPartProfile2Values(hLLT, abyProfileBuffer, ref tPartialProfile, tscanCONTROLType, 0, 1, null, null, null, adValueX, adValueZ, null, null)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error ConvertPartProfile2Values", iRetValue);
                return false;
            }

            // Display x and z values
            DisplayProfile(adValueX, adValueZ, uiResolution);

            // Extract the 16-byte timestamp from the profile buffer into timestamp buffer and display it
            Buffer.BlockCopy(abyProfileBuffer, (int)(tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth) - 16, abyTimestamp, 0, 16);
            DisplayTimestamp(abyTimestamp);

            // Stop continous profile transmission
            Console.WriteLine("Disable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return false;
            }

            return true;
        }

        /* 
         * Set the scanner to transmit only a part of the profile - in this case all data of the 1st reflection
         * This reduces the amount of transmitted data by the factor 4 
         */
        static bool Partial_Profile_Quarter(TScannerType tscanCONTROLType)
        {
            int iRetValue = 0;
            uint uiLostProfiles = 0;
            double[] adValueX = new double[uiResolution];
            double[] adValueZ = new double[uiResolution];
            byte[] abyTimestamp = new byte[16];
            bool noProfileReceived = true;

            // Struct necessary for defining the partial profile
            TPartialProfile tPartialProfile;

            // Set the partial profile structure
            tPartialProfile.nStartPoint = 0;                // Offset 0 -> start at the first point of the profile
            tPartialProfile.nStartPointData = 0;            // Dataoffset 0 Bytes -> no offset
            tPartialProfile.nPointCount = uiResolution;   // transmit the full resolution
            tPartialProfile.nPointDataWidth = 16;           // 16 Bytes -> full data set of the first reflection (see also Dataoffset)

            // Allocate buffer for partial profile
            byte[] abyProfileBuffer = new byte[tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth];

            // Set the partial profile stream setting
            Console.WriteLine("Set the partial profile struct");
            if ((iRetValue = CLLTI.SetPartialProfile(hLLT, ref tPartialProfile)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetPartialProfile", iRetValue);
                return false;
            }

            // Wait until all parameters are set before starting the transmission (this can take up to 120ms)
            System.Threading.Thread.Sleep(120);

            // Start continous profile transmission
            Console.WriteLine("Start the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 1)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return false;
            }



            // Get the next transmitted partial profile
            Console.WriteLine("Get Quarter Profile");
            while (noProfileReceived)
            {
                if ((iRetValue = CLLTI.GetActualProfile(hLLT, abyProfileBuffer, abyProfileBuffer.GetLength(0), TProfileConfig.PARTIAL_PROFILE, ref uiLostProfiles)) != abyProfileBuffer.GetLength(0))
                {
                    if (iRetValue == CLLTI.ERROR_PROFTRANS_NO_NEW_PROFILE)
                    {
                        System.Threading.Thread.Sleep((int)(uiIdleTime + uiExposureTime) / 100);
                        noProfileReceived = true;
                    }
                    else
                    {
                        OnError("Error during GetActualProfile", iRetValue);
                        return false;
                    }

                }
                else
                {
                    Console.WriteLine("Profile received");
                    noProfileReceived = false;
                }
            }

            // Convert partial profile to x and z values
            Console.WriteLine("Convert Profiles");
            if ((iRetValue = CLLTI.ConvertPartProfile2Values(hLLT, abyProfileBuffer, ref tPartialProfile, tscanCONTROLType, 0, 1, null, null, null, adValueX, adValueZ, null, null)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error ConvertPartProfile2Values", iRetValue);
                return false;
            }

            // Display x and z values
            DisplayProfile(adValueX, adValueZ, uiResolution);

            // Extract the 16-byte timestamp from the profile buffer into timestamp buffer and display it
            Buffer.BlockCopy(abyProfileBuffer, (int)(tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth) - 16, abyTimestamp, 0, 16);
            DisplayTimestamp(abyTimestamp);

            // Stop continous profile transmission
            Console.WriteLine("Disable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return false;
            }

            return true;
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

                // Wait a short time for display
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
    }
}
