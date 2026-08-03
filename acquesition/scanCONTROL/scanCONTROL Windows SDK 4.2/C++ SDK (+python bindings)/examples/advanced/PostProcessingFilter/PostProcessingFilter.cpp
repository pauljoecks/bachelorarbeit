//   PostProcessingFilter.cpp: demo-application for editing, writing und reading filters (ppp-file)
//    + read filter template (ppp-file) from file
//    + adapt filter parameters (median filter and average filter width)
//    + write filter to the LLT
//    + read filter back from LLT
//    + write adapted filter (ppp-file) to new file
//
//   Version 3.0.0.0
//
//   Copyright 2014
//
//   Bent Bruckner
//   MICRO-EPSILON Optronic GmbH
//   Lessingstrasse 14
//   01465 Dresden OT Langebrueck
//   Germany
//---------------------------------------------------------------------------

#include "stdafx.h"
#include <iostream>
#include <conio.h>
#include "InterfaceLLT_2.h"
#include "PostProcessingFilter.h"

using namespace std;
static CInterfaceLLT* m_pLLT = NULL;
int main(int argc, char* argv[])
{
  UNREFERENCED_PARAMETER(argc);
  UNREFERENCED_PARAMETER(argv);
  std::vector<unsigned int> vuiInterfaces(MAX_INTERFACE_COUNT);
  unsigned int uiInterfaceCount = 0;
  unsigned char ucInput = 0;
  bool bLoadError;
  int iRetValue;
  DWORD TempValue;
  // width median filter (odd number between 1 and 101)
  int medWidth = 89;
  // width average filter (odd number between 1 and 101)
  int avgWidth = 89;
  // filter template (ppp-file) to read from
  const char* pFilenameIn = "./filterTemplateMedAvg.ppp";
  std::ifstream FilestreamIn(pFilenameIn);
  // setup filename for adapted filter (ppp-file)
  char TempName[256];
  sprintf(TempName, "./filterMed%d_Avg%d.ppp", medWidth, avgWidth);
  // filter (ppp-file) read vom LLT to write to file
  const char* pFilenameOut = TempName;
  std::ofstream FilestreamOut(pFilenameOut);
  // buffer for filter description
  std::vector<DWORD> PostProcessParams;
  PostProcessParams.resize(SIZE_OF_POSTPROCESSING_PARAMETER);

  // medWidth == odd number and in range 1 .. 101
  if((medWidth % 2 == 1) & (medWidth > 2) & (medWidth < 102))
  {
    // encode to write to register
    medWidth = (medWidth - 1) / 2;
  }
  else
  {
    cout << "[Error] Invalid filter parameter for median filter passed ... exiting.\n";
    return -1;
  }

  // avgWidth == odd number and in range 1 .. 101
  if((avgWidth % 2 == 1) & (avgWidth > 2) & (avgWidth < 102))
  {
    // encode to write to register
    avgWidth = (avgWidth - 1) / 2;
  }
  else
  {
    cout << "[Error] Invalid filter parameter for average filter passed ... exiting.\n";
    return -1;
  }

  // Creating a LLT-object
  // The LLT-Object will load the LLT.dll automatically and give us an error if there is no LLT.dll
  m_pLLT = new CInterfaceLLT("LLT.dll", &bLoadError);

  if(bLoadError)
  {
    cout << "Error loading LLT.dll \n";

    // Wait for a keyboard hit
    while(!_kbhit())
    {
    }

    // Deletes the LLT-object
    delete m_pLLT;
    return -1;
  }

  // Test if the LLT.dll supports GetLLTType (Version 3.0.0.0 or higher)
  if(m_pLLT->m_pFunctions->CreateLLTDevice == NULL)
    cout << "Please use a LLT.dll version 3.0.0.0 or higher! \n";
  else
  {
    // Create an Ethernet Device
    if(m_pLLT->CreateLLTDevice(INTF_TYPE_ETHERNET))
      cout << "CreateLLTDevice OK \n";
    else
      cout << "Error during CreateLLTDevice\n";

    // Gets the available interfaces from the scanCONTROL-device
    iRetValue = m_pLLT->GetDeviceInterfacesFast(&vuiInterfaces[0], (unsigned int)vuiInterfaces.size());

    if(iRetValue == ERROR_GETDEVINTERFACES_REQUEST_COUNT)
    {
      cout << "There are more or equal than " << vuiInterfaces.size() << " scanCONTROL connected \n";
      uiInterfaceCount = vuiInterfaces.size();
    }
    else if(iRetValue < 0)
    {
      cout << "A error occured during searching for connected scanCONTROL \n";
      uiInterfaceCount = 0;
    }
    else
      uiInterfaceCount = iRetValue;

    if(uiInterfaceCount == 0)
      cout << "There is no scanCONTROL connected \n";
    else if(uiInterfaceCount == 1)
      cout << "There is 1 scanCONTROL connected \n";
    else
      cout << "There are " << uiInterfaceCount << " scanCONTROL's connected \n";
  }

  // read filter (ppp-file) from file to buffer
  for(unsigned int i = 0; i < SIZE_OF_POSTPROCESSING_PARAMETER; i++)
  {
    FilestreamIn >> std::hex >> PostProcessParams[i];
    PostProcessParams[i] = PostProcessParams[i] << 16;

    if(FilestreamIn.eof())
      break;

    if(FilestreamIn.fail())
    {
      cout << "[Error] Wrong char in ppp-file. \n";
      // m_pParent->OnError(IDS_ERROR_WRONG_CHAR_PPP, false);
      return 1;
    }

    FilestreamIn >> std::hex >> TempValue;

    // position of median filter (specific for filter template)
    if(i == 1)
      TempValue = medWidth;

    // positions of average filter (specific for filter template)
    if((i == 3) | (i == 5))
      TempValue = avgWidth;

    PostProcessParams[i] += TempValue;

    if(FilestreamIn.eof())
      break;

    if(FilestreamIn.fail())
    {
      cout << "[Error] Wrong char in ppp-file. \n";
      // m_pParent->OnError(IDS_ERROR_WRONG_CHAR_PPP, false);
      return 1;
    }
  }

  FilestreamIn.close();
  cout << "[Info] Successfully read filter template (";
  cout << pFilenameIn;
  cout << "). \n";
  // connect to LLT
  LLTConnect(vuiInterfaces[0], 1);
  // write filter to LLT
  iRetValue = m_pLLT->WritePostProcessingParameter(&PostProcessParams[0], PostProcessParams.size());

  if(iRetValue < 0)
  {
    OnError("[Error] while writing ppp-file (filter) to LLT.", iRetValue);

    if(iRetValue != -1001)
      LLTDisconnect(vuiInterfaces[0], 1);

    return 1;
  }
  else
  {
    cout << "[Info] Wrote adapted filter (";
    cout << pFilenameOut;
    cout << ") to LLT. \n";
  }

  FilestreamOut << std::hex;
  // read back from LLT and write to file
  iRetValue = m_pLLT->ReadPostProcessingParameter(&PostProcessParams[0], PostProcessParams.size());

  if(iRetValue < 0)
  {
    OnError("[Error] while writing ppp-file (filter) to LLT.", iRetValue);

    if(iRetValue != -1001)
      LLTDisconnect(vuiInterfaces[0], 1);

    return 1;
  }
  else
    cout << "[Info] Successfully read filter back from LLT. \n";

  for(int i = 0; i < iRetValue; i++)
  {
    FilestreamOut << "0x" << std::setfill('0') << std::setw(4) << (PostProcessParams[i] >> 16) << " ";
    FilestreamOut << "0x" << std::setfill('0') << std::setw(4) << (PostProcessParams[i] & 0x0000ffff) << "\n";
  }

  cout << "[Info] Wrote adapted filter (";
  cout << pFilenameOut;
  cout << ") to file. \n";
  FilestreamOut.close();
  LLTDisconnect(vuiInterfaces[0], 1);
  // Deletes the LLT-object
  delete m_pLLT;

  // Wait for a keyboard hit
  while(!_kbhit())
  {
  }

  return 0;
}

