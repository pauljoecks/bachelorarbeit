//   GetProfiles_Callback.cpp: demo-application for using the LLT.dll
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
#include "SaveAvis.h"
#include "AVIWriter.h"
#include <Windows.h>
#include <stdlib.h>
#include <deque>

using namespace std;

CInterfaceLLT* m_pLLT = NULL;
unsigned int m_uiResolution = 0;
TScannerType m_tscanCONTROLType = scanCONTROL2xxx;
TPartialProfile tPartialProfile;


unsigned int m_uiNeededProfileCount = 100;
static unsigned int m_uiReceivedProfileCount = 0;
unsigned int m_uiProfileDataSize;
HANDLE m_hProfileEvent = CreateEvent(NULL, true, false, "ProfileEvent");
vector<unsigned char> m_vucProfileBuffer;
vector<unsigned char> m_vucProfileBuffer1;
unsigned int counter = 0;

// Create an instance of the AviWriter class  
AviWriter save_avi;

int main(int argc, char* argv[])
{
	UNREFERENCED_PARAMETER(argc);
	UNREFERENCED_PARAMETER(argv);

	vector<unsigned int> vuiInterfaces(MAX_INTERFACE_COUNT);
	vector<DWORD> vdwResolutions(MAX_RESOULUTIONS);
	vector <char> vcDeviceName(100);
	unsigned int uiInterfaceCount = 0;
	unsigned int uiExposureTime = 100;
	unsigned int uiIdleTime = 900;
	DWORD serial_number = 0;
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
			//Get Device Name
			if ((iRetValue = m_pLLT->GetDeviceName(&vcDeviceName[0], (unsigned int)vcDeviceName.size(), NULL, NULL)) < GENERAL_FUNCTION_OK) {
				OnError("Error during GetDeviceName", iRetValue);
				bOK = false;
			}
		}

		if (bOK) {

			//Get serial number
			if ((iRetValue = m_pLLT->GetFeature(FEATURE_FUNCTION_SERIAL_NUMBER, &serial_number)) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during GetDeviceName", iRetValue);
				bOK = false;
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
			bOK = SaveAvis_FullSet(vcDeviceName, serial_number);
		}

		if (bOK)
		{
			bOK = SaveAvis_Quarter(vcDeviceName, serial_number);
		}

		if (bOK)
		{
			bOK = SaveAvis_Pure(vcDeviceName, serial_number);
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

// Write profiles with FullSet to AviFile
bool SaveAvis_FullSet(vector<char> &device_name, DWORD &SerialNumber)
{
	int iRetValue;
	unsigned int profileNumber = 0;
	static const char* AVI_FILENAME = "./SaveAvis_FullSet.AVI";
	vector<double> vdValueX(m_uiResolution);
	vector<double> vdValueZ(m_uiResolution);
	int bytesWritten = 0;
	unsigned int uiProfilesize = 25;
	m_uiProfileDataSize = 0;

	cout << "\nDemonstrate the SaveProfiles-Routine with FullSet" << endl;

	cout << "Register the callback\n";
	if ((iRetValue = m_pLLT->RegisterCallback(STD_CALL, (void*)NewProfile, (void*)1)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during RegisterCallback", iRetValue);
		return false;
	}
	
	cout << "Set Profile config to PROFILE\n";
	if ((iRetValue = m_pLLT->SetProfileConfig(PROFILE)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetProfileConfig", iRetValue);
		return false;
	}
	
	//collection of informations that are needed to build the avi header
	AviInfo header;
	header.serial = SerialNumber;
	header.rearrangement = 0;
	header.maintenance = 0x00000002;
	header.extended1 = 0xffffffff;
	header.profile_config = PROFILE;
	header.partial_config.nPointCount = 0;
	header.partial_config.nPointDataWidth = 0;
	header.partial_config.nStartPoint = 0;
	header.partial_config.nStartPointData = 0;
	header.name = &device_name[0];
	header.size.width = 64;
	header.size.height = m_uiResolution;
	header.version = 2;

	// SetMaxFilesize to x byte
	save_avi.SetMaxFileSize(2000000);

	//Set the amount of profiles for recording
	save_avi.SetMaxProfileSize(uiProfilesize);

	// Generate the avi header
	save_avi.init(AVI_FILENAME, header);	
		
	// Resize the profile buffer to the estimated profile size
	m_vucProfileBuffer.resize(m_uiResolution * 64 );

	cout << "Enable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, true)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return false;
	}

	cout << "Write every uneven profile to AviFile" << endl;

	unsigned int ProfileSaved = 0;

	// Save avis until the needed profile count is arrived
	while (m_uiReceivedProfileCount < m_uiNeededProfileCount) {

		//Wait until a profile arrives
		if (WaitForSingleObject(m_hProfileEvent, 1000) != WAIT_OBJECT_0)
		{
			cout << "Error getting profile over the callback \n\n";
			return false;
		}

		//Read back the profileNumber
		profileNumber = DisplayTimestamp(&m_vucProfileBuffer[m_uiResolution * 64 - 16]);

		// Write every uneven profile to AviFile
		if ((profileNumber % 2) != 0) {
			if (m_uiProfileDataSize != m_uiResolution * 64) {
				continue;
			}
			else {
				bytesWritten = save_avi.WriteBufferToAVIFile(m_vucProfileBuffer);
				ProfileSaved++;
				if (bytesWritten == 0) {
					cout << "Error during saving!" << endl;
					break;
				}
				else if (bytesWritten == -1) { // Error or maxFileSize reached
					cout << "Max filesize reached!\n";
					break;
				}
				else if (bytesWritten == -2) {//maxprofilesize reached
					cout << "Max Profilesize reached!" << endl;
					break;
				}
			}
		}

		// Reset the event
		ResetEvent(m_hProfileEvent);
	
	}
	
	cout << "Disable SavingProfiles" << endl;
	save_avi.~AviWriter();

	cout << (ProfileSaved-1) << " profiles have been saved!\n";
		
	cout << "Disable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, false)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return false;
	}

	cout << "De-Register Callback" << endl;
	if ((iRetValue = m_pLLT->RegisterCallback(STD_CALL, NULL, (void*)1)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during DeRegisterCallback", iRetValue);
		return false;
	}

	return true;
}

// Write Profiles with X/Z + data to AviFile
bool SaveAvis_Quarter(vector<char> &device_name, DWORD &SerialNumber) {

	int iRetValue;
	unsigned int profileNumber = 0;
	TPartialProfile tPartialProfile;
	static const char* AVI_FILENAME = "./SaveAvis_Quarter.AVI";
	vector<double> vdValueX(m_uiResolution);
	vector<double> vdValueZ(m_uiResolution);
	int bytesWritten = 0;
	unsigned int uiProfilesize = 35;
	m_uiProfileDataSize = 0;

	cout << "\nDemonstrate the SaveProfiles-Routine with full resolution and one reflection (X/Z + data)" << endl;

	cout << "Register the callback\n";
	if ((iRetValue = m_pLLT->RegisterCallback(STD_CALL, (void*)NewProfile, (void*)2)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during RegisterCallback", iRetValue);
		return false;
	}

	cout << "Set Profile config to PARTIAL_PROFILE\n";
	if ((iRetValue = m_pLLT->SetProfileConfig(PARTIAL_PROFILE)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetProfileConfig", iRetValue);
	}

	// Struct for a partial transfer with the full resolution and only one reflection (like QUARTER_PROFILE)
	tPartialProfile.nStartPoint = 0;              // Transfer starts at point 0 (as row)
	tPartialProfile.nStartPointData = 0;          // Transfer starts at data position 0 (as column)
	tPartialProfile.nPointCount = m_uiResolution; // Transfer size are the full resolution
	tPartialProfile.nPointDataWidth = 16;         // Transfer size of the transfered data is 16

	// Set partial prfole config
	if ((iRetValue = m_pLLT->SetPartialProfile(&tPartialProfile)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetPartialProfile", iRetValue);
		return false;
	}

	//collection of informations that are needed to build the avi header
	AviInfo header;
	header.serial = SerialNumber;
	header.rearrangement = 0;
	header.maintenance = 0x00000002;
	header.extended1 = 0xffffffff;
	header.profile_config = PARTIAL_PROFILE;
	header.partial_config.nPointCount = tPartialProfile.nPointCount;
	header.partial_config.nPointDataWidth = tPartialProfile.nPointDataWidth;
	header.partial_config.nStartPoint = tPartialProfile.nStartPoint;
	header.partial_config.nStartPointData = tPartialProfile.nStartPointData;
	header.name = &device_name[0];
	header.size.width = tPartialProfile.nPointDataWidth;
	header.size.height = tPartialProfile.nPointCount;
	header.version = 2;

	// SetMaxFilesize to x byte
	save_avi.SetMaxFileSize(2000000);

	//Set the amount of profiles for recording
	save_avi.SetMaxProfileSize(uiProfilesize);

	// Generate the avi header
	save_avi.init(AVI_FILENAME, header);

	// Resize the profile buffer to the estimated profile size
	m_vucProfileBuffer.resize(tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth);

	cout << "Enable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, true)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return false;
	}

	// Reset the counter
	m_uiReceivedProfileCount = 0;

	cout << "Write every uneven profile to AviFile" << endl;

	unsigned int ProfileSaved = 0;

	// Save avis until the needed profile count is arrived
	while (m_uiReceivedProfileCount < m_uiNeededProfileCount) {

	
		//Wait until a profile arrives
		if (WaitForSingleObject(m_hProfileEvent, 1000) != WAIT_OBJECT_0)
		{
			cout << "Error getting profile over the callback \n\n";
			return false;
		}

		//Read back the profileNumber
		profileNumber = DisplayTimestamp(&m_vucProfileBuffer[tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth - 16]);

		// Write every uneven profile to AviFile
		if ((profileNumber % 2) != 0) {
			if (m_uiProfileDataSize != tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth) {
				continue;
			}
			else {
				bytesWritten = save_avi.WriteBufferToAVIFile(m_vucProfileBuffer);
				ProfileSaved++;
				//cout << bytesWritten << endl;
				if (bytesWritten == 0) {
					cout << "Error during saving" << endl;
					break;
				}
				if (bytesWritten == -1) { // maxFileSize reached
					cout << "Max filesize reached!\n";
					break;
				}
				else if (bytesWritten == -2) {//amount of profiles reached
					cout << "Max Profilesize reached!" << endl;
					break;
				}
			}
		}

		// Reset the event
		ResetEvent(m_hProfileEvent);

	}

	cout << "Disable SavingProfiles" << endl;
	save_avi.~AviWriter();

	cout << (ProfileSaved-1) << " profiles have been saved!\n";


	cout << "Disable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, false)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return false;
	}

	cout << "De-Register Callback" << endl;
	if ((iRetValue = m_pLLT->RegisterCallback(STD_CALL, NULL, (void*)2)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during DeRegisterCallback", iRetValue);
		return false;
	}

	return true;
}

// Write profile with only X/Z data to AviFile
bool SaveAvis_Pure(vector<char> &device_name, DWORD &SerialNumber) {

	int iRetValue;
	unsigned int profileNumber = 0;
	int bytesWritten = 0;
	TPartialProfile tPartialProfile;
	static const char* AVI_FILENAME = "./SaveAvis_Pure.AVI";
	vector<double> vdValueX(m_uiResolution);
	vector<double> vdValueZ(m_uiResolution);
	unsigned int uiProfilesize = 13;
	m_uiProfileDataSize = 0;

	cout << "\nDemonstrate the SaveProfiles-Routine with full resolution and only X/Z values" << endl;

	cout << "Register the callback\n";
	if ((iRetValue = m_pLLT->RegisterCallback(STD_CALL, (void*)NewProfile, (void*)3)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during RegisterCallback", iRetValue);
		return false;
	}


	cout << "Set Profile config to PARTIAL_PROFILE\n";
	if ((iRetValue = m_pLLT->SetProfileConfig(PARTIAL_PROFILE)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetProfileConfig", iRetValue);
	}

	// Struct for a partial transfer with the full resolution and only one reflection (like QUARTER_PROFILE)
	tPartialProfile.nStartPoint = 0;              // Transfer starts at point 0 (as row)
	tPartialProfile.nStartPointData = 4;          // Transfer starts at data position 4 (as column)
	tPartialProfile.nPointCount = m_uiResolution; // Transfer size are the full resolution
	tPartialProfile.nPointDataWidth = 4;         // Transfer size of the transfered data is 4

	// Set partial prfole config
	if ((iRetValue = m_pLLT->SetPartialProfile(&tPartialProfile)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetPartialProfile", iRetValue);
		return false;
	}

	//collection of informations that are needed to build the avi header
	AviInfo header;
	header.serial = SerialNumber;
	header.rearrangement = 0;
	header.maintenance = 0x00000002;
	header.extended1 = 0xffffffff;
	header.profile_config = PARTIAL_PROFILE;
	header.partial_config.nPointCount = tPartialProfile.nPointCount;
	header.partial_config.nPointDataWidth = tPartialProfile.nPointDataWidth;
	header.partial_config.nStartPoint = tPartialProfile.nStartPoint;
	header.partial_config.nStartPointData = tPartialProfile.nStartPointData;
	header.name = &device_name[0];
	header.size.width = tPartialProfile.nPointDataWidth;
	header.size.height = tPartialProfile.nPointCount;
	header.version = 2;

	// SetMaxFilesize to x byte
	save_avi.SetMaxFileSize(2000000);

	//Set the amount of profiles for recording
	save_avi.SetMaxProfileSize(uiProfilesize);

	// Generate the avi header
	save_avi.init(AVI_FILENAME, header);

	// Resize the profile buffer to the estimated profile size
	m_vucProfileBuffer.resize(tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth);
	
	cout << "Enable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, true)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return false;
	}

	// Reset the counter
	m_uiReceivedProfileCount = 0;

	cout << "Write every uneven profile to AviFile" << endl;

	unsigned int ProfileSaved = 0;

	// Save avis until the needed profile count is arrived
	while (m_uiReceivedProfileCount < m_uiNeededProfileCount) {

		//Wait until a profile arrives
		if (WaitForSingleObject(m_hProfileEvent, 1000) != WAIT_OBJECT_0)
		{
			cout << "Error getting profile over the callback \n\n";
			return false;
		}

		//Read back the profileNumber
		profileNumber = DisplayTimestamp(&m_vucProfileBuffer[tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth - 16]);

		// Write every uneven profile to AviFile
		if ((profileNumber % 2) != 0) {
			if (m_uiProfileDataSize != tPartialProfile.nPointCount * tPartialProfile.nPointDataWidth) {
				continue;
			}
			else {
				bytesWritten = save_avi.WriteBufferToAVIFile(m_vucProfileBuffer);
				ProfileSaved++;
				if (bytesWritten == 0) {
					cout << "Error during saving" << endl;
					break;
				}
				if (bytesWritten == -1) { // maxFileSize reached
					cout << "Max filesize reached!\n";
					break;
				}
				else if (bytesWritten == -2) {//amount of profiles reached
					cout << "Max Profilesize reached!" << endl;
					break;
				}
			}
		}

		// Reset the event
		ResetEvent(m_hProfileEvent);

	}

	cout << "Disable SavingProfiles" << endl;
	save_avi.~AviWriter();

	cout << (ProfileSaved-1) << " profiles have been saved!\n";

	cout << "Disable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, false)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return false;
	}

	cout << "De-Register Callback" << endl;
	if ((iRetValue = m_pLLT->RegisterCallback(STD_CALL, NULL, (void*)3)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during DeRegisterCallback", iRetValue);
		return false;
	}

	return true;
}

// Callback function
void __stdcall NewProfile(const unsigned char* pucData, unsigned int uiSize, void* pUserData)
{
	if (uiSize > 0)
	{
		m_uiProfileDataSize = uiSize;
		if (m_uiReceivedProfileCount < m_uiNeededProfileCount) {

			//If the needed profile count not arrived: copy the profile data to the buffer for every new profile received
			//cout << "Size: " << uiSize << endl;
			memcpy(&m_vucProfileBuffer[0], pucData, uiSize);
			// once a profile arrives: set the event			
			m_uiReceivedProfileCount++;

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


// Convert a double value to a string
std::string Double2Str(double dValue)
{
	std::ostringstream NewStreamApp;
	NewStreamApp << dValue;

	return NewStreamApp.str();
}

// Displays the timestamp
unsigned int DisplayTimestamp(unsigned char* pucTimestamp)
{
	double dShutterOpen, dShutterClose;
	unsigned int uiProfileCount;

	// Decode the timestamp
	m_pLLT->Timestamp2TimeAndCount(pucTimestamp, &dShutterOpen, &dShutterClose, &uiProfileCount);

	return uiProfileCount;
}


