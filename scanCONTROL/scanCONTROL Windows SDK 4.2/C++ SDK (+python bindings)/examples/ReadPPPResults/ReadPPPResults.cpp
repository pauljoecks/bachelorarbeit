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
#include "ReadPPPResults.h"
#include <vector>
#include <array>

using namespace std;

CInterfaceLLT* m_pLLT = NULL;
unsigned int m_uiResolution = 0;
TScannerType m_tscanCONTROLType = scanCONTROL2xxx;

unsigned int m_uiNeededProfileCount = 10;
unsigned int m_uiReceivedProfileCount = 0;
unsigned int m_uiProfileDataSize;
HANDLE m_hProfileEvent = CreateEvent(NULL, true, false, "ProfileEvent");
vector<unsigned char> m_vucProfileBuffer;
bool isCompressedProfile = false;

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
			cout << "Check if compressed profile transmission is active\n";
			DWORD maintenance;
			if ((iRetValue = m_pLLT->GetFeature(FEATURE_FUNCTION_MAINTENANCE, &maintenance)) < GENERAL_FUNCTION_OK) {
				OnError("Error during GetFeature (FEATURE_FUNCTION_MAINTENANCE)", iRetValue);
				bOK = false;
			}
			else {
				isCompressedProfile = (bool) (maintenance & 0x1);
				cout << "Compressed: " << isCompressedProfile << endl;
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

void GetProfiles_Callback()
{
	int iRetValue;
	double offset = 85.0;  // Adapt to connected scanCONTROL type
	double scaling = 0.001; // Adapt to connected scanCONTROL type
	vector<double> vdValueX(m_uiResolution);
	vector<double> vdValueZ(m_uiResolution);
	std::vector<unsigned int> m_vucModuleResult(m_uiResolution);
	std::vector<unsigned int> m_vuiBeadResults(m_uiResolution);
	std::vector<unsigned char> m_vucModuleResultBuffer(m_uiResolution * 4);

	// Resets the event
	ResetEvent(m_hProfileEvent);

	cout << "\nDemonstrate the profile transfer via callback function\n";

	cout << "Register the callback\n";
	if ((iRetValue = m_pLLT->RegisterCallback(STD_CALL, (void*)NewProfile, 0)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during RegisterCallback", iRetValue);
		return;
	}

	// Resize the profile buffer to the estimated profile size
	m_vucProfileBuffer.resize(m_uiResolution * 64 * m_uiNeededProfileCount);

	cout << "Enable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, true)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}

	cout << "Wait for one profile\n";

	if (WaitForSingleObject(m_hProfileEvent, 1000) != WAIT_OBJECT_0)
	{
		cout << "Error getting profile over the callback \n\n";
		return;
	}

	cout << "Disable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, false)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}

	// Test the size from the profile
	if (m_uiProfileDataSize == m_uiResolution * 64)
		cout << "Profile size is OK \n";
	else
	{
		cout << "Profile size is wrong \n\n";
		return;
	}

	cout << m_uiReceivedProfileCount << " profiles have been received\n";

	cout << "Converting of profile data from the first reflection\n";
	iRetValue = m_pLLT->ConvertProfile2Values(&m_vucProfileBuffer[0], m_uiResolution, PROFILE, m_tscanCONTROLType, 0, true, NULL,
		NULL, NULL, &vdValueX[0], &vdValueZ[0], NULL, NULL);
	if (((iRetValue & CONVERT_X) == 0) || ((iRetValue & CONVERT_Z) == 0))
	{
		OnError("Error during Converting of profile data", iRetValue);
		return;
	}

	DisplayProfile(&vdValueX[0], &vdValueZ[0], m_uiResolution);

	cout << "\n\nDisplay the timestamp from the profile:";
	DisplayTimestamp(&m_vucProfileBuffer[m_uiResolution * 64 - 16]);

	
	//Extract post processing results from profile data
	if ((iRetValue = m_pLLT->ConvertProfile2ModuleResult(&m_vucProfileBuffer[0], m_vucProfileBuffer.size(), &m_vucModuleResultBuffer[0], m_vucModuleResultBuffer.size(), NULL)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during ConvertingProfile2ModuleResult", iRetValue);
		return;
	}


	//Convert m_vucModuleResultBuffer to an unsigned int Buffer
	//Data format: little endian
	for (unsigned int i = 0; i < m_uiResolution; i++) {
		m_vucModuleResult[i] = ((m_vucModuleResultBuffer[i * 4 + 3]) << 24) +
			((m_vucModuleResultBuffer[i * 4 + 2]) << 16) +
			((m_vucModuleResultBuffer[i * 4 + 1]) << 8) +
			m_vucModuleResultBuffer[i * 4];
	}	
	
	cout << "Get profile results\n";
	if (GetProfileResults(&m_vucModuleResult[0], iRetValue, false, offset, scaling) == 0)
		cout << "No post processing results appended to the profile!\n";
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
			// If the needed profile count is arrived: set the event
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

//Returns the bead results according to OPManPartC.html, "Bead Finder: Result Fields"
//@param *vucModuleResult: post processing results
//@param nModuleResultSize: size of post processing results
//@param *BeadResult: vector to write the results in
//@param beadIndex: index of the bead whose results to return
//@param littleEndian: set to true for PURE_PROFILE transmission
//@return: number of values stored in BeadResult
int GetProfileResults(unsigned int *vucModuleResult, int nModuleResultSize, bool littleEndian, double offset, double scaling)
{
	int idx = 0;
	int length = 0;
	unsigned int i, j;
	std::array<unsigned int, 15> dataArr;
	std::vector<std::array<unsigned int, 15>> vec;
	std::list<unsigned int> validHeaders = { 2, 4, 6, 7, 11, 13, 14, 15, 128, 129, 130 };
	std::list<unsigned int>::iterator it;

	// Step 1: collect Data into vector of arrays
	for (i = 0; i < nModuleResultSize; i++)
	{		
		if (!littleEndian)
		{
			//if (((vucModuleResult[i] & 0xFF000000) >> 24) == 131) // Common header
			if (((vucModuleResult[i] >> 16) == 33536)) // Common header
			{

				length = (vucModuleResult[i] & 0x000000FF);
				for (j = i + 2; j < i + length; j++) {
					// Get components of measurement value
					dataArr[0] = (vucModuleResult[j] & 0xFC000000) >> 26; // type
					dataArr[1] = (bool)((vucModuleResult[j] & 0x02000000) >> 25); // description_via_value
					dataArr[2] = (bool)((vucModuleResult[j] & 0x01000000) >> 24); // description_graphical
					dataArr[3] = (bool)((vucModuleResult[j] & 0x00800000) >> 23); // length_16_32
					dataArr[4] = (bool)((vucModuleResult[j] & 0x00400000) >> 22); // upper_lower
					dataArr[5] = (bool)((vucModuleResult[j] & 0x00200000) >> 21); // mv_valid
					dataArr[6] = (bool)((vucModuleResult[j] & 0x00100000) >> 20); // mv_name
					dataArr[7] = (bool)((vucModuleResult[j] & 0x00080000) >> 19); // mv_output
					if (dataArr[1]) { // description via value
						dataArr[8] = (vucModuleResult[j] & 0x0007FF80) >> 7; // mv_data
					}
					else { // description via pointer
						dataArr[8] = vucModuleResult[(vucModuleResult[j] & 0x0007FF80) >> 7]; // mv_data
					}
					dataArr[9] = (bool)((vucModuleResult[j] & 0x00000040) >> 6); // mask_active 
					dataArr[10] = (bool)((vucModuleResult[j] & 0x00000020) >> 5); // mv_not_show_num
					dataArr[11] = (bool)((vucModuleResult[j] & 0x00000010) >> 4); // mv_OK_NOK_available
					dataArr[12] = 0; // Reservation for OK/NOK
					dataArr[13] = (vucModuleResult[j] & 0x0000000F); // mv_len_description
					if (dataArr[13] == 2) { // mv_len_description
						j++;
						dataArr[14] = vucModuleResult[j]; // mv_mask
					}

					// append to data vector
					vec.push_back(dataArr);

					// increase number of detected values
					idx++;
				}
				break;
			}
			else 
			{
				// Fetch the iterator of element
				it = std::find(validHeaders.begin(), validHeaders.end(), ((vucModuleResult[i] >> 24) & 0xFF));
				// Check if iterator points to end or not
				if (it != validHeaders.end()) 
				{
					// Add length of result block to i to skip results of current module
					i += (int)(vucModuleResult[i] & 0x000000FF) - 1;
				}
				else if ((vucModuleResult[i]) == 0)
				{
					// Queue End
					cout << ("No results appended\n");
					break;
				}
			} 	
		}
		else {
			cout << "Module results in little endian order - conversion example for big endian only!";
		}
	}
	
	// Step 2: Add OK/NOK to array if available
	int oknok_counter = 0;
	for (int i = 0; i < vec.size(); i++) {
		if (vec.at(i)[11]) { // OK/NOK available
			// Look for OK/NOK vector
			if (vec.at(vec.size() - 1)[0] == 30) { // Type OK/NOK
				vec.at(i)[12] = (vec.at(vec.size() - 1)[8] & (1 << oknok_counter)) >> oknok_counter;
				oknok_counter++;
			}
		}
	}

	// Step 3: Calculation and Output
	for (i = 0; i < vec.size(); i++) {
		
		// Assign array values to variables
		unsigned int type = vec.at(i)[0];
		bool description_via_value = vec.at(i)[1];
		bool description_graphical = vec.at(i)[2];
		bool length_16_32 = vec.at(i)[3];
		bool upper_lower = vec.at(i)[4];
		bool mv_valid = vec.at(i)[5];
		bool mv_name = vec.at(i)[6];
		bool mv_output = vec.at(i)[7];
		unsigned int mv_data = vec.at(i)[8];
		bool mask_active = vec.at(i)[9];
		bool mv_not_show_num = vec.at(i)[10];
		bool mv_OK_NOK_available = vec.at(i)[11];
		bool mv_OK_NOK = vec.at(i)[12];
		unsigned int mv_len_description = vec.at(i)[13];
		unsigned int mv_mask = vec.at(i)[14];

		// Convert measurement value according to type:
		switch (type) {
		case 1: cout << "X: ";
			double x;
			if (length_16_32) { //32 bit length
				cout << "(32bit) ";
				x = (int)(mv_data - 32768) * scaling;
			}
			else { //16 Bit length
				if (upper_lower) { // x in lower 16 bit
					cout << "(16bit lower) ";
					x = (short)((mv_data & 0xFFFF) - 32768) * scaling;
				}
				else { // x in upper 16 bit
					cout << "(16bit upper) ";
					x = (short)(((mv_data & 0xFFFF0000) >> 16) - 32768) * scaling;
				}
			}
			
			cout << x;
			if (mv_OK_NOK_available) {
				cout << " (NOK/OK: " << mv_OK_NOK << ")";
			}
			cout << "\n";
			break;
		case 2: cout << "Z: ";
			double z;
			if (length_16_32) { //32 bit length
				cout << "(32bit) ";
				z = (int)(mv_data - 32768) * scaling + offset;
			}
			else { //16 Bit length
				if (upper_lower) { // z in lower 16 bit
					cout << "(16bit lower) ";
					z = (short)((mv_data & 0xFFFF) - 32768) * scaling + offset;
				}
				else { // z in upper 16 bit
					cout << "(16bit upper) ";
					z = (short)(((mv_data & 0xFFFF0000) >> 16) - 32768) * scaling + offset;
				}
			}
			cout << z;
			if (mv_OK_NOK_available) {
				cout << " (NOK/OK: " << mv_OK_NOK << ")";
			}
			cout << "\n";
			break;
		case 3: cout << "Binary: ";
			unsigned int bin;
			if (length_16_32) { //32 bit length
				if (mask_active) {
					bin = mv_data & mv_mask;
				}
				else {
					bin = mv_data;
				}
			}
			else { //16 Bit length
				if (upper_lower) { // bin in lower 16 bit
					bin = mv_data & 0xFFFF;
				}
				else { // bin in upper 16 bit
					bin = (mv_data & 0xFFFF0000) >> 16;
				}
			}
			cout << bin;
			if (mv_OK_NOK_available) {
				cout << " (NOK/OK: " << mv_OK_NOK << ")";
			}
			cout << "\n";
			break;
		case 4: cout << "Integer: ";
			unsigned int intvalue;
			if (mask_active) {
				cout << "(mask) ";
				intvalue = (mv_data & mv_mask);
				if (mv_mask == 0xFFF0000) { // temperature
					intvalue = intvalue >> 16;
				}
				else if (mv_mask == 0x10000000) { // laser state
					intvalue = intvalue >> 28;
				}
				else {
					; // no shift necessary for user mode and profile number
				}
			}
			else {
				if (length_16_32) { // 32 bit length
					cout << "(32bit) ";
					intvalue = mv_data;
				}
				else { // 16 bit length
					if (upper_lower) { // int in lower 16 bit
						cout << "(16bit lower) ";
						intvalue = mv_data & 0xFFFF;
					}
					else { // int in upper 16 bit
						cout << "(16bit upper) ";
						intvalue = (mv_data & 0xFFFF0000) >> 16;
					}
				}
			}
			cout << std::dec << intvalue;
			if (mv_OK_NOK_available) {
				cout << " (NOK/OK: " << mv_OK_NOK << ")";
			}
			cout << "\n";
			break;
		case 5: cout << "Distance: ";
			double distance;
			if (length_16_32) { //32 bit length
				cout << "(32bit) ";
				distance = (int)mv_data * scaling;
			}
			else { //16 Bit length
				if (upper_lower) { // distance in lower 16 bit
					cout << "(16bit lower) ";
					distance = (short)(mv_data & 0xFFFF) * scaling;
				}
				else { // distance in upper 16 bit
					cout << "(16bit upper) ";
					distance = (short)((mv_data & 0xFFFF0000) >> 16) * scaling;
				}
			}
			cout << distance;
			if (mv_OK_NOK_available) {
				cout << " (NOK/OK: " << mv_OK_NOK << ")";
			}
			cout << "\n";
			break;
		case 6: cout << "Angle: ";
			double angle;
			if (length_16_32) { //32 bit length
				cout << "(32bit) ";
				angle = (int)mv_data * 0.01;
			}
			else { //16 Bit length
				if (upper_lower) { // angle in lower 16 bit
					cout << "(16bit lower) ";
					angle = (short)(mv_data & 0xFFFF) * 0.01;
				}
				else { // angle in upper 16 bit
					cout << "(16bit upper) ";
					angle = (short)((mv_data & 0xFFFF0000) >> 16) * 0.01;
				}
			}
			cout << angle;
			if (mv_OK_NOK_available) {
				cout << " (NOK/OK: " << mv_OK_NOK << ")";
			}
			cout << "\n";
			break;
		case 7: cout << "Area: ";
			double area;
			area = (int)mv_data * scaling * scaling;
			cout << area;
			if (mv_OK_NOK_available) {
				cout << " (NOK/OK: " << mv_OK_NOK << ")";
			}
			cout << "\n";
			break;
		case 8: cout << "Point: ";
			if (length_16_32) { //32 bit length
				cout << "(32bit) ";
				unsigned int ptr_x = (mv_mask & 0xFFF00000) >> 20;
				x = (int)(vucModuleResult[ptr_x] - 32768) * scaling;
				unsigned int ptr_z = (mv_mask & 0xFFF0) >> 8;
				z = (int)(vucModuleResult[ptr_z] - 32768) * scaling + offset;
			}
			else { //16 Bit length
				cout << "(16bit) ";
				x = (int)(((mv_data & 0xFFFF0000) >> 16) - 32768) * scaling;
				z = (int)((mv_data & 0xFFFF) - 32768) * scaling + offset;
			}
			cout << x << ", " << z;
			if (mv_OK_NOK_available) {
				cout << " (NOK/OK: " << mv_OK_NOK << ")";
			}
			cout << "\n";
			break;
		case 9: cout << "Sigma: ";
			double sigma;
			if (length_16_32) { //32 bit length
				cout << "(32bit) ";
				sigma = (int)mv_data * scaling;
			}
			else { //16 Bit length
				if (upper_lower) { // sigma in lower 16 bit
					cout << "(16bit lower) ";
					sigma = (int)(mv_data & 0xFFFF) * scaling;
				}
				else { // sigma in upper 16 bit
					cout << "(16bit upper) ";
					sigma = (int)((mv_data & 0xFFFF0000) >> 16) * scaling;
				}
			}
			cout << sigma;
			if (mv_OK_NOK_available) {
				cout << " (NOK/OK: " << mv_OK_NOK << ")";
			}
			cout << "\n";
			break;
		case 10: cout << "Text: ";
			char text[4];
			if (length_16_32) { //32 bit length
				cout << "(32bit) ";
				text[0] = (mv_data >> 24) & 0xFF;
				text[1] = (mv_data >> 16) & 0xFF;
				text[2] = (mv_data >> 8) & 0xFF;
				text[3] = mv_data & 0xFF;
			}
			else { //16 Bit length
				if (upper_lower) { // text in lower 16 bit
					cout << "(16bit lower) ";
					text[0] = (mv_data >> 8) & 0xFF;
					text[1] = mv_data & 0xFF;
				}
				else { // text in upper 16 bit
					cout << "(16bit upper) ";
					text[0] = (mv_data >> 24) & 0xFF;
					text[1] = (mv_data >> 16) & 0xFF;
				}
			}
			for each (char var in text)
				cout << var;
			cout << "\n";
			break;
		case 30: cout << "OK/NOK: ";
			if (length_16_32) { // 32 bit length
				cout << "(32bit) ";
				cout << std::dec << mv_data << "\n";
			}
			else { // 16 bit length
				if (upper_lower) { // int in lower 16 bit
					cout << "(16bit lower) ";
					cout << std::dec << (mv_data & 0xFFFF) << "\n";
				}
				else { // int in upper 16 bit
					cout << "(16bit upper) ";
					cout << std::dec << (mv_data & 0xFFFF0000) << "\n";
				}
			}
			break;
		default: cout << "Unknown (" << type << ") \n"; break;
		}
	}
	return idx;
}