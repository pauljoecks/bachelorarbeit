//   LoadSave.h: demo-application for using the LLT.dll
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

#ifndef LLTLoadSaveH
#define LLTLoadSaveH

#define MAX_INTERFACE_COUNT    5
#define MAX_RESOULUTIONS       6

bool Save();
void Load();
void OnError(const char* szErrorTxt, int iErrorValue);

#endif
