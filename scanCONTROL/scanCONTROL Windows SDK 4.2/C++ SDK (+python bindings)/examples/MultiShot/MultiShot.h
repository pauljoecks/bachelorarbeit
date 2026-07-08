//   MultiShot.h: demo-application for using the LLT.dll
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

#ifndef LLTMultiShotH
#define LLTMultiShotH

#define MAX_INTERFACE_COUNT    5
#define MAX_RESOULUTIONS       6

void MultiShot();
void OnError(const char* szErrorTxt, int iErrorValue);

extern void __stdcall NewProfile(const unsigned char* pucData, unsigned int uiSize, void* pUserData);

#endif
