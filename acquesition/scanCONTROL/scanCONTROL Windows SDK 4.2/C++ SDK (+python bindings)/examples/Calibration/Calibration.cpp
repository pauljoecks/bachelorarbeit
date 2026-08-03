//   Calibration.cpp: demo-application for using the LLT.dll
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
#define _USE_MATH_DEFINES
#include <math.h>
#include <iostream>
#include <conio.h>
#include "InterfaceLLT_2.h"
#include "Calibration.h"

using namespace std;

CInterfaceLLT* m_pLLT = NULL;
TScannerType m_tscanCONTROLType = scanCONTROL2xxx;

int main(int argc, char* argv[])
{
	UNREFERENCED_PARAMETER(argc);
	UNREFERENCED_PARAMETER(argv);

	vector<unsigned int> vuiInterfaces(MAX_INTERFACE_COUNT);
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
		}

		if (bOK)
		{
			Calibration();
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

void Calibration()
{
	int iRetValue;
	/* Sensor parameters have to adjusted for sensor type - see Config Tools Manual */
	double offset = 95.0; // e.g. 65.0 mm;
	double scaling = 0.002; // e.g.0.001 mm;

	cout << "Offset: " << offset << "\n";
	cout << "Scaling: " << scaling << "\n";

	// Center of rotation and angle
	double center_x = 0.0; // usually x = 0.0mm
	double center_z = offset; // usually z = offset
	double angle = -2.0; // degree

	// Coordinate system is shifted by
	double shift_x = -2.0; // mm
	double shift_z = -2.0; // mm

	cout << "Read Calibration\n";
	ReadCalibration(offset, scaling);

	cout << "Reset Calibration\n";
	ResetCustomCalibration2();

	cout << "Read Calibration\n";
	ReadCalibration(offset, scaling);

	cout << "Set Calibration 1\n";
	SetCustomCalibration(center_x, center_z, angle, shift_x, shift_z, offset, scaling);

	cout << "Read Calibration\n";
	ReadCalibration(offset, scaling);

	cout << "Reset Calibration\n";
	ResetCustomCalibration2();

	cout << "Read Calibration\n";
	ReadCalibration(offset, scaling);

	cout << "Set Calibration 2\n";
	SetCustomCalibration2(center_x, center_z, angle, shift_x, shift_z, offset, scaling);

	cout << "Read Calibration\n";
	ReadCalibration(offset, scaling);

	cout << "Save calibration permanently\n";
	if ((iRetValue = m_pLLT->SaveGlobalParameter()) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SaveGlobalParameter", iRetValue);
	}
}

void ReadCalibration(double offset, double scaling) 
{
	DWORD tmp = 0;
	m_pLLT->GetFeature(FEATURE_FUNCTION_CALIBRATION_0, &tmp);
	cout << "FEATURE_FUNCTION_CALIBRATION_0: " << hex << tmp << "\n";
	m_pLLT->GetFeature(FEATURE_FUNCTION_CALIBRATION_1, &tmp);
	cout << "FEATURE_FUNCTION_CALIBRATION_1: " << hex << tmp << "\n";
	m_pLLT->GetFeature(FEATURE_FUNCTION_CALIBRATION_2, &tmp);
	cout << "FEATURE_FUNCTION_CALIBRATION_2: " << hex << tmp << "\n";
	m_pLLT->GetFeature(FEATURE_FUNCTION_CALIBRATION_3, &tmp);
	cout << "FEATURE_FUNCTION_CALIBRATION_3: " << hex << tmp << "\n";
	m_pLLT->GetFeature(FEATURE_FUNCTION_CALIBRATION_4, &tmp);
	cout << "FEATURE_FUNCTION_CALIBRATION_4: " << hex << tmp << "\n";
	m_pLLT->GetFeature(FEATURE_FUNCTION_CALIBRATION_5, &tmp);
	cout << "FEATURE_FUNCTION_CALIBRATION_5: " << hex << tmp << "\n";
	m_pLLT->GetFeature(FEATURE_FUNCTION_CALIBRATION_6, &tmp);
	cout << "FEATURE_FUNCTION_CALIBRATION_6: " << hex << tmp << "\n";
	m_pLLT->GetFeature(FEATURE_FUNCTION_CALIBRATION_7, &tmp);
	cout << "FEATURE_FUNCTION_CALIBRATION_7: " << hex << tmp << "\n";
}

void ResetCustomCalibration() 
{
	int iRetValue;
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0000)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0100)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0420)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0100)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
}

