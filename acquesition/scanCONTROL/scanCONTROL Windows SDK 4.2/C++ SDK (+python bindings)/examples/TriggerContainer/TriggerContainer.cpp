//   TriggerContainer.cpp: demo-application for using the LLT.dll
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
#include <math.h>
#include "InterfaceLLT_2.h"
#include "TriggerContainer.h"
#include <string>
#include <sstream>

using namespace std;

static CInterfaceLLT* m_pLLT = NULL;
static unsigned int m_uiResolution = 0;
static TScannerType m_tscanCONTROLType = scanCONTROL2xxx;
//Define how many informations/fields (e.g. X,Z and timestamp) you want to extract from the container
unsigned int uiFieldCount = 3;
//Define how many profiles you want to combine into one container
unsigned int uiProfileCount = 10;
vector<unsigned char> vucContainerBuffer;

static unsigned int uiExposureTime = 100;
static unsigned int uiIdleTime = 900;


int main(int argc, char* argv[])
{
	UNREFERENCED_PARAMETER(argc);
	UNREFERENCED_PARAMETER(argv);
	vector<unsigned int> vuiInterfaces(MAX_INTERFACE_COUNT);
	vector<DWORD> vdwResolutions(MAX_RESOULUTIONS);
	vector<char> vcDeviceName(100);
	bool isv46 = true;
	unsigned int uiInterfaceCount = 0;
	bool bLoadError = false;
	int iRetValue = 0;
	bool bOK = true;
	bool bConnected = false;
	bool triggerContainerSupported = false;
	
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
			//Get Device Name
			cout << "Get the Device Name" << endl;
			if ((iRetValue = m_pLLT->GetDeviceName(&vcDeviceName[0], (unsigned int)vcDeviceName.size(), NULL, NULL)) < GENERAL_FUNCTION_OK) {
				OnError("Error during GetDeviceName", iRetValue);
					bOK = false;
			}
			else { // Convert the GetDeviceName char array to string and search for Firmware which allows Software Trigger Container feature
				isv46 = ConvertToString(&vcDeviceName[0], (unsigned int)vcDeviceName.size());
			}
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
				cout << "The scanCONTROL 1 is a scanCONTROL26xx\n\n";
			}
			else if (m_tscanCONTROLType >= scanCONTROL29xx_25 && m_tscanCONTROLType <= scanCONTROL29xx_xxx)
			{
				cout << "The scanCONTROL 1 is a scanCONTROL29xx\n\n";
			}
			else if (m_tscanCONTROLType >= scanCONTROL30xx_25 && m_tscanCONTROLType <= scanCONTROL30xx_xxx)
			{
				cout << "The scanCONTROL is a scanCONTROL30xx\n\n";
			}
			else
			{
				cout << "The scanCONTROL is a undefined type\nPlease contact Micro-Epsilon for a newer SDK\n\n";
			}

			// Check firmware version 
			if (!isv46) {
				cout << "Trigger container feature not supported - Firmware update is required\n\n";
				bOK = false;
			}


			if (bOK) {
				cout << "Get all possible resolutions\n";
				if ((iRetValue = m_pLLT->GetResolutions(&vdwResolutions[0], (unsigned int)vdwResolutions.size())) < GENERAL_FUNCTION_OK)
				{
					OnError("Error during GetResolutions", iRetValue);
					bOK = false;
				}

				m_uiResolution = vdwResolutions[0];
			}
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
			cout << "Profile config set to CONTAINER\n";
			if ((iRetValue = m_pLLT->SetProfileConfig(CONTAINER)) < GENERAL_FUNCTION_OK)
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
			TriggerContainer();
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
};


