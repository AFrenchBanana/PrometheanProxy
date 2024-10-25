cmake_minimum_required(VERSION 3.15)

project(MyProject LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_FIND_LIBRARY_SUFFIXES .a)
set(BUILD_SHARED_LIBS OFF)

set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -static")

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(CMAKE_CXX_COMPILER g++)
    set(VCPKG_TARGET_TRIPLET "x64-linux")
    set(CMAKE_PREFIX_PATH "${CMAKE_SOURCE_DIR}/dep/vcpkg/installed/${VCPKG_TARGET_TRIPLET}")

elseif(CMAKE_SYSTEM_NAME STREQUAL "Windows")
    set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++)
    set(VCPKG_TARGET_TRIPLET "x64-mingw-static")
    set(CMAKE_PREFIX_PATH "${CMAKE_SOURCE_DIR}/dep/vcpkg/installed/${VCPKG_TARGET_TRIPLET}")
else()
    message(FATAL_ERROR "Unsupported system: ${CMAKE_SYSTEM_NAME}")
endif()

set(CMAKE_TOOLCHAIN_FILE "${CMAKE_SOURCE_DIR}/dep/vcpkg/scripts/buildsystems/vcpkg.cmake"
    CACHE STRING "Vcpkg toolchain file")

set(SOURCES "${CMAKE_SOURCE_DIR}/main.cpp")

message(STATUS "Found source files: ${SOURCES}")

find_package(CURL REQUIRED)

if(NOT CURL_FOUND)
    message(FATAL_ERROR "CURL not found. Ensure it is installed via vcpkg.")
endif()

add_executable(MyExecutable ${SOURCES})

target_link_libraries(MyExecutable PRIVATE ${CURL_LIBRARIES})

set_target_properties(MyExecutable PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "../bin"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
    ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
)


