#include <string.h>

#include <iostream>
#include <string>

#include "packed-resource.h"

namespace {

const char kDefaultExtractDir[] = ".";

void PrintUsage() {
  std::cout << "Usage: khrecom-ps2-rsrc-unpacker.exe C:\\path\\to\\resou.rce "
               "[-d C:\\optional\\extract\\dir\n]";
}

}  // namespace

int main(int argc, char** argv) {
  std::string file_path;
  std::string extract_dir = kDefaultExtractDir;
  bool is_default_dir = true;
  for (int i = 1; i < argc; ++i) {
    if (argv[i][0] == '-') {
      if (!strcmp(argv[i], "-d") && i < argc - 1) {
        extract_dir = argv[++i];
        is_default_dir = false;
      } else {
        PrintUsage();
        return 0;
      }
    } else if (argv[i][0] != '-' && file_path.empty()) {
      file_path = argv[i];
    }
  }
  if (file_path.empty()) {
    PrintUsage();
    return 0;
  }

  PackedResource packed_resource;
  if (!packed_resource.Open(file_path.c_str()) ||
      !packed_resource.ExtractToDir(extract_dir.c_str(), is_default_dir)) {
    std::cerr << "\n*** Unpack failed." << std::endl;
    return 1;
  }
  std::cout << "\nFinished unpacking "
            << packed_resource.GetFileExtractedCount() << " files."
            << std::endl;
  return 0;
}
