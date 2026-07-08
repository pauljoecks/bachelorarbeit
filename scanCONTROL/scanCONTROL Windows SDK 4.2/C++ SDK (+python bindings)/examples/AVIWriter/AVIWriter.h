#pragma once
#include <Windows.h>
#include <Vfw.h>
#include "scanControlDataTypes.h"

const auto MAX_FILESIZE = 50U * 1024U * 1024U;
struct SaveInfo
{
  /// collection of informations that general needed for saving
  bool is_container{false};
  unsigned int uiBufferCount{1U};
  unsigned int max_filesize{MAX_FILESIZE};
  unsigned int max_profilesize;
  TProfileConfig profile_config{NONE};
  std::string filename;
};

struct AviSaveInfo

{
  /// collection of informations that are needed by the VfW AVI* functions
  unsigned int frame_cnt{0};
  unsigned int color_cnt{0};
  unsigned int profile_size{0};
  AVICOMPRESSOPTIONS compress_option;
  LPBITMAPINFO bmp_info{nullptr};
  PAVIFILE pAviFile{nullptr};
  PAVISTREAM pAviStream{nullptr};
  PAVISTREAM pAviComprStream{nullptr};
  std::vector<char> bmp_data;
};

struct ImageSize
{
  unsigned int width{0};
  unsigned int height{0};
};
struct AviInfo
{
  /// collection of informations that are needed to build the avi header
  unsigned long serial{};
  unsigned long rearrangement{0};
  unsigned long maintenance{0};
  unsigned long extended1{0xffffffff};
  TProfileConfig profile_config{NONE};
  TPartialProfile partial_config;
  std::string name;
  ImageSize size;
  unsigned char version{2};

  std::vector<char> Generate_AVIHeader() const;
};

class AviWriter
{
public:
  AviWriter();
  ~AviWriter();
  bool init(const char* filename, const AviInfo& header);
  void SetMaxFileSize(unsigned int max_filesize);
  void SetMaxProfileSize(unsigned int max_profilesize);
  unsigned int GetMaxFileSize() const;
  unsigned int GetMaxProfileSize() const;
  unsigned int WriteBufferToAVIFile(const std::vector<unsigned char>& data);

#ifndef GTEST_AKTIV
private:
#else
public:
#endif // GTEST_AKTIV

  void InitBmpHeader(const AviInfo& info);
  unsigned int WriteBufferToAVIFile_Container(const unsigned char* pActualImage);
  int WriteBufferToAVIFile_Profile(unsigned char* pActualImage);

  std::vector<unsigned char> m_TempFlipProfile;
  bool m_bAviInit{false};
  AviSaveInfo m_AviParameter;
  SaveInfo m_SaveInfo;
};

void InitAviStreamInfo(AVISTREAMINFO& AviStreamInfo, BITMAPINFOHEADER BmpInfoHeader);
void FlipImageLines(unsigned char* pSourceImage, unsigned int nWidth, unsigned int nHeight, unsigned int nPointSize = 1,
                    unsigned char* pDestinationImage = nullptr);
void FlipImageLinesForSaving(unsigned char* pSourceImage, unsigned int nWidth, unsigned int nHeight, unsigned char* pDestinationImage);
void ChangeByteOrderForPureProfile(unsigned char* pPureProfileBuffer, unsigned int nPointCount);
inline bool IsQuarterProfile(unsigned int width)
{
  return width == 16;
};

inline bool IsReducedProfileFormat(TProfileConfig cfg)
{
  return cfg == PURE_PROFILE || cfg == QUARTER_PROFILE;
}

inline bool IsLoopbackActive(unsigned long value)
{
  return (value & 0x00000002) != 0U;
}

inline bool IsCompressActive(unsigned long value)
{
  return (value & 0x00000001) != 0U;
}
