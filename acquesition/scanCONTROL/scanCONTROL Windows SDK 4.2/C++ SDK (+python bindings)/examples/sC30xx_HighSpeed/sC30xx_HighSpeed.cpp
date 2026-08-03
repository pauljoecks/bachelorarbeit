//   sC30xx_HighSpeed.cpp: demo-application for using the LLT.dll
//
//   Version 3.9.0
//
//   Copyright 2019
//
//   MICRO-EPSILON GmbH & Co. KG
//   Königbacher Str. 15
//   94496 Ortenburg
//   Germany
//---------------------------------------------------------------------------

#include "stdafx.h"
#include <iostream>
#include <conio.h>
#include "InterfaceLLT_2.h"
#include "sC30xx_HighSpeed.h"

using namespace std;

CInterfaceLLT* m_pLLT = NULL;
unsigned int m_uiResolution = 512;
TScannerType m_tscanCONTROLType = scanCONTROL2xxx;
unsigned int m_uiDSP;
unsigned int m_uiFPGA1;
unsigned int m_uiFPGA2;

unsigned int m_uiNeededProfileCount = 5001;
unsigned int m_uiReceivedProfileCount = 0;
unsigned int m_uiProfileDataSize;
HANDLE m_hProfileEvent = CreateEvent(NULL, true, false, "ProfileEvent");
vector<unsigned char> m_vucProfileBuffer;
TPartialProfile tPartialProfile;
unsigned int m_uiProfilecountStart = 0;
double m_uiShutterOpenStart = 0;

int main(int argc, char* argv[])
{
	UNREFERENCED_PARAMETER(argc);
	UNREFERENCED_PARAMETER(argv);

	vector<unsigned int> vuiInterfaces(MAX_INTERFACE_COUNT);
	unsigned int uiInterfaceCount = 0;
	bool bLoadError = false;
	int iRetValue = 0;
	bool bOK = true;
	bool bConnected = false;

	// Creating a LLT-object
	// The LLT-Object will load the LLT.dll automaticly and give us a error if there is no LLT.dll
	m_pLLT = new CInterfaceLLT("..\\LLT.dll", &bLoadError);

	if (bLoadError)
	{
		cout << "Error loading LLT.dll \n";

		// Wait for a keyboard hit
		while (!_kbhit()) {}

		// Deletes the LLT-object
		delete m_pLLT;
		return -1;
	}

	// Create a Device
	if (m_pLLT->CreateLLTDevice(INTF_TYPE_ETHERNET))
		cout << "CreateLLTDevice OK \n";
	else
		cout << "Error during CreateLLTDevice\n";

	// Gets the available interfaces from the scanCONTROL-device
	iRetValue = m_pLLT->GetDeviceInterfacesFast(&vuiInterfaces[0], (unsigned int)vuiInterfaces.size());

	if (iRetValue == ERROR_GETDEVINTERFACES_REQUEST_COUNT)
	{
		cout << "There are more or equal than " << vuiInterfaces.size() << " scanCONTROL connected \n";
		uiInterfaceCount = (unsigned int)vuiInterfaces.size();
	}
	else if (iRetValue < 0)
	{
		cout << "A error occured during searching for connected scanCONTROL \n";
		uiInterfaceCount = 0;
	}
	else
	{
		uiInterfaceCount = iRetValue;
	}

	if (uiInterfaceCount == 0)
		cout << "There is no scanCONTROL connected \n";
	else if (uiInterfaceCount == 1)
		cout << "There is 1 scanCONTROL connected \n";
	else
		cout << "There are " << uiInterfaceCount << " scanCONTROL's connected \n";

	if (uiInterfaceCount >= 1)
	{
		cout << "\nSelect the device interface " << vuiInterfaces[0] << "\n";
		if ((iRetValue = m_pLLT->SetDeviceInterface(vuiInterfaces[0], 0)) < GENERAL_FUNCTION_OK)
		{
			OnError("Error during SetDeviceInterface", iRetValue);
			bOK = false;
		}

		if (bOK)
		{
			cout << "Connecting to scanCONTROL\n";
			if ((iRetValue = m_pLLT->Connect()) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during Connect", iRetValue);
				bOK = false;
			}
			else
				bConnected = true;
		}

		if (bOK)
		{
			cout << "Get scanCONTROL type\n";
			if ((iRetValue = m_pLLT->GetLLTType(&m_tscanCONTROLType)) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during GetLLTType", iRetValue);
				bOK = false;
			}

			if (iRetValue == GENERAL_FUNCTION_DEVICE_NAME_NOT_SUPPORTED)
			{
				cout << "Can't decode scanCONTROL type. Please contact Micro-Epsilon for a newer version of the LLT.dll.\n";
			}

            if (m_tscanCONTROLType >= scanCONTROL30xx_25 && m_tscanCONTROLType <= scanCONTROL30xx_xxx)
            {
                cout << "The scanCONTROL is a scanCONTROL30xx\n";
            } 
            else
            {
                cout << "The scanCONTROL is not a scanCONTROL30xx!\n";
				bOK = false;
            }
		}

		if (bOK)
		{
			cout << "Set trigger to internal\n\n";
			if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_TRIGGER, TRIG_INTERNAL)) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during SetFeature(FEATURE_FUNCTION_TRIGGER)", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Load Usermode 0 to reset the sensor to factory settings\n\n";
			if ((iRetValue = m_pLLT->ReadWriteUserModes(0,0)) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during Loading Usermode", iRetValue);
				bOK = false;
			}
		}

		if (bOK) 
		{
			ConfigureSensorForHighSpeed();
		}

		if (bOK)
		{
			GetProfiles_Callback();
		}

		if (bConnected)
		{
			cout << "Disconnect the scanCONTROL\n";
			if ((iRetValue = m_pLLT->Disconnect()) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during Disconnect", iRetValue);
			}
		}
	}

	// Deletes the LLT-object
	delete m_pLLT;

	CloseHandle(m_hProfileEvent);

	// Wait for a keyboard hit
	while (!_kbhit()) {}

	return 0;
}

