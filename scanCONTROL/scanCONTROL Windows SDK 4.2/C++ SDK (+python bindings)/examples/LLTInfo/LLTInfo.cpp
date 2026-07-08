//   LLTInfo.cpp: demo-application for using the LLT.dll
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
#include "LLTInfo.h"

using namespace std;
static CInterfaceLLT* m_pLLT = NULL;

int main(int argc, char* argv[])
{
	UNREFERENCED_PARAMETER(argc);
	UNREFERENCED_PARAMETER(argv);
	vector<unsigned int> vuiInterfaces(MAX_INTERFACE_COUNT);
	unsigned int uiInterfaceCount = 0;
	bool bLoadError = false;
	int iRetValue = 0;

	// Creating a LLT-object
	// The LLT-Object will load the LLT.dll automaticly and give us a error if ther no LLT.dll
	//CInterfaceLLT box("..\\LLT.dll", &bLoadError);
	//m_pLLT = &box;
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

	for (unsigned int i = 0; i < uiInterfaceCount; i++)
	{
		GetLLTInfos(vuiInterfaces[i], i + 1);
	}

	// Deletes the LLT-object
	delete m_pLLT;

	// Wait for a keyboard hit
	while (!_kbhit()) {}

	return 0;
}



void GetLLTInfos(unsigned int uiDeviceID, unsigned int uiLLTNumber)
{
	vector<DWORD> vdwResolutions(MAX_RESOULUTIONS);
	vector<char> vcDeviceName(100);
	TScannerType m_tscanCONTROLType;
	DWORD dwSerial = 0;
	int iRetValue;
	string str;
	
	cout << "\nDemonstrate the read out of informations from the scanCONTROL\n";

	cout << "Select the device interface " << uiDeviceID << "\n";
	if ((iRetValue = m_pLLT->SetDeviceInterface(uiDeviceID, 0)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetDeviceInterface", iRetValue);
		return;
	}

	cout << "Connecting to scanCONTROL " << uiLLTNumber << "\n";
	if ((iRetValue = m_pLLT->Connect()) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during Connect", iRetValue);
		return;
	}

	cout << "Gets the device name\n";
	if ((iRetValue = m_pLLT->GetDeviceName(&vcDeviceName[0], (unsigned int)vcDeviceName.size(), NULL, NULL)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during GetDeviceName", iRetValue);

		cout << "Disconnect the scanCONTROL\n";
		if ((iRetValue = m_pLLT->Disconnect()) < GENERAL_FUNCTION_OK)
		{
			OnError("Error during Disconnect", iRetValue);
		}
		return;
	}

	cout << "Device name is " << &vcDeviceName[0] << "\n";


	
	cout << "Gets the type of the scanCONTROL\n";
	if ((iRetValue = m_pLLT->GetLLTType(&m_tscanCONTROLType)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during GetLLTType", iRetValue);

		cout << "Disconnect the scanCONTROL\n";
		if ((iRetValue = m_pLLT->Disconnect()) < GENERAL_FUNCTION_OK)
		{
			OnError("Error during Disconnect", iRetValue);
		}
		return;
	}

	if (IsMeasurementRange100(m_tscanCONTROLType))
	{
		cout << "The measurement range is 100 mm\n";
	}
	else if (IsMeasurementRange50(m_tscanCONTROLType))
	{
		cout << "The measurement range is 50 mm\n";
	}
	else if (IsMeasurementRange25(m_tscanCONTROLType))
	{
		cout << "The measurement range is 25 mm\n";
	}
	else if (IsMeasurementRange10(m_tscanCONTROLType))
	{
		cout << "The measurement range is 10 mm\n";
	}

	cout << "Gets the serial number of the scanCONTROL\n";
	if ((iRetValue = m_pLLT->GetFeature(FEATURE_FUNCTION_SERIAL, &dwSerial)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during GetSerial", iRetValue);

		cout << "Disconnect the scanCONTROL\n";
		if ((iRetValue = m_pLLT->Disconnect()) < GENERAL_FUNCTION_OK)
		{
			OnError("Error during Disconnect", iRetValue);
		}
		return;
	}

	cout << "Serial is " << dwSerial << "\n";

	// Gets the available resolutions from the scanCONTROL
	int uiResolutionCount = m_pLLT->GetResolutions(&vdwResolutions[0], (unsigned int)vdwResolutions.size());

	if (uiResolutionCount > 0)
	{
		cout << "Available resolutions: \n";
		for (int i = 0; i < uiResolutionCount; i++)
		{
			cout << "  " << vdwResolutions[i] << "\n";
		}
		cout << "\n";
	}
	else
	{
		OnError("Error during GetResolutions", iRetValue);

		cout << "Disconnect the scanCONTROL\n";
		if ((iRetValue = m_pLLT->Disconnect()) < GENERAL_FUNCTION_OK)
		{
			OnError("Error during Disconnect", iRetValue);
		}
		return;
	}

	cout << "Disconnect the scanCONTROL\n";
	if ((iRetValue = m_pLLT->Disconnect()) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during Disconnect", iRetValue);
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

/**********************************************************************************************/ /**
  * \fn	bool IsMeasurementRange10(TScannerType scanCONTROLType)
  *
  * \brief	Query if 'scanCONTROLType' is measurement range 10.
  *
  * \date	04.11.2013
  *
  * \param	scanCONTROLType	Type of the scan control.
  *
  * \return	true if measurement range 10, false if not.
  **************************************************************************************************/
bool IsMeasurementRange10(TScannerType scanCONTROLType) { return scanCONTROLType == scanCONTROL28xx_10; }

/**********************************************************************************************/ /**
  * \fn	bool IsMeasurementRange25(TScannerType scanCONTROLType)
  *
  * \brief	Query if 'scanCONTROLType' is measurement range 25.
  *
  * \date	04.11.2013
  *
  * \param	scanCONTROLType	Type of the scan control.
  *
  * \return	true if measurement range 25, false if not.
  **************************************************************************************************/
bool IsMeasurementRange25(TScannerType scanCONTROLType)
{
	return scanCONTROLType == scanCONTROL25xx_25 || scanCONTROLType == scanCONTROL26xx_25 || scanCONTROLType == scanCONTROL27xx_25 ||
		scanCONTROLType == scanCONTROL28xx_25 || scanCONTROLType == scanCONTROL29xx_25 || scanCONTROLType == scanCONTROL30xx_25;
}
/**********************************************************************************************/ /**
  * \fn	bool IsMeasurementRange50(TScannerType scanCONTROLType)
  *
  * \brief	Query if 'scanCONTROLType' is measurement range 50.
  *
  * \date	04.11.2013
  *
  * \param	scanCONTROLType	Type of the scan control.
  *
  * \return	true if measurement range 50, false if not.
  **************************************************************************************************/
bool IsMeasurementRange50(TScannerType scanCONTROLType)
{
	return scanCONTROLType == scanCONTROL25xx_50 || scanCONTROLType == scanCONTROL26xx_50 || scanCONTROLType == scanCONTROL27xx_50 || scanCONTROLType == scanCONTROL29xx_50 || scanCONTROLType == scanCONTROL30xx_50;
}

/**********************************************************************************************/ /**
  * \fn	bool IsMeasurementRange100(TScannerType scanCONTROLType)
  *
  * \brief	Query if 'scanCONTROLType' is measurement range 100.
  *
  * \date	04.11.2013
  *
  * \param	scanCONTROLType	Type of the scan control.
  *
  * \return	true if measurement range 100, false if not.
  **************************************************************************************************/

bool IsMeasurementRange100(TScannerType scanCONTROLType)
{
	return scanCONTROLType == scanCONTROL26xx_100 || scanCONTROLType == scanCONTROL27xx_100 || scanCONTROLType == scanCONTROL25xx_100 ||
		scanCONTROLType == scanCONTROL28xx_100 || scanCONTROLType == scanCONTROL29xx_100;
}