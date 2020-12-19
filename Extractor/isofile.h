#include <fstream>
#include <vector>

// Lightweight class for reading and extracting files from a KH Re:COM (PS2)
// ISO.
class IsoFile {
 public:
  IsoFile() {}
  ~IsoFile() {}

  // Opens the ISO file at the given path and parses all DAT file entries.
  bool Open(const char* iso_path);

  // Returns true if the ISO file was opened successfully.
  bool IsOpen() const { return file_.good() && file_.is_open(); }

  // Returns the total number of files in the ISO.
  size_t GetFileCount() const { return file_entries_.size(); }

  // Returns the total number of files extracted with ExtractToDir().
  size_t GetFileExtractedCount() const { return files_extracted_; }

  // Extracts all files to the given directory. Attempts to create
  // subdirectories beforehand if they do not exist.
  bool ExtractToDir(const char* dir);

  IsoFile(const IsoFile&) = delete;
  IsoFile& operator=(const IsoFile&) = delete;

 private:
  bool ValidatePvd();
  bool ParseFileEntries();
  void ParseArchive(const std::string& archive_name, int data_sector,
                    int group_count);

  struct FileEntry {
    std::string path;
    bool is_compressed = false;
    uint32_t sector = 0;
    uint32_t disk_size = 0;
    uint32_t uncompressed_size = 0;
  };
  std::vector<FileEntry> file_entries_;

  std::ifstream file_;
  size_t files_extracted_ = 0;
};
