//   PartialProfile.h: demo-application for using the LLT.dll
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

#ifndef LLTPartialProfileH
#define LLTPartialProfileH

#define MAX_INTERFACE_COUNT    5
#define MAX_RESOULUTIONS       6

bool PartialProfile_Pure(TScannerType tscanCONTROLType);
bool PartialProfile_Quarter(TScannerType tscanCONTROLType);

void OnError(const char* szErrorTxt, int iErrorValue);
void DisplayProfile(double* pdValueX, double* pdValueZ, unsigned int uiResolution);
void DisplayTimestamp(unsigned char* pucTimestamp);
std::string Double2Str(double dValue);

#endif
