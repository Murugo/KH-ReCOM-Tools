cmake_minimum_required(VERSION 3.0.0)
project(khrecom VERSION 0.1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(CTest)
enable_testing()

set(SOURCES Extractor/isofile.cpp Extractor/isofile.h Extractor/decompress.h)
add_executable(khrecom-ps2-extractor Extractor/main.cpp ${SOURCES})

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)
