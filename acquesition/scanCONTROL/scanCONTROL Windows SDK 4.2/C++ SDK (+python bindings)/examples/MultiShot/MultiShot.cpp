//   MultiShot.cpp: demo-application for using the LLT.dll
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
#include "MultiShot.h"

using namespace std;

CInterfaceLLT* m_pLLT = NULL;
unsigned int m_uiProfileCount = 0;
unsigned int m_uiResolution = 0;
TScannerType m_tscanCONTROLType = scanCONTROL2xxx;

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
	int iRetValue = 0;
	bool bOK = true;
	bool bConnected = false;

	// Creating a LLT-object
	// The LLT-Object will load the LLT.dll automaticly and give us a error if ther no LLT.dll
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
			if (m_tscanCONTROLType >= scanCONTROL27xx_25 && m_tscanCONTROLType <= scanCONTROL27xx_xxx)
			{
				cout << "The scanCONTROL is a scanCONTROL27xx\n\n";
			}
			else if (m_tscanCONTROLType >= scanCONTROL25xx_25 && m_tscanCONTROLType <= scanCONTROL25xx_xxx)
			{
				cout << "The scanCONTROL is a scanCONTROL25xx\n\n";
			}
			else if (m_tscanCONTROLType >= scanCONTROL26xx_25 && m_tscanCONTROLType <= scanCONTROL26xx_xxx)
			{
				cout << "The scanCONTROL is a scanCONTROL26xx\n\n";
			}
			else if (m_tscanCONTROLType >= scanCONTROL29xx_25 && m_tscanCONTROLType <= scanCONTROL29xx_xxx)
			{
				cout << "The scanCONTROL is a scanCONTROL29xx\n\n";
			}
			else if (m_tscanCONTROLType >= scanCONTROL30xx_25 && m_tscanCONTROLType <= scanCONTROL30xx_xxx)
			{
				cout << "The scanCONTROL is a scanCONTROL30xx\n\n";
			}
			else
			{
				cout << "The scanCONTROL is a undefined type\nPlease contact Micro-Epsilon for a newer SDK\n\n";
			}

			cout << "Get all possible resolutions\n";
			if ((iRetValue = m_pLLT->GetResolutions(&vdwResolutions[0], (unsigned int)vdwResolutions.size())) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during GetResolutions", iRetValue);
				bOK = false;
			}

			m_uiResolution = vdwResolutions[0];
		}

		if (bOK)
		{
			cout << "Set resolution to " << m_uiResolution << "\n";
			if ((iRetValue = m_pLLT->SetResolution(m_uiResolution)) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during SetResolution", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Set trigger to internal\n";
			if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_TRIGGER, TRIG_INTERNAL)) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during SetFeature(FEATURE_FUNCTION_TRIGGER)", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Profile config set to PROFILE\n";
			if ((iRetValue = m_pLLT->SetProfileConfig(PROFILE)) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during SetProfileConfig", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Set shutter time to " << uiExposureTime << "\n";
			if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME, uiExposureTime)) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME)", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Set idle time to " << uiIdleTime << "\n";
			if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_IDLE_TIME, uiIdleTime)) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during SetFeature(FEATURE_FUNCTION_IDLE_TIME)", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			MultiShot();
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

	// Wait for a keyboard hit
	while (!_kbhit()) {}

	return 0;
}

void MultiShot()
{
	int iRetValue;

	cout << "\nDemonstrate the multi shot-routines\n";

	cout << "Register the callback\n";
	if ((iRetValue = m_pLLT->RegisterCallback(STD_CALL, (void*)NewProfile, 0)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during RegisterCallback", iRetValue);
		return;
	}

	cout << "Enable the measurement for shots\n";
	if ((iRetValue = m_pLLT->TransferProfiles(SHOT_TRANSFER, true)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}

	cout << "Get one shot (call MultiShot(1))\n";
	if ((iRetValue = m_pLLT->MultiShot(1)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during MultiShot(1)", iRetValue);
		return;
	}

	// Sleep for a while to warm up the transfer
	Sleep(500);

	// Test if only one profile recived
	if (m_uiProfileCount != 1)
	{
		cout << "Wrong profile count received \n\n";
		return;
	}

	cout << "Received one profile OK\n";

	m_uiProfileCount = 0;

	cout << "Get 10 shots MultiShot(10)\n";
	if ((iRetValue = m_pLLT->MultiShot(10)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during MultiShot(10)", iRetValue);
		return;
	}

	// Sleep for a while to warm up the transfer
	Sleep(1000);

	// Test if only 10 profile recived
	if (m_uiProfileCount != 10)
	{
		cout << "Wrong profile count received \n\n";
		return;
	}

	cout << "Received 10 profiles OK\n\n";

	cout << "Disable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(SHOT_TRANSFER, false)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}
}

// Callback function
void __stdcall NewProfile(const unsigned char* pucData, unsigned int uiSize, void* pUserData)
{
	m_uiProfileCount++;
	UNREFERENCED_PARAMETER(pucData);
	UNREFERENCED_PARAMETER(uiSize);
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
