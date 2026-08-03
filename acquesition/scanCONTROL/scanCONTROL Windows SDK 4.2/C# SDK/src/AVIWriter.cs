

namespace MEScanControl
{
	using System;
    using System.Text;
    using System.Drawing;
	using System.Runtime.InteropServices;
    using System.IO;


    public class AviInfo
    {
        internal ulong serial = 0;
        internal uint rearrangement;
        internal uint maintenance;
        internal uint extended1 = 0xffffffff;
        internal TProfileConfig  profileConfig;
        internal TPartialProfile partialProfile;
        internal string name;
        internal string version ;

    }

    public class SaveInfo
    {
        internal bool is_container = false;
        internal uint uiBufferCount = 1U;
        internal uint max_filesize = 50U * 1024U * 1024U;
        internal uint max_profilesize;
        internal TProfileConfig profileConfig;
        //internal string filename;

    }
    public class AVIWriter 
	{
        // AVI file
        private IntPtr file = IntPtr.Zero;
        // video stream
        private IntPtr stream = IntPtr.Zero;
        // compressed stream
		private IntPtr streamCompressed = IntPtr.Zero;
        // buffer
		private IntPtr buffer = IntPtr.Zero;
        private IntPtr bytesWritten_ptr = IntPtr.Zero;

        // width of video frames
        private int width;
        // height of vide frames
        private int height;
        // quality
		private int quality = -1;
        // current position
		private int position;

        private static Win32.AVICOMPRESSOPTIONS options = new Win32.AVICOMPRESSOPTIONS();
        static private AviInfo AviInfo = new AviInfo();
        static private SaveInfo saveInfo = new SaveInfo();


        public void SetMaxFileSize(uint max_filesize)
        {
            saveInfo.max_filesize = max_filesize;
        }

        public void SetMaxProfileSize(uint max_profilesize)
        {
            saveInfo.max_profilesize = max_profilesize;
        }

        /// <summary>
        /// </summary>
        /// 
        public AVIWriter( )
		{
			Win32.AVIFileInit( );
		}

        ~AVIWriter()
        {
            Win32.AVIFileExit();
        }


        /// <summary>
        /// Create new AVI file and open it for writing.
        /// </summary>
        /// 
        /// 
        public unsafe void Open( string fileName, int width, int height, ref AviInfo header)
		{
			// close previous file
			Close( );

           // check width and height
            if ( ( ( width & 1 ) != 0 ) || ( ( height & 1 ) != 0 ) )
            {
	            throw new ArgumentException( "Video file resolution must be a multiple of two." );
            }

            bool success = false;

            saveInfo.profileConfig = header.profileConfig;

            try
            {
                this.width = width;
                this.height = height;

                // create new file
                if ( Win32.AVIFileOpen( out file, fileName, Win32.OpenFileMode.Create | Win32.OpenFileMode.Write | Win32.OpenFileMode.ShareExclusive , IntPtr.Zero ) != 0 )
                    throw new System.IO.IOException( "Failed opening the specified file." );


                char[] Header = Generate_AVIHeader(ref header);

                Win32.AVIFileWriteData(file, Win32.mmioFOURCC('L', 'I', 'S', 'T'), Header, Header.Length);

                // describe new stream
                Win32.AVISTREAMINFO info = new Win32.AVISTREAMINFO( );

                info.type    = Win32.mmioFOURCC('v', 'i', 'd', 's');
                info.handler = Win32.mmioFOURCC('D','I','B', ' ');
                info.scale   = 1;
                info.rate    = 250;
                info.suggestedBufferSize = width * height;
                info.rectFrame = new Win32.RECT();
                info.rectFrame.bottom = height;
                info.rectFrame.right = width;

                // create stream
                if (Win32.AVIFileCreateStream(file, out stream, ref info) != 0)
                {
                    Console.WriteLine("False");
                }
                        

                // describe compression options                  
                options.fccHandler = (uint)Win32.mmioFOURCC('D', 'I', 'B', ' ' );
                options.dwQuality = (uint)quality;
                options.dwFlags = 0x00000008;
                options.fccType = (uint)Win32.mmioFOURCC('v', 'i', 'd', 's');

                // create compressed stream
                int fret = Win32.AVIMakeCompressedStream(out streamCompressed, stream, ref options, IntPtr.Zero);


                Win32.BITMAPINFO BITMAPINFO = new Win32.BITMAPINFO();
                BITMAPINFO.bmiHeader.size = sizeof(Win32.BITMAPINFOHEADER);
                BITMAPINFO.bmiHeader.width = width;
                BITMAPINFO.bmiHeader.height = height;
                BITMAPINFO.bmiHeader.sizeImage = width * height;
                BITMAPINFO.bmiHeader.bitCount = 8;
                BITMAPINFO.bmiHeader.colorsUsed = 256;
                BITMAPINFO.bmiHeader.planes = 1;
                BITMAPINFO.bmiHeader.compression = 0;


                BITMAPINFO.bmiColors = new Win32.RGBQUAD[256];
                    
                for (uint i = 0; i < 256; i++)
                {
                    BITMAPINFO.bmiColors[i].rgbBlue = (byte)i;
                    BITMAPINFO.bmiColors[i].rgbRed = (byte)i;
                    BITMAPINFO.bmiColors[i].rgbGreen = (byte)i;
                    BITMAPINFO.bmiColors[i].rgbReserved = (byte)i;
                }

                // set frame format
                if ( Win32.AVIStreamSetFormat( streamCompressed, 0, ref BITMAPINFO, 1088 ) != 0)
                {
                    Console.WriteLine("False");
                }
                        

                // alloc unmanaged memory for frame
                buffer = Marshal.AllocHGlobal( width * height );

                if ( buffer == IntPtr.Zero )
                {
                    throw new OutOfMemoryException( "Insufficient memory for internal buffer." );
                }

                position = 0;
                success = true;
                
            }
            finally
            {
                if ( !success )
                {
                    Close( );
                }
            }
		}

