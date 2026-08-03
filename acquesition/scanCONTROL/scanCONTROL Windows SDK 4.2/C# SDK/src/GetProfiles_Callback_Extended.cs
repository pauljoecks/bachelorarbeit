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
    public const int MAX_INTERFACE_COUNT        = 5;
    public const int MAX_RESOULUTIONS           = 6;

    static public uint uiResolution = 0;
    static public uint hLLT = 0;
    static public TScannerType tscanCONTROLType;

    static public byte[] abyProfileBuffer;
	
	static public uint uiReceivedProfileCount = 0;
    static public uint uiNeededProfileCount = 10; // Profile count until event is set
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

      StringBuilder sbExportedConfig = new StringBuilder("lltConfigExport.txt");
      StringBuilder sbDevName = new StringBuilder(100);
      StringBuilder sbVenName = new StringBuilder(100);

      TProfileConfig tpcProfileConfig = new TProfileConfig();
      ProfileReceiveMethod fnProfileReceiveMethod = null;

      uint uiDSP = 0, uiFPGA1 = 0, uiFPGA2 = 0;
      ulong ulMinPacketSize = 0, ulMaxPacketSize = 0;
      uint uiBufferCount = 20, uiMainReflection = 0, uiMaxFileSize = 12800, uiPacketSize = 1024;
      uint uiHeight = 4096, uiWidth = 1280, uiMaxHeight = 0, uiMaxWidth = 0, uiHeart = 2000;

      uint uiCurrentUserMode = 0, uiUserModeCount = 0, uiWorkingUserMode = 7;

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
      if(hLLT != 0)
        Console.WriteLine("CreateLLTDevice OK");
      else
        Console.WriteLine("Error during CreateLLTDevice\n");

      /*
      // Gets the available interfaces from the scanCONTROL-device (SLOWER than GetDeviceInterfacesFast)
      iInterfaceCount = CLLTI.GetDeviceInterfaces(hLLT, auiInterfaces, auiInterfaces.GetLength(0));          
      if(iInterfaceCount == 0)
        Console.WriteLine("There is no scanCONTROL connected");
      else if(iInterfaceCount == 1)
        Console.WriteLine("There is 1 scanCONTROL connected ");        
      else
          Console.WriteLine("There are " + iInterfaceCount + " scanCONTROL's connected");
       */

      iInterfaceCount = 0;

       //Gets the available interfaces from the scanCONTROL-device with the FAST function
       iInterfaceCount = CLLTI.GetDeviceInterfacesFast(hLLT, auiInterfaces, auiInterfaces.GetLength(0));
       if (iInterfaceCount == 0)
           Console.WriteLine("FAST: There is no scanCONTROL connected");
       else if (iInterfaceCount == 1)
           Console.WriteLine("FAST: There is 1 scanCONTROL connected ");
       else
           Console.WriteLine("FAST: There are " + iInterfaceCount + " scanCONTROL's connected");

      if(iInterfaceCount >= 1)
      {
        uint target4 = auiInterfaces[0] & 0x000000FF;
        uint target3 = (auiInterfaces[0] & 0x0000FF00) >> 8;
        uint target2 = (auiInterfaces[0] & 0x00FF0000) >> 16;
        uint target1 = (auiInterfaces[0] & 0xFF000000) >> 24;

        // Set the first IP address detected by GetDeviceInterfacesFast to handle
        Console.WriteLine("Select the device interface: " + target1 + "." + target2 + "." + target3 + "." + target4);
        if((iRetValue = CLLTI.SetDeviceInterface(hLLT, auiInterfaces[0], 0))
            < CLLTI.GENERAL_FUNCTION_OK)
        {
          OnError("Error during SetDeviceInterface", iRetValue);
          bOK = false;
        }

        // Check if correct interface type
        Console.WriteLine("Check if correct Interface");
        if ((iRetValue = CLLTI.GetInterfaceType(hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
        {
            OnError("Error during GetInterfaceType", iRetValue);
            bOK = false;
        }
        else
        {
            Console.WriteLine("This scanCONTROL InterfaceType is: " + Enum.GetName(typeof(TInterfaceType), iRetValue));
        }

        // Get discovery broadcast target (default: broadcast)
        uint target = 0;
        if (bOK)
        {
            Console.WriteLine("Get Discovery Broadcast Target");
            if ((target = CLLTI.GetDiscoveryBroadcastTarget(hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetDiscoveryBroadcastTarget", (int)target);
                bOK = false;
            }
            else
            {
                target4 = target & 0x000000FF;
                target3 = (target & 0x0000FF00) >> 8;
                target2 = (target & 0x00FF0000) >> 16;
                target1 = (target & 0xFF000000) >> 24;
                Console.WriteLine("TargetAddress: " + target1 + ":" + target2 + ":" + target3 + ":" + target4);
            }
        }

        // Set Discovery Broadcast target (this function can limit the Broadcast to a single network adapter; set to default broadcast)
        if (bOK)
        {
            Console.WriteLine("Set Discovery Broadcast Target");
            if ((iRetValue = CLLTI.SetDiscoveryBroadcastTarget(hLLT, 0, 0)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetDiscoveryBroadcastTarget", iRetValue);
                bOK = false;
            }
        }

        if(bOK)
        {
          // Connect to sensor with the device interface set before
          Console.WriteLine("Connecting to scanCONTROL");
          if((iRetValue = CLLTI.Connect(hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
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
            // Read the Firmware Version from scanner
            Console.WriteLine("Get LLT Version");
            if ((iRetValue = CLLTI.GetLLTVersions(hLLT, ref uiDSP, ref uiFPGA1, ref uiFPGA2)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during Get LLT Version", iRetValue);
                bOK = false;
            }
            else
            {
                Console.WriteLine(" - DSP: " + uiDSP + "\n - FPGA1: " + uiFPGA1 + "\n - FPGA2: " + uiFPGA2);
            }
        } 

        if(bOK)
        {
          // Get the scanCONTROL type and check if it is valid
          Console.WriteLine("Get scanCONTROL type");
          if((iRetValue = CLLTI.GetLLTType(hLLT, ref tscanCONTROLType)) < CLLTI.GENERAL_FUNCTION_OK)
          {
            OnError("Error during GetLLTType", iRetValue);
            bOK = false;
          }
    
          if(iRetValue == CLLTI.GENERAL_FUNCTION_DEVICE_NAME_NOT_SUPPORTED)
          {
            Console.WriteLine(" - Can't decode scanCONTROL type. Please contact Micro-Epsilon for a newer version of the LLT.dll.");
          }

          if(tscanCONTROLType >= TScannerType.scanCONTROL27xx_25 && tscanCONTROLType <= TScannerType.scanCONTROL27xx_xxx)
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

        // Set scanner settings to valid parameters for this example (extended)

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
            // Max file size for saving data
            Console.WriteLine("Set MaxFileSize to " + uiMaxFileSize);
            if ((iRetValue = CLLTI.SetMaxFileSize(hLLT, uiMaxFileSize)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetMaxFileSize", iRetValue);
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
            Console.WriteLine("Set ContainerPacketsize to the width " + uiWidth + " and the heigth " + uiHeight);
            if ((iRetValue = CLLTI.SetProfileContainerSize(hLLT, uiWidth, uiHeight)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetProfileContainerSize", iRetValue);
                bOK = false;
            }
        }

        // Time during which the software/scanner must respond until connection timeout
        if (bOK)
        {
            Console.WriteLine("Set EthernetHeartbeatTimeout to " + uiHeart);
            if ((iRetValue = CLLTI.SetEthernetHeartbeatTimeout(hLLT, uiHeart)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetEthernetHeartbeatTimeout", iRetValue);
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
            Console.WriteLine("Set threshold to dynamic 128");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_THRESHOLD, CLLTI.THRESHOLD_BACKGROUND_FILTER | CLLTI.THRESHOLD_VIDEO_FILTER | 
                                                                                        CLLTI.THRESHOLD_DYNAMIC | 128)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_THRESHOLD)", iRetValue);
                bOK = false;
            }
        }

       if (bOK)
        {
            Console.WriteLine("Set processing configuration");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_PROFILE_PROCESSING, CLLTI.PROC_HIGH_RESOLUTION | CLLTI.PROC_CALIBRATION | 
                                                                                                     CLLTI.PROC_MULITREFL_MAXINTENS | CLLTI.PROC_POSTPROCESSING_ON | 
                                                                                                     CLLTI.PROC_FLIP_DISTANCE | CLLTI.PROC_AUTOSHUTTER_ADVANCED)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_PROFILE_PROCESSING)", iRetValue);
                bOK = false;
            }
        }

        if (bOK)
        {
            Console.WriteLine("Set start exposure time to " + uiExposureTime + " and activate automatic exposure time");
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXPOSURE_TIME, uiExposureTime | CLLTI.EXPOSURE_AUTOMATIC)) < CLLTI.GENERAL_FUNCTION_OK)
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

        // Read back scanner parameters

        if (bOK)
        {
            Console.WriteLine("\n----- Get scanCONTROL Parameters -----\n");

            // Get the minimal and maximal valid packet size for this scanner
            Console.WriteLine("Get MinMaxPacketSize ");
            if ((iRetValue = CLLTI.GetMinMaxPacketSize(hLLT, ref ulMinPacketSize, ref ulMaxPacketSize)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetMinMaxPacketSize", iRetValue);
                bOK = false;
            }
            else
            {
                Console.WriteLine(" - Max Packet Size: " + ulMaxPacketSize + "\n - MinPacketSize: " + ulMinPacketSize);
            }
        }

        if (bOK)
        {
            Console.WriteLine("Get Resolution ");
            if ((iRetValue = CLLTI.GetResolution(hLLT, ref uiResolution)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetResolution", iRetValue);
                bOK = false;
            }
            else
            {
                Console.WriteLine(" - Resolution: " + uiResolution);
            }
        }

        if (bOK)
        {
            Console.WriteLine("Get BufferCount ");
            if ((iRetValue = CLLTI.GetBufferCount(hLLT, ref uiBufferCount)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetBufferCount", iRetValue);
                bOK = false;
            }
            else
            {
                Console.WriteLine(" - Buffercount: " + uiBufferCount);
            }
        }

        if (bOK)
        {
            Console.WriteLine("Get MainReflection ");
            if ((iRetValue = CLLTI.GetMainReflection(hLLT, ref uiMainReflection)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetMainReflection", iRetValue);
                bOK = false;
            }
            else
            {
                Console.WriteLine(" - MainReflection: " + uiMainReflection);
            }
        }

        if (bOK)
        {
            Console.WriteLine("Get MaxFileSize ");
            if ((iRetValue = CLLTI.GetMaxFileSize(hLLT, ref uiMaxFileSize)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetMaxFileSize", iRetValue);
                bOK = false;
            }
            else
            {
                Console.WriteLine(" - MaxFileSize: " + uiMaxFileSize);
            }
        }

        if (bOK)
        {
            Console.WriteLine("Get Packetsize ");
            if ((iRetValue = CLLTI.GetPacketSize(hLLT, ref uiPacketSize)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetPacketsize", iRetValue);
                bOK = false;
            }
            else
            {
                Console.WriteLine(" - Packetsize: " + uiPacketSize);
            }
        } 

        if (bOK)
        {
            Console.WriteLine("GetProfileConfig");
            if ((iRetValue = CLLTI.GetProfileConfig(hLLT, ref tpcProfileConfig)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetProfileConfig", iRetValue);
                bOK = false;
            }
            else
            {
                Console.WriteLine(" - TProfile Config: " + tpcProfileConfig);
            }
        }

        if (bOK)
        {
            // Get the max. container size
            Console.WriteLine("GetMaxProfileContainerSize");
            if ((iRetValue = CLLTI.GetMaxProfileContainerSize(hLLT, ref uiMaxWidth, ref uiMaxHeight)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetProfileConfig", iRetValue);
                bOK = false;
            }
            else
            {
                Console.WriteLine(" - Height: " + uiMaxHeight + "\n - Width: " + uiMaxWidth);
            }
        }

        if (bOK)
        {
            Console.WriteLine("GetProfileContainerSize");
            if ((iRetValue = CLLTI.GetProfileContainerSize(hLLT, ref uiWidth, ref uiHeight)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetProfileContainerSize", iRetValue);
                bOK = false;
            }
            else
            {
                Console.WriteLine(" - Height: " + uiHeight + "\n - Width: " + uiWidth);
            }
        }

        if (bOK)
        {
            Console.WriteLine("GetEthernetHeartbeatTimeout");
            if ((iRetValue = CLLTI.GetEthernetHeartbeatTimeout(hLLT, ref uiHeart)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during GetEthernetHeartbeatTimeout", iRetValue);
                bOK = false;
            }
            else
            {
                Console.WriteLine(" - Heartbeat: " + uiHeart);
            }
        }

        if (bOK)
        {
            // Get current usermode
            Console.WriteLine("GetActualUserMode");
            if ((iRetValue = CLLTI.GetActualUserMode(hLLT, ref uiCurrentUserMode, ref uiUserModeCount)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during getting UM", iRetValue);
                bOK = false;
            }
            else
            {
                Console.WriteLine(" - Current UM : " + uiCurrentUserMode + " - Available UMs: " + uiUserModeCount);
            }
        }

        Console.WriteLine("\n----- MISC-----\n");

        if (bOK)
        {
            // Export the complete configuration to a file
            Console.WriteLine("Export LLT Config to " + sbExportedConfig);
            if ((iRetValue = CLLTI.ExportLLTConfig(hLLT, sbExportedConfig)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during exporting Config", iRetValue);
                bOK = false;
            }
        }

        if (bOK)
        {
            // Write settings to usermode
            Console.WriteLine("Write to Usermode 7");
            if ((iRetValue = CLLTI.ReadWriteUserModes(hLLT, 1, uiWorkingUserMode)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during writing UM 7", iRetValue);
                bOK = false;
            }
            System.Threading.Thread.Sleep(100);
        }

        if (bOK)
        {
            // Load settings from usermode
            Console.WriteLine("Load Usermode 7");
            if ((iRetValue = CLLTI.ReadWriteUserModes(hLLT, 0, uiWorkingUserMode)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during loading UM 7", iRetValue);
                bOK = false;
            }
            System.Threading.Thread.Sleep(100);
            
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
        if(bOK)
        {
          Console.WriteLine("\n----- Get profiles with Callback from scanCONTROL -----\n");

          GetProfiles_Callback();
        }        

        if(bConnected)
        {
          Console.WriteLine("\n----- Disconnect from scanCONTROL -----\n");

          // Disconnect from the sensor
          Console.WriteLine("Disconnect the scanCONTROL");
          if((iRetValue = CLLTI.Disconnect(hLLT)) < CLLTI.GENERAL_FUNCTION_OK)
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
      while(true)
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

        // Test the size of profilee
        if (uiProfileDataSize == uiResolution * 64)
            Console.WriteLine("Profile size is OK");
        else
        {
            Console.WriteLine("Profile size is wrong");
            return;
        }

        // Convert profile to x and z values
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
      for(uint i=0; i<uiResolution; i++)
      {
          
        //Prints the X- and Z-values
        iNumberSize =  adValueX[i].ToString().Length;
        Console.Write("\r" + "Profiledata: X = " + adValueX[i].ToString());

        for(; iNumberSize<8; iNumberSize++)
        {
          Console.Write(" ");
        }
        
        iNumberSize =  adValueZ[i].ToString().Length;
        Console.Write(" Z = " + adValueZ[i].ToString());
        
        for(; iNumberSize<8; iNumberSize++)
        {
          Console.Write(" ");
        }

        // Wait a for display
        if(i%8 == 0)
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
      if(CLLTI.TranslateErrorValue(hLLT, iErrorValue, acErrorString, acErrorString.GetLength(0))
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
                if (uiReceivedProfileCount < uiNeededProfileCount)
                {
                    //If the needed profile count not arrived: copy the new Profile in the buffer and increase the recived buffer count
                    uiProfileDataSize = uiSize;
                    //Kopieren des Unmanaged Datenpuffers (data) in die Anwendung
                    fixed (byte* dst = &abyProfileBuffer[uiReceivedProfileCount * uiSize])
                    {
                        memcpy(dst, data, uiSize);
                    }
                    uiReceivedProfileCount++;
                }

                if (uiReceivedProfileCount >= uiNeededProfileCount)
                {
                    //If the needed profile count is arived: set the event
                    hProfileEvent.Set();                    
                }
            }
        }
  }
}
