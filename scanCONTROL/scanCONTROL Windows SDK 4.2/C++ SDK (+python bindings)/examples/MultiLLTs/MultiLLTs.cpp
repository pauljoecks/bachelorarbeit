//   MultiLLTs.cpp: demo-application for using the LLT.dll
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
#include "MultiLLTs.h"

using namespace std;

static CInterfaceLLT* m_pLLT1 = NULL;
static CInterfaceLLT* m_pLLT2 = NULL;
static unsigned int m_uiResolution1 = 0;
static unsigned int m_uiResolution2 = 0;

static TScannerType m_tscanCONTROLType1 = scanCONTROL2xxx;
static TScannerType m_tscanCONTROLType2 = scanCONTROL2xxx;

static unsigned int m_uiProfileDataSize1 = 0;
static unsigned int m_uiProfileDataSize2 = 0;
static HANDLE m_hProfileEvent = CreateEvent(NULL, true, false, "ProfileEvent");
static vector<unsigned char> m_vucProfileBuffer1;
static vector<unsigned char> m_vucProfileBuffer2;
static bool m_bReceivedFromLLT1 = false;
static bool m_bReceivedFromLLT2 = false;

int main(int argc, char* argv[])
{
	UNREFERENCED_PARAMETER(argc);
	UNREFERENCED_PARAMETER(argv);

	vector<unsigned int> vuiInterfaces(MAX_INTERFACE_COUNT);
	vector<DWORD> vdwResolutions(MAX_RESOULUTIONS);
	unsigned int uiInterfaceCount = 0;
	unsigned int uiExposureTime = 100;
	unsigned int uiIdleTime = 3900;
	bool bLoadError = false;
	bool bOK = true;
	int iRetValue = 0;

	m_bReceivedFromLLT1 = m_bReceivedFromLLT2 = false;

	// Creating the first LLT-object
	// The LLT-Object will load the LLT.dll automaticly and give us a error if ther no LLT.dll
	m_pLLT1 = new CInterfaceLLT("..\\LLT.dll", &bLoadError);

	if (bLoadError)
	{
		cout << "Error loading LLT.dll \n";

		// Wait for a keyboard hit
		while (!_kbhit()) {}

		// Deletes the LLT-object
		delete m_pLLT1;
		return -1;
	}

	// Creating the second LLT-object
	// The LLT-Object will load the LLT.dll automaticly and give us a error if ther no LLT.dll
	m_pLLT2 = new CInterfaceLLT("..\\LLT.dll", &bLoadError);

	if (bLoadError)
	{
		cout << "Error loading LLT.dll \n";

		// Wait for a keyboard hit
		while (!_kbhit()) {}

		// Deletes the LLT-object
		delete m_pLLT2;
		return -1;
	}

	// Create Devices
	if (m_pLLT1->CreateLLTDevice(INTF_TYPE_ETHERNET) && m_pLLT2->CreateLLTDevice(INTF_TYPE_ETHERNET))
		cout << "CreateLLTDevice OK \n";
	else
		cout << "Error during CreateLLTDevice\n";

	// Gets the available interfaces from the scanCONTROL-device
	iRetValue = m_pLLT1->GetDeviceInterfacesFast(&vuiInterfaces[0], (unsigned int)vuiInterfaces.size());

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

	if (uiInterfaceCount >= 2)
	{
		cout << "\nSelect the device interface " << vuiInterfaces[0] << " for LLT 1\n";
		if ((iRetValue = m_pLLT1->SetDeviceInterface(vuiInterfaces[0], 0)) < GENERAL_FUNCTION_OK)
		{
			OnError(m_pLLT1, "Error during SetDeviceInterface", iRetValue);
			bOK = false;
		}

		if (bOK)
		{
			cout << "Select the device interface " << vuiInterfaces[1] << " for LLT 2\n";
			if ((iRetValue = m_pLLT2->SetDeviceInterface(vuiInterfaces[1], 0)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT2, "Error during SetDeviceInterface", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Connecting to the scanCONTROL 1\n";
			if ((iRetValue = m_pLLT1->Connect()) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT1, "Error during Connect", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Connecting to the scanCONTROL 2\n";
			if ((iRetValue = m_pLLT2->Connect()) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT2, "Error during Connect", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Get scanCONTROL type of scanCONTROL 1\n";
			if ((iRetValue = m_pLLT1->GetLLTType(&m_tscanCONTROLType1)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT1, "Error during GetLLTType", iRetValue);
				bOK = false;
			}

			if (iRetValue == GENERAL_FUNCTION_DEVICE_NAME_NOT_SUPPORTED)
			{
				cout << "Can't decode scanCONTROL type. Please contact Micro-Epsilon for a newer version of the LLT.dll.\n";
			}

			else if (m_tscanCONTROLType1 >= scanCONTROL27xx_25 && m_tscanCONTROLType1 <= scanCONTROL27xx_xxx)
			{
				cout << "The scanCONTROL 1 is a scanCONTROL27xx\n";
			}
			else if (m_tscanCONTROLType1 >= scanCONTROL25xx_25 && m_tscanCONTROLType1 <= scanCONTROL25xx_xxx)
			{
				cout << "The scanCONTROL 1 is a scanCONTROL25xx\n\n";
			}
			else if (m_tscanCONTROLType1 >= scanCONTROL26xx_25 && m_tscanCONTROLType1 <= scanCONTROL26xx_xxx)
			{
				cout << "The scanCONTROL 1 is a scanCONTROL26xx\n";
			}
			else if (m_tscanCONTROLType1 >= scanCONTROL29xx_25 && m_tscanCONTROLType1 <= scanCONTROL29xx_xxx)
			{
				cout << "The scanCONTROL 1 is a scanCONTROL29xx\n";
			}
			else if (m_tscanCONTROLType1 >= scanCONTROL30xx_25 && m_tscanCONTROLType1 <= scanCONTROL30xx_xxx)
            {
                cout << "The scanCONTROL 1 is a scanCONTROL30xx\n\n";
            } 
			else
			{
				cout << "The scanCONTROL 1 is a undefined type\nPlease contact Micro-Epsilon for a newer SDK\n";
			}

			cout << "Get all possible resolutions for scanCONTROL 1\n\n";
			if ((iRetValue = m_pLLT1->GetResolutions(&vdwResolutions[0], (unsigned int)vdwResolutions.size())) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT1, "Error during GetResolutions", iRetValue);
				bOK = false;
			}

			m_uiResolution1 = vdwResolutions[0];
		}

		if (bOK)
		{
			cout << "Get scanCONTROL type of scanCONTROL 2\n";
			if ((iRetValue = m_pLLT2->GetLLTType(&m_tscanCONTROLType2)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT2, "Error during GetLLTType", iRetValue);
				bOK = false;
			}

			if (iRetValue == GENERAL_FUNCTION_DEVICE_NAME_NOT_SUPPORTED)
			{
				cout << "Can't decode scanCONTROL type. Please contact Micro-Epsilon for a newer version of the LLT.dll.\n";
			}

			else if (m_tscanCONTROLType2 >= scanCONTROL27xx_25 && m_tscanCONTROLType2 <= scanCONTROL27xx_xxx)
			{
				cout << "The scanCONTROL 2 is a scanCONTROL27xx\n";
			}
			else if (m_tscanCONTROLType2 >= scanCONTROL25xx_25 && m_tscanCONTROLType2 <= scanCONTROL25xx_xxx)
			{
				cout << "The scanCONTROL 2 is a scanCONTROL25xx\n\n";
			}
			else if (m_tscanCONTROLType2 >= scanCONTROL26xx_25 && m_tscanCONTROLType2 <= scanCONTROL26xx_xxx)
			{
				cout << "The scanCONTROL 2 is a scanCONTROL26xx\n";
			}
			else if (m_tscanCONTROLType2 >= scanCONTROL29xx_25 && m_tscanCONTROLType2 <= scanCONTROL29xx_xxx)
			{
				cout << "The scanCONTROL 2 is a scanCONTROL29xx\n";
			}
			else if (m_tscanCONTROLType2 >= scanCONTROL30xx_25 && m_tscanCONTROLType2 <= scanCONTROL30xx_xxx)
            {
                cout << "The scanCONTROL 2 is a scanCONTROL30xx\n\n";
            } 
			else
			{
				cout << "The scanCONTROL 2 is a undefined type\nPlease contact Micro-Epsilon for a newer SDK\n";
			}

			cout << "Get all possible resolutions for scanCONTROL 2\n\n";
			if ((iRetValue = m_pLLT2->GetResolutions(&vdwResolutions[0], (unsigned int)vdwResolutions.size())) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT2, "Error during GetResolutions", iRetValue);
				bOK = false;
			}

			m_uiResolution2 = vdwResolutions[0];
		}

		if (bOK)
		{
			cout << "Set resolution of scanCONTROL 1 to " << m_uiResolution1 << "\n";
			if ((iRetValue = m_pLLT1->SetResolution(m_uiResolution1)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT1, "Error during SetResolution", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Set resolution of scanCONTROL 2 to " << m_uiResolution2 << "\n";
			if ((iRetValue = m_pLLT2->SetResolution(m_uiResolution2)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT2, "Error during SetResolution", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Set trigger to internal\n";
			if ((iRetValue = m_pLLT1->SetFeature(FEATURE_FUNCTION_TRIGGER, TRIG_INTERNAL)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT1, "Error during SetFeature(FEATURE_FUNCTION_TRIGGER)", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			if ((iRetValue = m_pLLT2->SetFeature(FEATURE_FUNCTION_TRIGGER, TRIG_INTERNAL)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT2, "Error during SetFeature(FEATURE_FUNCTION_TRIGGER)", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Profile config set to PROFILE\n";
			if ((iRetValue = m_pLLT1->SetProfileConfig(PROFILE)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT1, "Error during SetProfileConfig", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			if ((iRetValue = m_pLLT2->SetProfileConfig(PROFILE)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT2, "Error during SetProfileConfig", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Set shutter time to " << uiExposureTime << "\n";
			if ((iRetValue = m_pLLT1->SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME, uiExposureTime)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT1, "Error during SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME)", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			if ((iRetValue = m_pLLT2->SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME, uiExposureTime)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT2, "Error during SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME)", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Set idle time to " << uiIdleTime << "\n";
			if ((iRetValue = m_pLLT1->SetFeature(FEATURE_FUNCTION_IDLE_TIME, uiIdleTime)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT1, "Error during SetFeature(FEATURE_FUNCTION_IDLE_TIME)", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			if ((iRetValue = m_pLLT2->SetFeature(FEATURE_FUNCTION_IDLE_TIME, uiIdleTime)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT2, "Error during SetFeature(FEATURE_FUNCTION_IDLE_TIME)", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Set packet size to 1024\n";
			if ((iRetValue = m_pLLT1->SetPacketSize(1024)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT1, "Error during SetPacketSize", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			if ((iRetValue = m_pLLT2->SetPacketSize(1024)) < GENERAL_FUNCTION_OK)
			{
				OnError(m_pLLT2, "Error during SetPacketSize", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			MultiLLTs();
		}

		cout << "Disconnect scanCONTROL 1\n";
		if ((iRetValue = m_pLLT1->Disconnect()) < GENERAL_FUNCTION_OK)
		{
			OnError(m_pLLT1, "Error during Disconnect", iRetValue);
		}

		cout << "Disconnect scanCONTROL 2\n";
		if ((iRetValue = m_pLLT2->Disconnect()) < GENERAL_FUNCTION_OK)
		{
			OnError(m_pLLT2, "Error during Disconnect", iRetValue);
		}
	}
	else
		cout << "Please connect at least 2 scanCONTROL\n";

	// Deletes the LLT-objects
	if (m_pLLT1)
		delete m_pLLT1;
	if (m_pLLT2)
		delete m_pLLT2;

	CloseHandle(m_hProfileEvent);

	// Wait for a keyboard hit
	while (!_kbhit()) {}

	return 0;
}

void MultiLLTs()
{
	vector<double> vcValueX(max(m_uiResolution1, m_uiResolution2));
	vector<double> vcValueZ(max(m_uiResolution1, m_uiResolution2));
	int iRetValue;

	// Resize the profile buffers to the estimated profile size
	m_vucProfileBuffer1.resize(m_uiResolution1 * 64);
	m_vucProfileBuffer2.resize(m_uiResolution2 * 64);

	// Resets the event
	ResetEvent(m_hProfileEvent);

	cout << "\nDemonstrate the profile transfer via callback function\n";

	cout << "Register the callback for scanCONTROL 1\n";
	if ((iRetValue = m_pLLT1->RegisterCallback(STD_CALL, (void*)NewProfile, m_pLLT1)) < GENERAL_FUNCTION_OK)
	{
		OnError(m_pLLT1, "Error during RegisterCallback", iRetValue);
		return;
	}

	cout << "Register the callback for scanCONTROL 2\n";
	if ((iRetValue = m_pLLT2->RegisterCallback(STD_CALL, (void*)NewProfile, m_pLLT2)) < GENERAL_FUNCTION_OK)
	{
		OnError(m_pLLT2, "Error during RegisterCallback", iRetValue);
		return;
	}

	cout << "Enable the measurement for scanCONTROL 1\n";
	if ((iRetValue = m_pLLT1->TransferProfiles(NORMAL_TRANSFER, true)) < GENERAL_FUNCTION_OK)
	{
		OnError(m_pLLT1, "Error during TransferProfiles", iRetValue);
		return;
	}

	cout << "Enable the measurement for scanCONTROL 2\n";
	if ((iRetValue = m_pLLT2->TransferProfiles(NORMAL_TRANSFER, true)) < GENERAL_FUNCTION_OK)
	{
		OnError(m_pLLT2, "Error during TransferProfiles", iRetValue);
		return;
	}

	cout << "Wait for one profile\n";

	if (WaitForSingleObject(m_hProfileEvent, 1000) != WAIT_OBJECT_0)
	{
		cout << "Error getting profile over the callback \n\n";
		return;
	}

	cout << "Disable the measurement for scanCONTROL 1\n";
	if ((iRetValue = m_pLLT1->TransferProfiles(NORMAL_TRANSFER, false)) < GENERAL_FUNCTION_OK)
	{
		OnError(m_pLLT1, "Error during TransferProfiles", iRetValue);
		return;
	}

	cout << "Disable the measurement for scanCONTROL 2\n";
	if ((iRetValue = m_pLLT2->TransferProfiles(NORMAL_TRANSFER, false)) < GENERAL_FUNCTION_OK)
	{
		OnError(m_pLLT2, "Error during TransferProfiles", iRetValue);
		return;
	}

	// Test the size from the profile
	if (m_uiProfileDataSize1 == m_uiResolution1 * 64)
		cout << "Profile size for scanCONTROL 1 is OK \n";
	else
	{
		cout << "Profile size for scanCONTROL 1 is wrong \n\n";
		return;
	}

	// Test the size from the profile
	if (m_uiProfileDataSize2 == m_uiResolution2 * 64)
		cout << "Profile size for scanCONTROL 2 is OK \n";
	else
	{
		cout << "Profile size for scanCONTROL 2 is wrong \n\n";
		return;
	}

	cout << "Converting of profile data from the first scanCONTROL\n";
	iRetValue = m_pLLT1->ConvertProfile2Values(&m_vucProfileBuffer1[0], m_uiResolution1, PROFILE, m_tscanCONTROLType1, 0, true,
		NULL, NULL, NULL, &vcValueX[0], &vcValueZ[0], NULL, NULL);

	if (((iRetValue & CONVERT_X) == 0) || ((iRetValue & CONVERT_Z) == 0))
	{
		OnError(m_pLLT1, "Error during Converting of profile data", iRetValue);
		return;
	}

	DisplayProfile(&vcValueX[0], &vcValueZ[0], m_uiResolution1);

	cout << "\n\nDisplay the timestamp from the first scanCONTROL";
	DisplayTimestamp(m_pLLT1, &m_vucProfileBuffer1[m_uiResolution1 * 64 - 16]);

	cout << "Converting of profile data from the second scanCONTROL\n";
	iRetValue = m_pLLT2->ConvertProfile2Values(&m_vucProfileBuffer2[0], m_uiResolution2, PROFILE, m_tscanCONTROLType2, 0, true,
		NULL, NULL, NULL, &vcValueX[0], &vcValueZ[0], NULL, NULL);

	if (((iRetValue & CONVERT_X) == 0) || ((iRetValue & CONVERT_Z) == 0))
	{
		OnError(m_pLLT2, "Error during Converting of profile data", iRetValue);
		return;
	}

	DisplayProfile(&vcValueX[0], &vcValueZ[0], m_uiResolution2);

	cout << "\n\nDisplay the timestamp from the second scanCONTROL";
	DisplayTimestamp(m_pLLT1, &m_vucProfileBuffer2[m_uiResolution2 * 64 - 16]);
}

// Callback function
void __stdcall NewProfile(const unsigned char* pucData, unsigned int uiSize, void* pUserData)
{
	if (uiSize > 0)
	{

		// If the profile from LLT1, copy the new Profile in the first buffer
		if (pUserData == m_pLLT1)
		{
			memcpy(&m_vucProfileBuffer1[0], pucData, uiSize);
			m_bReceivedFromLLT1 = true;
			m_uiProfileDataSize1 = uiSize;
		}

		if (pUserData == m_pLLT2)
		{
			memcpy(&m_vucProfileBuffer2[0], pucData, uiSize);
			m_bReceivedFromLLT2 = true;
			m_uiProfileDataSize2 = uiSize;
		}

		if ((m_bReceivedFromLLT1 == true) && (m_bReceivedFromLLT2 == true))
		{
			// Recived from each scanCONTROL one profile -> set the event
			SetEvent(m_hProfileEvent);
		}
	}
}

// Displaying the error text
void OnError(CInterfaceLLT* pLLT, const char* szErrorTxt, int iErrorValue)
{
	char acErrorString[200];

	cout << szErrorTxt << "\n";
	if (pLLT->TranslateErrorValue(iErrorValue, acErrorString, sizeof(acErrorString)) >= GENERAL_FUNCTION_OK)
		cout << acErrorString << "\n\n";
}

// Displays one profile
void DisplayProfile(double* pdValueX, double* pdValueZ, unsigned int uiResolution)
{
	size_t tNumberSize;

	for (unsigned int i = 0; i < uiResolution; i++)
	{
		// Prints the X- and Z-values
		tNumberSize = Double2Str(*pdValueX).size();
		cout << "\r"
			<< "Profiledata: X = " << *pdValueX++;
		for (; tNumberSize < 8; tNumberSize++)
		{
			cout << " ";
		}

		tNumberSize = Double2Str(*pdValueZ).size();
		cout << " Z = " << *pdValueZ++;
		for (; tNumberSize < 8; tNumberSize++)
		{
			cout << " ";
		}

		// Somtimes wait a short time (only for display)
		if (i % 8 == 0)
		{
			Sleep(10);
		}
	}
}

// Displays the timestamp
void DisplayTimestamp(CInterfaceLLT* pLLT, unsigned char* pucTimestamp)
{
	double dShutterOpen, dShutterClose;
	unsigned int uiProfileCount;

	// Decode the timestamp
	pLLT->Timestamp2TimeAndCount(pucTimestamp, &dShutterOpen, &dShutterClose, &uiProfileCount);
	cout << "\nShutterOpen: " << dShutterOpen << " ShutterClose: " << dShutterClose << "\n";
	cout << "ProfileCount: " << uiProfileCount << "\n";
	cout << "\n";
}

// Convert a double value to a string
std::string Double2Str(double dValue)
{
	std::ostringstream NewStreamApp;
	NewStreamApp << dValue;

	return NewStreamApp.str();
}
