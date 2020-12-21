#include <fstream>
#include <vector>

// Class for extracting files from a packed resource file.
class PackedResource {
 public:
  PackedResource() {}
  ~PackedResource() {}

  // Opens the resource and parses the file table.
  bool Open(const char* pathname);

  // Returns true if the resource file was opened successfully.
  bool IsOpen() const { return file_.good() && file_.is_open(); }

  // Extracts all files to the given directory. Attempts to create
  // subdirectories beforehand if they do not exist.
  bool ExtractToDir(const char* dir, bool is_default_dir);

  // Returns the total number of files extracted with ExtractToDir().
  size_t GetFileExtractedCount() const { return files_extracted_; }

  PackedResource(const PackedResource&) = delete;
  PackedResource& operator=(const PackedResource&) = delete;

 private:
  struct FileEntry {
    std::string name;
    bool is_compressed = false;
    uint32_t size = 0;
    uint32_t offset = 0;
  };
  std::vector<FileEntry> file_entries_;

  std::string source_filename_;
  std::ifstream file_;
  size_t files_extracted_ = 0;
};
