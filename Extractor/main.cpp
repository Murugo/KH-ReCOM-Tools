#include <string.h>

#include <iostream>
#include <string>

#include "isofile.h"

namespace {

const char kDefaultExtractDir[] = ".\\extract\\";

void PrintUsage() {
  std::cout << "Usage: khrecom-ps2-extractor.exe C:\\path\\to\\game.iso \\\n"
               "    [-d C:\\optional\\extract\\dir]"
            << std::endl;
}

}  // namespace

int main(int argc, char** argv) {
  std::string iso_path;
  std::string extract_dir = kDefaultExtractDir;
  for (int i = 1; i < argc; ++i) {
    if (argv[i][0] == '-') {
      if (!strcmp(argv[i], "-d") && i < argc - 1) {
        extract_dir = argv[++i];
      } else {
        PrintUsage();
        return 0;
      }
    } else if (argv[i][0] != '-' && iso_path.empty()) {
      iso_path = argv[i];
    }
  }
  if (iso_path.empty()) {
    PrintUsage();
    return 0;
  }

  IsoFile iso_file;
  if (!iso_file.Open(iso_path.c_str()) ||
      !iso_file.ExtractToDir(extract_dir.c_str())) {
    std::cerr << "\n*** Extraction failed." << std::endl;
    return 1;
  }
  std::cout << "\nFinished extracting " << iso_file.GetFileExtractedCount()
            << " files." << std::endl;
  return 0;
}
