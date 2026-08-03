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
using System.Runtime.InteropServices;

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
        static public TConvertContainerParameter convertContainerParameter;

        static public uint uiExposureTime = 100;
        static public uint uiIdleTime = 3900;

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

            uint uiBufferCount = 3, uiPacketSize = 320;

            int iInterfaceCount = 0;
 
            int iRetValue;
            bool bOK = true;
            bool isv46 = true;
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
                        string DevName = sbDevName.ToString();
                        isv46 = CheckForFirmware(ref DevName, sbDevName.Capacity);                        
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

                    // Check for Firmware v46
                    if (!isv46)
                    {
                        Console.WriteLine("Trigger container feature not supported - Firmware update is required");
                        bOK = false;
                    }

                    if (bOK)
                    {
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
                }

                // Set scanner settings to valid parameters for this example

                if (bOK)
                {
                    Console.WriteLine("\n----- Set scanCONTROL Parameters -----\n");

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
                    Console.WriteLine("Set Packetsize to " + uiPacketSize);
                    if ((iRetValue = CLLTI.SetPacketSize(hLLT, uiPacketSize)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during SetPacketSize", iRetValue);
                        bOK = false;
                    }
                }

                if (bOK)
                {
                    Console.WriteLine("Set Profile config to Container");
                    if ((iRetValue = CLLTI.SetProfileConfig(hLLT, TProfileConfig.CONTAINER)) < CLLTI.GENERAL_FUNCTION_OK)
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
                    Console.WriteLine("\n----- Trigger for rearranged container -----\n");

                    TriggerContainer();

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
         * Set the sensor to transmit rearranged profile container - in this case 3 profiles with X, Z and the Timestamp
         * This reduces the amount of data which has to be transmitted and the necessary response time of the software
         */
        static void TriggerContainer()
        {
            int iRetValue;
            uint uiFieldCount = 3;    // Number of fields transmitted (TS is one field)
            uint uiProfileCount = 3;  // Number of profiles in one container
            uint uiProfileCounter = 0;
            uint uiInquiry = 0;
            uint uiLostProfiles = 0;
            ushort usValue = 0;
            double dTimeShutterOpen = 0.0;
            double dTimeShutterClose = 0.0;
            bool noContainerReceived = true;

            //Declare array
            double[] adValueX = new double[uiResolution * uiProfileCount];
            double[] adValueZ = new double[uiResolution * uiProfileCount];
            double[] DisplayX = new double[uiResolution];
            double[] DisplayZ = new double[uiResolution];

            // Calculate the bitfield for the resolution (e.g. if Resolution 160 the result must be 7; for 1280 the result must be 10)
            double dTempLog = 1.0 / Math.Log(2.0);
            uint uiResolutionBitField = (uint)Math.Floor((Math.Log((double)uiResolution) * dTempLog) + 0.5);

            // Check if sensor supports the container mode
            if ((iRetValue = CLLTI.GetFeature(hLLT, CLLTI.INQUIRY_FUNCTION_PROFILE_REARRANGEMENT, ref uiInquiry)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetFeature", iRetValue);
                return;
            }
            if ((uiInquiry & 0x80000000) == 0)
            {
                Console.WriteLine("The connected scanCONTROL doesn't support the container mode");
                return;
            }

            //Extract X and Z
            //Insert empty field for timestamp
            //Insert timestamp
            //calculation for the points per profile = Round(Log2(resolution))
            //Extract only 1th reflection
            Console.WriteLine("Set the rearrangement parameter");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_PROFILE_REARRANGEMENT, (CLLTI.CONTAINER_STRIPE_1 | CLLTI.CONTAINER_DATA_Z |
                                                                                                      CLLTI.CONTAINER_DATA_X | CLLTI.CONTAINER_DATA_EMPTYFIELD4TS |
                                                                                                      CLLTI.CONTAINER_DATA_TS | CLLTI.CONTAINER_DATA_LSBF |
                                                                                                      (uiResolutionBitField << 12)))) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature", iRetValue);
                return;
            }

            // Read out the rearrangement parameter
            if ((iRetValue = CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_PROFILE_REARRANGEMENT, ref uiInquiry)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetFeature", iRetValue);
                return;
            }


            // Set the profile container size according to the given profile count
            Console.WriteLine("Set profile container size");
            if ((iRetValue = CLLTI.SetProfileContainerSize(hLLT, 0, uiProfileCount)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetProfileContainerSize", iRetValue);
                return;
            }

            // Wait until all parameters are set before starting the transmission (this can take up to 120ms)
            System.Threading.Thread.Sleep(120);

            // Start continous profile transmission
            Console.WriteLine("Enable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_CONTAINER_MODE, 1)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return;
            }

            //Start triggerung container
            Console.WriteLine("Enable the Container-Trigger");
            if ((iRetValue = CLLTI.ContainerTriggerEnable(hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during Enabling Container-Trigger", iRetValue);
                return;
            }

            // Allocate buffersize according to transmitted data
            byte[] abyContainerBuffer = new byte[uiResolution * 2 * uiFieldCount * uiProfileCount]; // 2* because 1 value has 2 bytes
            byte[] abyTimestamp = new byte[16];

   

            Console.WriteLine("Trigger one container");
            CLLTI.TriggerContainer(hLLT);

            // Trigger one container
            while (noContainerReceived)
            {
                if ((iRetValue = CLLTI.GetActualProfile(hLLT, abyContainerBuffer, abyContainerBuffer.GetLength(0), TProfileConfig.CONTAINER, ref uiLostProfiles)) != abyContainerBuffer.GetLength(0))
                {
                    if (iRetValue == CLLTI.ERROR_PROFTRANS_NO_NEW_PROFILE)
                    {
                        System.Threading.Thread.Sleep((int)(uiIdleTime + uiExposureTime) / 100);
                        noContainerReceived = true;
                    }
                    else
                    {
                        OnError("Error during GetActualProfile", iRetValue);
                        return;
                    }
                    
                }
                else
                {
                    Console.WriteLine("Container received");
                    noContainerReceived = false;
                }
            }

            GCHandle pinnArray = GCHandle.Alloc(abyContainerBuffer, GCHandleType.Pinned);
            GCHandle pinnX = GCHandle.Alloc(adValueX, GCHandleType.Pinned);
            GCHandle pinnZ = GCHandle.Alloc(adValueZ, GCHandleType.Pinned);
            IntPtr ptr_to_buf = pinnArray.AddrOfPinnedObject();
            IntPtr ptr_to_X = pinnX.AddrOfPinnedObject();
            IntPtr ptr_to_Z = pinnZ.AddrOfPinnedObject();


            //collection of information that are needed to extract the necessary informations from the container           
            convertContainerParameter.Container = ptr_to_buf;
            convertContainerParameter.profileRearrangement = uiInquiry;
            convertContainerParameter.numberOfProfilesToExtract = uiProfileCount;
            convertContainerParameter.scanner = (uint)tscanCONTROLType;
            convertContainerParameter.reflectionNumber = 0;
            convertContainerParameter.ConvertToMM = 1;
            convertContainerParameter.ReflectionWidth = IntPtr.Zero;
            convertContainerParameter.MaxIntensity = IntPtr.Zero;
            convertContainerParameter.Threshold = IntPtr.Zero;
            convertContainerParameter.Moment0 = IntPtr.Zero;
            convertContainerParameter.Moment1 = IntPtr.Zero;
            convertContainerParameter.X = ptr_to_X;
            convertContainerParameter.Z = ptr_to_Z;


            // Extract X-/Z-values 
            if ((iRetValue = CLLTI.ConvertContainer2Values(hLLT, convertContainerParameter)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during ConvertContainer2Values", iRetValue);
                return;
            }

            Console.WriteLine("----Extract the X/Z data and Timestamp informations from container ----");
            for (int iProfile = 0; iProfile < uiProfileCount; iProfile++)
            {
                // Extract the 16-byte timestamp from the container buffer into timestamp buffer and display it
                Buffer.BlockCopy(abyContainerBuffer, (int)(2 * (iProfile + 1) * uiResolution * uiFieldCount - 16), abyTimestamp, 0, 16);
                // Extract the X and Z values from each profile
                Buffer.BlockCopy(adValueX, (int)(uiResolution * iProfile * 8), DisplayX, 0, DisplayX.Length * 8);
                Buffer.BlockCopy(adValueZ, (int)(uiResolution * iProfile * 8), DisplayZ, 0, DisplayZ.Length * 8);
                CLLTI.Timestamp2TimeAndCount(abyTimestamp, ref dTimeShutterOpen, ref dTimeShutterClose, ref uiProfileCounter);
                // Display x and z values
                // show only the first four points of each profile --> if you want to show every point, just pass parameter uiResolution instead of 4
                DisplayProfile(DisplayX, DisplayZ, 4, dTimeShutterOpen, dTimeShutterClose, uiProfileCounter);

            }

            pinnArray.Free();
            pinnX.Free();
            pinnZ.Free();

            /*
            // Print the x/z data of the first 4 points of the transmitted profiles
            for (int iProfile = 0; iProfile < uiProfileCount; iProfile++)
            {
                for (int iCurrentField = 0; iCurrentField < 2; iCurrentField++)
                {
                    for (int iCurrentPointByte = 0; iCurrentPointByte < 8; iCurrentPointByte = iCurrentPointByte + 2)
                    {
                        usValue = (ushort)(((abyContainerBuffer[(2 * iProfile * uiResolution * uiFieldCount) + (2 * iCurrentField * uiResolution) + (iCurrentPointByte)]) << 8) + (abyContainerBuffer[(2 * iProfile * uiResolution * uiFieldCount) + (2 * iCurrentField * uiResolution) + (iCurrentPointByte + 1)]));
                        Console.WriteLine("Field: " + (int)(iCurrentField + 1) + " Point: " + (int)(iCurrentPointByte / 2) + ": Value - " + usValue);
                    }
                }
                Buffer.BlockCopy(abyContainerBuffer, (int)(2 * (iProfile + 1) * uiResolution * uiFieldCount) - 16, abyTimestamp, 0, 16);
                CLLTI.Timestamp2TimeAndCount(abyTimestamp, ref dTimeShutterOpen, ref dTimeShutterClose, ref uiProfileCounter);
                Console.WriteLine("Profile Counter: " + uiProfileCounter);
            }*/

            // Stop continous profile transmission
            Console.WriteLine("Disable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_CONTAINER_MODE, 0)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return;
            }

            //Stop Triggerung Container
            Console.WriteLine("Disable Container-Trigger");
            if ((iRetValue = CLLTI.ContainerTriggerDisable(hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during Disabling Container-Trigger", iRetValue);
                return;
            }
            
        }

        //Check if the correct firmware is used for container trigger
        static bool CheckForFirmware (ref string DeviceName, int size)
        {
            int found = DeviceName.IndexOf("v");
            string Firmware = DeviceName.Substring(found + 1, 2);
            int used_Firmware = Convert.ToInt32(Firmware);
            int req_Firmware = 46;

            //Check if Firmware >= 46 is used
            if (used_Firmware >= req_Firmware)
            {
                return true;
            }
            else
            {
                return false;
            }
            
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

        // Display the X/Z-Data of one profile
        static void DisplayProfile(double[] adValueX, double[] adValueZ, uint uiResolution, double shutterOpen, double shutterClose, uint counter)
        {
            int iNumberSize = 0;
            Console.WriteLine("\r" + "Show the X/Z points from ProfileNumber: " + counter + " and the ShutterOpen: " + shutterOpen + " ShutterClose: " + shutterClose + " Time");
            for (uint i = 0; i < uiResolution; i++)
            {

                //Prints the X- and Z-values
                iNumberSize = adValueX[i].ToString().Length;
                Console.Write("Profiledata: X = " + adValueX[i].ToString());

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
                Console.WriteLine("");
            }
            Console.WriteLine("");
        }
    }
}
