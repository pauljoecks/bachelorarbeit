//   sC30xx_HighSpeed.h: demo-application for using the LLT.dll
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

#ifndef LLTsC30xxHighSpeedH
#define LLTsC30xxHighSpeedH

#define MAX_INTERFACE_COUNT    5
#define MAX_RESOULUTIONS       6

void ConfigureSensorForHighSpeed();
void GetProfiles_Callback();
void OnError(const char* szErrorTxt, int iErrorValue);

extern void __stdcall NewProfile(const unsigned char* pucData, unsigned int uiSize, void* pUserData);

#endif
