//   GetProfiles_Callback.h: demo-application for using the LLT.dll
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

bool SaveAvis_FullSet(std::vector<char> &device_name, DWORD &SerialNumber);
bool SaveAvis_Quarter(std::vector<char> &device_name, DWORD &SerialNumber);
bool SaveAvis_Pure(std::vector<char> &device_name, DWORD &SerialNumber);
void OnError(const char* szErrorTxt, int iErrorValue);
unsigned int DisplayTimestamp(unsigned char* pucTimestamp);
std::string Double2Str(double dValue);

extern void __stdcall NewProfile(const unsigned char* pucData, unsigned int uiSize, void* pUserData);

#endif
