//   TriggerProfile.cpp: demo-application for using the LLT.dll
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
#include <conio.h>
#include <vector>
#include <sstream>
#include <iostream>
#include <memory>

#if _MSC_VER < 1600
#error "Only for VS2010 and above"
#endif // _MSC_VER < 1600

#include "InterfaceLLT_2.h"
#include "TriggerProfile.h"

using namespace std;

//static std::unique_ptr<CInterfaceLLT> m_pLLT(nullptr);
static CInterfaceLLT* m_pLLT = NULL;
static unsigned int m_uiResolution = 0;
static TScannerType m_tscanCONTROLType = scanCONTROL2xxx;
const unsigned int MAX_INTERFACE_COUNT = 5U;
const unsigned int MAX_RESOULUTIONS = 6U;
unsigned int uiExposureTime = 100;
unsigned int uiIdleTime = 3900;
vector<unsigned char> vucProfileBuffer;

int main(int argc, char* argv[])
{
	UNREFERENCED_PARAMETER(argc);
	UNREFERENCED_PARAMETER(argv);
	vector<unsigned int> vuiInterfaces(MAX_INTERFACE_COUNT);
	vector<DWORD> vdwResolutions(MAX_RESOULUTIONS);
	unsigned int uiInterfaceCount = 0;
	bool bLoadError = false;
	int iRetValue = 0;

	// Creating a LLT-object
	// The LLT-Object will load the LLT.dll automaticly and give us a error if ther no LLT.dll
	m_pLLT = new CInterfaceLLT("..\\LLT.dll", &bLoadError);

	if (bLoadError)
	{
		cout << "Error loading LLT.dll \n";

		// Wait for a keyboard hit
		while (!_kbhit()) {}

		return -1;
	}

	// proper LLT.dll version?
	if (m_pLLT->m_pFunctions->TriggerProfile == NULL)
	{
		cout << "Please use a LLT.dll version 3.6.0.0 or higher! \n";
		return 1;
	}

	// Create a Device
	iRetValue = m_pLLT->CreateLLTDevice(INTF_TYPE_ETHERNET);
	bool bOK = iRetValue == GENERAL_FUNCTION_OK;
	if (!bOK)
	{
		cout << "Error during CreateLLTDevice\n";
		return iRetValue;
	}

	// scan for devices
	iRetValue = m_pLLT->GetDeviceInterfacesFast(vuiInterfaces.data(), (unsigned int)vuiInterfaces.size());

	if (iRetValue == ERROR_GETDEVINTERFACES_REQUEST_COUNT)
	{
		cout << "There are more or equal than " << (unsigned int)vuiInterfaces.size() << " scanCONTROL connected \n";
		uiInterfaceCount = (unsigned int)vuiInterfaces.size();
	}
	else if (iRetValue < 0)
	{
		cout << "A error occured during searching for connected scanCONTROL \n";
		return iRetValue;
	}
	else
		uiInterfaceCount = iRetValue;

	if (uiInterfaceCount == 0)
	{
		cout << "There is no scanCONTROL connected \n";
		return 1;
	}
	else if (uiInterfaceCount == 1)
		cout << "There is 1 scanCONTROL connected \n";
	else
		cout << "There are " << uiInterfaceCount << " scanCONTROL's connected \n";

	// select the first scanCONTROL
	cout << "\nSelect the device interface " << vuiInterfaces[0] << "\n";
	iRetValue = m_pLLT->SetDeviceInterface(vuiInterfaces[0], 0);
	bOK = iRetValue == GENERAL_FUNCTION_OK;

	if (!bOK)
	{
		OnError("Error during SetDeviceInterface", iRetValue);
		return iRetValue;
	}

	cout << "Connecting to scanCONTROL\n";
	iRetValue = m_pLLT->Connect();
	bOK = iRetValue == GENERAL_FUNCTION_OK;

	if (!bOK)
	{
		OnError("Error during Connect", iRetValue);
		return iRetValue;
	}

	cout << "Get scanCONTROL type\n";
	iRetValue = m_pLLT->GetLLTType(&m_tscanCONTROLType);

	if (iRetValue == GENERAL_FUNCTION_DEVICE_NAME_NOT_SUPPORTED)
		cout << "Can't decode scanCONTROL type. Please contact Micro-Epsilon for a newer version of the LLT.dll.\n";
	bOK = iRetValue == GENERAL_FUNCTION_OK;
	if (!bOK)
	{
		OnError("Error during GetLLTType", iRetValue);
		return iRetValue;
	}
    
	if (m_tscanCONTROLType >= scanCONTROL27xx_25 && m_tscanCONTROLType <= scanCONTROL27xx_xxx)
		cout << "The scanCONTROL is a scanCONTROL27xx\n\n";
	else if (m_tscanCONTROLType >= scanCONTROL25xx_25 && m_tscanCONTROLType <= scanCONTROL25xx_xxx)
		cout << "The scanCONTROL is a scanCONTROL25xx\n\n";
	else if (m_tscanCONTROLType >= scanCONTROL26xx_25 && m_tscanCONTROLType <= scanCONTROL26xx_xxx)
		cout << "The scanCONTROL is a scanCONTROL26xx\n\n";
	else if (m_tscanCONTROLType >= scanCONTROL29xx_25 && m_tscanCONTROLType <= scanCONTROL29xx_xxx)
		cout << "The scanCONTROL is a scanCONTROL29xx\n\n";
	else if (m_tscanCONTROLType >= scanCONTROL30xx_25 && m_tscanCONTROLType <= scanCONTROL30xx_xxx)
		cout << "The scanCONTROL is a scanCONTROL30xx\n\n";
	else
		cout << "The scanCONTROL is a undefined type\nPlease contact Micro-Epsilon for a newer SDK\n\n";

	cout << "Get all possible resolutions\n";
	iRetValue = m_pLLT->GetResolutions(vdwResolutions.data(), (unsigned int)vdwResolutions.size());
	bOK = iRetValue != ERROR_SETGETFUNCTIONS_SIZE_TOO_LOW;
	if (!bOK)
	{
		OnError("Error during GetResolutions", iRetValue);
		return iRetValue;
	}

	m_uiResolution = vdwResolutions[0];
	cout << "Set resolution to " << m_uiResolution << "\n";
	iRetValue = m_pLLT->SetResolution(m_uiResolution);
	bOK = iRetValue == GENERAL_FUNCTION_OK;
	if (!bOK)
	{
		OnError("Error during SetResolution", iRetValue);
		return iRetValue;
	}

	/// the device must set in external trigger mode, only then TriggerProfile should be used
	cout << "Set trigger to external\n";
	iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_TRIGGER, TRIG_EXT_ACTIVE);
	bOK = iRetValue == GENERAL_FUNCTION_OK;
	if (!bOK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_TRIGGER)", iRetValue);
		return iRetValue;
	}

	cout << "Set shutter time to " << uiExposureTime << "\n";
	iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME, uiExposureTime);
	bOK = iRetValue == GENERAL_FUNCTION_OK;
	if (!bOK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME)", iRetValue);
		return iRetValue;
	}

	cout << "Set idle time to " << uiIdleTime << "\n";
	iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_IDLE_TIME, uiIdleTime);
	bOK = iRetValue == GENERAL_FUNCTION_OK;
	if (!bOK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_IDLE_TIME)", iRetValue);
		return iRetValue;
	}

	cout << "Profile config set to PROFILE\n";
	iRetValue = m_pLLT->SetProfileConfig(PROFILE);
	bOK = iRetValue == GENERAL_FUNCTION_OK;
	if (!bOK)
	{
		OnError("Error during SetProfileConfig", iRetValue);
		return iRetValue;
	}

	TriggerProfileAndShow();

	// Deletes the LLT-object
	delete m_pLLT;

	// Wait for a keyboard hit
	while (!_kbhit()) {}
	
	return 0;
}