void ResetCustomCalibration2() 
{
	int iRetValue;
	//Deactivate calibration
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_CALIBRATION_0, 0x00000000)) < GENERAL_FUNCTION_OK)
		OnError("Error during Activation 0", iRetValue);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_CALIBRATION_1, 0x00000000)) < GENERAL_FUNCTION_OK)
		OnError("Error during Activation 1", iRetValue);
	//Reset calibration registers
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_CALIBRATION_2, 0x00000000)) < GENERAL_FUNCTION_OK)
		OnError("Error during Calibration 2", iRetValue);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_CALIBRATION_3, 0x00000000)) < GENERAL_FUNCTION_OK)
		OnError("Error during Calibration 3", iRetValue);
}

void SetCustomCalibration(double cX, double cZ, double angle, double sX, double sZ, double offset, double scaling) 
{
	int iRetValue;
	DWORD tmp;
	double rotate_angle = angle;
	double PI = M_PI;
	double xTrans = -sX;
	double zTrans = offset - sZ;

	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0000)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0100)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0420)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0305)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0204)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0308)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0280)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}

	// Read current state of invert_x and invert_z from sensor
	if ((iRetValue = m_pLLT->GetFeature(FEATURE_FUNCTION_PROFILE_PROCESSING, &tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during GetFeature(FEATURE_FUNCTION_PROFILE_PROCESSING)", iRetValue);
	}
	unsigned int uiInvertX = (tmp & PROC_FLIP_POSITION) >> 7;
	unsigned int uiInvertZ = (tmp & PROC_FLIP_DISTANCE) >> 6;

	// invert angle if necessary
	if (uiInvertX != uiInvertZ)
	{
		rotate_angle = -angle;
	}
	double sinus = sin(rotate_angle * PI / 180);
	double cosinus = cos(rotate_angle * PI / 180);

	// Rotation angle
	if (rotate_angle < 0)
	{
		rotate_angle = floor(65536 + rotate_angle / 0.01 + 0.5);
	}
	else
	{
		rotate_angle = floor(rotate_angle / 0.01 + 0.5);
	}

	// Rotation center 1 for rotating
	double x1 = cX / scaling + 32768;
	double z1 = (cZ - offset) / scaling + 32768;

	// Rotation center 2 for translating
	double x2 = xTrans / scaling + 32768;
	double z2 = 65536 - ((zTrans - offset) / scaling + 32768);

	// Calculate the combined rotation center
	double x3 = x1 + (x2 - 32768) * cosinus + (z2 - 32768) * sinus;
	double z3 = z1 + (z2 - 32768) * cosinus - (x2 - 32768) * sinus;
	xTrans = floor(x3 + 0.5);
	zTrans = floor(z3 + 0.5);

	// Saturation
	if (xTrans < 0) xTrans = 0; else if (xTrans > 65535) xTrans = 65535;
	if (zTrans < 0) zTrans = 0; else if (zTrans > 65535) zTrans = 65535;
	if (rotate_angle < 0) rotate_angle = 0; else if (rotate_angle > 65535) rotate_angle = 65535;

	unsigned int a = unsigned int(xTrans);
	unsigned int b = unsigned int(zTrans);

	// Ausgabe
	// X High
	tmp = 0x300 | ((a & 0xFF00) >> 8);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	// X Low
	tmp = 0x200 | (a & 0xFF);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	// Z High
	tmp = 0x300 | ((b & 0xFF00) >> 8);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	// Z Low
	tmp = 0x200 | (b & 0xFF);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}

	a = 0;
	b = unsigned int(rotate_angle);

	// Ausgabe
	// X High
	tmp = 0x300 | ((a & 0xFF00) >> 8);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	// X Low
	tmp = 0x200 | (a & 0xFF);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	// Z High
	tmp = 0x300 | ((b & 0xFF00) >> 8);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	// Z Low
	tmp = 0x200 | (b & 0xFF);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}

	// Abschluss
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0300)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0200)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_EXTRA_PARAMETER, 0x0100)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during SetFeature(EXTRAPARAMETER)", iRetValue);
	}
}

