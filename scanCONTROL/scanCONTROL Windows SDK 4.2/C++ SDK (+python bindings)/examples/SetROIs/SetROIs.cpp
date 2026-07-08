//   SetROIs.cpp: demo-application for using the LLT.dll
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
#include "SetROIs.h"

using namespace std;

CInterfaceLLT* m_pLLT = NULL;
unsigned int m_uiResolution = 0;
TScannerType m_tscanCONTROLType = scanCONTROL2xxx;
double raster_x = 0;
double raster_z = 0;

unsigned int m_uiNeededProfileCount = 10;
unsigned int m_uiReceivedProfileCount = 0;
unsigned int m_uiProfileDataSize;
HANDLE m_hProfileEvent = CreateEvent(NULL, true, false, "ProfileEvent");
vector<unsigned char> m_vucProfileBuffer;

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
				raster_x = 1.25;
				raster_z = 100.0 / 480.0;
            }
			else if (m_tscanCONTROLType >= scanCONTROL25xx_25 && m_tscanCONTROLType <= scanCONTROL25xx_xxx)
			{
				cout << "The scanCONTROL is a scanCONTROL25xx\n\n";
				raster_x = 2.5;
				raster_z = 100.0 / 1024.0;
			}
            else if (m_tscanCONTROLType >= scanCONTROL26xx_25 && m_tscanCONTROLType <= scanCONTROL26xx_xxx)
            {
                cout << "The scanCONTROL is a scanCONTROL26xx\n\n";
				raster_x = 1.25;
				raster_z = 100.0 / 480.0;
            } 
            else if (m_tscanCONTROLType >= scanCONTROL29xx_25 && m_tscanCONTROLType <= scanCONTROL29xx_xxx)
            {
                cout << "The scanCONTROL is a scanCONTROL29xx\n\n";
				raster_x = 2.5;
				raster_z = 100.0 / 1024.0;
            } 
            else if (m_tscanCONTROLType >= scanCONTROL30xx_25 && m_tscanCONTROLType <= scanCONTROL30xx_xxx)
            {
                cout << "The scanCONTROL is a scanCONTROL30xx\n\n";
				raster_x = 1.5625;
				raster_z = 200.0 / 1088.0;
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
			if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME, uiExposureTime | EXPOSURE_AUTOMATIC)) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during SetFeature(FEATURE_FUNCTION_EXPOSURE_TIME)", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			cout << "Set idle time to " << uiIdleTime << "\n\n";
			if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_IDLE_TIME, uiIdleTime)) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during SetFeature(FEATURE_FUNCTION_IDLE_TIME)", iRetValue);
				bOK = false;
			}
		}

		if (bOK)
		{
			SetROI1();
		}

		if (bOK)
		{
			SetROI2();
		}

		if (bOK)
		{
			SetRONI();
		}

		if (bOK)
		{
			SetROIAutoExposure();
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

void SetROI1()
{
	int iRetValue; 
	unsigned short col_start;
	unsigned short col_size;
	unsigned short row_start;
	unsigned short row_size;

	// Percentage X/Z of ROI
	double start_z = 10.0;
	double end_z = 90.0;
	double start_x = 10.0;
	double end_x = 45.0;

	cout << "ROI1 Start Z (%): " << start_z << "\n";
	cout << "ROI1 End Z (%): " << end_z << "\n";
	cout << "ROI1 Start X (%): " << start_x << "\n";
	cout << "ROI1 End X (%): " << end_x << "\n";

	if (m_tscanCONTROLType >= scanCONTROL26xx_25 && m_tscanCONTROLType <= scanCONTROL26xx_xxx) {
		col_start = USHORT(65535 - ((round(end_x / raster_x) * raster_x) / 100 * 65535));
		col_size = USHORT(round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
		row_start = USHORT(round(start_z / raster_z) * raster_z / 100 * 65536);
		row_size = USHORT(round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
	}
	else if (m_tscanCONTROLType >= scanCONTROL25xx_25 && m_tscanCONTROLType <= scanCONTROL25xx_xxx) {
		col_start = USHORT(65535 - ((round(end_x / raster_x) * raster_x) / 100 * 65535));
		col_size = USHORT(round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
		row_start = USHORT(65535 - ((round(end_z / raster_x) * raster_x) / 100 * 65535));
		row_size = USHORT(round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
	}
	else if (m_tscanCONTROLType >= scanCONTROL27xx_25 && m_tscanCONTROLType <= scanCONTROL27xx_xxx) {
		col_start = USHORT(65535 - ((round(end_x / raster_x) * raster_x) / 100 * 65535));
		col_size = USHORT(round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
		row_start = USHORT(65535 - ((round(end_z / raster_x) * raster_x) / 100 * 65535));
		row_size = USHORT(round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
	}
	else if (m_tscanCONTROLType >= scanCONTROL29xx_25 && m_tscanCONTROLType <= scanCONTROL29xx_xxx) {
		col_start = USHORT(65535 - ((round(end_x / raster_x) * raster_x) / 100 * 65535));
		col_size = USHORT(round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
		row_start = USHORT(65535 - ((round(end_z / raster_x) * raster_x) / 100 * 65535));
		row_size = USHORT(round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
	} 
	else if (m_tscanCONTROLType >= scanCONTROL30xx_25 && m_tscanCONTROLType <= scanCONTROL30xx_xxx)
	{
		col_start = USHORT(round(start_x / raster_x) * raster_x / 100 * 65536);
		col_size = USHORT(round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
		row_start = USHORT(round(start_z / raster_z) * raster_z / 100 * 65536);
		row_size = USHORT(round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
	}
	else {
		cout << "The scanCONTROL is a undefined type\nPlease contact Micro-Epsilon for a newer SDK\n\n";
		return;
	}

	cout << "Enable ROI1 free region\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_ROI1_PRESET, 0x800)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_PRESET)", iRetValue);
	}

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

	cout << "Activate ROI1 free region \n\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER)", iRetValue);
	}
}

void SetROI2()
{
	int iRetValue;
	DWORD tmp;
	unsigned short col_start;
	unsigned short col_size;
	unsigned short row_start;
	unsigned short row_size;

	// Percentage X/Z of ROI
	double start_z = 10.0;
	double end_z = 90.0;
	double start_x = 55.0;
	double end_x = 90.0;

	cout << "ROI2 Start Z (%): " << start_z << "\n";
	cout << "ROI2 End Z (%): " << end_z << "\n";
	cout << "ROI2 Start X (%): " << start_x << "\n";
	cout << "ROI2 End X (%): " << end_x << "\n";

	if (m_tscanCONTROLType >= scanCONTROL30xx_25 && m_tscanCONTROLType <= scanCONTROL30xx_xxx)
	{
		col_start = USHORT(round(start_x / raster_x) * raster_x / 100 * 65536);
		col_size = USHORT(round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
		row_start = USHORT(round(start_z / raster_z) * raster_z / 100 * 65536);
		row_size = USHORT(round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
	}
	else {
		cout << "ROI 2 cannot be set for this scanCONTROL type\n\n";
		return;
	}

	cout << "Enable ROI2 free region\n";
	if ((iRetValue = m_pLLT->GetFeature(FEATURE_FUNCTION_IMAGE_FEATURES, &tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during GetFeature(FEATURE_FUNCTION_IMAGE_FEATURES)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_IMAGE_FEATURES, tmp | 0x1)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_IMAGE_FEATURES)", iRetValue);
	}

	cout << "Set ROI2_Position parameter \n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_ROI2_POSITION, (col_start << 16) + col_size)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_ROI2_POSITION)", iRetValue);
	}
	cout << "Set ROI2_Distance parameter\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_ROI2_DISTANCE, (row_start << 16) + row_size)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_ROI2_DISTANCE)", iRetValue);
	}
}


void SetRONI()
{
	int iRetValue;
	DWORD tmp;
	unsigned short col_start;
	unsigned short col_size;
	unsigned short row_start;
	unsigned short row_size;

	// Percentage X/Z of ROI
	double start_z = 35.0;
	double end_z = 55.0;
	double start_x = 30.0;
	double end_x = 70.0;

	cout << "RONI Start Z (%): " << start_z << "\n";
	cout << "RONI End Z (%): " << end_z << "\n";
	cout << "RONI Start X (%): " << start_x << "\n";
	cout << "RONI End X (%): " << end_x << "\n";
	
	if (m_tscanCONTROLType >= scanCONTROL30xx_25 && m_tscanCONTROLType <= scanCONTROL30xx_xxx)
	{
		col_start = USHORT(round(start_x / raster_x) * raster_x / 100 * 65536);
		col_size = USHORT(round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
		row_start = USHORT(round(start_z / raster_z) * raster_z / 100 * 65536);
		row_size = USHORT(round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
	}
	else {
		cout << "RONI cannot be set for this scanCONTROL type\n\n";
		return;
	}

	cout << "Enable RONI free region\n";
	if ((iRetValue = m_pLLT->GetFeature(FEATURE_FUNCTION_IMAGE_FEATURES, &tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during GetFeature(FEATURE_FUNCTION_IMAGE_FEATURES)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_IMAGE_FEATURES, tmp | 0x2)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_IMAGE_FEATURES)", iRetValue);
	}

	cout << "Set RONI_Position parameter \n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_RONI_POSITION, (col_start << 16) + col_size)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_RONI_POSITION)", iRetValue);
	}
	cout << "Set RONI_Distance parameter\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_RONI_DISTANCE, (row_start << 16) + row_size)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_RONI_DISTANCE)", iRetValue);
	}
}

void SetROIAutoExposure()
{
	int iRetValue;
	DWORD tmp;
	unsigned short col_start;
	unsigned short col_size;
	unsigned short row_start;
	unsigned short row_size;

	// Percentage X/Z of ROI
	double start_z = 5.0;
	double end_z = 95.0;
	double start_x = 5.0;
	double end_x = 95.0;

	cout << "ROI auto exposure Start Z (%): " << start_z << "\n";
	cout << "ROI auto exposure End Z (%): " << end_z << "\n";
	cout << "ROI auto exposure Start X (%): " << start_x << "\n";
	cout << "ROI auto exposure End X (%): " << end_x << "\n";

	if (m_tscanCONTROLType >= scanCONTROL30xx_25 && m_tscanCONTROLType <= scanCONTROL30xx_xxx)
	{
		col_start = USHORT(round(start_x / raster_x) * raster_x / 100 * 65536);
		col_size = USHORT(round((end_x - start_x) / raster_x) * raster_x / 100 * 65535);
		row_start = USHORT(round(start_z / raster_z) * raster_z / 100 * 65536);
		row_size = USHORT(round((end_z - start_z) / raster_z) * raster_z / 100 * 65535);
	}
	else {
		cout << "ROI auto exposure cannot be set for this scanCONTROL type\n\n";
		return;
	}

	cout << "Enable auto exposure region\n";
	if ((iRetValue = m_pLLT->GetFeature(FEATURE_FUNCTION_IMAGE_FEATURES, &tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during GetFeature(FEATURE_FUNCTION_IMAGE_FEATURES)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_IMAGE_FEATURES, tmp | 0x4)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_IMAGE_FEATURES)", iRetValue);
	}

	cout << "Set ROI auto exposure position parameter \n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EA_REFERENCE_REGION_POSITION, (col_start << 16) + col_size)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_ROI1_POSITION)", iRetValue);
	}
	cout << "Set ROI auto exposure distance parameter\n";
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EA_REFERENCE_REGION_DISTANCE, (row_start << 16) + row_size)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(FEATURE_FUNCTION_EA_REFERENCE_REGION_DISTANCE)", iRetValue);
	}
}

void GetProfiles_Callback()
{
	int iRetValue;
	vector<double> vdValueX(m_uiResolution);
	vector<double> vdValueZ(m_uiResolution);

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
