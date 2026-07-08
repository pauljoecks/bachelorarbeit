//   LLTInfo.h: demo-application for using the LLT.dll
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

#ifndef LLTInfoH
#define LLTInfoH

#define MAX_INTERFACE_COUNT    5
#define MAX_RESOULUTIONS       6

void GetLLTInfos(unsigned int uiDeviceID, unsigned int uiLLTNumber);
void OnError(const char* szErrorTxt, int iErrorValue);
bool IsMeasurementRange10(TScannerType);
bool IsMeasurementRange25(TScannerType);
bool IsMeasurementRange50(TScannerType);
bool IsMeasurementRange100(TScannerType);


#endif
