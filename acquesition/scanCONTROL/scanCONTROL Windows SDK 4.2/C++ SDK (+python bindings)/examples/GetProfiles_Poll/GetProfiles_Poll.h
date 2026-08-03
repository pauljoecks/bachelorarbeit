//   GetProfiles_Poll.h: demo-application for using the LLT.dll
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

#ifndef LLTGetProfilesPollH
#define LLTGetProfilesPollH

#define MAX_INTERFACE_COUNT    5
#define MAX_RESOULUTIONS       6

void GetProfiles_Poll();
void OnError(const char* szErrorTxt, int iErrorValue);
void DisplayProfile(double* pdValueX, double* pdValueZ, unsigned int uiResolution);
void DisplayTimestamp(unsigned char* pucTimestamp);
std::string Double2Str(double dValue);

#endif
