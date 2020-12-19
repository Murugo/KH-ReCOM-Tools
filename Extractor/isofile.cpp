#include "isofile.h"

#include <string.h>

#include <filesystem>
#include <iostream>
#include <sstream>

#include "decompress.h"

namespace {

constexpr int kPvdOffset = 0x8000;
constexpr int kPvdTypeCode = 1;
constexpr char kStandardIdentifier[] = "CD001";

constexpr int kBlockSize = 0x800;
constexpr int kBlockSizePvdOffset = 0x80;

constexpr uint32_t kDatMagic = 0x5441442E;  // ".DAT"

// These sectors are hard-coded in CRcfCD::initialize(), and are the same for
// all known PS2 versions of KH Re:COM.
//
// SLUS_217.99 (2008-10-01): Instruction @ 001BC7C8
constexpr int kRecomBlockHeaderSector = 0x244;
// SLUS_217.99 (2008-10-01): Instruction @ 001BC834
constexpr int kRecomInfoBlockSector = 0x245;

// Struct names loosely follow their corresponding debug symbols.

struct BlockHeader {
  uint32_t magic;  // ".DAT"
  uint16_t version;
  uint16_t num_files;
  uint16_t sector_size;
};

struct InfoBlockEntry {
  char filename[0x10];
  uint32_t data_sector;
  uint32_t data_sector_size;
  uint32_t group_table_offs;
  uint32_t group_table_count;
};

// Subgroup of files in a data archive (gXXX.dat).
struct DataGroupEntry {
  uint32_t id;
  uint32_t data_sector;
  uint32_t data_sector_size;
  uint8_t member_table_sector_size;
  uint8_t range_ratio;
  uint8_t unk;
  uint8_t reverb_val;
  uint32_t unk2[4];
};

// Single file from an archive subgroup.
struct CdMemberHeader {
  char filename[0x18];
  uint32_t disk_size_uncompressed;
  uint32_t rsrc_group;
  uint32_t unk;
  uint32_t sector_size;
  uint32_t sector;
  uint8_t rsrc_id;
  uint8_t is_compressed;
  uint16_t unk3;
};

}  // namespace

bool IsoFile::Open(const char* iso_path) {
  file_.open(iso_path, std::ifstream::in | std::ifstream::binary);
  if (!IsOpen()) {
    std::cerr << "ERR: Failed to open ISO: " << iso_path << std::endl;
    return false;
  }
  std::cout << "Reading " << iso_path << "..." << std::endl;
  if (!ValidatePvd() || !ParseFileEntries()) {
    return false;
  }
  return true;
}

bool IsoFile::ExtractToDir(const char* dir) {
  if (!IsOpen() || file_entries_.empty()) {
    std::cerr << "ERR: No files to extract." << std::endl;
    return false;
  }
  std::filesystem::path base_path(dir);
  for (const FileEntry& file_entry : file_entries_) {
    std::filesystem::path path = base_path / file_entry.path;
    std::cout << "Extracting: " << path.string() << "..." << std::endl;

    // Create directories if they do not exist.
    std::error_code ec;
    std::filesystem::create_directories(path.parent_path(), ec);
    if (ec.value() != 0) {
      std::cerr << "ERR: Failed to create directory for extraction: "
                << ec.message();
      return false;
    }

    uint8_t* buffer = new uint8_t[file_entry.disk_size];
    file_.seekg(file_entry.sector * kBlockSize, file_.beg);
    file_.read(reinterpret_cast<char*>(buffer), file_entry.disk_size);
    std::ofstream out_file(path, std::ofstream::out | std::ofstream::binary);
    if (!out_file) {
      std::cerr << "ERR: Failed to open file for writing: " << path
                << std::endl;
      return false;
    }
    if (file_entry.is_compressed) {
      uint8_t* decompressed_buffer = Decompress(buffer, file_entry.disk_size,
                                                file_entry.uncompressed_size);
      delete buffer;
      buffer = decompressed_buffer;
    }
    out_file.write(reinterpret_cast<char*>(buffer),
                   file_entry.is_compressed ? file_entry.uncompressed_size
                                            : file_entry.disk_size);
    delete buffer;

    files_extracted_++;
  }
  return true;
}

