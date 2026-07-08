//   MultiLLTs.h: demo-application for using the LLT.dll
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

#ifndef LLTMultiLLTsH
#define LLTMultiLLTsH

#define MAX_INTERFACE_COUNT    5
#define MAX_RESOULUTIONS       6

void MultiLLTs();
void OnError(CInterfaceLLT* pLLT, const char* szErrorTxt, int iErrorValue);
void DisplayProfile(double* pdValueX, double* pdValueZ, unsigned int uiResolution);
void DisplayTimestamp(CInterfaceLLT* pLLT, unsigned char* pucTimestamp);
std::string Double2Str(double dValue);

extern void __stdcall NewProfile(const unsigned char* pucData, unsigned int uiSize, void* pUserData);

#endif
