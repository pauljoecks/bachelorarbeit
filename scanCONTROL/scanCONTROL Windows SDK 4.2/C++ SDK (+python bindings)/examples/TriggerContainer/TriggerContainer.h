//   ContainerMode.h: demo-application for using the LLT.dll
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

#ifndef LLTContainerModeH
#define LLTContainerModeH

#define MAX_INTERFACE_COUNT    5
#define MAX_RESOULUTIONS       6

bool ConvertToString(char *name, int size);
void TriggerContainer();
int GetScalingAndOffsetByType(TScannerType scanner_type, double *scaling, double *offset);
void OnError(const char* szErrorTxt, int iErrorValue);
void DisplayProfile(double* pdValueX, double* pdValueZ, unsigned int uiResolution);
std::string Double2Str(double dValue);
void DisplayTimestamp(unsigned char* pucTimestamp);


#endif