bool IsoFile::ValidatePvd() {
  // Perform basic checks on the primary volume descriptor.
  char buf[6] = {0};
  file_.seekg(kPvdOffset, file_.beg);
  file_.read(buf, 1);
  if (buf[0] != kPvdTypeCode) {
    std::cerr << "ERR: Unexpected PVD type code " << buf[0] << std::endl;
    return false;
  }
  file_.read(buf, 5);
  if (strcmp(buf, kStandardIdentifier) != 0) {
    std::cerr << "ERR: Expected PVD standard identifier CD001" << std::endl;
    return false;
  }
  uint16_t block_size = 0;
  file_.seekg(kPvdOffset + kBlockSizePvdOffset, file_.beg);
  file_.read(buf, 2);
  if (*reinterpret_cast<uint16_t*>(buf) != kBlockSize) {
    std::cerr << "ERR: Unexpected logical block size " << block_size
              << " in PVD" << std::endl;
    return false;
  }
  return true;
}

bool IsoFile::ParseFileEntries() {
  BlockHeader block_header;
  const int block_header_offs = kRecomBlockHeaderSector * kBlockSize;
  file_.seekg(kRecomBlockHeaderSector * kBlockSize, file_.beg);
  file_.read(reinterpret_cast<char*>(&block_header), sizeof(BlockHeader));
  if (block_header.magic != kDatMagic) {
    std::cerr << "ERR: Expected \".DAT\" at offset " << std::hex
              << block_header_offs << std::endl;
    return false;
  }

  std::vector<InfoBlockEntry> info_block_entries;
  info_block_entries.resize(block_header.num_files);
  file_.seekg(kRecomInfoBlockSector * kBlockSize, file_.beg);
  file_.read(reinterpret_cast<char*>(info_block_entries.data()),
             sizeof(InfoBlockEntry) * block_header.num_files);
  for (const InfoBlockEntry& info_block_entry : info_block_entries) {
    if (info_block_entry.group_table_count == 0) {
      FileEntry file_entry;
      file_entry.path = info_block_entry.filename;
      file_entry.sector = info_block_entry.data_sector;
      file_entry.disk_size = info_block_entry.data_sector_size * kBlockSize;
      file_entries_.push_back(std::move(file_entry));
    } else {
      ParseArchive(info_block_entry.filename, info_block_entry.data_sector,
                   info_block_entry.group_table_count);
    }
  }
  return true;
}

void IsoFile::ParseArchive(const std::string& archive_name, int data_sector,
                           int group_count) {
  std::vector<DataGroupEntry> data_group_entries;
  data_group_entries.resize(group_count);
  file_.seekg(data_sector * kBlockSize, file_.beg);
  file_.read(reinterpret_cast<char*>(data_group_entries.data()),
             sizeof(DataGroupEntry) * group_count);
  for (const DataGroupEntry& data_group_entry : data_group_entries) {
    if (data_group_entry.member_table_sector_size == 0) {
      continue;
    }
    file_.seekg((data_sector + data_group_entry.data_sector) * kBlockSize);
    int bytes_read = 0;
    const int bytes_max =
        data_group_entry.member_table_sector_size * kBlockSize;
    while (bytes_read < bytes_max) {
      CdMemberHeader header;
      file_.read(reinterpret_cast<char*>(&header), sizeof(CdMemberHeader));
      if (file_.gcount() == 0 || header.filename[0] == '\0') {
        break;
      }
      FileEntry file_entry;
      file_entry.sector =
          data_sector + data_group_entry.data_sector + header.sector;
      file_entry.disk_size = header.sector_size * 0x800;
      if (header.is_compressed) {
        file_entry.is_compressed = true;
        file_entry.uncompressed_size = header.disk_size_uncompressed;
      }
      std::stringstream path_ss;
      path_ss << archive_name << "/" << data_group_entry.id << "/"
              << header.filename;
      file_entry.path = path_ss.str();
      file_entries_.push_back(std::move(file_entry));
    }
  }
}
