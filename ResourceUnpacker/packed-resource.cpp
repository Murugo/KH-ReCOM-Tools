#include "packed-resource.h"

#include <filesystem>
#include <iostream>

namespace {

constexpr char kDefaultDirSuffix[] = ".out";

constexpr int kFileEntrySize = 0x20;
constexpr int kFileSizeOffset = 0x1C;
constexpr int kFileLocOffsetA = 0x0;
constexpr int kFileLocOffsetB = 0x10;
constexpr int kFileNameOffsetA = 0x4;
constexpr int kFileNameOffsetB = 0x0;
constexpr int kFileNameLength = 0x16;

}  // namespace

bool PackedResource::Open(const char* pathname) {
  std::filesystem::path path(pathname);
  file_.open(path, std::ifstream::in | std::ifstream::binary);
  if (!IsOpen()) {
    std::cerr << "ERR: Failed to open resource: " << path << std::endl;
    return false;
  }
  source_filename_ = path.filename().string();
  file_.seekg(0, file_.end);
  const size_t total_size = file_.tellg();

  char buf[kFileEntrySize] = {0};
  file_.seekg(0, file_.beg);
  while (file_.tellg() < total_size) {
    file_.read(buf, kFileEntrySize);
    if (file_.gcount() < kFileEntrySize) {
      break;
    }

    FileEntry file_entry;
    const int file_size = *reinterpret_cast<int*>(buf + kFileSizeOffset);
    if (file_size == 0) {
      break;
    } else if (file_size < 0) {
      file_entry.size = file_size & 0x7FFFFFFF;
      file_entry.offset = *reinterpret_cast<int*>(buf + kFileLocOffsetA);
      file_entry.name = std::string(buf + kFileNameOffsetA);
    } else {
      file_entry.size = file_size;
      file_entry.offset = *reinterpret_cast<int*>(buf + kFileLocOffsetB);
      file_entry.name = std::string(buf + kFileNameOffsetB);
    }
    if (file_entry.offset < 0 ||
        static_cast<size_t>(file_entry.offset) + file_entry.size > total_size) {
      std::cerr << "ERR: Not a valid packed resource" << std::endl;
      return false;
    }
    file_entries_.push_back(std::move(file_entry));
  }
  return true;
}

bool PackedResource::ExtractToDir(const char* dir, bool is_default_dir) {
  if (!IsOpen() || file_entries_.empty()) {
    std::cerr << "ERR: No files to extract." << std::endl;
    return false;
  }
  std::filesystem::path base_path(dir);
  base_path /= is_default_dir ? source_filename_ + kDefaultDirSuffix : "";
  for (const FileEntry& file_entry : file_entries_) {
    const std::filesystem::path path = base_path / file_entry.name;
    std::cout << "Extracting: " << path.string() << " ..." << std::endl;

    // Create directories if they do not exist.
    std::error_code ec;
    std::filesystem::create_directories(path.parent_path(), ec);
    if (ec.value() != 0) {
      std::cerr << "ERR: Failed to create directory for extraction: "
                << ec.message();
      return false;
    }

    char* buffer = new char[file_entry.size];
    file_.seekg(file_entry.offset);
    file_.read(buffer, file_entry.size);
    std::ofstream out_file(path, std::ofstream::out | std::ofstream::binary);
    if (!out_file) {
      std::cerr << "ERR: Failed to open file for writing: " << path
                << std::endl;
      return false;
    }
    out_file.write(buffer, file_entry.size);
    delete buffer;
    files_extracted_++;
  }
  return true;
}