void TriggerContainer()
{	
	int iRetValue;
	unsigned char* pucContainerBuffer;
	vector<double> vdValueX(m_uiResolution *uiProfileCount);
	vector<double> vdValueZ(m_uiResolution*uiProfileCount);
	DWORD dwInquiry;
	bool noContainerReceived = true;
	DWORD dwRearrangement;
	TConvertContainerParameter param;

	// Bitfeld=Round(Log2(resolution)) for the resolution bitfield for the container
	double dTempLog = 1.0 / log(2.0);
	DWORD dwResolutionBitField = (DWORD)floor((log((double)m_uiResolution) * dTempLog) + 0.5);

	cout << "\nDemonstrate the container mode with rearrangement\n";
	if ((iRetValue = m_pLLT->GetFeature(INQUIRY_FUNCTION_PROFILE_REARRANGEMENT, &dwInquiry)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during GetFeature", iRetValue);
		return;
	}

	if ((dwInquiry & 0x80000000) == NULL)
	{
		cout << "\nThe connected scanCONTROL don't support the container mode\n\n";
		return;
	}

	// Extract X and Z
	// Insert empty field for timestamp
	// Insert timestamp
	// calculation for the points per profile = Round(Log2(resolution))
	// Extract only 1th reflection
	cout << "Set the rearangement parameter\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_PROFILE_REARRANGEMENT, CONTAINER_DATA_Z | CONTAINER_DATA_X | CONTAINER_DATA_TS |
																				CONTAINER_DATA_EMPTYFIELD4TS | CONTAINER_STRIPE_1 | 
																				dwResolutionBitField << 12)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_PROFILE_REARRANGEMENT)", iRetValue);
		return;
	}

	//Get the rearrangement settings
	if ((iRetValue = m_pLLT->GetFeature(FEATURE_FUNCTION_PROFILE_REARRANGEMENT, &dwRearrangement)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during GetFeature(FEATURE_FUNCTION_PROFILE_REARRANGEMENT)", iRetValue);
		return;
	}

	cout << "Set profile container size\n";
	if ((iRetValue = m_pLLT->SetProfileContainerSize(0, uiProfileCount)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetProfileContainerSize", iRetValue);
		return;
	}

	
	cout << "Enable container-trigger" << endl;
	if ((iRetValue = m_pLLT->ContainerTriggerEnable()) < GENERAL_FUNCTION_OK) {
		OnError("Error during Enabling Container-Trigger", iRetValue);
		return;
	}
	// Wait until all parameters are set before starting the transmission (this can take up to 120ms)
	Sleep(120);

	cout << "Enable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_CONTAINER_MODE, true)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}

	cout << "Trigger one container\n";
	m_pLLT->TriggerContainer();

	vucContainerBuffer.resize(2 * m_uiResolution * uiFieldCount * uiProfileCount);

	//Trigger one container
	while (noContainerReceived) {

		if ((iRetValue = m_pLLT->GetActualProfile(&vucContainerBuffer[0], (unsigned int)vucContainerBuffer.size(), CONTAINER, NULL)) !=
			(int)(vucContainerBuffer.size()))
		{
			noContainerReceived = true;
			Sleep((uiExposureTime+uiIdleTime)/100);
		}
		else
		{
			cout << "Container received \n\n";
			noContainerReceived = false;
		}

	}

	cout << "Converting of container data from the first reflection\n";
	//Collection of information that are needed for using the ConvertContainer2Values function
	param.pContainer = &vucContainerBuffer[0];
	param.profileRearrangement = dwRearrangement;
	param.numberOfProfilesToExtract = uiProfileCount;
	param.scannerType = m_tscanCONTROLType;
	param.reflectionNumber = 0;
	param.convertToMM = true;
	param.pReflectionWidth = nullptr;
	param.pMaxIntensity = nullptr;
	param.pThreshold = nullptr;
	param.pMoment0 = nullptr;
	param.pMoment1 = nullptr;
	param.pX = &vdValueX[0];
	param.pZ = &vdValueZ[0];

	if ((iRetValue = m_pLLT->ConvertContainer2Values(param)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during ConvertingContainer2Values", iRetValue);
		return;
	}

	DisplayProfile(&vdValueX[0], &vdValueZ[0], m_uiResolution);


	/*
    double scaling_mm = 0.0, offset_mm = 0.0;
    if ((iRetValue = GetScalingAndOffsetByType(m_tscanCONTROLType, &scaling_mm, &offset_mm)) < GENERAL_FUNCTION_OK)
    {
        OnError("Error during GetScalingAndOffsetByType", iRetValue);
        return;
    }

	// Walk through container and convert data to mm
	for (unsigned int uiProfile = 0; uiProfile < uiProfileCount; uiProfile++)
	{
		for (unsigned int i = 0; i < uiFieldCount-1; i++)
		{
			pucContainerBuffer = &vucContainerBuffer[2 * uiProfile * m_uiResolution * uiFieldCount + 2 * m_uiResolution * i];

			cout << "The first 4 points from the " << i + 1 << "th field in the " << uiProfile + 1;
			cout << "th profile in the container are:\n";

			for (unsigned int j = 0; j < 4; j++)
			{
				unsigned short usPoint = *pucContainerBuffer << 8;
				usPoint += *(pucContainerBuffer + 1);
				pucContainerBuffer += 2;
                if (i == 0)
				    cout << (usPoint - 32768) * scaling_mm + offset_mm << ", ";
                if (i == 1)
                    cout << (usPoint - 32768) * scaling_mm << ", ";
			}
			cout << "\n";
		}

		m_pLLT->Timestamp2TimeAndCount(&vucContainerBuffer[2 * (uiProfile + 1) * m_uiResolution * uiFieldCount - 16], NULL, NULL,
			&uiProfileCounter);

		cout << "Profile count from the timestamp: " << uiProfileCounter << "\n\n";
	}*/

	cout << "Disable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_CONTAINER_MODE, false)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}
	cout << "Disable container-trigger" << endl;
	if ((iRetValue = m_pLLT->ContainerTriggerDisable()) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during disabling container-trigger", iRetValue);
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

void DisplayProfile(double* pdValueX, double* pdValueZ, unsigned int uiResolution)
{
	size_t tNumberSize;


	for (unsigned int uiProfile = 0; uiProfile < 3; uiProfile++) {

		cout << "Displaying data from row:" << uiProfile << endl;


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


		cout << endl;
		DisplayTimestamp(&vucContainerBuffer[2 * (uiProfile + 1) * m_uiResolution * uiFieldCount - 16]);
	}


}

// Convert a double value to a string
std::string Double2Str(double dValue)
{
	std::ostringstream NewStreamApp;
	NewStreamApp << dValue;

	return NewStreamApp.str();
}

void DisplayTimestamp(unsigned char* pucTimestamp)
{
	double dShutterOpen, dShutterClose;
	unsigned int uiProfileCount;

	// Decode the timestamp
	m_pLLT->Timestamp2TimeAndCount(pucTimestamp, &dShutterOpen, &dShutterClose, &uiProfileCount);
	cout << "ProfileCount: " << uiProfileCount << "\n";
	cout << "\n";
}

bool ConvertToString(char *name, int size) {
	
	string DeviceName = "";
	int req_Firmware = 46;		// supports Container Trigger Feature


	for (int i = 0; i < size; i++) {
		//Search for firmware version in string
		DeviceName = DeviceName + name[i];
		if (DeviceName.find("v") != string::npos) {
			size_t found = DeviceName.find("v");
			DeviceName = "";
			for (int j = 1; j < 3; j++) {
				DeviceName = DeviceName + name[found + j];				
			}
			break;
		}
		
	}
	
	//Convert string to int
	stringstream string_to_int(DeviceName);
	int used_Firmware = 0;
	string_to_int >> used_Firmware;

	if (used_Firmware >= req_Firmware) {
		// Check if Frimware >= v46 is used
		return true;
	}
	else {
		return false;
	}
}

int GetScalingAndOffsetByType(TScannerType scanner_type, double *scaling, double *offset)
{
    double tmp_scaling = 0.0;
    double tmp_offset = 0.0;

    if (scanner_type == scanCONTROL26xx_10 || scanner_type == scanCONTROL29xx_10) {
        tmp_scaling = 0.0005;
        tmp_offset = 55.0;
	}
	else if (scanner_type == scanCONTROL26xx_25 || scanner_type == scanCONTROL29xx_25 || scanner_type == scanCONTROL25xx_25) {
        tmp_scaling = 0.001;
        tmp_offset = 65.0;
	}
	else if (scanner_type == scanCONTROL26xx_50 || scanner_type == scanCONTROL29xx_50 || scanner_type == scanCONTROL25xx_50) {
        tmp_scaling = 0.002;
        tmp_offset = 95.0;
	}
	else if (scanner_type == scanCONTROL26xx_100 || scanner_type == scanCONTROL29xx_100 || scanner_type == scanCONTROL25xx_100) {
        tmp_scaling = 0.005;
        tmp_offset = 250.0;
    } else if (scanner_type == scanCONTROL27xx_25) {
        tmp_scaling = 0.001;
        tmp_offset = 100.0;
    } else if (scanner_type == scanCONTROL27xx_50) {
        tmp_scaling = 0.002;
        tmp_offset = 210.0;
    } else if (scanner_type == scanCONTROL27xx_100) {
        tmp_scaling = 0.005;
        tmp_offset = 450.0;
    } else if (scanner_type >= scanCONTROL30xx_25) {
        DWORD scaling_nm, offset_nm;
        if ((m_pLLT->GetFeature(FEATURE_FUNCTION_CALIBRATION_SCALE, &scaling_nm)) == GENERAL_FUNCTION_OK
            && (m_pLLT->GetFeature(FEATURE_FUNCTION_CALIBRATION_OFFSET, &offset_nm)) == GENERAL_FUNCTION_OK) {
            tmp_scaling = scaling_nm / 1000000.0;
            tmp_offset = offset_nm / 1000000.0;
        } else {
            return GENERAL_FUNCTION_DEVICE_NAME_NOT_SUPPORTED;
        }
    } else {
        return GENERAL_FUNCTION_DEVICE_NAME_NOT_SUPPORTED;
    }

    if (scaling != NULL) {
        *scaling = tmp_scaling;
    }
    if (offset != NULL) {
        *offset = tmp_offset;
    }

    return GENERAL_FUNCTION_OK;
}