void ConfigureSensorForHighSpeed()
{
	// The maximum profile frequency that can be reached by scanCONTROL 30xx sensors is limited by several factors.
	// Used Measuring field / Region of Interest (ROI) on the sensor matrix
	// Shutter time / Idle time
	// Number of points per profile
	// Data transmission type (single profile / container mode)
	// Ethernet bandwidth requirements
	// Please care for scanCONTROL_30xx_QuickReference.html to get further information
	// Example Configuration for 5kHz
	int iRetValue;
	vector<DWORD> vdwResolutions(MAX_RESOULUTIONS);
	cout << "Configure the sensor for high speed profile acquisition\n";
	cout << "Set operating mode to high speed\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_IMAGE_FEATURES, 0x40000000)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_IMAGE_FEATURES)", iRetValue);
	}

	cout << "Enable ROI1 free region\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_ROI1_PRESET, 0x800)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_PRESET)", iRetValue);
	}

	// Percentage X/Z of ROI 1
	double start_z = 45.0;
	double end_z = 55.0;
	double start_x = 20.0;
	double end_x = 80.0;

	cout << "Start Z (%): " << start_z << "\n";
	cout << "End Z (%): " << end_z << "\n";
	cout << "Start X (%): " << start_x << "\n";
	cout << "End X (%): " << end_x << "\n";

	// X/Z raster for sensor matrix
	double raster_x = 1.5625;
	double raster_z = 200.0 / 1088.0;

	unsigned short col_start = USHORT(round(start_x / raster_x) * raster_x / 100 * 65536);
	unsigned short col_size = USHORT(round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);

	unsigned short row_start = USHORT(round(start_z / raster_z) * raster_z / 100 * 65536);
	unsigned short row_size = USHORT(round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
	
	cout << "Set ROI1_Position parameter \n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_ROI1_POSITION, (col_start << 16) + col_size)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_POSITION)", iRetValue);
	}
    cout << "Set ROI1_Distance parameter\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_ROI1_DISTANCE, (row_start << 16) + row_size)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_DISTANCE)", iRetValue);
	}

	cout << "Activate ROI1 free region \n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER)", iRetValue);
	}

	// Exposure Time / Idle Time in µs
	unsigned int uiIdleTime = 33;
	unsigned int uiExposureTime = 167;
	cout << "Set idle time to " << uiIdleTime << "\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_IDLE_TIME, (((uiIdleTime % 10) << 12) & 0xF000) + ((uiIdleTime / 10) & 0xFFF))) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_IDLE_TIME)", iRetValue);
	}
	cout << "Set exposure time to " << uiExposureTime << "\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME, (((uiExposureTime % 10) << 12) & 0xF000) + ((uiExposureTime / 10) & 0xFFF))) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME)", iRetValue);
	}

	// Set resolution to 1/4
	cout << "Get all possible resolutions\n";
	if ((iRetValue = m_pLLT->GetResolutions(&vdwResolutions[0], (unsigned int)vdwResolutions.size())) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during GetResolutions", iRetValue);
	}

	m_uiResolution = vdwResolutions[2];
	cout << "Set resolution to " << m_uiResolution << "\n";
	if ((iRetValue = m_pLLT->SetResolution(m_uiResolution)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetResolution", iRetValue);
	}
	
	// Profile configuration Partial Profile
	cout << "Profile config set to PARTIAL_PROFILE\n";
	if ((iRetValue = m_pLLT->SetProfileConfig(PARTIAL_PROFILE)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetProfileConfig", iRetValue);
	}

	// Struct for a partial transfer (like PURE_PROFILE)
	tPartialProfile.nStartPoint = 0;                 
	tPartialProfile.nStartPointData = 4;              
	tPartialProfile.nPointCount = m_uiResolution; 
	tPartialProfile.nPointDataWidth = 4;              

	if ((iRetValue = m_pLLT->SetPartialProfile(&tPartialProfile)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetPartialProfile", iRetValue);
	}

	cout << "Set packet size to 1024\n\n";
	if ((iRetValue = m_pLLT->SetPacketSize(1024)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetPacketSize", iRetValue);
	}
}

void GetProfiles_Callback()
{
	int iRetValue;
	vector<double> vdValueX(m_uiResolution);
	vector<double> vdValueZ(m_uiResolution);
	double m_dShutterOpen, m_dShutterClose;
	unsigned int m_uiProfileCount;

	// Resize the profile buffer to the maximal profile size
	m_vucProfileBuffer.resize(tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth * m_uiNeededProfileCount);

	// Resets the event
	ResetEvent(m_hProfileEvent);

	cout << "\nDemonstrate the profile transfer via callback function\n";

	cout << "Register the callback\n";
	if ((iRetValue = m_pLLT->RegisterCallback(STD_CALL, (void*)NewProfile, 0)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during RegisterCallback", iRetValue);
		return;
	}

	cout << "Enable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, true)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}

	cout << "Wait for " << m_uiNeededProfileCount << " profiles\n";

	if (WaitForSingleObject(m_hProfileEvent, 2000) != WAIT_OBJECT_0)
	{
		cout << "Error getting profiles over the callback \n\n";
		return;
	}

	cout << "Disable the measurement\n\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, false)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}

	cout << m_uiReceivedProfileCount << " profiles received\n";

	// Eval timestamp from the first profile
	m_pLLT->Timestamp2TimeAndCount(&m_vucProfileBuffer[tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth - 16], &m_dShutterOpen, &m_dShutterClose, &m_uiProfileCount);
	m_uiProfilecountStart = m_uiProfileCount;
	m_uiShutterOpenStart = m_dShutterOpen;
	
	// Eval timestamp from the last profile
	m_pLLT->Timestamp2TimeAndCount(&m_vucProfileBuffer[tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth * (m_uiNeededProfileCount)-16], &m_dShutterOpen, &m_dShutterClose, &m_uiProfileCount);
	cout << m_uiProfileCount - m_uiProfilecountStart - (m_uiReceivedProfileCount - 1) << " Profiles lost\n";
	cout << "Resulting profile frequency: " << (m_uiReceivedProfileCount - 1) /  (m_dShutterOpen - m_uiShutterOpenStart) << " Hz\n\n";
}

// Callback function
void __stdcall NewProfile(const unsigned char* pucData, unsigned int uiSize, void* pUserData)
{
	if (uiSize > 0)
	{
		if (m_uiReceivedProfileCount < m_uiNeededProfileCount)
		{
			// If the needed profile count not arrived: copy the new Profile in the buffer and increase the recived buffer count
			m_uiProfileDataSize = uiSize;
			memcpy(&m_vucProfileBuffer[m_uiReceivedProfileCount * uiSize], pucData, uiSize);
			m_uiReceivedProfileCount++;
		}

		if (m_uiReceivedProfileCount >= m_uiNeededProfileCount)
		{
			// If the needed profile count is arived: set the event
			SetEvent(m_hProfileEvent);
		}
	}
	UNREFERENCED_PARAMETER(pUserData);
}

// Displaying the error text
void OnError(const char* szErrorTxt, int iErrorValue)
{
	char acErrorString[200];

	cout << szErrorTxt << "\n";
	if (m_pLLT->TranslateErrorValue(iErrorValue, acErrorString, sizeof(acErrorString)) >= GENERAL_FUNCTION_OK)
		cout << acErrorString << "\n\n";
}
