
  /*
   * CONNECT TO SENSOR
   */
  
  // EXAMPE TASK 1:
  
  // set the desired free measuring field
  unsigned short start_z = 22938;
  unsigned short size_z = 15073;
  unsigned short start_x = 0;
  unsigned short size_x = 65535;

  // Enable the free measuring field
  if ((iRetValue = m_pLLT->SetFeature(FEATURE_FUNCTION_MEASURINGFIELD, 0x82000800)) < GENERAL_FUNCTION_OK)
  {
	  OnError("Error during setting the free measuring field", iRetValue);
  }
  // Set the values
  if ((iRetValue = SetFreeMeasuringFieldValues(start_z, size_z, start_x, size_x)) < GENERAL_FUNCTION_OK)
  {
	  OnError("Error during setting the free measuring field", iRetValue);
  }
  
    // EXAMPLE TASK 2:
  
  // Set peak filters
  if ((iRetValue = SetPeakValues(2, 12, 100, 1023)) < GENERAL_FUNCTION_OK)
  {
	  OnError("Error during setting the free measuring field", iRetValue);
  }
  
  /*
   * DISCONNECT
   */
  
  
int SetPeakValues(unsigned short min_width, unsigned short max_width, unsigned short min_intensity, unsigned short max_intensity)
{
	reset_command_list();
	write_value(max_width);
	write_value(min_width);
	write_value(max_intensity);
	write_value(min_intensity);
	end_command_list();

	return GENERAL_FUNCTION_OK;
}

int SetFreeMeasuringFieldValues(unsigned short start_z, unsigned short size_z, unsigned short start_x, unsigned short size_x)
{
	reset_command_list();
	write_command(2, 8);
	write_value(start_z);
	write_value(size_z);
	write_value(start_x);
	write_value(size_x);
	end_command_list();

	return GENERAL_FUNCTION_OK;
}

int SetDynamicMeasuringFieldTrackingValues(unsigned short div_x, unsigned short div_z, unsigned short multi_x, unsigned short multi_z)
{
	reset_command_list();
	write_command(2, 16);
	write_value(div_x);
	write_value(div_z);
	write_value(multi_x);
	write_value(multi_z);
	end_command_list();

	return GENERAL_FUNCTION_OK;
}

void write_command(int command, int data)
{
  m_pLLT->SetFeature(FEATURE_FUNCTION_SHARPNESS, (command << 9) + (m_toggle << 8) + data);
  m_toggle = !m_toggle;
}

void write_value(unsigned short value)
{
  write_command(1, value/256);
  write_command(1, value%256);
}

void reset_command_list()
{
  write_command(0, 0); 
  write_command(0, 0); 
}

void end_command_list()
{
  write_command(0, 0); 
}

//Displaying the error text
void OnError(const char* szErrorTxt, int iErrorValue)
{
  char acErrorString[200];

  cout << szErrorTxt << "\n";
  if(m_pLLT->TranslateErrorValue(iErrorValue, acErrorString, sizeof(acErrorString)) >= GENERAL_FUNCTION_OK)
    cout << acErrorString << "\n\n";
}

