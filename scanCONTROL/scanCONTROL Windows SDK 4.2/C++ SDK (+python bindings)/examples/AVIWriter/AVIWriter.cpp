////////////////////////////////////////////////////////////////////////////////////////////////////
/// \file
/// \brief Write AVIs to file
///
////////////////////////////////////////////////////////////////////////////////////////////////////

// clang-format off
////////////////////////////////////////////////////////////////////////////////////////////////////
/// \class AVIWriter
/// \details
///
/// # remarks #
/// - there is no file check, i.e. an existing file will be overwritten
/// - default max. filesize is 50MB
/// - no checks of the input data
///
/// For the reduced profile formats (PURE_PROFILE and QUARTER_PROFILE), the ImageSize must be set accordingly.
/// i.e. PURE_PROFILE width = 4, heigth = resolution + 8
///      QUARTER_PROFILE = width = 16, heigth =  resolution + 8
///
/// # not implemented until now #
/// - container avis, therefore the rearrangement field __must__ be zero
/// - the monitoring of the file size
/////////////////////////////////////////////////////////////////////////////////////////////////
// clang-format on
#include <random>
#include <cassert>
#include <direct.h>
#include "AVIWriter.h"

// For including FMT-lib, following steps are necessary:
// define the FMT_HEADER_ONLY macro
// Add the fmt library (downloadable from GitHub) to the AVIWriter project (./examples/AVIWriter/FMT-Lib) (for VS2013 the recommended FMT-Lib version is fmt-5.1.0)
// include the fmt directory from include
// Example:
#define FMT_HEADER_ONLY
#include "FMT-Lib/include/fmt/format.h"


