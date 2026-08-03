//   CmmTrigger.cpp: demo-application for using the LLT.dll
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
#include "CmmTrigger.h"

using namespace std;

static CInterfaceLLT* m_pLLT = NULL;
static unsigned int m_uiResolution = 0;
static TScannerType m_tscanCONTROLType = scanCONTROL2xxx;

static unsigned int uiExposureTime = 100;
static unsigned int uiIdleTime = 3900;

int main(int argc, char* argv[])
{
	UNREFERENCED_PARAMETER(argc);
	UNREFERENCED_PARAMETER(argv);
	vector<unsigned int> vuiInterfaces(MAX_INTERFACE_COUNT);
	vector<DWORD> vdwResolutions(MAX_RESOULUTIONS);
	unsigned int uiInterfaceCount = 0;
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

	if (uiInterfaceCount <= 0)
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
			CmmTrigger();
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

void CmmTrigger()
{
	// Resize the profile buffer to the maximal profile size
	vector<unsigned char> pucProfileBuffer(m_uiResolution * 64);
	int iRetValue;
	DWORD dwInquiryCmmTrigger;
	DWORD InterfaceFunctionValue = 0;
	unsigned int uiInCounter, uiCmmCount;
	int iCmmTrigger, iCmmActive;
	bool noProfileReceived = true;

	cout << "\nDemonstrate the CmmTrigger\n";
	cout << "The CmmTrigger is a optional function for the scanCONTROL\n\n";

	if (m_tscanCONTROLType >= scanCONTROL27xx_25 && m_tscanCONTROLType <= scanCONTROL27xx_xxx)
	{
		InterfaceFunctionValue = RS422_INTERFACE_FUNCTION_CMM_TRIGGER;
	}
	else if (m_tscanCONTROLType >= scanCONTROL26xx_25 && m_tscanCONTROLType <= scanCONTROL30xx_xxx)
	{
		InterfaceFunctionValue = MULTI_RS422_CMM;
	}

	cout << "Test the scanCONTROL for support of the Cmm-Trigger feature\n";
	if ((iRetValue = m_pLLT->GetFeature(INQUIRY_FUNCTION_CMM_TRIGGER, &dwInquiryCmmTrigger)) < GENERAL_FUNCTION_OK)
	{
		cout << "The connected scanCONTROL doesn't support the Cmm-Trigger feature.\n";
		return;
	}

	cout << "Set Digital IO function to 'cmm trigger'\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_DIGITAL_IO, InterfaceFunctionValue)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_DIGITAL_IO)", iRetValue);
	}

	cout << "Set the CmmTrigger configuration: mark space ratio 1:1\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_CMM_TRIGGER, 0x00000401)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_CMM_TRIGGER)", iRetValue);
		return;
	}
	cout << "Set the CmmTrigger configuration: skew correction 2us\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_CMM_TRIGGER, 0x00000804)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_CMM_TRIGGER)", iRetValue);
		return;
	}

	cout << "Set the CmmTrigger configuration: output port 1\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_CMM_TRIGGER, 0x00000c00)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_CMM_TRIGGER)", iRetValue);
		return;
	}

	cout << "Set the CmmTrigger configuration: Divisor  1\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_CMM_TRIGGER, 0x00000001)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_CMM_TRIGGER)", iRetValue);
		return;
	}

	// Wait until all parameters are set before starting the transmission (this can take up to 120ms)
	Sleep(120);
	cout << "Start the profile transmission and poll one profile \n";
	m_pLLT->TransferProfiles(NORMAL_TRANSFER, 1);
	

	while (noProfileReceived) {
		if ((iRetValue = m_pLLT->GetActualProfile(&pucProfileBuffer[0], (unsigned int)pucProfileBuffer.size(), PROFILE, NULL)) !=
			(int)pucProfileBuffer.size())
		{
			if (iRetValue == ERROR_PROFTRANS_NO_NEW_PROFILE) {
				Sleep((uiIdleTime + uiExposureTime) / 100);
				continue;
			}
			else {
				OnError("Error during GetActualProfile", iRetValue);
				return;
			}
		}
		else {
			cout << "Profile received\n";
			noProfileReceived = false;
		}
	}

	m_pLLT->Timestamp2CmmTriggerAndInCounter(&pucProfileBuffer[(unsigned int)pucProfileBuffer.size() - 16], &uiInCounter, &iCmmTrigger, &iCmmActive,
		&uiCmmCount);

	cout << "TransferProfiles OK\n";
	cout << "InCounter: " << uiInCounter << "\n";
	cout << "CMM trigger impulse: " << (iCmmTrigger ? "true" : "false");
	cout << ", CMM trigger active: " << (iCmmActive ? "true" : "false");
	cout << ", CMM trigger counter: " << uiCmmCount << "\n\n";

	m_pLLT->TransferProfiles(NORMAL_TRANSFER, 0);
}

// Displaying the error text
void OnError(const char* szErrorTxt, int iErrorValue)
{
	char acErrorString[200];

	cout << szErrorTxt << "\n";
	if (m_pLLT->TranslateErrorValue(iErrorValue, acErrorString, sizeof(acErrorString)) >= GENERAL_FUNCTION_OK)
		cout << acErrorString << "\n\n";
}
