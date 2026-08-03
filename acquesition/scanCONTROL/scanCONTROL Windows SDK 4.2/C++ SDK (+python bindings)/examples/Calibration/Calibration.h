//   Calibration.h: demo-application for using the LLT.dll
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

#ifndef LLTGetProfilesCallbackH
#define LLTGetProfilesCallbackH

#define MAX_INTERFACE_COUNT    5
#define MAX_RESOULUTIONS       6

void Calibration();
void ReadCalibration(double offset, double scaling);
void ResetCustomCalibration();
void ResetCustomCalibration2();
void SetCustomCalibration(double cX, double cZ, double angle, double sX, double sZ, double offset, double scaling);
void SetCustomCalibration2(double cX, double cZ, double angle, double sX, double sZ, double offset, double scaling);

void OnError(const char* szErrorTxt, int iErrorValue);

extern void __stdcall NewProfile(const unsigned char* pucData, unsigned int uiSize, void* pUserData);

#endif
