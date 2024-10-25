cmake_minimum_required(VERSION 3.15)

project(MyProject LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)  # Change to C++20
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Prefer static libraries
set(CMAKE_FIND_LIBRARY_SUFFIXES .a)
set(BUILD_SHARED_LIBS OFF)

# Link statically
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -static")

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(CMAKE_CXX_COMPILER g++)
    set(VCPKG_TARGET_TRIPLET "x64-linux")
    message(STATUS "Configuring for Linux with g++")

elseif(CMAKE_SYSTEM_NAME STREQUAL "Windows")
    set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++)
    set(VCPKG_TARGET_TRIPLET "x64-mingw-static")
    message(STATUS "Cross-compiling for Windows with MinGW")
endif()

# Toolchain file for vcpkg
set(CMAKE_TOOLCHAIN_FILE "${CMAKE_SOURCE_DIR}/src/Client/Client_C++/dep/vcpkg/scripts/buildsystems/vcpkg.cmake"
    CACHE STRING "Vcpkg toolchain file")

# Directly specify the main source file
set(SOURCES "${CMAKE_SOURCE_DIR}/main.cpp")

# Debug message to check found source files
message(STATUS "Found source files: ${SOURCES}")

# Add executable target
add_executable(MyExecutable ${SOURCES})

# Set the output directory for the executable to the 'bin' folder in the root of the project
set_target_properties(MyExecutable PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "../bin"
    LIBRARY_OUTPUT_DIRECTORY "../bin"
    ARCHIVE_OUTPUT_DIRECTORY "../bin"
)