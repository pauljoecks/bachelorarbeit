
namespace MEScanControl
{
    using System;
    using System.Runtime.InteropServices;

    internal static class Win32
    {

#if WIN64
        [DllImport("ntdll.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern int memcpy(
            long dst,
            long src,
            int count);
#else
        [DllImport("ntdll.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern int memcpy(
            int dst,
            int src,
            int count);
#endif


        [DllImport( "avifil32.dll" )]
        public static extern void AVIFileInit( );

        [DllImport( "avifil32.dll" )]
        public static extern void AVIFileExit( );

        [DllImport( "avifil32.dll", CharSet = CharSet.Unicode )]
        public static extern int AVIFileOpen(
            out IntPtr aviHandler,
            String fileName,
            OpenFileMode mode,
            IntPtr handler );

        [DllImport( "avifil32.dll" )]
        public static extern int AVIFileRelease(
            IntPtr aviHandler );

        [DllImport( "avifil32.dll" )]
        public static extern int AVIFileGetStream(
            IntPtr aviHandler,
            out IntPtr streamHandler,
            int streamType,
            int streamNumner );

        [DllImport( "avifil32.dll" )]
        public static extern int AVIFileCreateStream(
            IntPtr aviHandler,
            out IntPtr streamHandler,
            ref AVISTREAMINFO streamInfo );

        [DllImport( "avifil32.dll" )]
        public static extern int AVIStreamRelease(
            IntPtr streamHandler );

        [DllImport( "avifil32.dll" )]
        public static extern int AVIStreamSetFormat(
            IntPtr streamHandler,
            int position,
            ref BITMAPINFO format,
            int formatSize );

        [DllImport( "avifil32.dll" )]
        public static extern int AVIStreamStart(
            IntPtr streamHandler );

        [DllImport( "avifil32.dll" )]
        public static extern int AVIStreamLength(
            IntPtr streamHandler );

        [DllImport( "avifil32.dll", CharSet = CharSet.Unicode )]
        public static extern int AVIStreamInfo(
            IntPtr streamHandler,
            ref AVISTREAMINFO streamInfo,
            int infoSize );

        [DllImport( "avifil32.dll" )]
        public static extern IntPtr AVIStreamGetFrameOpen(
            IntPtr streamHandler,
            ref BITMAPINFOHEADER wantedFormat );

        [DllImport( "avifil32.dll" )]
        public static extern IntPtr AVIStreamGetFrameOpen(
            IntPtr streamHandler,
            int wantedFormat );

        [DllImport( "avifil32.dll" )]
        public static extern int AVIStreamGetFrameClose(
            IntPtr getFrameObject );

        [DllImport("avifil32.dll", EntryPoint = "AVIFileWriteData")]
        internal static extern int AVIFileWriteData(IntPtr ppfile, Int32 ckid, char[] buf, int cbData);

        [DllImport( "avifil32.dll" )]
        public static extern IntPtr AVIStreamGetFrame(
            IntPtr getFrameObject,
            int position );


        [DllImport( "avifil32.dll" )]
        public unsafe static extern int AVIStreamWrite(
            IntPtr streamHandler,
            int start,
            int samples,
            IntPtr buffer,
            int bufferSize,
            int flags,
            IntPtr samplesWritten,
            int* bytesWritten );


        [DllImport( "avifil32.dll" )]
        public static extern int AVISaveOptions(
            IntPtr window,
            int flags,
            int streams,
            [In, MarshalAs( UnmanagedType.LPArray, SizeParamIndex = 0 )] IntPtr[] streamInterfaces,
            [In, MarshalAs( UnmanagedType.LPArray, SizeParamIndex = 0 )] IntPtr[] options );

        [DllImport( "avifil32.dll" )]
        public static extern int AVISaveOptionsFree(
            int streams,
            [In, MarshalAs( UnmanagedType.LPArray, SizeParamIndex = 0 )] IntPtr[] options );


        [DllImport( "avifil32.dll", EntryPoint = "AVIMakeCompressedStream")]
        public static extern int AVIMakeCompressedStream(
            out IntPtr compressedStream,
            IntPtr sourceStream,
            ref AVICOMPRESSOPTIONS options,
            IntPtr clsidHandler );

 
        /// 
        [StructLayout( LayoutKind.Sequential, Pack = 1 )]
        public struct RECT
        {

            [MarshalAs( UnmanagedType.I4 )]
            public int left;

            [MarshalAs( UnmanagedType.I4 )]
            public int top;

            [MarshalAs( UnmanagedType.I4 )]
            public int right;

            [MarshalAs( UnmanagedType.I4 )]
            public int bottom;
        }


        [StructLayout( LayoutKind.Sequential, CharSet = CharSet.Unicode, Pack = 1 )]
        public struct AVISTREAMINFO
        {

            [MarshalAs( UnmanagedType.I4 )]
            public int type;

            [MarshalAs( UnmanagedType.I4 )]
            public int handler;

            [MarshalAs( UnmanagedType.I4 )]
            public int flags;

            [MarshalAs( UnmanagedType.I4 )]
            public int Capabilities;

            [MarshalAs( UnmanagedType.I2 )]
            public short priority;

            [MarshalAs( UnmanagedType.I2 )]
            public short language;

            [MarshalAs( UnmanagedType.I4 )]
            public int scale;

            [MarshalAs( UnmanagedType.I4 )]
            public int rate;

            [MarshalAs( UnmanagedType.I4 )]
            public int start;

            [MarshalAs( UnmanagedType.I4 )]
            public int length;

            [MarshalAs( UnmanagedType.I4 )]
            public int initialFrames;

            [MarshalAs( UnmanagedType.I4 )]
            public int suggestedBufferSize;

            [MarshalAs( UnmanagedType.I4 )]
            public int quality;

            [MarshalAs( UnmanagedType.I4 )]
            public int sampleSize;
 
            [MarshalAs( UnmanagedType.Struct, SizeConst = 16 )]
            public RECT rectFrame;

            [MarshalAs( UnmanagedType.I4 )]
            public int editCount;

            [MarshalAs( UnmanagedType.I4 )]
            public int formatChangeCount;

            [MarshalAs( UnmanagedType.ByValTStr, SizeConst = 64 )]
            public string name;
        }

        [StructLayout( LayoutKind.Sequential, Pack = 1 )]
        public struct BITMAPINFOHEADER
        {

            [MarshalAs( UnmanagedType.I4 )]
            public int size;

            [MarshalAs( UnmanagedType.I4 )]
            public int width;

            [MarshalAs( UnmanagedType.I4 )]
            public int height;

            [MarshalAs( UnmanagedType.I2 )]
            public short planes;

            [MarshalAs( UnmanagedType.I2 )]
            public short bitCount;

            [MarshalAs( UnmanagedType.I4 )]
            public int compression;

            [MarshalAs( UnmanagedType.I4 )]
            public int sizeImage;

            [MarshalAs( UnmanagedType.I4 )]
            public int xPelsPerMeter;

            [MarshalAs( UnmanagedType.I4 )]
            public int yPelsPerMeter;

            [MarshalAs( UnmanagedType.I4 )]
            public int colorsUsed;

            [MarshalAs( UnmanagedType.I4 )]
            public int colorsImportant;

        }


        [StructLayout(LayoutKind.Sequential, Pack = 1)]
        public struct BITMAPINFO
        {
            public BITMAPINFOHEADER bmiHeader;
            //public static RGBQUAD[] bmiColors = new RGBQUAD [256];
            [MarshalAs(UnmanagedType.ByValArray, ArraySubType = UnmanagedType.LPStruct, SizeConst = 255)]
            public RGBQUAD[] bmiColors;
        }

        [StructLayout(LayoutKind.Sequential)]
        public struct RGBQUAD
        {
            public byte rgbBlue;
            public byte rgbGreen;
            public byte rgbRed;
            public byte rgbReserved;
        }

        [StructLayout(LayoutKind.Sequential)]
        public struct AVICOMPRESSOPTIONS
        {
            public UInt32 fccType;
            public UInt32 fccHandler;
            public UInt32 dwKeyFrameEvery;
            public UInt32 dwQuality;
            public UInt32 dwBytesPerSecond;
            public UInt32 dwFlags;
            public IntPtr lpFormat;
            public UInt32 cbFormat;
            public IntPtr lpParms;
            public UInt32 cbParms;
            public UInt32 dwInterleaveEvery;
        }

        [Flags]
        public enum OpenFileMode
        {
            Read = 0x00000000,
            Write = 0x00000001,
            ReadWrite = 0x00000002,
            ShareCompat = 0x00000000,
            ShareExclusive = 0x00000010,
            ShareDenyWrite = 0x00000020,
            ShareDenyRead = 0x00000030,
            ShareDenyNone = 0x00000040,
            Parse = 0x00000100,
            Delete = 0x00000200,
            Verify = 0x00000400,
            Cancel = 0x00000800,
            Create = 0x00001000,
            Prompt = 0x00002000,
            Exist = 0x00004000,
            Reopen = 0x00008000
        }


        public static Int32 mmioFOURCC(char ch0, char ch1, char ch2, char ch3)
        {
            return ((Int32)(byte)(ch0) | ((byte)(ch1) << 8) | ((byte)(ch2) << 16) | ((byte)(ch3) << 24));
        }

 
        public static string decode_mmioFOURCC( int code )
        {
            char[] chs = new char[4];

            for ( int i = 0; i < 4; i++ )
            {
                chs[i] = (char) (byte) ( ( code >> ( i << 3 ) ) & 0xFF );
                if ( !char.IsLetterOrDigit( chs[i] ) )
                    chs[i] = ' ';
            }
            return new string( chs );
        }

    }
}
