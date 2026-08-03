//   PostProcessingFilter.h: demo-application for editing filter in ppp-file
//
//   Version 3.0.0.0
//
//   Copyright 2014
//
//   Bent Brückner
//   MICRO-EPSILON Optronic GmbH
//   Lessingstrasse 14
//   01465 Dresden OT Langebrueck
//   Germany
//---------------------------------------------------------------------------

#ifndef PostProcessingFilterH
#define PostProcessingFilterH

#define MAX_INTERFACE_COUNT    5
#define MAX_RESOULUTIONS       6

#define SIZE_OF_POSTPROCESSING_PARAMETER    1025

void LLTConnect(unsigned int uiDeviceID, unsigned int uiLLTNumber);
void LLTDisconnect(unsigned int uiDeviceID, unsigned int uiLLTNumber);
void OnError(const char* szErrorTxt, int iErrorValue);
bool IsMeasurementRange10(TScannerType);
bool IsMeasurementRange25(TScannerType);
bool IsMeasurementRange50(TScannerType);
bool IsMeasurementRange100(TScannerType);

#endif