void TriggerProfileAndShow()
{
	vector<double> vdValueX(m_uiResolution);
	vector<double> vdValueZ(m_uiResolution);
	int iRetValue;
	bool noProfileReceived = true;

	// Resize the profile buffer to the maximal profile size
	vucProfileBuffer.resize(m_uiResolution * 64);

	// Wait until all parameters are set before starting the transmission (this can take up to 120ms)
	Sleep(120);

	cout << "Enable the measurement\n";
	iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, true);
	bool bOK = iRetValue >= GENERAL_FUNCTION_NOT_AVAILABLE;
	if (!bOK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}
	
	// Trigger and get profile
	while (noProfileReceived) {
		if ((iRetValue = m_pLLT->GetActualProfile(&vucProfileBuffer[0], (unsigned int)vucProfileBuffer.size(), PROFILE, NULL)) !=
			(int)vucProfileBuffer.size())
		{
			if (iRetValue == ERROR_PROFTRANS_NO_NEW_PROFILE) {
				m_pLLT->TriggerProfile();
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
	DisplayTimestamp(&vucProfileBuffer[m_uiResolution * 64 - 16]);
	
	cout << "Disable the measurement\n";
	iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, false);
	bOK = iRetValue == GENERAL_FUNCTION_OK;
	if (!bOK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}

	return;
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
			cout << " ";

		tNumberSize = Double2Str(*pdValueZ).size();
		cout << " Z = " << *pdValueZ++;

		for (; tNumberSize < 8; tNumberSize++)
			cout << " ";

		// Somtimes wait a short time (only for display)
		if (i % 8 == 0)
			Sleep(10);
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

// Displaying the error text
void OnError(const char* szErrorTxt, int iErrorValue)
{
	char acErrorString[200];
	cout << szErrorTxt << endl;

	if (m_pLLT->TranslateErrorValue(iErrorValue, acErrorString, sizeof(acErrorString)) >= GENERAL_FUNCTION_OK)
		cout << acErrorString << endl << endl;
}
