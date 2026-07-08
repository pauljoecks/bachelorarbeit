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
 * Author: Daniel Rauch <daniel.rauch@micro-epsilon.de>
 */

using System;
using System.Text;

namespace MEScanControl
{
  class CScanCONTROLSample
  {
    public const int MAX_INTERFACE_COUNT        = 5;
    public const int MAX_RESOULUTIONS           = 6;

    static public uint uiResolution = 0;
    static public uint hLLT = 0;
    static public CLLTI.TScannerType tscanCONTROLType;

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

      uint uiBufferCount = 20, uiMainReflection = 0, uiPacketSize = 1024 , uiFirewireConnectionSpeed = 100;
        
      int iInterfaceCount = 0;
      uint uiShutterTime = 100;
      uint uiIdleTime = 900;
      int iRetValue;
      bool bOK = true;
      bool bConnected = false;
      ConsoleKeyInfo cki;

      hLLT = 0;
      uiResolution = 0;

      Console.WriteLine("----- Connect to scanCONTROL -----\n");

      //Create a Firewire Device -> returns handle to LLT device
      hLLT = CLLTI.CreateLLTFirewire();
      // or
      //hLLT = CLLTI.CreateLLTDevice(CLLTI.TInterfaceType.INTF_TYPE_FIREWIRE);
      if(hLLT != 0)
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

      if(iInterfaceCount >= 1)
      {
        // Set the first Firewire node detected by GetDeviceInterfacesFast to handle
        if((iRetValue = CLLTI.SetDeviceInterface(hLLT, auiInterfaces[0], 0)) < CLLTI.GENERAL_FUNCTION_OK)
        {
          OnError("Error during SetDeviceInterface", iRetValue);
          bOK = false;
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

          if(tscanCONTROLType >= CLLTI.TScannerType.scanCONTROL28xx_25 && tscanCONTROLType <= CLLTI.TScannerType.scanCONTROL28xx_xxx)
          {
              Console.WriteLine(" - The scanCONTROL is a scanCONTROL28xx");
          }
          else if(tscanCONTROLType >= CLLTI.TScannerType.scanCONTROL27xx_25 && tscanCONTROLType <= CLLTI.TScannerType.scanCONTROL27xx_xxx)
          {
              Console.WriteLine(" - The scanCONTROL is a scanCONTROL27xx");
          }
          else if (tscanCONTROLType >= CLLTI.TScannerType.scanCONTROL26xx_25 && tscanCONTROLType <= CLLTI.TScannerType.scanCONTROL26xx_xxx)
          {
              Console.WriteLine(" - The scanCONTROL is a scanCONTROL26xx");
          }
          else if (tscanCONTROLType >= CLLTI.TScannerType.scanCONTROL29xx_25 && tscanCONTROLType <= CLLTI.TScannerType.scanCONTROL29xx_xxx)
          {
              Console.WriteLine(" - The scanCONTROL is a scanCONTROL29xx");
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
            Console.WriteLine("Set FirewireConnectionSpeed to " + uiFirewireConnectionSpeed);
            if ((iRetValue = CLLTI.SetFirewireConnectionSpeed(hLLT, uiFirewireConnectionSpeed)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFirewireConnectionSpeed", iRetValue);
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
            if ((iRetValue = CLLTI.SetProfileConfig(hLLT, CLLTI.TProfileConfig.PROFILE)) < CLLTI.GENERAL_FUNCTION_OK)
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
            Console.WriteLine("Set shutter time to " + uiShutterTime);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_SHUTTERTIME, uiShutterTime)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_SHUTTERTIME)", iRetValue);
                bOK = false;
            }
        }

        if (bOK)
        {
            Console.WriteLine("Set idle time to " + uiIdleTime);
            if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_IDLETIME, uiIdleTime)) < CLLTI.GENERAL_FUNCTION_OK)
            {
                OnError("Error during SetFeature(FEATURE_FUNCTION_IDLETIME)", iRetValue);
                bOK = false;
            }
        }

        // Main tasks in this example
        if(bOK)
        {
          Console.WriteLine("\n----- Poll from scanCONTROL via Firewire -----\n");

          GetProfiles_Poll();
        }

        Console.WriteLine("\n----- Disconnect from scanCONTROL -----\n");

        if(bConnected)
        {
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
    static void GetProfiles_Poll()
    {
      int iRetValue;
      uint uiLostProfiles = 0;
      double[] adValueX = new double[uiResolution];
      double[] adValueZ = new double[uiResolution];

      // Allocate buffer for partial profile (PURE_PROFILE)
      byte[] abyProfileBuffer = new byte[uiResolution*4+16];
      byte[] abyTimestamp = new byte[16];     

      // Start continous profile transmission
      Console.WriteLine("Enable the measurement");
      if((iRetValue = CLLTI.TransferProfiles(hLLT, CLLTI.TTransferProfileType.NORMAL_TRANSFER, 1)) < CLLTI.GENERAL_FUNCTION_OK)
      {
        OnError("Error during TransferProfiles", iRetValue);
        return;
      }

      //Sleep for a while to warm up the transfer
      System.Threading.Thread.Sleep(100); 

       /*
        * This shows how to get 1 Profile in polling mode with PURE_PROFILE config, which means only X/Z-Data and the Timestamp is evaluated.
        * To see how to get more profiles with the full profile config, see the Ethernet Poll example!
        */

      // Get the next transmitted partial profile
      if((iRetValue = CLLTI.GetActualProfile(hLLT, abyProfileBuffer, abyProfileBuffer.GetLength(0), CLLTI.TProfileConfig.PURE_PROFILE, ref uiLostProfiles))
                                           != abyProfileBuffer.GetLength(0))
      {
        OnError("Error during GetActualProfile", iRetValue);
        return;
      }
      Console.WriteLine("Profile received");

      // Convert partial profile to x and z values
      Console.WriteLine("Converting of profile data from the first reflection");
      iRetValue = CLLTI.ConvertProfile2Values(hLLT, abyProfileBuffer, uiResolution, CLLTI.TProfileConfig.PURE_PROFILE, tscanCONTROLType,
        0, 1, null, null, null, adValueX, adValueZ, null, null);
      if(((iRetValue & CLLTI.CONVERT_X) == 0) || ((iRetValue & CLLTI.CONVERT_Z) == 0))
      {
        OnError("Error during Converting of profile data", iRetValue);
        return;
      }

      // Display x and z values
      DisplayProfile(adValueX, adValueZ, uiResolution);
      
      // Extract the 16-byte timestamp from the profile buffer into timestamp buffer and display it      
      Buffer.BlockCopy(abyProfileBuffer, 4 * (int)uiResolution - 16, abyTimestamp, 0, 16);
      DisplayTimestamp(abyTimestamp);

      // Stop continous profile transmission
      Console.WriteLine("Disable the measurement");
      if((iRetValue = CLLTI.TransferProfiles(hLLT, CLLTI.TTransferProfileType.NORMAL_TRANSFER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
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

        //Somtimes wait a short time (only for display)
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
  }
}