// Inlcude Windwos Multimedia Vfw lib
#pragma comment (lib, "Vfw32.lib")

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn AviWriter::AviWriter()
///
/// \brief  Constructor for the AVIWriter class.
///
/// \author Sven Ackermann
/// \date 02.03.2016
////////////////////////////////////////////////////////////////////////////////////////////////////
AviWriter::AviWriter()
{
  AVIFileInit();
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn AviWriter::~AviWriter()
///
/// \brief  Destructor for the AVIWriter class.
///
/// \author Sven Ackermann
/// \date 02.03.2016
////////////////////////////////////////////////////////////////////////////////////////////////////
AviWriter::~AviWriter()
{
  if (m_AviParameter.pAviStream != nullptr)
    AVIStreamRelease(m_AviParameter.pAviStream);

  if (m_AviParameter.pAviComprStream != nullptr)
    AVIStreamRelease(m_AviParameter.pAviComprStream);

  if (m_AviParameter.pAviFile != nullptr)
    AVIFileRelease(m_AviParameter.pAviFile);
  AVIFileExit();

  m_AviParameter.pAviFile = nullptr;
  m_AviParameter.pAviStream = nullptr;
  m_AviParameter.pAviComprStream = nullptr;

  if (m_bAviInit)
  {
    m_bAviInit = false;
    CoUninitialize();
  }
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn void AviWriter::SetMaxFileSize(unsigned int max_filesize)
///
/// \brief  Sets a new max file size.
///
/// \author Sven Ackermann
/// \date 02.03.2016
///
/// \param  max_filesize New maximal size of the file.
////////////////////////////////////////////////////////////////////////////////////////////////////
void AviWriter::SetMaxFileSize(unsigned int max_filesize)
{
  m_SaveInfo.max_filesize = max_filesize;
}

void AviWriter::SetMaxProfileSize(unsigned int max_profilesize) 
{
	m_SaveInfo.max_profilesize = max_profilesize;
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn unsigned int AviWriter::GetMaxFileSize() const
///
/// \brief  Gets the actual max file size.
///
/// \author Sven Ackermann
/// \date 02.03.2016
///
/// \return The actual max file size.
////////////////////////////////////////////////////////////////////////////////////////////////////
unsigned int AviWriter::GetMaxFileSize() const
{
  return m_SaveInfo.max_filesize;
}

unsigned int AviWriter::GetMaxProfileSize() const 
{
	return m_SaveInfo.max_profilesize;
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn bool AviWriter::init(const char* filename, const AviInfo& header)
///
/// \brief  Initializes this object
///
/// \author Sven Ackermann
/// \date 11.11.2019
///
/// \param  filename  Filename of the file.
/// \param  header    The header.
///
/// \return True if it succeeds, false if it fails.
////////////////////////////////////////////////////////////////////////////////////////////////////
bool AviWriter::init(const char* filename, const AviInfo& header)
{
  m_AviParameter.frame_cnt = 0;
  m_SaveInfo.filename = filename;
  m_SaveInfo.profile_config = header.profile_config;
  /// es ist ein Container, wenn die Anzahl der '0' != 8 ist
  m_SaveInfo.is_container = header.rearrangement != 0UL;

  bool bOK = false;

  m_AviParameter.color_cnt = 256;

  if (!m_bAviInit)
  {
    m_bAviInit = true;
    CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
  }
  InitBmpHeader(header);

  DeleteFile(m_SaveInfo.filename.c_str());
  if (AVIFileOpen(&m_AviParameter.pAviFile, m_SaveInfo.filename.c_str(), OF_WRITE | OF_CREATE | OF_SHARE_EXCLUSIVE, nullptr) == AVIERR_OK)
  {
    AVISTREAMINFO AviStreamInfo;
    InitAviStreamInfo(AviStreamInfo, m_AviParameter.bmp_info->bmiHeader);

    std::vector<char> Header = header.Generate_AVIHeader();

    AVIFileWriteData(m_AviParameter.pAviFile, mmioFOURCC('L', 'I', 'S', 'T'), &Header[0], Header.size());

    // create the stream for the profiles
    if (AVIFileCreateStream(m_AviParameter.pAviFile, &m_AviParameter.pAviStream, &AviStreamInfo) == AVIERR_OK)
    {
      memset(&m_AviParameter.compress_option, 0, sizeof(m_AviParameter.compress_option));
      m_AviParameter.compress_option.fccHandler = mmioFOURCC('D', 'I', 'B', ' '); // Device Independent Bitmap
      m_AviParameter.compress_option.dwFlags = AVICOMPRESSF_VALID;
      m_AviParameter.compress_option.fccType = streamtypeVIDEO;

      if (AVIMakeCompressedStream(&m_AviParameter.pAviComprStream, m_AviParameter.pAviStream, &m_AviParameter.compress_option, nullptr)
          == AVIERR_OK)
      {
        if (AVIStreamSetFormat(m_AviParameter.pAviComprStream, 0, m_AviParameter.bmp_info,
                               m_AviParameter.bmp_info->bmiHeader.biSize + m_AviParameter.bmp_info->bmiHeader.biClrUsed * sizeof(RGBQUAD))
            == AVIERR_OK)
        {
          bOK = true;
        }
      }
    }
  }

  if (!bOK)
  {
    m_bAviInit = false;
    CoUninitialize();
  }
  return bOK;
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn void AviWriter::InitBmpHeader(const AviInfo& info)
///
/// \brief  Initialize the BMP-header for writing profiles in the AVI-data format.
///
/// \author Sven Ackermann
/// \date 02.03.2016
///
/// \param  info  The information.
////////////////////////////////////////////////////////////////////////////////////////////////////
void AviWriter::InitBmpHeader(const AviInfo& info)
{

  m_AviParameter.bmp_data.resize(sizeof(BITMAPINFOHEADER) + (sizeof(RGBQUAD) * m_AviParameter.color_cnt));
  m_AviParameter.bmp_info = reinterpret_cast<LPBITMAPINFO>(m_AviParameter.bmp_data.data());

  memset(&m_AviParameter.bmp_info->bmiHeader, 0, sizeof(BITMAPINFOHEADER));
  m_AviParameter.bmp_info->bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
  m_AviParameter.bmp_info->bmiHeader.biWidth = info.size.width;
  m_AviParameter.bmp_info->bmiHeader.biHeight = info.size.height;
  m_AviParameter.bmp_info->bmiHeader.biSizeImage = m_AviParameter.bmp_info->bmiHeader.biWidth * m_AviParameter.bmp_info->bmiHeader.biHeight;
  m_AviParameter.bmp_info->bmiHeader.biBitCount = 8;
  m_AviParameter.bmp_info->bmiHeader.biClrUsed = 256;

  for (unsigned int i = 0; i < 256; i++)
  {
    m_AviParameter.bmp_info->bmiColors[i].rgbBlue = i;
    m_AviParameter.bmp_info->bmiColors[i].rgbRed = i;
    m_AviParameter.bmp_info->bmiColors[i].rgbGreen = i;
    m_AviParameter.bmp_info->bmiColors[i].rgbReserved = i;
  }
  m_AviParameter.bmp_info->bmiHeader.biPlanes = 1;
  m_AviParameter.bmp_info->bmiHeader.biCompression = BI_RGB;
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn void InitAviStreamInfo(AVISTREAMINFO& AviStreamInfo, BITMAPINFOHEADER BmpInfoHeader)
///
/// \brief  Initialize the InitAviStreamInfo with general data.
///
/// \author Sven Ackermann
/// \date 23.05.2016
///
/// \param [in,out] AviStreamInfo Information describing the avi stream.
/// \param          BmpInfoHeader The bitmap information header.
////////////////////////////////////////////////////////////////////////////////////////////////////
void InitAviStreamInfo(AVISTREAMINFO& AviStreamInfo, BITMAPINFOHEADER BmpInfoHeader)
{
  memset(&AviStreamInfo, 0, sizeof(AviStreamInfo));
  AviStreamInfo.fccType = streamtypeVIDEO; // stream type
  AviStreamInfo.fccHandler = 0;
  AviStreamInfo.dwScale = 1;
  AviStreamInfo.dwRate = 25; // 25 fps

  AviStreamInfo.dwSuggestedBufferSize = BmpInfoHeader.biSizeImage;
  SetRect(&AviStreamInfo.rcFrame, 0, 0, (int)BmpInfoHeader.biWidth, (int)BmpInfoHeader.biHeight);
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn std::vector<char> AviInfo::Generate_AVIHeader() const
///
/// \brief  Generates an avi header
///
/// \author Sven Ackermann
/// \date 13.11.2019
///
/// \return The avi header.
////////////////////////////////////////////////////////////////////////////////////////////////////
std::vector<char> AviInfo::Generate_AVIHeader() const
{
  // for the same behavior as llt.dll
  auto profile_cfg = static_cast<unsigned int>(profile_config);
  if (IsReducedProfileFormat(profile_config))
    profile_cfg = profile_cfg | 0x00000080;

  if (IsLoopbackActive(maintenance))
    profile_cfg = profile_cfg | 0x00000040;
  unsigned char is_compressed = IsCompressActive(maintenance);
  std::vector<char> Header{{'I', 'N', 'F', 'O', 'I', 'C', 'M', 'T', '\0', '\0', '\0', '\0'}};
  auto preambleSize = Header.size();
  fmt::format_to(std::back_inserter(Header), "{}\t{:64}\t{:<13}\t{:02x}\t{:04x}\t{:04x}\t{:08x}\t{:08x}\t{:1d}", version, name, serial,
                 profile_cfg, partial_config.nStartPoint, partial_config.nStartPointData, rearrangement, extended1, is_compressed);

  Header.emplace_back('\0');
  assert((255u > (Header.size() - preambleSize)));
  Header[8] = static_cast<char>(Header.size() - preambleSize);
  return Header;
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn unsigned int AviWriter::WriteBufferToAVIFile()
///
/// \brief  Writes a buffer with the AVI-data format to a file.
///
/// \author Sven Ackermann
/// \date 02.03.2016
///
/// \return Written bytes.
////////////////////////////////////////////////////////////////////////////////////////////////////
unsigned int AviWriter::WriteBufferToAVIFile(const std::vector<unsigned char>& data)
{

  std::vector<unsigned char> working_buffer(data);
  if (m_SaveInfo.profile_config == PURE_PROFILE)
  {
    auto pActualImage = working_buffer.data();
    // change the byte order
    for (unsigned int i = 0; i < m_SaveInfo.uiBufferCount; i++)
    {
      ChangeByteOrderForPureProfile(pActualImage, m_AviParameter.bmp_info->bmiHeader.biHeight - 8);
      pActualImage += (m_AviParameter.bmp_info->bmiHeader.biHeight - 8) * m_AviParameter.bmp_info->bmiHeader.biWidth + 16;
    }
  }

  unsigned int nBytesWritten = WriteBufferToAVIFile_Profile(working_buffer.data());

  return nBytesWritten;
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn void ChangeByteOrderForPureProfile(unsigned char* pPureProfileBuffer, unsigned int nPointCount)
///
/// \brief  Changes the order from a pure profile.
///
/// \author Sven Ackermann
/// \date 02.03.2016
///
/// \param [in,out] pPureProfileBuffer  Pointer to a buffer with the profile.
/// \param          nPointCount         Point count of the profile.
///
/// # remarks #
/// - nPointCount must be divisible by 2
////////////////////////////////////////////////////////////////////////////////////////////////////
void ChangeByteOrderForPureProfile(unsigned char* pPureProfileBuffer, unsigned int nPointCount)
{
  auto pure_buffer = reinterpret_cast<unsigned short*>(pPureProfileBuffer);
  for (unsigned int idx{0}; idx < 2 * nPointCount; idx++)
  {
    auto tmp = _byteswap_ushort(*pure_buffer);
    *pure_buffer = tmp;
    ++pure_buffer;
  }
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn unsigned int AviWriter::WriteBufferToAVIFile_Profile(unsigned char* pActualImage)
///
/// \brief  Writes a profile buffer with the AVI-data format to a file.
///
/// \author Sven Ackermann
/// \date 02.03.2016
///
/// \param [in,out] pActualImage  Pointer to the buffer with the profiles.
///
/// \return Written bytes.
////////////////////////////////////////////////////////////////////////////////////////////////////
int AviWriter::WriteBufferToAVIFile_Profile(unsigned char* pActualImage)
{
	long nBytesSample;
	int nBytesWritten = 0;
	bool bOK = false;

	if (m_TempFlipProfile.size() != m_AviParameter.bmp_info->bmiHeader.biSizeImage)
	{
		m_TempFlipProfile.resize(m_AviParameter.bmp_info->bmiHeader.biSizeImage);
	}

	if (m_SaveInfo.profile_config == PURE_PROFILE || m_SaveInfo.profile_config == QUARTER_PROFILE)
	{
		FlipImageLinesForSaving(pActualImage, m_AviParameter.bmp_info->bmiHeader.biWidth, m_AviParameter.bmp_info->bmiHeader.biHeight,
			&m_TempFlipProfile[0]);
	}
	else
	{
		FlipImageLines(pActualImage, m_AviParameter.bmp_info->bmiHeader.biWidth, m_AviParameter.bmp_info->bmiHeader.biHeight, 1,
			&m_TempFlipProfile[0]);
	}

	// Check max file size and profile size

	if ((m_AviParameter.frame_cnt ) < m_SaveInfo.max_profilesize) {
		if (m_SaveInfo.max_filesize >= (m_AviParameter.frame_cnt + 1) * m_AviParameter.bmp_info->bmiHeader.biSizeImage) {
			
			bOK = AVIStreamWrite(m_AviParameter.pAviComprStream, m_AviParameter.frame_cnt, 1, &m_TempFlipProfile[0],
				m_AviParameter.bmp_info->bmiHeader.biSizeImage, 0, nullptr, &nBytesSample)
				== AVIERR_OK;
			nBytesWritten += nBytesSample;
			pActualImage += m_AviParameter.profile_size;
			m_AviParameter.frame_cnt += 1;
		}
		else {// error max size is reached
			return nBytesWritten = -1;
		}
	}
	else {//error maxprofile size is reached
		return nBytesWritten = -2;
	}
		
	if (!bOK)
		nBytesWritten = 0;

	return nBytesWritten;
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn unsigned int AviWriter::WriteBufferToAVIFile_Container(const unsigned char* pActualImage)
///
/// \brief  Writes a container buffer with the AVI-data format to a file.
///
/// \author Sven Ackermann
/// \date 02.03.2016
///
/// \param  pActualImage  Pointer to the buffer with the profiles.
///
/// \return Written bytes.
////////////////////////////////////////////////////////////////////////////////////////////////////
unsigned int AviWriter::WriteBufferToAVIFile_Container(const unsigned char* pActualImage)
{
	
  std::vector<unsigned char> TempContainer;
  bool bOK = false;

  TempContainer.resize(m_AviParameter.bmp_info->bmiHeader.biSizeImage);
  unsigned int nTempProfileSize = m_AviParameter.profile_size / 2;

  auto pTempContainer = TempContainer.data();
  auto pTempProfile = pActualImage;

  for (unsigned int j = 0; j < nTempProfileSize; j++)
  {
    const unsigned char nNULL = 0;
    *(pTempContainer++) = *(pTempProfile++);
    *(pTempContainer++) = *(pTempProfile++);
    *(pTempContainer++) = nNULL;
    *(pTempContainer++) = nNULL;
  }

  long nSampleWritten, nBytesSample;
  unsigned int nBytesWritten = 0;
  FlipImageLines(&TempContainer[0], m_AviParameter.bmp_info->bmiHeader.biWidth, m_AviParameter.bmp_info->bmiHeader.biHeight, 4);

  // Check max file size and profile size
  if ((m_AviParameter.frame_cnt) < m_SaveInfo.max_profilesize) {
	  if (m_SaveInfo.max_filesize >= (m_AviParameter.frame_cnt + 1) * m_AviParameter.bmp_info->bmiHeader.biSizeImage) {
		  bOK = AVIStreamWrite(m_AviParameter.pAviComprStream, m_AviParameter.frame_cnt, 1, &TempContainer[0],
			  m_AviParameter.bmp_info->bmiHeader.biSizeImage, 0, &nSampleWritten, &nBytesSample)
			  == AVIERR_OK;

		  m_AviParameter.frame_cnt += nSampleWritten;
		  nBytesWritten += nBytesSample;
	  }
	  else {// error max size is reached
		  return nBytesWritten = -1;
	  }
  }
  //else {//error maxprofile size is reached
	  //return nBytesWritten = -2;
  //}

  if (!bOK)
    nBytesWritten = 0;

  return nBytesWritten;
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn void FlipImageLines(unsigned char* pSourceImage, unsigned int nWidth, unsigned int nHeight, unsigned int nPointSize , unsigned char*
/// pDestinationImage )
///
/// \brief  Flips the lines for a bitmap/profile image (only for the BMP format)
///
/// \author Sven Ackermann
/// \date 02.03.2016
///
/// \param [in,out] pSourceImage      Pointer to the source image.
/// \param          nWidth            Width of the bitmap.
/// \param          nHeight           Height of the bitmap.
/// \param          nPointSize
/// \param [in,out] pDestinationImage If non-null, destination image.
////////////////////////////////////////////////////////////////////////////////////////////////////
void FlipImageLines(unsigned char* pSourceImage, unsigned int nWidth, unsigned int nHeight, unsigned int nPointSize /*=1*/,
                    unsigned char* pDestinationImage /*=NULL*/)
{
  nWidth *= nPointSize;

  unsigned char* pTempImage = pDestinationImage;

  std::vector<unsigned char> TempProfile;

  if (pTempImage == nullptr)
  {
    TempProfile.resize(nWidth * nHeight);
    pTempImage = &TempProfile[nWidth * (nHeight - 1)];
  }
  else
    pTempImage += nWidth * (nHeight - 1);

  auto pSourceImage2 = pSourceImage;
  for (unsigned int i = 0; i < nHeight; i++)
  {
    memcpy(pTempImage, pSourceImage2, nWidth);
    pSourceImage2 += nWidth;
    pTempImage -= nWidth;
  }

  // TODO: wenn pDestinationImage == nullptr -> Flip in Place?
  if (pDestinationImage == nullptr)
    memcpy(pSourceImage, &TempProfile[0], nWidth * nHeight);
}

////////////////////////////////////////////////////////////////////////////////////////////////////
/// \fn void FlipImageLinesForSaving(unsigned char* pSourceImage, unsigned int nWidth, unsigned int nHeight, unsigned char*
/// pDestinationImage)
///
/// \brief  Flips the lines for a bitmap/profile image (only for the BMP format)
///
/// \author Sven Ackermann
/// \date 02.03.2016
///
/// \param [in,out] pSourceImage      Pointer to the source image.
/// \param          nWidth            Width of the bitmap.
/// \param          nHeight           Height of the bitmap.
/// \param [in,out] pDestinationImage Pointer to the destination image.
///
/// # Remarks #
/// hier erfolgt die Sonderbehandlung des Timestamp für Quarter/Pure Profile
///
////////////////////////////////////////////////////////////////////////////////////////////////////
void FlipImageLinesForSaving(unsigned char* pSourceImage, unsigned int nWidth, unsigned int nHeight, unsigned char* pDestinationImage)
{
  FlipImageLines(pSourceImage, nWidth, nHeight - 8, 1, pDestinationImage + nWidth * 8);

  memset(pDestinationImage, 0, nWidth * 8);

  auto pTimestamp = pSourceImage + nWidth * (nHeight - 8);

  pDestinationImage += nWidth * 8;

  if (IsQuarterProfile(nWidth))
    pDestinationImage -= 12;
  else
    pDestinationImage -= 4;

  for (unsigned int j = 0; j < 8; j++)
  {
    memcpy(pDestinationImage, pTimestamp, 2);
    pTimestamp += 2;

    pDestinationImage -= nWidth;
  }
}
