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
    public const int MAX_INTERFACE_COUNT        = 5;
    public const int MAX_RESOULUTIONS           = 6;

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
        if(bOK)
        {
          Console.WriteLine("\n----- Set Peak Filter -----\n");

          SetPeakFilters();
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
       * Set Extra Parameters - peak filter, free measuring field
       */ 
    static void SetPeakFilters()
    {
      int iRetValue = 0;

      // set the desired PeakFilter values

      ushort min_width = 2;
      ushort max_width = 256;
      ushort min_intensity = 0;
      ushort max_intensity = 1023;

      /*
      // Since LLT.dll version 3.7.x.x & scanCONTROL firmware v43 this method is prefered 
      // Readout of currently set values also possible with GetFeature
      
      // Set width
      if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_PEAKFILTER_WIDTH, (max_width << 16) + min_width)) < CLLTI.GENERAL_FUNCTION_OK)
      {
	      OnError("Error during setting the free measuring field", iRetValue);
          return;
      }

      // Set height
      if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_PEAKFILTER_HEIGHT, (max_intensity << 16) + min_intensity)) < CLLTI.GENERAL_FUNCTION_OK)
      {
	      OnError("Error during setting the free measuring field", iRetValue);
          return;
      }

      // Activate settings
      if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
      {
	      OnError("Error during setting the free measuring field", iRetValue);
          return;
      }
      */

      // Write PeakFilter settings to sensor (legacy mode)
      Console.WriteLine("Write Peak filter:\n - Min width: " + min_width + "\n - Max width: " + max_width + "\n - Min intensity: " + min_intensity + "\n - Max intensity: " + max_intensity);  
      if ((iRetValue = SetPeakValues(min_width, max_width, min_intensity, max_intensity)) < CLLTI.GENERAL_FUNCTION_OK)
      {
	      OnError("Error during setting peak values", iRetValue);
      }

      // set the desired free measuring field

      ushort start_z = 20000;
      ushort size_z = 25000;
      ushort start_x = 20000;
      ushort size_x = 25000;

      // Write free measuring field settings to sensor
      Console.WriteLine("Write free measuring field:\n - Start z: " + start_z + "\n - Size z: " + size_z + "\n - Start x: " + start_x + "\n - Size x: " + size_x); 
      // Enable the free measuring field
      if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_ROI1_PRESET, CLLTI.MEASFIELD_ACTIVATE_FREE)) < CLLTI.GENERAL_FUNCTION_OK)
      {
	      OnError("Error during setting the free measuring field", iRetValue);
          return;
      }

      /*
      // Since LLT.dll version 3.7.x.x & scanCONTROL firmware v43 this method is prefered 
      // Readout of currently set values also possible with GetFeature
      
      // Set X range
      if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_FREE_MEASURINGFIELD_X, (start_x << 16) + size_x)) < CLLTI.GENERAL_FUNCTION_OK)
      {
	      OnError("Error during setting the free measuring field", iRetValue);
          return;
      }

      // Set Z range
      if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_FREE_MEASURINGFIELD_Z, (start_z << 16) + size_z)) < CLLTI.GENERAL_FUNCTION_OK)
      {
	      OnError("Error during setting the free measuring field", iRetValue);
          return;
      }

      // Activate settings
      if ((iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, 0)) < CLLTI.GENERAL_FUNCTION_OK)
      {
	      OnError("Error during setting the free measuring field", iRetValue);
          return;
      }
      */

      // Set the values (legacy mode)
      if ((iRetValue = SetFreeMeasuringFieldValues(start_z, size_z, start_x, size_x)) < CLLTI.GENERAL_FUNCTION_OK)
      {
	      OnError("Error during setting the free measuring field", iRetValue);
          return;
      }
    }

    // Set PeakFilter values
    static int SetPeakValues(ushort min_width, ushort max_width, ushort min_intensity, ushort max_intensity)
    {
	    reset_command_list();
	    write_value(max_width);
	    write_value(min_width);
	    write_value(max_intensity);
	    write_value(min_intensity);
	    end_command_list();

	    return CLLTI.GENERAL_FUNCTION_OK;
    }

    // Set free measuring field
    static int SetFreeMeasuringFieldValues(ushort start_z, ushort size_z, ushort start_x, ushort size_x)
    {
	    reset_command_list();
	    write_command(2, 8);
	    write_value(start_z);
	    write_value(size_z);
	    write_value(start_x);
	    write_value(size_x);
	    end_command_list();

	    return CLLTI.GENERAL_FUNCTION_OK;
    }

    // Set dynamic measuring field tracking
    static int SetDynamicMeasuringFieldTrackingValues(ushort div_x, ushort div_z, ushort multi_x, ushort multi_z)
    {
	    reset_command_list();
	    write_command(2, 16);
	    write_value(div_x);
	    write_value(div_z);
	    write_value(multi_x);
	    write_value(multi_z);
	    end_command_list();

	    return CLLTI.GENERAL_FUNCTION_OK;
    }

    // Write command for sequenciell register
    static void write_command(uint command, uint data)
    {
      CLLTI.SetFeature(hLLT , CLLTI.FEATURE_FUNCTION_EXTRA_PARAMETER, (uint)(command << 9) + (m_toggle << 8) + data);
      if (m_toggle == 1)
      {
          m_toggle = 0;
      }
      else
      {
          m_toggle = 1;
      }
    }

    // Write value in sequenciell register
    static void write_value(ushort value)
    {
      write_command(1, (uint)(value/256));
      write_command(1, (uint)(value%256));
    }

    // Reset seq. register
    static void reset_command_list()
    {
      write_command(0, 0); 
      write_command(0, 0); 
    }

    // End writing to seq. register
    static void end_command_list()
    {
      write_command(0, 0); 
    }    

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