        /// <summary>
        /// Close video file.
        /// </summary>
        /// 
        public void Close( )
		{
 
            // free unmanaged memory
            if ( buffer != IntPtr.Zero )
            {
                Marshal.FreeHGlobal( buffer );
                Marshal.FreeHGlobal(bytesWritten_ptr);
                buffer = IntPtr.Zero;
                bytesWritten_ptr = IntPtr.Zero;
            }

            // release compressed stream
            if ( streamCompressed != IntPtr.Zero )
            {
                Win32.AVIStreamRelease( streamCompressed );
                streamCompressed = IntPtr.Zero;
            }

            // release stream
            if ( stream != IntPtr.Zero )
            {
                Win32.AVIStreamRelease( stream );
                stream = IntPtr.Zero;
            }

            // release file
            if ( file != IntPtr.Zero )
            {
                Win32.AVIFileRelease( file );
                file = IntPtr.Zero;
            }
          
		}

        /// <summary>
        /// Add new frame to the AVI file.
        /// </summary>
        public unsafe int AddFrame( ref byte [] data  )
		{

            bytesWritten_ptr = Marshal.AllocHGlobal(64);
            int* ptr = (int*)bytesWritten_ptr.ToPointer();
            int bytesWritten = 0;


            // check if AVI file was properly opened
            if ( buffer == IntPtr.Zero )
                throw new System.IO.IOException( "AVI file should be successfully opened before writing." );

  
            if (saveInfo.profileConfig == TProfileConfig.PURE_PROFILE || saveInfo.profileConfig == TProfileConfig.QUARTER_PROFILE)
            {
                FlipImageLinesForSaving(ref data, width, height);

            }
            else
            {
                FlipImageLines(ref data, width, height, 1);
            }


            if (position < saveInfo.max_profilesize)
            {
                if (saveInfo.max_filesize >= (position + 1) * (width * height))
                {

                    if (Win32.AVIStreamWrite(streamCompressed, position, 1, buffer,
                        width * height, 0, IntPtr.Zero, ptr) != 0)
                    {
                        return bytesWritten = 0;
                    }
                    position++;
                }
                else
                {
                    //error max file size reached
                    return bytesWritten = -1;
                }
            }
            else
            {
                //error maxprofilesize reached
                return bytesWritten = -2;
            }
            return bytesWritten = *ptr;
            
		}

