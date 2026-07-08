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
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.IO;

namespace MEScanControl
{
    class CScanCONTROLSample
    {
        /* Global variables */
        public const int MAX_INTERFACE_COUNT = 5;
        public const int MAX_RESOULUTIONS = 6;
        static public uint uiResolution = 0;
        static public uint hLLT = 0;
        static public bool isCompressedProfile = false;
        static public TScannerType tscanCONTROLType;

        static public byte[] abyProfileBuffer;

        static public uint bProfileReceived = 0;
        static public uint uiNeededProfileCount = 10;
        static public uint uiProfileDataSize = 0;

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

                if (bOK)
                {
                    Console.WriteLine("Check if compressed profile transmission is active");
                    UInt32 maintenance = 0;
                    if ((iRetValue = CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_MAINTENANCE,  ref maintenance)) < CLLTI.GENERAL_FUNCTION_OK)
                    {
                        OnError("Error during GetFeature (FEATURE_FUNCTION_MAINTENANCE)", iRetValue);
                        bOK = false;
                    }
                    else
                    {
                        isCompressedProfile = Convert.ToBoolean(maintenance & 0x1);
                        Console.WriteLine("Compressed: " + isCompressedProfile);
                    }
                    
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

                // Setup callback
                if (bOK)
                {
                    Console.WriteLine("\n----- Setup Callback function and event -----\n");

                    Console.WriteLine("Register the callback");
                    // Set the callback function
                    fnProfileReceiveMethod = new ProfileReceiveMethod(ProfileEvent);

                    // Register the callback
                    if ((iRetValue = CLLTI.RegisterCallback(hLLT, TCallbackType.STD_CALL, fnProfileReceiveMethod, hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
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
         * Evalute reveived profiles via callback function
         */

        static unsafe void GetProfiles_Callback()
        {
            int iRetValue;
            double offset = 85.0;
            double scaling = 0.001;
            double[] adValueX = new double[uiResolution];
            double[] adValueZ = new double[uiResolution];
            uint[] m_vuiBeadResults = new uint[uiResolution];
            uint[] m_vucModuleResult = new uint[uiResolution];
            byte[] m_vucModuleResultBuffer = new byte[uiResolution * 4];

            // Define struct for ConvertProfile2ModuleResult
            TPartialProfile tpartialProfile = new TPartialProfile();
            tpartialProfile.nStartPoint = 0;
            tpartialProfile.nStartPointData = 0;
            tpartialProfile.nPointDataWidth = 64;
            tpartialProfile.nPointCount = uiResolution;


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

            if ((iRetValue = CLLTI.ConvertProfile2ModuleResult(hLLT, abyProfileBuffer, (uint)abyProfileBuffer.Length, m_vucModuleResultBuffer, (uint)m_vucModuleResultBuffer.Length, ref tpartialProfile)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during ConvertingProfile2ModuleResult", iRetValue);
                return;
            }

            //Convert m_vucModuleResultBuffer to an unsigned int Buffer
            //Data format: little endian
            for (int i =0; i< uiResolution; i++)
            {
                m_vucModuleResult[i] = (((uint)m_vucModuleResultBuffer[i * 4 + 3]) << 24) + 
                    (((uint)m_vucModuleResultBuffer[i * 4 + 2]) << 16) + 
                    (((uint)m_vucModuleResultBuffer[i * 4 + 1]) << 8) + 
                    (uint)m_vucModuleResultBuffer[i * 4];
            }

            Console.WriteLine("Get appended results");

            fixed (uint* vucModuleResult = &m_vucModuleResult[0])
            {
                iRetValue = GetAppendedResults(vucModuleResult, iRetValue, false, offset, scaling);
            }

            // Stop continous profile transmission
            Console.WriteLine("Disable the measurement");
            if ((iRetValue = CLLTI.TransferProfiles(hLLT, TTransferProfileType.NORMAL_TRANSFER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during TransferProfiles", iRetValue);
                return;
            }
        }
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

        //Returns the appended module results
        //@param *vucModuleResult: post processing results
        //@param nModuleResultSize: size of post processing results
        //@param littleEndian: set to true for PURE_PROFILE transmission
        //@param offset: Sensor offset
        //@param scaling: Sensor scaling
        static unsafe int GetAppendedResults(uint* vucModuleResult, int nModuleResultSize, bool littleEndian, double offset, double scaling)
        {
            
            int idx = 0;
            uint length = 0;
            int i, j;
            uint[] dataArr = new uint[15];         
            List<List<uint>> vec = new List<List<uint>>();
            for (i = 0; i<= nModuleResultSize; i++)
            {
                vec.Add(new List<uint>());
            }
            List<uint> validHeaders = new List<uint>() { 2, 4, 6, 7, 11, 13, 14, 15, 128, 129, 130 };

            // Step 1: collect Data into vector of arrays
            for (i = 0; i < nModuleResultSize; i++)
            {
                
                if (!littleEndian) 
                {

                    if (((vucModuleResult[i] >> 24) & 0xFF) == 131) // header must be 131
                    {

                        length = (uint)(vucModuleResult[i] & 0x000000FF);
                        for (j = i + 2; j < i + length; j++)
                        {

                            // Get components of measurement value
                            dataArr[0] = ((vucModuleResult[j] & 0xFC000000) >> 26); // type

                            dataArr[1] = (((vucModuleResult[j] & 0x02000000) >> 25)); // description_via_value
                            dataArr[2] = ((vucModuleResult[j] & 0x01000000) >> 24); // description_graphical
                            dataArr[3] = ((vucModuleResult[j] & 0x00800000) >> 23); // length_16_32
                            dataArr[4] = ((vucModuleResult[j] & 0x00400000) >> 22); // upper_lower
                            dataArr[5] = ((vucModuleResult[j] & 0x00200000) >> 21); // mv_valid
                            dataArr[6] = ((vucModuleResult[j] & 0x00100000) >> 20); // mv_name

                            dataArr[7] = ((vucModuleResult[j] & 0x00080000) >> 19); // mv_output
                            if (Convert.ToBoolean(dataArr[1]))
                            { // description via value
                                dataArr[8] = (vucModuleResult[j] & 0x0007FF80) >> 7; // mv_data

                            }
                            else
                            { // description via pointer
                                dataArr[8] = vucModuleResult[(vucModuleResult[j] & 0x0007FF80) >> 7]; // mv_data     

                            }
                            dataArr[9] = ((vucModuleResult[j] & 0x00000040) >> 6); // mask_active 
                            dataArr[10] = ((vucModuleResult[j] & 0x00000020) >> 5); // mv_not_show_num
                            dataArr[11] = ((vucModuleResult[j] & 0x00000010) >> 4); // mv_OK_NOK_available
                            dataArr[12] = 0; // Reservation for OK/NOK
                            dataArr[13] = (vucModuleResult[j] & 0x0000000F); // mv_len_description
                            if (dataArr[13] == 2)
                            { // mv_len_description
                                j++;
                                dataArr[14] = vucModuleResult[j]; // mv_mask
                            }
                            // append to data liste                          
                            vec[j].AddRange(dataArr);

                            // increase number of detected values
                            idx++;
                        }
                        break;
                    }
                    else if (validHeaders.Contains((vucModuleResult[i] >> 24) & 0xFF)) // header valid
                    {
                        // Add length of result block to i to skip results of current module
                        i += (int)(vucModuleResult[i] & 0x000000FF) - 1;
                    }
                    else if ((vucModuleResult[i]) == 0)
                    {
                        // Queue End
                        Console.WriteLine("No results appended");
                        break;
                    }
                }
                else
                {
                    Console.WriteLine("Module results in little endian order - conversion example for big endian only!");
                    break;
                }
            }
            

            int Count = (int)(i + length);


            // Step 2: Add OK/NOK to array if available
            int oknok_counter = 0;
            
            for (int s = i + 2; s < Count; s++)
            {
                try
                {

                    if (Convert.ToBoolean(vec[s][11]))
                    { // OK/NOK available
                      // Look for OK/NOK vector

                        if (vec[(Count - 1)][0] == 30)
                        { // Type OK/NOK
                            vec[s][12] = (uint)(vec[(Count - 1)][8] & (1 << oknok_counter)) >> oknok_counter;

                            oknok_counter++;
                        }
                    }
                }
                catch (System.ArgumentOutOfRangeException)
                {

                }
            }
            

            for (i = i+2; i < Count;i++)
            {
                
                try
                {
                    // Assign array values to variables
                    uint type = vec[(i)][0];
                    bool description_via_value = Convert.ToBoolean(vec[i][1]);
                    bool description_graphical = Convert.ToBoolean(vec[i][2]);
                    bool length_16_32 = Convert.ToBoolean(vec[i][3]);
                    bool upper_lower = Convert.ToBoolean(vec[i][4]);
                    bool mv_valid = Convert.ToBoolean(vec[i][5]);
                    bool mv_name = Convert.ToBoolean(vec[i][6]);
                    bool mv_output = Convert.ToBoolean(vec[i][7]);
                    uint mv_data = vec[i][8];
                    bool mask_active = Convert.ToBoolean(vec[i][9]);
                    bool mv_not_show_num = Convert.ToBoolean(vec[i][10]);
                    bool mv_OK_NOK_available = Convert.ToBoolean(vec[i][11]);
                    bool mv_OK_NOK = Convert.ToBoolean(vec[i][12]);
                    uint mv_len_description = vec[i][13];
                    uint mv_mask = vec[i][14];

                    // Convert measurement value according to type:

                    switch (type)
                    {
                        case 1:
                            Console.Write("X: ");
                            double x;
                            if (length_16_32)
                            { //32 bit length
                                Console.Write("(32bit): ");
                                x = (int)(mv_data - 32768) * scaling;
                            }
                            else
                            { //16 Bit length
                                if (upper_lower)
                                { // x in lower 16 bit
                                    Console.Write("(16bit lower): ");
                                    x = (short)((mv_data & 0xFFFF) - 32768) * scaling;
                                }
                                else
                                { // x in upper 16 bit
                                    Console.Write("(16bit upper): ");
                                    x = (short)(((mv_data & 0xFFFF0000) >> 16) - 32768) * scaling;
                                }
                            }

                            Console.Write(x);
                            if (mv_OK_NOK_available)
                            {
                                Console.Write(" (NOK/OK: " + mv_OK_NOK + ")");
                            }
                            Console.Write("\n");
                            break;
                        case 2:
                            Console.Write("Z: ");
                            double z;
                            if (length_16_32)
                            { //32 bit length
                                Console.Write("(32bit): ");
                                z = (int)(mv_data - 32768) * scaling + offset;
                            }
                            else
                            { //16 Bit length
                                if (upper_lower)
                                { // z in lower 16 bit
                                    Console.Write("(16bit lower): ");
                                    z = (short)((mv_data & 0xFFFF) - 32768) * scaling + offset;
                                }
                                else
                                { // z in upper 16 bit
                                    Console.Write("(16bit upper): ");
                                    z = (short)(((mv_data & 0xFFFF0000) >> 16) - 32768) * scaling + offset;
                                }
                            }
                            Console.Write(z);
                            if (mv_OK_NOK_available)
                            {
                                Console.Write(" (NOK/OK: " + mv_OK_NOK + ")");
                            }
                            Console.Write("\n");
                            break;
                        case 3:
                            Console.Write("Binary: ");
                            uint bin;
                            if (length_16_32)
                            { //32 bit length
                                if (mask_active)
                                {
                                    bin = mv_data & mv_mask;
                                }
                                else
                                {
                                    bin = mv_data;
                                }
                            }
                            else
                            { //16 Bit length
                                if (upper_lower)
                                { // bin in lower 16 bit
                                    bin = mv_data & 0xFFFF;
                                }
                                else
                                { // bin in upper 16 bit
                                    bin = (mv_data & 0xFFFF0000) >> 16;
                                }
                            }
                            Console.Write(bin);
                            if (mv_OK_NOK_available)
                            {
                                Console.Write(" (NOK/OK: " + mv_OK_NOK + ")");
                            }
                            Console.Write("\n");
                            break;

                        case 4:
                            Console.Write("Integer: ");
                            uint intvalue = 0;
                            if (mask_active)
                            {
                                Console.Write("(mask): ");
                                intvalue = (mv_data & mv_mask);
                                //if (!Convert.ToBoolean((mv_mask & 0xFFFF)))
                                //{ // Temperature is in upper 16 Bit
                                //    intvalue = intvalue >> 16;
                                //}

                                if (mv_mask == 0xFFF0000)
                                { // temperature
                                    intvalue = intvalue >> 16;
                                }
                                else if (mv_mask == 0x10000000)
                                { // laser state
                                    intvalue = intvalue >> 28;
                                }
                                else
                                {
                                    ; // no shift necessary for user mode and profile number
                                }

                            }
                            else
                            {
                                if (length_16_32)
                                { // 32 bit length
                                    Console.Write("(32bit): ");
                                    //Console.Write((decimal)mv_data + "\n");
                                    intvalue = mv_data;
                                }
                                else
                                { // 16 bit length
                                    if (upper_lower)
                                    { // int in lower 16 bit
                                        Console.Write("(16bit lower): ");
                                        intvalue = mv_data & 0xFFFF;
                                    }
                                    else
                                    { // int in upper 16 bit
                                        Console.Write("(16bit upper): ");
                                        intvalue = (mv_data & 0xFFFF0000) >> 16;
                                    }
                                }
                            }
                            Console.Write((decimal)intvalue);
                            if (mv_OK_NOK_available)
                            {
                                Console.Write(" (NOK/OK: " + mv_OK_NOK + ")");
                            }
                            Console.Write("\n");
                            break;

                        case 5:
                            Console.Write("Distance: ");
                            double distance;
                            if (length_16_32)
                            { //32 bit length
                                Console.Write("(32bit): ");
                                distance = (int)mv_data * scaling;
                            }
                            else
                            { //16 Bit length
                                if (upper_lower)
                                { // distance in lower 16 bit
                                    Console.Write("(16bit lower): ");
                                    distance = (short)(mv_data & 0xFFFF) * scaling;
                                }
                                else
                                { // distance in upper 16 bit
                                    Console.Write("(16bit upper): ");
                                    distance = (short)((mv_data & 0xFFFF0000) >> 16) * scaling;
                                }
                            }
                            Console.Write(distance);
                            if (mv_OK_NOK_available)
                            {
                                Console.Write(" (NOK/OK: " + mv_OK_NOK + ")");
                            }
                            Console.Write("\n");
                            break;
                        case 6:
                            Console.Write("Angle: ");
                            double angle;
                            if (length_16_32)
                            { //32 bit length
                                Console.Write("(32bit): ");
                                angle = (int)mv_data * 0.01;
                            }
                            else
                            { //16 Bit length
                                if (upper_lower)
                                { // angle in lower 16 bit
                                    Console.Write("(16bit lower): ");
                                    angle = (short)(mv_data & 0xFFFF) * 0.01;
                                }
                                else
                                { // angle in upper 16 bit
                                    Console.Write("(16bit upper): ");
                                    angle = (short)((mv_data & 0xFFFF0000) >> 16) * 0.01;
                                }
                            }
                            Console.Write(angle);
                            if (mv_OK_NOK_available)
                            {
                                Console.Write(" (NOK/OK: " + mv_OK_NOK + ")");
                            }
                            Console.Write("\n");
                            break;
                        case 7:
                            Console.Write("Area: ");
                            double area;
                            area = (int)mv_data * scaling * scaling;
                            Console.Write(area);
                            if (mv_OK_NOK_available)
                            {
                                Console.Write(" (NOK/OK: " + mv_OK_NOK + ")");
                            }
                            Console.Write("\n");
                            break;

                        case 8:
                            Console.Write("Point: ");

                            if (length_16_32)
                            { //32 bit length
                                Console.Write("(32bit): ");
                                uint ptr_x = (mv_mask & 0xFFF00000) >> 20;
                                x = (int)(vucModuleResult[ptr_x] - 32768) * scaling;
                                uint ptr_z = (mv_mask & 0xFFF0) >> 8;
                                z = (int)(vucModuleResult[ptr_z] - 32768) * scaling + offset;
                            }
                            else
                            { //16 Bit length
                                Console.Write("(16bit): ");
                                x = (int)(((mv_data & 0xFFFF0000) >> 16) - 32768) * scaling;
                                z = (int)((mv_data & 0xFFFF) - 32768) * scaling + offset;
                            }
                            Console.Write(x + " , " + z);
                            if (mv_OK_NOK_available)
                            {
                                Console.Write(" (NOK/OK: " + mv_OK_NOK + ")");
                            }
                            Console.Write("\n");
                            break;

                        case 9:
                            Console.Write("Sigma: ");
                            double sigma;
                            if (length_16_32)
                            { //32 bit length
                                Console.Write("(32bit): ");
                                sigma = (int)mv_data * scaling;
                            }
                            else
                            { //16 Bit length
                                if (upper_lower)
                                { // sigma in lower 16 bit
                                    Console.Write("(16bit lower): ");
                                    sigma = (int)(mv_data & 0xFFFF) * scaling;
                                }
                                else
                                { // sigma in upper 16 bit
                                    Console.Write("(16bit upper): ");
                                    sigma = (int)((mv_data & 0xFFFF0000) >> 16) * scaling;
                                    
                                }
                            }
                            Console.Write(sigma);
                            if (mv_OK_NOK_available)
                            {
                                Console.Write(" (NOK/OK: " + mv_OK_NOK + ")");
                            }
                            Console.Write("\n");
                            break;
                        case 10:
                            Console.Write("Text: ");
                            char[] text = new char[4];
                            if (length_16_32)
                            { //32 bit length
                                Console.Write("(32bit): ");
                                text[0] = Convert.ToChar((mv_data >> 24) & 0xFF);
                                text[1] = Convert.ToChar((mv_data >> 16) & 0xFF);
                                text[2] = Convert.ToChar((mv_data >> 8) & 0xFF);
                                text[3] = Convert.ToChar(mv_data & 0xFF);
                            }
                            else
                            { //16 Bit length
                                if (upper_lower)
                                { // text in lower 16 bit
                                    Console.Write("(16bit lower): ");
                                    text[0] = Convert.ToChar((mv_data >> 8) & 0xFF);
                                    text[1] = Convert.ToChar(mv_data & 0xFF);
                                }
                                else
                                { // text in upper 16 bit
                                    Console.Write("(16bit upper): ");
                                    text[0] = Convert.ToChar((mv_data >> 24) & 0xFF);
                                    text[1] = Convert.ToChar((mv_data >> 16) & 0xFF);
                                }
                            }
                            foreach (char chr in text)
                                Console.Write(chr);
                            Console.Write("\n");
                            break;
                        case 30:
                            Console.Write("OK/NOK: ");
                            if (length_16_32)
                            { // 32 bit length
                                Console.Write("(32bit): ");
                                Console.Write((decimal)(mv_data & 0x000000FF) + "\n");
                            }
                            else
                            { // 16 bit length
                                if (upper_lower)
                                { // int in lower 16 bit
                                    Console.Write("(16bit lower): ");
                                    Console.Write((decimal)(mv_data & 0xFFFF) + "\n");
                                }
                                else
                                { // int in upper 16 bit
                                    Console.Write("(16bit upper): ");
                                    Console.Write((decimal)(mv_data & 0xFFFF0000) + "\n");
                                }
                            }
                            break;
                        default: Console.WriteLine("Unknown: (" + type + ") \n"); break;
                    }
                }
                catch (System.ArgumentOutOfRangeException)
                {
                    
                }
            }
            Console.WriteLine ("\n");
            return idx;
        }

    }
}

