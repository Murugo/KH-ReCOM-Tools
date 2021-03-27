cmake_minimum_required(VERSION 3.0.0)
project(khrecom VERSION 0.1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(CTest)
enable_testing()

set(EXTRACTOR_SOURCES Extractor/isofile.cpp Extractor/isofile.h Extractor/decompress.h)
add_executable(khrecom-ps2-extractor Extractor/main.cpp ${EXTRACTOR_SOURCES})
target_link_libraries(khrecom-ps2-extractor -static)

set(RSRC_UNPACKER_SOURCES ResourceUnpacker/packed-resource.cpp ResourceUnpacker/packed-resource.h)
add_executable(khrecom-ps2-rsrc-unpacker ResourceUnpacker/main.cpp ${RSRC_UNPACKER_SOURCES})
target_link_libraries(khrecom-ps2-rsrc-unpacker -static)

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)