        //necessary for 32/64 bit handling
#if WIN64
        private void FlipImageLines (ref byte [] SourceImage , int width, int height, uint pointSize)
        {
            
            IntPtr _data = IntPtr.Zero;
            long dst_x64 = 0;
            long src_x64 = 0;


            unsafe
            {
                fixed (byte* ptr = &SourceImage[0])
                {
                    _data = (IntPtr)ptr;
                }
            }

            src_x64 = _data.ToInt64();
            if (saveInfo.profileConfig == TProfileConfig.PURE_PROFILE || saveInfo.profileConfig == TProfileConfig.QUARTER_PROFILE)
            {
                dst_x64 = buffer.ToInt64() + width * (height - 1) + width * 8;
            }
            else
            {
                //dst = buffer.ToInt32();
                dst_x64 = buffer.ToInt64() + width * (height - 1);
            }


            for (int y = 0; y < height; y++)
            {
                Win32.memcpy(dst_x64, src_x64, width);
                dst_x64 -= width;
                src_x64 += width;
            }
                        
        }
        private void FlipImageLinesForSaving(ref byte[] SourceImage, int width, int height)
        {
            IntPtr _sourceTimestamp = IntPtr.Zero;

            if (saveInfo.profileConfig == TProfileConfig.PURE_PROFILE)
            {
                byte[] arr = ChangeByteOrderForPureProfile(ref SourceImage, height - 8);
                FlipImageLines(ref arr, width, height - 8, 1);
            }
            else
            {
                FlipImageLines(ref SourceImage, width, height - 8, 1);
            }


            unsafe
            {
                fixed (byte* ptr = &SourceImage[0])
                {
                    _sourceTimestamp = (IntPtr)ptr;
                }
            }
            long src_timestamp = _sourceTimestamp.ToInt64() + width * (height - 8);
            long dst_timestamp = buffer.ToInt64() + width * 8;

            if (IsQuarterProfile((uint)width))
            {
                dst_timestamp = buffer.ToInt64() + width * 8 - 12;
            }
            else
            {
                dst_timestamp = buffer.ToInt64() + width * 8 - 4;
            }

            for (uint j = 0; j < 8; j++)
            {
                Win32.memcpy(dst_timestamp, src_timestamp, 2);
                src_timestamp += 2;
                dst_timestamp -= width;
            }
        }
#else

        private void FlipImageLines(ref byte[] SourceImage, int width, int height, uint pointSize)
        {

            IntPtr _data = IntPtr.Zero;
            int dst = 0;
            int src = 0;

            unsafe
            {

                fixed (byte* ptr = &SourceImage[0])
                {
                    _data = (IntPtr)ptr;
                }
            }


            src = _data.ToInt32();

            if (saveInfo.profileConfig == TProfileConfig.PURE_PROFILE || saveInfo.profileConfig == TProfileConfig.QUARTER_PROFILE)
            {
                dst = buffer.ToInt32() + width * (height - 1) + width * 8;
            }
            else
            {
                dst = buffer.ToInt32() + width * (height - 1);
            }

            for (int y = 0; y < height; y++)
            {
                Win32.memcpy(dst, src, width);
                dst -= width;
                src += width;
            }
        }

        private void FlipImageLinesForSaving(ref byte [] SourceImage, int width, int height)
        {
            IntPtr _sourceTimestamp = IntPtr.Zero;

            if (saveInfo.profileConfig == TProfileConfig.PURE_PROFILE)
            {
                byte [] arr = ChangeByteOrderForPureProfile(ref SourceImage, height - 8);
                FlipImageLines(ref arr, width, height - 8, 1);
            }
            else
            {
                FlipImageLines(ref SourceImage, width, height - 8, 1);
            }
            
                               
            unsafe
            {
                fixed (byte* ptr = &SourceImage[0])
                {
                    _sourceTimestamp = (IntPtr)ptr;
                }
            }
            int src_timestamp = _sourceTimestamp.ToInt32() + width * (height - 8);
            int dst_timestamp = buffer.ToInt32() + width * 8;

            if (IsQuarterProfile((uint)width))
            {
                dst_timestamp = buffer.ToInt32()+ width*8-12;
            }
            else
            {
                dst_timestamp = buffer.ToInt32() +width*8- 4;
            }

            for (uint j =0; j <8; j++)
            {
                Win32.memcpy(dst_timestamp, src_timestamp, 2);
                src_timestamp += 2;
                dst_timestamp -= width;
            }
        }
#endif

        private byte [] ChangeByteOrderForPureProfile(ref byte[] pPureProfileBuffer, int nPointCount)
        {
            byte[] _buf = new byte[0];
            ushort[] working_buffer = new ushort[pPureProfileBuffer.Length / 2];
            Buffer.BlockCopy(pPureProfileBuffer, 0, working_buffer, 0, pPureProfileBuffer.Length-8);
            int j = 0;
            
            for (uint idx = 0; idx < 2 * nPointCount; idx++)
            {
                ushort tmp = ReverseBytes((ushort)working_buffer[idx]);
                working_buffer[idx] = tmp;
                j++;

            }

            for (int i = 0; i < working_buffer.Length; i++)
            {
                
                var bytes = BitConverter.GetBytes(working_buffer[i]);
                foreach(byte b in bytes)
                {
                    Array.Resize(ref _buf, _buf.Length + 1);
                    _buf[_buf.Length-1] = b;
                    
                }
                
            }

            return _buf;
        }

