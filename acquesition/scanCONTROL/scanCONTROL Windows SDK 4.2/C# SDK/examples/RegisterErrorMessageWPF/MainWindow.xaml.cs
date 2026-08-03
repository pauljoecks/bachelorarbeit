using System;
using System.Windows;
using MEScanControl;
using System.Windows.Interop;

namespace RegisterErrorMessageWPF
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {

        uint hLLT = 0;
        
        public MainWindow()
        {
            InitializeComponent();

            uint[] auiInterfaces = new uint[6];

            int iInterfaceCount = 0;
            int iRetValue = 0;

            //Create a Ethernet Device -> returns handle to LLT device
            hLLT = CLLTI.CreateLLTDevice(TInterfaceType.INTF_TYPE_ETHERNET);
            if (hLLT == 0)
                return;
            else 

            //Gets the available interfaces from the scanCONTROL-device
            iInterfaceCount = CLLTI.GetDeviceInterfacesFast(hLLT, auiInterfaces, auiInterfaces.GetLength(0));
            if (iInterfaceCount <= 0)
                return;
            else MessageBox.Show(iInterfaceCount + " Sensor(s) found");

            // Set the first IP address detected by GetDeviceInterfacesFast to handle
            if ((iRetValue = CLLTI.SetDeviceInterface(hLLT, auiInterfaces[0], 0))
                < CLLTI.GENERAL_FUNCTION_OK)
            {
                return;
            }
        }

        private void Button_Click(object sender, RoutedEventArgs e)
        {
            if (CLLTI.Connect(hLLT) < CLLTI.GENERAL_FUNCTION_OK)
            {
                return;
            }
            else MessageBox.Show("Sensor connected!");

            IntPtr windowHandle = new WindowInteropHelper(this).Handle;

            HwndSource source = HwndSource.FromHwnd(windowHandle);
            source.AddHook(new HwndSourceHook(WndProc));
            CLLTI.RegisterErrorMsg(hLLT, 0x0400, windowHandle, (UIntPtr)0);
        }

        private void Button_Click_1(object sender, RoutedEventArgs e)
        {
            if (CLLTI.Disconnect(hLLT) < CLLTI.GENERAL_FUNCTION_OK)
            {
                return;
            }
            else  MessageBox.Show("Sensor disconnected!");
        }

        private static IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
        {
            if (msg == 0x0400)
            {
                if ((int)lParam == CLLTI.ERROR_CONNECTIONLOST)
                // error handling, if error code "connection lost"

                // Show Message Box if connection to sensor is lost
                MessageBox.Show("Connection to scanner lost");
            }

            return IntPtr.Zero;
        }
    }
}
