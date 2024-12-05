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

    # Specify sources explicitly for Linux
    file(GLOB SOURCES 
        "${CMAKE_SOURCE_DIR}/main.cpp"
        "${CMAKE_SOURCE_DIR}/Linux/*.cpp"
        "${CMAKE_SOURCE_DIR}/Linux/*.h"
        "${CMAKE_SOURCE_DIR}/Linux/Beacon/*.cpp"
        "${CMAKE_SOURCE_DIR}/Linux/Beacon/*.h"
        "${CMAKE_SOURCE_DIR}/Generic/*.cpp"
        "${CMAKE_SOURCE_DIR}/Generic/*.h"
    )

elseif(CMAKE_SYSTEM_NAME STREQUAL "Windows")
    set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++)
    set(VCPKG_TARGET_TRIPLET "x64-mingw-static")
    set(CMAKE_PREFIX_PATH "${CMAKE_SOURCE_DIR}/dep/vcpkg/installed/${VCPKG_TARGET_TRIPLET}")

    # Specify sources for Windows
    file(GLOB SOURCES 
        "${CMAKE_SOURCE_DIR}/main.cpp"
        "${CMAKE_SOURCE_DIR}/Generic/*.cpp"
        "${CMAKE_SOURCE_DIR}/Generic/*.h"
        "${CMAKE_SOURCE_DIR}/Windows/*.cpp"
        "${CMAKE_SOURCE_DIR}/Windows/*.h"
        "${CMAKE_SOURCE_DIR}/Windows/Beacon/*.cpp"
        "${CMAKE_SOURCE_DIR}/Windows/Beacon/*.h"
    )

    # Link Windows-specific libraries for networking
    set(WINDOWS_LIBS ws2_32 iphlpapi)
else()
    message(FATAL_ERROR "Unsupported system: ${CMAKE_SYSTEM_NAME}")
endif()

set(CMAKE_TOOLCHAIN_FILE "${CMAKE_SOURCE_DIR}/dep/vcpkg/scripts/buildsystems/vcpkg.cmake"
    CACHE STRING "Vcpkg toolchain file")

message(STATUS "Found source files: ${SOURCES}")

find_package(CURL REQUIRED)
if(NOT CURL_FOUND)
    message(FATAL_ERROR "CURL not found.")
endif()

find_package(Threads REQUIRED)
if (NOT Threads_FOUND)
    message(FATAL_ERROR "Threads not found.")
endif()

find_package(jsoncpp CONFIG REQUIRED)

add_executable(MyExecutable ${SOURCES})

if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
    target_link_libraries(MyExecutable PRIVATE CURL::libcurl ${Threads_LIBRARIES} ${WINDOWS_LIBS} JsonCpp::JsonCpp)
elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_link_libraries(MyExecutable PRIVATE CURL::libcurl ${Threads_LIBRARIES} JsonCpp::JsonCpp )
endif()

set_target_properties(MyExecutable PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "../bin"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
    ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
)