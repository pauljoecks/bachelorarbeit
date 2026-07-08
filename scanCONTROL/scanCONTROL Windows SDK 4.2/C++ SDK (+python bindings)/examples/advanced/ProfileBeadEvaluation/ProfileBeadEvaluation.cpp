//   GetProfiles_Poll.cpp: demo-application for using the LLT.dll
//
//   Version 3.0.0.0
//
//   Copyright 2009
//
//   Sebastian Lueth
//   MICRO-EPSILON Optronic GmbH
//   Lessingstrasse 14
//   01465 Dresden OT Langebrueck
//   Germany
//---------------------------------------------------------------------------

#include "GetProfiles_Poll.h"
#include "InterfaceLLT_2.h"
#include "stdafx.h"
#include <conio.h>
#include <iostream>

using namespace std;

int main(int argc, char *argv[])
{
	std::vector<unsigned int> vuiInterfaces(MAX_INTERFACE_COUNT);
	std::vector<DWORD> vdwResolutions(MAX_RESOULUTIONS);
	unsigned int uiInterfaceCount = 0;
	unsigned int uiShutterTime = 100;
	unsigned int uiIdleTime = 900;
	bool bLoadError = false;
	int iRetValue = 0;
	bool bOK = true;
	bool bConnected = false;
	m_uiResolution = 0;

	// Creating a LLT-object
	// The LLT-Object will load the LLT.dll automaticly and give us a error if ther no LLT.dll
	m_pLLT = new CInterfaceLLT("LLT.dll", &bLoadError);

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
		uiInterfaceCount = vuiInterfaces.size();
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
				cout << "Can't decode scanCONTROL type. Please contact Micro-Epsilon for a newer version of the "
					"LLT.dll.\n";
			}

			if (m_tscanCONTROLType >= scanCONTROL28xx_25 && m_tscanCONTROLType <= scanCONTROL28xx_xxx)
			{
				cout << "The scanCONTROL is a scanCONTROL28xx\n\n";
			}
			else if (m_tscanCONTROLType >= scanCONTROL27xx_25 && m_tscanCONTROLType <= scanCONTROL27xx_xxx)
			{
				cout << "The scanCONTROL is a scanCONTROL27xx\n\n";
			}
			else
			{
				cout << "The scanCONTROL is a undefined type\nPlease contact Micro-Epsilon for a newer SDK\n\n";
			}

			cout << "Get all possible resolutions\n";
			if ((iRetValue = m_pLLT->GetResolutions(&vdwResolutions[0], vdwResolutions.size())) < GENERAL_FUNCTION_OK)
			{
				OnError("Error during GetResolutions", iRetValue);
				bOK = false;
			}

			m_uiResolution = vdwResolutions[2];
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
	int iNoOfResults;
	std::vector<double> vdValueX(m_uiResolution);
	std::vector<double> vdValueZ(m_uiResolution);
	// Resize the profile buffer to the maximal profile size
	std::vector<unsigned char> vucProfileBuffer(m_uiResolution * 64);
	std::vector<unsigned char> vucModuleResult(m_uiResolution * 64);
	std::vector<unsigned int> vuiBeadResults(39); // max 39 results of a bead possible

	cout << "\nDemonstrate the profile transfer via poll function\n";

	cout << "Gets the type of the scanCONTROL (measurement range)\n";

	cout << "Enable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, true)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}

	// Sleep for a while to warm up the transfer
	Sleep(1000);

	// Gets 1 profile in "polling-mode" and PROFILE configuration
	if ((iRetValue = m_pLLT->GetActualProfile(&vucProfileBuffer[0], (unsigned int)vucProfileBuffer.size(), PROFILE,
		NULL)) != vucProfileBuffer.size())
	{
		OnError("Error during GetActualProfile", iRetValue);
		return;
	}
	cout << "Get profile in polling-mode and PURE_PROFILE configuration OK \n";

	cout << "Converting of profile data from the first reflection\n";
	iRetValue = m_pLLT->ConvertProfile2Values(&vucProfileBuffer[0], m_uiResolution, PROFILE, m_tscanCONTROLType, 0,
		true, NULL, NULL, NULL, &vdValueX[0], &vdValueZ[0], NULL, NULL);
	if (((iRetValue & CONVERT_X) == 0) || ((iRetValue & CONVERT_Z) == 0))
	{
		OnError("Error during Converting of profile data", iRetValue);
		return;
	}

	cout << "Disable the measurement\n";
	if ((iRetValue = m_pLLT->TransferProfiles(NORMAL_TRANSFER, false)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during TransferProfiles", iRetValue);
		return;
	}

	cout << "Extract post-processing results from the fourth stripe\n";
	iRetValue = m_pLLT->ConvertProfile2ModuleResult(&vucProfileBuffer[0], (unsigned int)vucProfileBuffer.size(),
		&vucModuleResult[0], (unsigned int)vucModuleResult.size());

	cout << "Proceed post-processing results\n";
	iNoOfResults = GetBeadResults(&vucModuleResult[0], iRetValue, &vuiBeadResults[0], 0, false);
	cout << "Number of valid results: " << iNoOfResults << "\n";
	cout << "\nDisplay post-processing results:\n";
	DisplayPPP(&vuiBeadResults[0], iNoOfResults, 75.0, 0.0005); // Adjust values depending on sensor type

	cout << "Proceed post-processing results\n";
	iNoOfResults = GetBeadResults(&vucModuleResult[0], iRetValue, &vuiBeadResults[0], 1, false);
	cout << "Number of valid results: " << iNoOfResults << "\n";
	cout << "\nDisplay post-processing results:\n";
	DisplayPPP(&vuiBeadResults[0], iNoOfResults, 75.0, 0.0005); // Adjust values depending on sensor type

	cout << "Proceed post-processing results\n";
	iNoOfResults = GetBeadResults(&vucModuleResult[0], iRetValue, &vuiBeadResults[0], 2, false);
	cout << "Number of valid results: " << iNoOfResults << "\n";
	cout << "\nDisplay post-processing results:\n";
	DisplayPPP(&vuiBeadResults[0], iNoOfResults, 75.0, 0.0005); // Adjust values depending on sensor type

	cout << "Proceed post-processing results\n";
	iNoOfResults = GetBeadResults(&vucModuleResult[0], iRetValue, &vuiBeadResults[0], 3, false);
	cout << "Number of valid results: " << iNoOfResults << "\n";
	cout << "\nDisplay post-processing results:\n";
	DisplayPPP(&vuiBeadResults[0], iNoOfResults, 75.0, 0.0005); // Adjust values depending on sensor type
}