        public static char[] Generate_AVIHeader(ref AviInfo aviInfo)
        {
            var profile_cfg = (uint)aviInfo.profileConfig;
            
            if (IsReducedProfileFormat(aviInfo.profileConfig) == true)
            {
                profile_cfg = profile_cfg | 0x00000080;
            }

            if (IsLoopbackActive((uint)aviInfo.maintenance) == true)
            {
                profile_cfg = profile_cfg | 0x00000040;
            }

            bool is_compressed = IsCompressActive((uint)aviInfo.maintenance);
            uint b_is_compressed = Convert.ToUInt16(is_compressed);
            //uint b_is_compressed = 10;

            char[] Header = { 'I', 'N', 'F', 'O', 'I', 'C', 'M', 'T', '\0', '\0', '\0', '\0' };
            var preambleSize = Header.Length;

            
            
            //Conversion
            byte[] version = Encoding.ASCII.GetBytes(aviInfo.version);
            byte[] name = Encoding.ASCII.GetBytes(aviInfo.name);
            string s_serial = aviInfo.serial.ToString();
            byte[] serial = Encoding.ASCII.GetBytes(s_serial);
            string s_profile_cfg = Convert.ToString(profile_cfg, 16);
            string s_StartPoint = Convert.ToString(aviInfo.partialProfile.nStartPoint, 16);
            string s_StartPointData = Convert.ToString(aviInfo.partialProfile.nStartPointData, 16);
            string s_rearrangement = Convert.ToString(aviInfo.rearrangement, 16);
            string s_extended1 = Convert.ToString(aviInfo.extended1, 16);
            string s_is_compressed = Convert.ToString(b_is_compressed);
            byte[] by_is_compressed = Encoding.ASCII.GetBytes(s_is_compressed);


            //Version
            Array.Resize(ref Header, Header.Length + version.Length);
            foreach (char b in version)
            {
                Header[Header.GetUpperBound(0)] = b;
            }

            Array.Resize(ref Header, Header.Length + 1);
            Header[Header.GetUpperBound(0)] = '\t';

            //name
            foreach (char n in name)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = n;
            }

            for (int i = 0; i < 64 - name.Length; i++)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = ' ';
            }

            Array.Resize(ref Header, Header.Length + 1);
            Header[Header.GetUpperBound(0)] = '\t';

            //serial
            foreach (char s in serial)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = s;
            }

            for (int i = 0; i < 13 - serial.Length; i++)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = ' ';
            }

            Array.Resize(ref Header, Header.Length + 1);
            Header[Header.GetUpperBound(0)] = '\t';

            //profileConfig
            foreach (char p in s_profile_cfg)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = p;
            }

            Array.Resize(ref Header, Header.Length + 1);
            Header[Header.GetUpperBound(0)] = '\t';

            // partial profile startPoint
            for (int i = 0; i < 4 - s_StartPoint.Length; i++)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = '0';
            }
            foreach (char p in s_StartPoint)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = p;
            }



            Array.Resize(ref Header, Header.Length + 1);
            Header[Header.GetUpperBound(0)] = '\t';

            //partial profile StartPointData
            for (int i = 0; i < 4 - s_StartPointData.Length; i++)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = '0';
            }
            foreach (char p in s_StartPointData)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = p;
            }


            Array.Resize(ref Header, Header.Length + 1);
            Header[Header.GetUpperBound(0)] = '\t';

            //rearrangement
            foreach (char p in s_rearrangement)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = p;
            }
            for (int i = 0; i < 8 - s_rearrangement.Length; i++)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = '0';
            }

            Array.Resize(ref Header, Header.Length + 1);
            Header[Header.GetUpperBound(0)] = '\t';

            //extended
            foreach (char p in s_extended1)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = p;
            }
            for (int i = 0; i < 8 - s_extended1.Length; i++)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = '0';
            }

            Array.Resize(ref Header, Header.Length + 1);
            Header[Header.GetUpperBound(0)] = '\t';

            // is_cpmpressed
            foreach (char p in by_is_compressed)
            {
                Array.Resize(ref Header, Header.Length + 1);
                Header[Header.GetUpperBound(0)] = p;
            }



            Array.Resize(ref Header, Header.Length + 1);
            Header[Header.GetUpperBound(0)] = '\0';

            Header[8] = (char)(Header.Length - preambleSize);


            return Header;


        }

        private static bool IsReducedProfileFormat(TProfileConfig cfg)
        {
            if (cfg == TProfileConfig.PURE_PROFILE || cfg == TProfileConfig.QUARTER_PROFILE)
            {
                return true;
            }
            else
            {
                return false;
            }
        }

        private static bool IsLoopbackActive(uint value)
        {
            return (value & 0x00000002) != 0U;
        }

        private static bool IsCompressActive(uint value)
        {
            return (value & 0x00000001) != 0U;
        }

        private static bool IsQuarterProfile(uint width)
        {
            return width == 16;
        }

        public static UInt16 ReverseBytes(UInt16 value)
        {
            return (UInt16)((value & 0xFFU) << 8 | (value & 0xFF00U) >> 8);
        }
    }
}
