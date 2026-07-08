/*
 * scanCONTROL C# SDK - C# wrapper for LLT.dll
 *
 * MIT License
 *
 * Copyright © 2017-2018 Micro-Epsilon Messtechnik GmbH & Co. KG
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:

 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.

 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 * Author: Daniel Rauch <daniel.rauch@micro-epsilon.de>
 */

using System;
using System.Windows.Forms;

namespace MEScanControl
{
    public partial class Form1 : Form
    {       
        CScanCONTROLSample sc = new CScanCONTROLSample();

        public Form1()
        {
            // Init
            InitializeComponent();              
        }

        // Handle connect button click
        private void button1_Click(object sender, System.EventArgs e)
        {
            sc.scanCONTROL_Sample();            
            System.Threading.Thread.Sleep(2000);  
       
            // Register the error message handling
            CLLTI.RegisterErrorMsg(CScanCONTROLSample.hLLT, 0x0400, this.Handle, (UIntPtr)0);
            label2.Text = "Connected";            
        }
       
        // Overwritten WndProc for message handling
        protected override void WndProc(ref Message m)
        {
            if (m.Msg == 0x0400)
            {
                if ((int)m.LParam == CLLTI.ERROR_CONNECTIONLOST)
                    // error handling, if error code "connection lost"
                    sc.Disconnect();
                    label2.Text = "Connection Lost";

                    // Show Message Box if connection to sensor is lost
                    MessageBox.Show("Connection to scanner lost");
            }

            base.WndProc(ref m);           
        }

        // Handle disconnect button click
        private void button2_Click(object sender, EventArgs e)
        {
            sc.Disconnect();
            label2.Text = "Disconnected";
        }
    }
}