// Displaying the error text
void OnError(const char *szErrorTxt, int iErrorValue)
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

// Returns the bead results according to OPManPartC.html, "Bead Finder: Result Fields"
//@param *vucModuleResult: vector returned by LLT.dll-Function ConvertProfile2ModuleResults
//@param nModuleResultSize: return value of LLT.dll-Function ConvertProfile2ModuleResults
//@param *BeadResult: vector to write the results in
//@param beadIndex: index of the bead whose results to return
//@param littleEndian: set to true for PURE_PROFILE transmission
//@return: values stored in BeadResult
int GetBeadResults(unsigned char *vucModuleResult, int nModuleResultSize, unsigned int *vuiBeadResult, int beadIndex,
	bool littleEndian)
{
	int beadResultIndex = 0;
	int idx = 0;
	int length = 0;
	unsigned short line_q12, line_q34;
	int line_q1234;
	int i, j, k;

	for (i = 0; i < nModuleResultSize; i++)
	{
		if (vucModuleResult[i] == 2) // Bead header
		{
			if (littleEndian)
			{
				length = vucModuleResult[i + 3];
			}
			else {
				length = vucModuleResult[i - 3];
				for (j = 0; j < length - 1; j++) 
				{
					k = (i + 1) + j * 4;
					// Conversion of the results
					line_q12 = (((short)vucModuleResult[k + 1]) << 8) | (short)vucModuleResult[k + 0];
					line_q34 = (((short)vucModuleResult[k + 3]) << 8) | (short)vucModuleResult[k + 2];
					line_q1234 = ((line_q34) << 16) | line_q12;
					// Put results into the result vector
					switch (j) {
					case 3:
					case 4:
					case 9:
					case 10:
					case 12: // signed values, 32 Bit
						vuiBeadResult[idx] = (unsigned int)line_q1234;
						idx++;
						break;
					default: // unsigned values, 16Bit
						vuiBeadResult[idx] = (unsigned short)line_q34;
						idx++;
						vuiBeadResult[idx] = (unsigned short)line_q12;
						idx++;
						break;
					}
				}
			}
			// desired bead found
			if (beadIndex == beadResultIndex)
			{
				break;
			}
			else
			{
				beadResultIndex++;
				idx = 0;
			}
		}
	}
	return idx;
}

