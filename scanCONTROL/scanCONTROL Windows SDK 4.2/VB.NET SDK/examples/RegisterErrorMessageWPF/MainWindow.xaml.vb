Imports System
Imports System.Collections.Generic
Imports System.Runtime.InteropServices
Imports System.Text
Imports System.Threading
Imports System.Windows
Imports System.Windows.Interop

Namespace VB


    Partial Public Class MainWindow
        Inherits Window

        Dim hLLT As UInteger

        Public Sub New()
            'MyBase.New()
            Dim auiInterfaces(6) As UInteger
            Dim iRetValue As Integer
            Dim iInterfaceCount As Integer = 0

            'Create a Ethernet Device -> returns a handle to the LLT device
            hLLT = CLLTI.CreateLLTDevice(CLLTI.TInterfaceType.INTF_TYPE_ETHERNET)
            If (hLLT = 0) Then
                Return
            End If

            'Gets the available interfaces from the scanCONTROL device
            iInterfaceCount = CLLTI.GetDeviceInterfacesFast(hLLT, auiInterfaces, auiInterfaces.GetLength(0))
            If (iInterfaceCount <= 0) Then
                Return
            Else
                MessageBox.Show(iInterfaceCount & " Sensor(s) found")
            End If

            'Set the first IP Adress detected by the GetDeviceInterfaceFast to handle
            iRetValue = CLLTI.SetDeviceInterface(hLLT, auiInterfaces(0), 0)
            If (iRetValue < CLLTI.GENERAL_FUNCTION_OK) Then
                Return
            End If

        End Sub

        Private Sub Button_Click(sender As Object, e As RoutedEventArgs)
            If (CLLTI.Connect(hLLT) < CLLTI.GENERAL_FUNCTION_OK) Then
                Return
            Else
                MessageBox.Show("Sensor connected!")
            End If


            Dim windowHandle As IntPtr = New WindowInteropHelper(Me).Handle

            Dim source As HwndSource = HwndSource.FromHwnd(windowHandle)
            source.AddHook(New HwndSourceHook(AddressOf WndProc))
            CLLTI.RegisterErrorMsg(hLLT, &H400, windowHandle, 0)
        End Sub

        Private Sub Button_Click_1(sender As Object, e As RoutedEventArgs)
            If (CLLTI.Disconnect(hLLT) < CLLTI.GENERAL_FUNCTION_OK) Then
                Return
            Else
                MessageBox.Show("Sensor disconnected!")
            End If
        End Sub

        Private Function WndProc(hwnd As IntPtr, msg As Integer, wParam As IntPtr, lParam As IntPtr, ByRef handled As Boolean) As IntPtr

            If (msg = &H400) Then
                If (CInt(lParam) = CLLTI.ERROR_CONNECTIONLOST) Then
                    ' error handling, if error code "connection lost"

                    ' Show Message Box if connection to sensor is lost
                    MessageBox.Show("Connection to scanner lost!")
                End If
            End If
            Return IntPtr.Zero
        End Function

    End Class


End Namespace
