Imports System
Imports System.Collections.Generic
Imports System.Runtime.InteropServices
Imports System.Text
Imports System.Threading

Namespace VB

    Public Class VBscanCNONTROLSample

        ' Global variables
        Const MAX_INTERFACE_COUNT As Integer = 5
        Const Max_RESOLUTIONS As Integer = 6

        Public Shared uiResolution As UInteger = 0
        Public Shared hLLT As UInteger = 0
        Public Shared tscanCONTROLType As CLLTI.TScannerType
        Public Shared convertContainerParameter As CLLTI.TConvertContainerParameter
        Public Shared uiShutterTime As UInteger = 100
        Public Shared uiIdleTime As UInteger = 900

        Shared Sub Main()
            scanCONTROL_Sample()
        End Sub

        Shared Sub scanCONTROL_Sample()
            Dim auiInterfaces(MAX_INTERFACE_COUNT - 1) As UInteger
            Dim auiResolutions(Max_RESOLUTIONS - 1) As UInteger

            Dim sbDevName As StringBuilder = New StringBuilder(100)
            Dim sbVenName As StringBuilder = New StringBuilder(100)

            Dim uiBufferCount As UInteger = 3
            Dim uiPacketSize As UInteger = 320

            Dim iInterfaceCount As Integer = 0
            Dim iRetValue As Integer
            Dim bOK As Boolean = True
            Dim isv46 As Boolean = True
            Dim bConnected As Boolean = False
            Dim cki As ConsoleKeyInfo

            hLLT = 0
            uiResolution = 0

            Console.WriteLine("----- Connect to scanCONTROL -----" & Environment.NewLine)

            ' Create an Ethernet Device -> returns handle to LLT device
            hLLT = CLLTI.CreateLLTDevice(CLLTI.TInterfaceType.INTF_TYPE_ETHERNET)
            If (hLLT <> 0) Then
                Console.WriteLine("CreateLLTDevice OK")
            Else
                Console.WriteLine("Error during CreateLLTDevice" & Environment.NewLine)
            End If

            ' Gets the available interfaces from the scanCONTROL handle
            iInterfaceCount = CLLTI.GetDeviceInterfacesFast(hLLT, auiInterfaces, auiInterfaces.GetLength(0))
            If (iInterfaceCount <= 0) Then
                Console.WriteLine("FAST: There is no scanCONTROL connected")
            ElseIf (iInterfaceCount = 1) Then
                Console.WriteLine("FAST: There is 1 scanCONTROL connected ")
            Else
                Console.WriteLine("FAST: There are " & iInterfaceCount & " scanCONTROL's connected")
            End If

            If (iInterfaceCount >= 1) Then
                Dim target4 As UInteger = auiInterfaces(0) And &HFF
                Dim target3 As UInteger = (auiInterfaces(0) And &HFF00) >> 8
                Dim target2 As UInteger = (auiInterfaces(0) And &HFF0000) >> 16
                Dim target1 As UInteger = (auiInterfaces(0) And &HFF000000) >> 24

                ' Set the first IP address detected by GetDeviceInterfacesFast to handle
                Console.WriteLine("Select the device interface: " & target1 & "." & target2 & "." & target3 & "." & target4)
                iRetValue = CLLTI.SetDeviceInterface(hLLT, auiInterfaces(0), 0)
                If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                    OnError("Error during SetDeviceInterface", iRetValue)
                    bOK = False
                End If

                If (bOK) Then
                    ' Connect to sensor with the device interface set before
                    Console.WriteLine("Connecting to scanCONTROL")
                    iRetValue = CLLTI.Connect(hLLT)
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then

                        OnError("Error during Connect", iRetValue)
                        bOK = False

                    Else
                        bConnected = True
                    End If
                End If

                If (bOK) Then
                    Console.WriteLine(Environment.NewLine & "----- Get scanCONTROL Info -----" & Environment.NewLine)
                    ' Read the device name and vendor from scanner
                    Console.WriteLine("Get Device Name")
                    iRetValue = CLLTI.GetDeviceName(hLLT, sbDevName, sbDevName.Capacity, sbVenName, sbVenName.Capacity)
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                        OnError("Error during GetDevName", iRetValue)
                        bOK = False
                    Else
                        Console.WriteLine(" - Devname: " & sbDevName.ToString & Environment.NewLine & " - Venname: " & sbVenName.ToString)
                        Dim DevName As String = sbDevName.ToString()
                        isv46 = CheckForFirmware(DevName, sbDevName.Capacity())
                    End If
                End If

                If (bOK) Then

                    ' Get the scanCONTROL type and check if it is valid
                    Console.WriteLine("Get scanCONTROL type")
                    iRetValue = CLLTI.GetLLTType(hLLT, tscanCONTROLType)
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                        OnError("Error during GetLLTType", iRetValue)
                        bOK = False
                    End If

                    If (iRetValue = CLLTI.GENERAL_FUNCTION_DEVICE_NAME_NOT_SUPPORTED) Then
                        Console.WriteLine(" - Can't decode scanCONTROL type. Please contact Micro-Epsilon for a newer version of the LLT.dll.")
                    End If

                    If (tscanCONTROLType >= CLLTI.TScannerType.scanCONTROL27xx_25 And tscanCONTROLType <= CLLTI.TScannerType.scanCONTROL27xx_xxx) Then
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL27xx")
                    ElseIf (tscanCONTROLType >= CLLTI.TScannerType.scanCONTROL25xx_25 And tscanCONTROLType <= CLLTI.TScannerType.scanCONTROL25xx_xxx) Then
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL25xx")
                    ElseIf (tscanCONTROLType >= CLLTI.TScannerType.scanCONTROL26xx_25 And tscanCONTROLType <= CLLTI.TScannerType.scanCONTROL26xx_xxx) Then
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL26xx")
                    ElseIf (tscanCONTROLType >= CLLTI.TScannerType.scanCONTROL29xx_25 And tscanCONTROLType <= CLLTI.TScannerType.scanCONTROL29xx_xxx) Then
                        Console.WriteLine(" - The scanCONTROL is a scanCONTROL29xx")
                    ElseIf (tscanCONTROLType >= CLLTI.TScannerType.scanCONTROL30xx_25 And tscanCONTROLType <= CLLTI.TScannerType.scanCONTROL30xx_xxx) Then

                    Else
                        Console.WriteLine(" - The scanCONTROL is a undefined type!" & Environment.NewLine & "Please contact Micro-Epsilon for a newer SDK!")
                    End If

                    ' Check for Firmware v46
                    If Not (isv46) Then
                        Console.WriteLine("Trigger container feature not supported - Firmware update is required")
                        bOK = False
                    End If

                    ' Get all possible resolutions for connected sensor and save them in array 
                    Console.WriteLine("Get all possible resolutions")
                    iRetValue = CLLTI.GetResolutions(hLLT, auiResolutions, auiResolutions.GetLength(0))
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                        OnError("Error during GetResolutions", iRetValue)
                        bOK = False
                    End If

                    ' Set the max. possible resolution
                    uiResolution = auiResolutions(0)
                End If

                ' Set scanner settings to valid parameters for this example
                If (bOK) Then
                    Console.WriteLine(Environment.NewLine & "----- Set scanCONTROL Parameters -----" & Environment.NewLine)
                    Console.WriteLine("Set resolution to " & uiResolution)
                    iRetValue = CLLTI.SetResolution(hLLT, uiResolution)
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                        OnError("Error during SetResolution", iRetValue)
                        bOK = False
                    End If
                End If

                If (bOK) Then
                    Console.WriteLine("Set BufferCount to " & uiBufferCount)
                    iRetValue = CLLTI.SetBufferCount(hLLT, uiBufferCount)
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                        OnError("Error during SetBufferCount", iRetValue)
                        bOK = False
                    End If
                End If

                If (bOK) Then
                    Console.WriteLine("Set Packetsize to " & uiPacketSize)
                    iRetValue = CLLTI.SetPacketSize(hLLT, uiPacketSize)
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                        OnError("Error during SetPacketSize", iRetValue)
                        bOK = False
                    End If
                End If

                If (bOK) Then
                    Console.WriteLine("Set Profile config to Container")
                    iRetValue = CLLTI.SetProfileConfig(hLLT, CLLTI.TProfileConfig.CONTAINER)
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                        OnError("Error during SetProfileConfig", iRetValue)
                        bOK = False
                    End If
                End If

                If (bOK) Then
                    Console.WriteLine("Set trigger to internal")
                    iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_TRIGGER, CLLTI.TRIG_INTERNAL)
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                        OnError("Error during SetFeature(FEATURE_FUNCTION_TRIGGER)", iRetValue)
                        bOK = False
                    End If
                End If

                If (bOK) Then
                    Console.WriteLine("Set shutter time to " & uiShutterTime)
                    iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_EXPOSURE_TIME, uiShutterTime)
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                        OnError("Error during SetFeature(FEATURE_FUNCTION_SHUTTERTIME)", iRetValue)
                        bOK = False
                    End If
                End If

                If (bOK) Then
                    Console.WriteLine("Set idle time to " & uiIdleTime)
                    iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_IDLETIME, uiIdleTime)
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                        OnError("Error during SetFeature(FEATURE_FUNCTION_IDLETIME)", iRetValue)
                        bOK = False
                    End If
                End If

                ' Main tasks in this example
                If (bOK) Then

                    Console.WriteLine(Environment.NewLine & "----- Trigger for rearranged container -----" & Environment.NewLine)
                    TriggerContainer()

                End If

                Console.WriteLine(Environment.NewLine & "----- Disconnect from scanCONTROL -----" & Environment.NewLine)

                If (bConnected) Then
                    ' Disconnect from the sensor
                    Console.WriteLine("Disconnect the scanCONTROL")
                    iRetValue = CLLTI.Disconnect(hLLT)
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                        OnError("Error during Disconnect", iRetValue)
                    End If
                End If

                If (bConnected) Then
                    ' Free ressources
                    Console.WriteLine("Delete the scanCONTROL instance")
                    iRetValue = CLLTI.DelDevice(hLLT)
                    If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                        OnError("Error during Delete", iRetValue)
                    End If
                End If
            End If

            'Wait for a keyboard hit
            While (True)
                cki = Console.ReadKey()
                If (cki.KeyChar <> "0") Then
                    Exit While
                End If
            End While

        End Sub

        Shared Sub TriggerContainer()

            Dim iRetValue As Integer
            Dim uiFieldCount As UInteger = 3
            Dim uiProfileCount As UInteger = 3
            Dim uiProfileCounter As UInteger = 0
            Dim uiInquiry As UInteger = 0
            Dim uiLostProfiles As UInteger = 0
            Dim usValue As UShort = 0
            Dim dTimeShutterOpen As Double = 0.0
            Dim dTimeShutterClose As Double = 0.0
            Dim noContainerReceived As Boolean = True

            ' Calculate the bitfield for the resolution (e.g. if Resolution 160 the result must be 7; for 1280 the result must be 10)
            Dim dTempLog As Double = 1.0 / Math.Log(2.0)
            Dim uiResolutionBitField As UInteger = CUInt(Math.Floor((Math.Log(uiResolution) * dTempLog) + 0.5))


            'Extract X and Z
            'Insert empty field for timestamp
            'Insert timestamp
            'calculation for the points per profile = Round(Log2(resolution))
            'Extract only 1th reflection
            Console.WriteLine("Set the rearrangement parameter")
            iRetValue = CLLTI.SetFeature(hLLT, CLLTI.FEATURE_FUNCTION_REARRANGEMENT_PROFILE, (CLLTI.CONTAINER_STRIPE_1 Or CLLTI.CONTAINER_DATA_Z Or
                                                                                                CLLTI.CONTAINER_DATA_X Or CLLTI.CONTAINER_DATA_EMPTYFIELD4TS Or
                                                                                                CLLTI.CONTAINER_DATA_TS Or CLLTI.CONTAINER_DATA_LSBF Or
                                                                                                (uiResolutionBitField << 12)))
            If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                OnError("Error during SetFeature", iRetValue)
                Return
            End If

            'Check if sensor supports the container mode
            iRetValue = CLLTI.GetFeature(hLLT, CLLTI.FEATURE_FUNCTION_REARRANGEMENT_PROFILE, uiInquiry)
            If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                OnError("Error during GetFeature", iRetValue)

            End If

            ' Set the profile container size according to the given profile count
            Console.WriteLine("Set profile container size")
            iRetValue = CLLTI.SetProfileContainerSize(hLLT, 0, uiProfileCount)
            If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                OnError("Error during SetProfileContainerSize", iRetValue)
                Return
            End If

            'Wait until all parameters are set before starting the transmission (this can take up to 120ms)
            System.Threading.Thread.Sleep(120)

            'Start continous profile transmission
            Console.WriteLine("Enable the measurement")
            iRetValue = CLLTI.TransferProfiles(hLLT, CLLTI.TTransferProfileType.NORMAL_CONTAINER_MODE, 1)
            If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                OnError("Error during TransferProfiles", iRetValue)
                Return
            End If

            'Start Container Triggerung
            Console.WriteLine("Enable container-trigger")
            iRetValue = CLLTI.ContainerTriggerEnable(hLLT)
            If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                OnError("Error during Enabling Container-Trigger", iRetValue)
                Return
            End If

            'Allocate buffersize according to transmitted data
            Dim abyContainerBuffer(uiResolution * 2 * uiFieldCount * uiProfileCount - 1) As Byte
            Dim adValueX(uiResolution * uiProfileCount) As Double
            Dim adValueZ(uiResolution * uiProfileCount) As Double
            Dim DisplayX(uiResolution) As Double
            Dim DisplayZ(uiResolution) As Double
            Dim abyTimestamp(16) As Byte


            Console.WriteLine("Trigger one container")
            CLLTI.TriggerContainer(hLLT)

            'Trigger one container
            Do While (noContainerReceived)
                iRetValue = CLLTI.GetActualProfile(hLLT, abyContainerBuffer, abyContainerBuffer.GetLength(0), CLLTI.TProfileConfig.CONTAINER, uiLostProfiles)
                If (iRetValue <> abyContainerBuffer.GetLength(0)) Then
                    If (iRetValue = CLLTI.ERROR_PROFTRANS_NO_NEW_PROFILE) Then
                        System.Threading.Thread.Sleep(CInt((uiShutterTime + uiIdleTime) / 100))
                        noContainerReceived = True
                    Else
                        OnError("Error during GetActualProfile", iRetValue)
                        Return
                    End If
                Else
                    noContainerReceived = False
                    Console.WriteLine("Container received")
                End If
            Loop

            Dim pinnArray As GCHandle = GCHandle.Alloc(abyContainerBuffer, GCHandleType.Pinned)
            Dim pinnX As GCHandle = GCHandle.Alloc(adValueX, GCHandleType.Pinned)
            Dim pinnZ As GCHandle = GCHandle.Alloc(adValueZ, GCHandleType.Pinned)
            Dim ptr_to_buf As IntPtr = pinnArray.AddrOfPinnedObject()
            Dim ptr_to_X As IntPtr = pinnX.AddrOfPinnedObject()
            Dim ptr_to_Z As IntPtr = pinnZ.AddrOfPinnedObject()

            convertContainerParameter.Container = ptr_to_buf
            convertContainerParameter.profileRearrangement = uiInquiry
            convertContainerParameter.numberOfProfilesToExtract = uiProfileCount
            convertContainerParameter.scanner = CUInt(tscanCONTROLType)
            convertContainerParameter.reflectionNumber = 0
            convertContainerParameter.ConvertToMM = 1
            convertContainerParameter.ReflectionWidth = IntPtr.Zero
            convertContainerParameter.MaxIntensity = IntPtr.Zero
            convertContainerParameter.Threshold = IntPtr.Zero
            convertContainerParameter.Moment0 = IntPtr.Zero
            convertContainerParameter.Moment1 = IntPtr.Zero
            convertContainerParameter.X = ptr_to_X
            convertContainerParameter.Z = ptr_to_Z

            iRetValue = CLLTI.ConvertContainer2Values(hLLT, convertContainerParameter)
            If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                OnError("Error during ConvertContainer2Values", iRetValue)
                Return
            End If

            'Print the x/z data of the first 4 points of the transmitted profiles

            'For iProfile As UInteger = 0 To uiProfileCount - 1 Step 1

            '    For iCurrentField As UInteger = 0 To 1

            '        For iCurrentPointByte As UInteger = 0 To 6 Step 2
            '            usValue = (CUShort(abyContainerBuffer((2 * iProfile * uiResolution * uiFieldCount) + (2 * iCurrentField * uiResolution) + (iCurrentPointByte))) << 8) + abyContainerBuffer((2 * iProfile * uiResolution * uiFieldCount) + (2 * iCurrentField * uiResolution) + (iCurrentPointByte + 1))
            '            Console.WriteLine("Field: " & (iCurrentField + 1) & " Point: " & (iCurrentPointByte / 2) & ": Value - " & usValue)
            '        Next

            '    Next
            '    Buffer.BlockCopy(abyContainerBuffer, (2 * (iProfile + 1) * uiResolution * uiFieldCount) - 16, abyTimestamp, 0, 16)
            '    CLLTI.Timestamp2TimeAndCount(abyTimestamp, dTimeShutterOpen, dTimeShutterClose, uiProfileCounter)
            '    Console.WriteLine("Profile Counter: " & uiProfileCounter)

            'Next
            Console.WriteLine("----Extract the X/Z data and Timestamp informations from container ----")
            For iProfile As Integer = 0 To uiProfileCount - 1 Step 1

                'Extract the 16-byte timestamp from the container buffer into timestamp buffer And display it
                Buffer.BlockCopy(abyContainerBuffer, (2 * (iProfile + 1) * uiResolution * uiFieldCount - 16), abyTimestamp, 0, 16)
                'Extract the X And Z values from each profile
                Buffer.BlockCopy(adValueX, (uiResolution * iProfile * 8), DisplayX, 0, DisplayX.Length * 8)
                Buffer.BlockCopy(adValueZ, (uiResolution * iProfile * 8), DisplayZ, 0, DisplayZ.Length * 8)
                CLLTI.Timestamp2TimeAndCount(abyTimestamp, dTimeShutterOpen, dTimeShutterClose, uiProfileCounter)
                'Display x And z values
                'show only the first four points of each profile --> if you want to show every point, just pass parameter uiResolution instead of 4
                DisplayProfile(DisplayX, DisplayZ, 4, dTimeShutterOpen, dTimeShutterClose, uiProfileCounter)

            Next

            pinnArray.Free()
            pinnX.Free()
            pinnZ.Free()

            'Stop continous proifle transmission
            Console.WriteLine("Disable the measurement")
            iRetValue = CLLTI.TransferProfiles(hLLT, CLLTI.TTransferProfileType.NORMAL_CONTAINER_MODE, 0)
            If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                OnError("Error during TransferProfiles", iRetValue)
                Return
            End If

            'Stop Triggerung Container
            Console.WriteLine("Disable container-trigger")
            iRetValue = CLLTI.ContainerTriggerDisable(hLLT)
            If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                OnError("Error during Disabling Container-Trigger", iRetValue)
                Return
            End If

        End Sub

        'Check if the correct Firmware is used for container trigger
        Shared Function CheckForFirmware(ByRef DeviceName As String, size As Integer) As Boolean

            Dim found As Integer = DeviceName.IndexOf("v")
            Dim Fimrware As String = DeviceName.Substring(found + 1, 2)
            Dim used_Firmware = Convert.ToInt32(Fimrware)
            Dim req_Firmware = 46

            'Check if Firmware >= v46 is used
            If (used_Firmware >= req_Firmware) Then
                Return True
            Else
                Return False
            End If
        End Function

        ' Display the error text
        Shared Sub OnError(strErrorTxt As String, iErrorValue As Integer)

            Dim acErrorString(200) As Byte

            Console.WriteLine(strErrorTxt)
            If (CLLTI.TranslateErrorValue(hLLT, iErrorValue, acErrorString, acErrorString.GetLength(0)) _
                                            >= CLLTI.GENERAL_FUNCTION_OK) Then
                Console.WriteLine(System.Text.Encoding.ASCII.GetString(acErrorString, 0, acErrorString.GetLength(0)))
            End If
        End Sub

        ' Display the X/Z-Data of one profile
        Shared Sub DisplayProfile(adValueX As Double(), adValueZ As Double(), uiResolution As UInteger, shutterOpen As Double, shutterClose As Double, counter As UInteger)

            Dim iNumberSize As Integer = 0
            Console.WriteLine("\r" & "Show the X/Z points from ProfileNumber: " & counter & " and the ShutterOpen: " & shutterOpen & " ShutterClose: " & shutterClose & " Time")
            For i As Integer = 0 To uiResolution - 1
                ' Prints the X- and Z-values
                iNumberSize = adValueX(i).ToString().Length
                Console.Write(Environment.NewLine & "Profiledata (" & i & "): X = " & adValueX(i).ToString())

                Do Until iNumberSize = 8
                    Console.Write(" ")
                    iNumberSize += 1
                Loop

                iNumberSize = adValueZ(i).ToString().Length
                Console.Write(" Z = " & adValueZ(i).ToString())

                Do Until iNumberSize = 8
                    Console.Write(" ")
                    iNumberSize += 1
                Loop

                ' Wait for display
                If (i Mod 8 = 0) Then
                    System.Threading.Thread.Sleep(10)
                End If
            Next
            Console.WriteLine("")
        End Sub

    End Class

End Namespace