// Convert the bead results into cartesian coordinates according to resolution and offset of the sensor
// Display the bead results
//@param vuiBeadResult: result vector returned by GetBeadResults
//@param nBeadResultSize: number of valid values in the result vector
//@param offset: offset according to the sensor type
//@param resolution: sensor resolution according to the sensor type
void DisplayPPP(unsigned int *vuiBeadResult, int nBeadResultSize, double offset, double resolution)
{
	int zerovalue = 32768;
	if (nBeadResultSize > 0)
		cout << "anchor point x: " << Double2Str(((unsigned short)vuiBeadResult[0] - zerovalue) * resolution)
		<< " mm\n";
	if (nBeadResultSize > 1)
		cout << "anchor point z: " << Double2Str((((unsigned short)vuiBeadResult[1] - zerovalue) * resolution) + offset)
		<< " mm\n";
	if (nBeadResultSize > 2)
		cout << "left reference points count : " << Double2Str(((unsigned short)vuiBeadResult[2])) << " \n";
	if (nBeadResultSize > 3)
		cout << "right reference points count : " << Double2Str(((unsigned short)vuiBeadResult[3])) << " \n";
	if (nBeadResultSize > 4)
		cout << "left reference orientation : " << Double2Str(((signed short)vuiBeadResult[4]) * 0.01) << " grad\n";
	if (nBeadResultSize > 5)
		cout << "right reference orientation : " << Double2Str(((signed short)vuiBeadResult[5]) * 0.01) << " grad\n";
	if (nBeadResultSize > 6)
		cout << "left reference level: "
		<< Double2Str((((signed int)vuiBeadResult[6] - zerovalue) * resolution) + offset) << " mm\n";
	if (nBeadResultSize > 7)
		cout << "right reference level: "
		<< Double2Str((((signed int)vuiBeadResult[7] - zerovalue) * resolution) + offset) << " mm\n";
	if (nBeadResultSize > 8)
		cout << "left reference standard deviation: " << Double2Str(((unsigned short)vuiBeadResult[8]) * resolution)
		<< " \n";
	if (nBeadResultSize > 9)
		cout << "left reference standard deviation: " << Double2Str(((unsigned short)vuiBeadResult[9]) * resolution)
		<< " \n";
	if (nBeadResultSize > 10)
		cout << "bead left position x: " << Double2Str(((unsigned short)vuiBeadResult[10] - zerovalue) * resolution)
		<< " mm\n";
	if (nBeadResultSize > 11)
		cout << "bead left position z: "
		<< Double2Str((((unsigned short)vuiBeadResult[11] - zerovalue) * resolution) + offset) << " mm\n";
	if (nBeadResultSize > 12)
		cout << "bead top position x: " << Double2Str(((unsigned short)vuiBeadResult[12] - zerovalue) * resolution)
		<< " mm\n";
	if (nBeadResultSize > 13)
		cout << "bead top position z: "
		<< Double2Str((((unsigned short)vuiBeadResult[13] - zerovalue) * resolution) + offset) << " mm\n";
	if (nBeadResultSize > 14)
		cout << "bead right position x: " << Double2Str(((unsigned short)vuiBeadResult[14] - zerovalue) * resolution)
		<< " mm\n";
	if (nBeadResultSize > 15)
		cout << "bead right position z: "
		<< Double2Str((((unsigned short)vuiBeadResult[15] - zerovalue) * resolution) + offset) << " mm\n";
	if (nBeadResultSize > 16)
		cout << "bead width: " << Double2Str((((signed int)vuiBeadResult[16]) * resolution)) << " mm\n";
	if (nBeadResultSize > 17)
		cout << "bead height: " << Double2Str((((signed int)vuiBeadResult[17]) * resolution)) << " mm\n";
	if (nBeadResultSize > 18) ; // Reserved-Field
	if (nBeadResultSize > 19)
		cout << "bead points count : " << Double2Str((signed short)vuiBeadResult[19]) << " \n";
	if (nBeadResultSize > 20)
		cout << "bead area: " << Double2Str((signed int)vuiBeadResult[20] * resolution * resolution) << " mm*mm\n";
	if (nBeadResultSize > 21)
		cout << "computation time : " << Double2Str(((unsigned short)vuiBeadResult[21])) << " ms\n";
	if (nBeadResultSize > 22)
		cout << "error code: " << Double2Str(((unsigned short)vuiBeadResult[22]));
		char acErrorString[200];
		if ((unsigned short)vuiBeadResult[22] > 0)
		{
			m_pLLT->TranslateErrorValue((unsigned short)vuiBeadResult[22], acErrorString, sizeof(acErrorString));
			cout << " (" << acErrorString << ")";
		}
		else
			cout << " (IO)";
		cout << "\n";
	if (nBeadResultSize > 23)
		cout << "point of minimum distance x: "
		<< Double2Str(((unsigned short)vuiBeadResult[23] - zerovalue) * resolution) << " mm\n";
	if (nBeadResultSize > 24)
		cout << "point of minimum distance z: "
		<< Double2Str((((unsigned short)vuiBeadResult[24] - zerovalue) * resolution) + offset) << " mm\n";
	if (nBeadResultSize > 25)
		cout << "point of maximum distance x: "
		<< Double2Str(((unsigned short)vuiBeadResult[25] - zerovalue) * resolution) << " mm\n";
	if (nBeadResultSize > 26)
		cout << "point of maximum distance z: "
		<< Double2Str((((unsigned short)vuiBeadResult[26] - zerovalue) * resolution) + offset) << " mm\n";
	if (nBeadResultSize > 27)
		cout << "leftmost valid point x: " << Double2Str(((unsigned short)vuiBeadResult[27] - zerovalue) * resolution)
		<< " mm\n";
	if (nBeadResultSize > 28)
		cout << "leftmost valid point : "
		<< Double2Str((((unsigned short)vuiBeadResult[28] - zerovalue) * resolution) + offset) << " mm\n";
	if (nBeadResultSize > 29)
		cout << "rightmost valid point x: " << Double2Str(((unsigned short)vuiBeadResult[29] - zerovalue) * resolution)
		<< " mm\n";
	if (nBeadResultSize > 30)
		cout << "rightmost valid point z: "
		<< Double2Str((((unsigned short)vuiBeadResult[30] - zerovalue) * resolution) + offset) << " mm\n";
	if (nBeadResultSize > 31)
		cout << "intersection point x: " << Double2Str(((unsigned short)vuiBeadResult[31] - zerovalue) * resolution)
		<< " mm\n";
	if (nBeadResultSize > 32)
		cout << "intersection point z: "
		<< Double2Str((((unsigned short)vuiBeadResult[32] - zerovalue) * resolution) + offset) << " mm\n";
	if (nBeadResultSize > 33)
		cout << "left COG x: " << Double2Str((((unsigned short)vuiBeadResult[33] - zerovalue) * resolution)) << " mm\n";
	if (nBeadResultSize > 34)
		cout << "left COG z: " << Double2Str((((unsigned short)vuiBeadResult[34] - zerovalue) * resolution) + offset)
		<< " mm\n";
	if (nBeadResultSize > 35)
		cout << "right COG x: " << Double2Str((((unsigned short)vuiBeadResult[35] - zerovalue) * resolution))
		<< " mm\n";
	if (nBeadResultSize > 36)
		cout << "right COG z: " << Double2Str((((unsigned short)vuiBeadResult[36] - zerovalue) * resolution) + offset)
		<< " mm\n";
	if (nBeadResultSize > 37)
		cout << "left distance to origin: "
		<< Double2Str((((unsigned short)vuiBeadResult[37] - zerovalue) * resolution)) << " mm\n";
	if (nBeadResultSize > 38)
		cout << "right distance to origin: "
		<< Double2Str((((unsigned short)vuiBeadResult[38] - zerovalue) * resolution)) << " mm\n";

	cout << "\n";
}