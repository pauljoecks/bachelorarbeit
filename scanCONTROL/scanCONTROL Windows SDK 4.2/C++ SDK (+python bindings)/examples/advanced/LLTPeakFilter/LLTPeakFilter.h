
#ifndef LLTInfoH
#define LLTInfoH

#define MAX_INTERFACE_COUNT    5
#define MAX_RESOULUTIONS       6

void SetPeakFilter(unsigned int uiDeviceID, unsigned int uiLLTNumber);
int SetPeakValues(unsigned short min_width, unsigned short max_width, unsigned short min_intensity, unsigned short max_intensity);
int SetFreeMeasuringFieldValues(unsigned short start_z, unsigned short size_z, unsigned short start_x, unsigned short size_x);
int SetDynamicMeasuringFieldTrackingValues(unsigned short div_x, unsigned short div_z, unsigned short multi_x, unsigned short multi_z);
void OnError(const char* szErrorTxt, int iErrorValue);
void write_command(int command, int data);
void write_value(unsigned short value);
void reset_command_list();
void end_command_list();

CInterfaceLLT* m_pLLT;
int m_toggle = 0;

#endif
