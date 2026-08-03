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
        static public uint uiNeededProfileCount = 100;
        static public uint uiProfileDataSize = 0;
        

        static ProfileReceiveMethod fnProfileReceiveMethod = null;
        // Define an array with two AutoResetEvent WaitHandles. 
        static AutoResetEvent hProfileEvent = new AutoResetEvent(false);

        public static AVIWriter writer = new AVIWriter();

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
            uint SerialNumber = 0;


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
                    //GetSerialNumber
                    if ((iRetValue = CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_SERIAL_NUMBER, ref SerialNumber)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during GetDevName", iRetValue);
                        bOK = false;
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
                /*
                if (bOK)
                {
                    if ((iRetValue = CLLTI.SetProfileConfig(hLLT, CLLTI.TProfileConfig.PROFILE)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetProfileConfig", iRetValue);
                        bOK = false;
                    }
                }*/

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

                // Setup callback
                /*
                if (bOK)
                {
                    Console.WriteLine("\n----- Setup Callback function and event -----\n");

                    fnProfileReceiveMethod = new CLLTI.ProfileReceiveMethod(ProfileEvent);

                    // Register the callback
                    if ((iRetValue = CLLTI.RegisterCallback(hLLT, CLLTI.TCallbackType.STD_CALL, fnProfileReceiveMethod, hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during RegisterCallback", iRetValue);
                        bOK = false;
                    }
                }*/

                // Main tasks in this example
                if (bOK)
                {

                    bOK = SaveAvis_FullSet(sbDevName, SerialNumber);
                }
                if (bOK)
                {
                    bOK = SaveAvis_Quarter(sbDevName, SerialNumber);
                }
                if (bOK)
                {
                    bOK = SaveAvis_Pure(sbDevName, SerialNumber);
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

        static unsafe bool SaveAvis_FullSet(StringBuilder DevName, uint serialNumber)
        {
            int iRetValue;
            string AVI_Filename = "./SaveAvis_FullSet.avi";
            uint profileNumber = 0;
            int bytesWritten = 0;
            int profileSaved = 0;

            // Allocate the profile buffer to the maximal profile size times the profile count
            abyProfileBuffer = new byte[uiResolution * 64];
            byte[] abyTimestamp = new byte[16];

            Console.WriteLine("\n---Demonstrate the SaveProfiles-Routine with FullSet--- \n");

            Console.WriteLine("Register the callback");
            // Set the callback function
            fnProfileReceiveMethod = new ProfileReceiveMethod(ProfileEvent);

            // Register the callback
            if ((iRetValue = CLLTI.RegisterCallback(hLLT, TCallbackType.STD_CALL, fnProfileReceiveMethod, hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during RegisterCallback", iRetValue);
                return false;
            }
            //Set ProfileConfig
            Console.WriteLine("Set Profile config to PROFILE");
            if ((iRetValue = CLLTI.SetProfileConfig(hLLT, TProfileConfig.PROFILE)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetProfileConfig", iRetValue);
                return false;
            }

            //Header
            AviInfo header = new AviInfo();
            header.serial = serialNumber;
            header.rearrangement = 0;
            header.maintenance = 0x00000002;
            header.extended1 = 0xffffffff;
            header.profileConfig = TProfileConfig.PROFILE;
            header.partialProfile.nPointCount = 0;
            header.partialProfile.nPointDataWidth = 0;
            header.partialProfile.nStartPoint = 0;
            header.partialProfile.nStartPointData = 0;
            header.name = DevName.ToString();
            header.version = "2";

            //SetMaxFileSize
            writer.SetMaxFileSize(2000000);
            //Set the amount of profiles for recording
            writer.SetMaxProfileSize(20);
            //Generate avi header
            writer.Open(AVI_Filename, 64, (int)uiResolution, ref header);

            // Start continous profile transmission
            Console.WriteLine("Enable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 1)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return false;
            }

            Console.WriteLine("Write every uneven profile to AviFile");
            while (bProfileReceived < uiNeededProfileCount)
            {
                //Wait until a profile arrives
                if (hProfileEvent.WaitOne(2000) != true)
                {
                    Console.WriteLine("No profile received");
                    return false;
                }

                //Read back profile number
                Buffer.BlockCopy(abyProfileBuffer, (int)(uiResolution * 64 - 16), abyTimestamp, 0, 16);
                profileNumber = DisplayTimestamp(abyTimestamp);
                if ((profileNumber %2) != 0)
                {
                    bytesWritten = writer.AddFrame(ref abyProfileBuffer);
                    
                    //Error Handling
                    if (bytesWritten == 0)
                    {
                        Console.WriteLine("Error during saving!");
                        break;
                    }
                    else if (bytesWritten == -1)
                    {
                        Console.WriteLine("Max filesize reached!");
                        break;
                    }
                    else if (bytesWritten == -2)
                    {
                        Console.WriteLine("Max Profilesize reached!");
                        break;
                    }
                    profileSaved++;
                }
  
            }

            Console.WriteLine("Disable SavingProfiles");
            writer.Close();
            Console.WriteLine(profileSaved + " profiles have been saved!");

            // Stop continous profile transmission
            Console.WriteLine("Disable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return false;
            }

            // De-Register Callback
            if ((iRetValue = CLLTI.RegisterCallback(hLLT, TCallbackType.STD_CALL, null, hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during RegisterCallback", iRetValue);
                return false;
            }

            return true;

        }

        static unsafe bool SaveAvis_Quarter(StringBuilder DevName, uint serialNumber)
        {
            int iRetValue;
            string AVI_Filename = "./SaveAvis_Quarter.avi";
            TPartialProfile partialProfile = new TPartialProfile();
            uint profileNumber = 0;
            int bytesWritten = 0;
            int profileSaved = 0;

            //Reset bProfileReceivedCounter
            bProfileReceived = 0;

            Console.WriteLine("\n---Demonstrate the SaveProfiles-Routine with full resolution and one reflection (X/Z + data)--- \n");

            Console.WriteLine("Register the callback");
            // Set the callback function
            fnProfileReceiveMethod = new ProfileReceiveMethod(ProfileEvent);

            // Register the callback
            if ((iRetValue = CLLTI.RegisterCallback(hLLT, TCallbackType.STD_CALL, fnProfileReceiveMethod, hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during RegisterCallback", iRetValue);
                return false;
            }
            //Set ProfileConfig
            Console.WriteLine("Set Profile config to Partial_Profile");
            if ((iRetValue = CLLTI.SetProfileConfig(hLLT, TProfileConfig.PARTIAL_PROFILE)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetProfileConfig", iRetValue);
                return false;
            }

            // Struct for a partial transfer with the full resolution and only one reflection (like QUARTER_PROFILE)
            partialProfile.nStartPoint = 0; // Transfer starts at point 0 (as row)
            partialProfile.nStartPointData = 0; // Transfer starts at data position 0 (as column)
            partialProfile.nPointCount = uiResolution;  // Transfer size are the full resolution
            partialProfile.nPointDataWidth = 16;    // Transfer size of the transfered data is 16

            if ((iRetValue = CLLTI.SetPartialProfile(hLLT, ref partialProfile)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetPartialProfile", iRetValue);
                return false;
            }

            // Allocate the profile buffer to the maximal profile size times the profile count
            abyProfileBuffer = new byte[uiResolution * partialProfile.nPointDataWidth];
            byte[] abyTimestamp = new byte[16];

            //Header
            AviInfo header = new AviInfo();
            header.serial = serialNumber;
            header.rearrangement = 0;
            header.maintenance = 0x00000002;
            header.extended1 = 0xffffffff;
            header.profileConfig = TProfileConfig.PARTIAL_PROFILE;
            header.partialProfile.nPointCount = partialProfile.nPointCount;
            header.partialProfile.nPointDataWidth = partialProfile.nPointDataWidth;
            header.partialProfile.nStartPoint = partialProfile.nStartPoint;
            header.partialProfile.nStartPointData = partialProfile.nStartPointData;
            header.name = DevName.ToString();
            header.version = "2";

            //SetMaxFileSize
            writer.SetMaxFileSize(2000000);
            //Set the amount of profiles for recording
            writer.SetMaxProfileSize(20);
            //Generate avi header
            writer.Open(AVI_Filename, (int)partialProfile.nPointDataWidth, (int)uiResolution, ref header);

            // Start continous profile transmission
            Console.WriteLine("Enable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 1)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return false;
            }

            Console.WriteLine("Write every uneven profile to AviFile");
            while (bProfileReceived < uiNeededProfileCount)
            {
                //Wait until a profile arrives
                if (hProfileEvent.WaitOne(2000) != true)
                {
                    Console.WriteLine("No profile received");
                    return false;
                }

                //Read back profile number
                Buffer.BlockCopy(abyProfileBuffer, (int)(uiResolution * partialProfile.nPointDataWidth - 16), abyTimestamp, 0, 16);
                profileNumber = DisplayTimestamp(abyTimestamp);
                if ((profileNumber % 2) != 0)
                {
                    bytesWritten = writer.AddFrame(ref abyProfileBuffer);

                    //Error Handling
                    if (bytesWritten == 0)
                    {
                        Console.WriteLine("Error during saving!");
                        break;
                    }
                    else if (bytesWritten == -1)
                    {
                        Console.WriteLine("Max filesize reached!");
                        break;
                    }
                    else if (bytesWritten == -2)
                    {
                        Console.WriteLine("Max Profilesize reached!");
                        break;
                    }
                    profileSaved++;
                }

            }

            Console.WriteLine("Disable SavingProfiles");
            writer.Close();
            Console.WriteLine(profileSaved + " profiles have been saved!");

            // Stop continous profile transmission
            Console.WriteLine("Disable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return false;
            }

            // De-Register Callback
            if ((iRetValue = CLLTI.RegisterCallback(hLLT, TCallbackType.STD_CALL, null, hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during RegisterCallback", iRetValue);
                return false;
            }

            return true;

        }

        static unsafe bool SaveAvis_Pure(StringBuilder DevName, uint serialNumber)
        {
            int iRetValue;
            string AVI_Filename = "./SaveAvis_Pure.avi";
            TPartialProfile partialProfile = new TPartialProfile();
            uint profileNumber = 0;
            int bytesWritten = 0;
            int profileSaved = 0;

            //Reset bProfileReceivedCounter
            bProfileReceived = 0;


            Console.WriteLine("\n---Demonstrate the SaveProfiles-Routine with full resolution and only X/Z values--- \n");

            Console.WriteLine("Register the callback");
            // Set the callback function
            fnProfileReceiveMethod = new ProfileReceiveMethod(ProfileEvent);

            // Register the callback
            if ((iRetValue = CLLTI.RegisterCallback(hLLT, TCallbackType.STD_CALL, fnProfileReceiveMethod, hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during RegisterCallback", iRetValue);
                return false;
            }
            //Set ProfileConfig
            Console.WriteLine("Set Profile config to Partial_Profile");
            if ((iRetValue = CLLTI.SetProfileConfig(hLLT, TProfileConfig.PARTIAL_PROFILE)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetProfileConfig", iRetValue);
                return false;
            }

            // Struct for a partial transfer with the full resolution and only X/Z data (like Pure_PROFILE)
            partialProfile.nStartPoint = 0; // Transfer starts at point 0 (as row)
            partialProfile.nStartPointData = 4; // Transfer starts at data position 4 (as column)
            partialProfile.nPointCount = uiResolution;  // Transfer size are the full resolution
            partialProfile.nPointDataWidth = 4;    // Transfer size of the transfered data is 4

            if ((iRetValue = CLLTI.SetPartialProfile(hLLT, ref partialProfile)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetPartialProfile", iRetValue);
                return false;
            }

            // Allocate the profile buffer to the maximal profile size times the profile count
            abyProfileBuffer = new byte[uiResolution * partialProfile.nPointDataWidth];
            byte[] abyTimestamp = new byte[16];

            //Header
            AviInfo header = new AviInfo();
            header.serial = serialNumber;
            header.rearrangement = 0;
            header.maintenance = 0x00000002;
            header.extended1 = 0xffffffff;
            header.profileConfig = TProfileConfig.PARTIAL_PROFILE;
            header.partialProfile.nPointCount = partialProfile.nPointCount;
            header.partialProfile.nPointDataWidth = partialProfile.nPointDataWidth;
            header.partialProfile.nStartPoint = partialProfile.nStartPoint;
            header.partialProfile.nStartPointData = partialProfile.nStartPointData;
            header.name = DevName.ToString();
            header.version = "2";

            //SetMaxFileSize
            writer.SetMaxFileSize(20000000);
            //Set the amount of profiles for recording
            writer.SetMaxProfileSize(20);
            //Generate avi header
            writer.Open(AVI_Filename, (int)partialProfile.nPointDataWidth, (int)uiResolution, ref header);

            // Start continous profile transmission
            Console.WriteLine("Enable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 1)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return false;
            }

            Console.WriteLine("Write every uneven profile to AviFile");
            while (bProfileReceived < uiNeededProfileCount)
            {
                //Wait until a profile arrives
                if (hProfileEvent.WaitOne(2000) != true)
                {
                    Console.WriteLine("No profile received");
                    return false;
                }

                //Read back profile number
                Buffer.BlockCopy(abyProfileBuffer, (int)(uiResolution * partialProfile.nPointDataWidth - 16), abyTimestamp, 0, 16);
                profileNumber = DisplayTimestamp(abyTimestamp);
                if ((profileNumber % 2) != 0)
                {
                    bytesWritten = writer.AddFrame(ref abyProfileBuffer);

                    //Error Handling
                    if (bytesWritten == 0)
                    {
                        Console.WriteLine("Error during saving!");
                        break;
                    }
                    else if (bytesWritten == -1)
                    {
                        Console.WriteLine("Max filesize reached!");
                        break;
                    }
                    else if (bytesWritten == -2)
                    {
                        Console.WriteLine("Max Profilesize reached!");
                        break;
                    }
                    profileSaved++;
                }

            }

            Console.WriteLine("Disable SavingProfiles");
            writer.Close();
            Console.WriteLine(profileSaved + " profiles have been saved!");

            // Stop continous profile transmission
            Console.WriteLine("Disable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return false;
            }

            // De-Register Callback
            if ((iRetValue = CLLTI.RegisterCallback(hLLT, TCallbackType.STD_CALL, null, hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during RegisterCallback", iRetValue);
                return false;
            }

            return true;

        }

        // Display the timestamp
        static uint DisplayTimestamp(byte[] abyTimestamp)
        {
            double dShutterOpen = 0, dShutterClose = 0;
            uint uiProfileCount = 0;

            //Decode the timestamp
            CLLTI.Timestamp2TimeAndCount(abyTimestamp, ref dShutterOpen, ref dShutterClose, ref uiProfileCount);
            return uiProfileCount;
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
                    fixed (byte* dst = &abyProfileBuffer[0])
                    {
                        memcpy(dst, data, uiSize);
                    }
                    bProfileReceived++;
                //}

                //if (bProfileReceived >= uiNeededProfileCount)
                //{
                    //If the needed profile count is arrived: set the event
                    hProfileEvent.Set();                    
                }
            }
        }
    }
}