void SetCustomCalibration2(double cX, double cZ, double angle, double sX, double sZ, double offset, double scaling) 
{
	int iRetValue;
	DWORD tmp = 0;
	double rotate_angle = angle;
	double PI = M_PI;
	double xTrans = -sX;
	double zTrans = offset - sZ;

	// Read current state of invert_x and invert_z from sensor
	if ((iRetValue = m_pLLT->GetFeature(FEATURE_FUNCTION_PROFILE_PROCESSING, &tmp)) < GENERAL_FUNCTION_OK)
	{
		OnError("Error during GetFeature(FEATURE_FUNCTION_PROFILE_PROCESSING)", iRetValue);
	}
	unsigned int uiInvertX = (tmp & PROC_FLIP_POSITION) >> 7;
	unsigned int uiInvertZ = (tmp & PROC_FLIP_DISTANCE) >> 6;

	// invert angle if necessary
	if (uiInvertX != uiInvertZ)
	{
		rotate_angle = -angle;
	}
	double sinus = sin(rotate_angle * PI / 180);
	double cosinus = cos(rotate_angle * PI / 180);

	// Rotation angle
	if (rotate_angle < 0)
	{
		rotate_angle = floor(65536 + rotate_angle / 0.01 + 0.5);
	}
	else
	{
		rotate_angle = floor(rotate_angle / 0.01 + 0.5);
	}

	// Rotation center 1 for rotating
	double x1 = cX / scaling + 32768;
	double z1 = (cZ - offset) / scaling + 32768;

	// Rotation center 2 for translating
	double x2 = xTrans / scaling + 32768;
	double z2 = 65536 - ((zTrans - offset) / scaling + 32768);

	// Calculate the combined rotation center
	double x3 = x1 + (x2 - 32768) * cosinus + (z2 - 32768) * sinus;
	double z3 = z1 + (z2 - 32768) * cosinus - (x2 - 32768) * sinus;
	xTrans = floor(x3 + 0.5);
	zTrans = floor(z3 + 0.5);

	// Saturation
	if (xTrans < 0) xTrans = 0; else if (xTrans > 65535) xTrans = 65535;
	if (zTrans < 0) zTrans = 0; else if (zTrans > 65535) zTrans = 65535;
	if (rotate_angle < 0) rotate_angle = 0; else if (rotate_angle > 65535) rotate_angle = 65535;

	// Compute register values
	unsigned int calib2 = ((unsigned int)xTrans << 16) + (unsigned int)zTrans;
	unsigned int calib3 = (unsigned int)rotate_angle;

	// Write calibration to sensor
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_CALIBRATION_0, 0x05000004)) < GENERAL_FUNCTION_OK)
		OnError("Error during Activation 0", iRetValue);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_CALIBRATION_1, 0x08000080)) < GENERAL_FUNCTION_OK)
		OnError("Error during Activation 1", iRetValue);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_CALIBRATION_2, calib2)) < GENERAL_FUNCTION_OK)
		OnError("Error during Calibration 2", iRetValue);
	if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_CALIBRATION_3, calib3)) < GENERAL_FUNCTION_OK)
		OnError("Error during Calibration 3", iRetValue);
}

// Displaying the error text
void OnError(const char* szErrorTxt, int iErrorValue)
{
	char acErrorString[200];

	cout << szErrorTxt << "\n";
	if (m_pLLT->TranslateErrorValue(iErrorValue, acErrorString, sizeof(acErrorString)) >= GENERAL_FUNCTION_OK)
		cout << acErrorString << "\n\n";
}
