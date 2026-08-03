//   GetProfiles_Poll.cpp: demo-application for using the LLT.dll
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
#include "GetProfiles_Poll.h"

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
		cout << "Error loading LLT.dll" << endl;

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
			GetProfiles_Poll();
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

void GetProfiles_Poll()
{
	int iRetValue;
	bool noProfileReceived = true;
	vector<double> vdValueX(m_uiResolution);
	vector<double> vdValueZ(m_uiResolution);
	// Resize the profile buffer to the maximal profile size
	vector<unsigned char> vucProfileBuffer(m_uiResolution * 64);

	cout << "\nDemonstrate the profile transfer via poll function\n";

	cout << "Gets the type of the scanCONTROL (measurement range)\n";

	// Wait until all parameters are set before starting the transmission (this can take up to 120ms)
	Sleep(120);

	cout << "Enable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, true)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}

	// Gets 1 profile in "polling-mode" and PURE_PROFILE (x/z only) configuration
	while (noProfileReceived) {
		if ((iRetValue = m_pLLT->GetActualProfile(&vucProfileBuffer[0], (unsigned int)vucProfileBuffer.size(), PROFILE, NULL)) !=
			(int)vucProfileBuffer.size())
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
			cout << "Get profile in polling-mode and PURE_PROFILE configuration OK \n";
			noProfileReceived = false;
		}
	}

	cout << "Converting of profile data from the first reflection\n";
	iRetValue = m_pLLT->ConvertProfile2Values(&vucProfileBuffer[0], m_uiResolution, PROFILE, m_tscanCONTROLType, 0, true, NULL,
		NULL, NULL, &vdValueX[0], &vdValueZ[0], NULL, NULL);
	if (((iRetValue & CONVERT_X) == 0) || ((iRetValue & CONVERT_Z) == 0))
	{
		OnError("Error during Converting of profile data", iRetValue);
		return;
	}

	DisplayProfile(&vdValueX[0], &vdValueZ[0], m_uiResolution);

	cout << "\n\nDisplay the timestamp from the profile:";
	DisplayTimestamp(&vucProfileBuffer[(unsigned int)vucProfileBuffer.size() - 16]);

	cout << "Disable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, false)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}
}

// Displaying the error text
void OnError(const char* szErrorTxt, int iErrorValue)
{
	char acErrorString[200];

	cout << szErrorTxt << "\n";
	if (m_pLLT->TranslateErrorValue(iErrorValue, acErrorString, sizeof(acErrorString)) >= GENERAL_FUNCTION_OK)
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
void DisplayTimestamp(unsigned char* pucTimestamp)
{
	double dShutterOpen, dShutterClose;
	unsigned int uiProfileCount;

	// Decode the timestamp
	m_pLLT->Timestamp2TimeAndCount(pucTimestamp, &dShutterOpen, &dShutterClose, &uiProfileCount);
    
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
