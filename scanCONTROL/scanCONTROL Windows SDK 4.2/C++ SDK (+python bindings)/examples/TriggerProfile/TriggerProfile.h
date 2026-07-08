//   TriggerProfile.h: demo-application for using the LLT.dll
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

#ifndef _TRIGGER_PROFILE_H_
#define _TRIGGER_PROFILE_H_

#include <string>

void OnError(const char* szErrorTxt, int iErrorValue);
void TriggerProfileAndShow(void);
void DisplayProfile(double* pdValueX, double* pdValueZ, unsigned int uiResolution);
void DisplayTimestamp(unsigned char* pucTimestamp);
std::string Double2Str(double dValue);

#endif // _TRIGGER_PROFILE_H_