void LLTConnect(unsigned int uiDeviceID, unsigned int uiLLTNumber)
{
  int iRetValue;
  cout << "Select the device interface " << uiDeviceID << "\n";

  if((iRetValue = m_pLLT->SetDeviceInterface(uiDeviceID, 0)) < GENERAL_FUNCTION_OK)
  {
    OnError("Error during SetDeviceInterface", iRetValue);
    return;
  }

  cout << "Connecting to scanCONTROL " << uiLLTNumber << "\n";

  if((iRetValue = m_pLLT->Connect()) < GENERAL_FUNCTION_OK)
  {
    OnError("Error during Connect", iRetValue);
    return;
  }
}

void LLTDisconnect(unsigned int uiDeviceID, unsigned int uiLLTNumber)
{
  int iRetValue;
  cout << "Disconnect the scanCONTROL\n";

  if((iRetValue = m_pLLT->Disconnect()) < GENERAL_FUNCTION_OK)
    OnError("Error during Disconnect", iRetValue);
  UNREFERENCED_PARAMETER(uiLLTNumber);
  UNREFERENCED_PARAMETER(uiDeviceID);
}

// Displaying the error text
void OnError(const char* szErrorTxt, int iErrorValue)
{
  char acErrorString[200];
  cout << szErrorTxt << "\n";

  if(m_pLLT->TranslateErrorValue(iErrorValue, acErrorString, sizeof(acErrorString)) >= GENERAL_FUNCTION_OK)
    cout << acErrorString << "\n\n";
}
