cmake_minimum_required(VERSION 3.5.0)
project(PrometheanProxy VERSION 0.1.0 LANGUAGES C CXX)

add_executable(PrometheanProxy main.cpp)

include(CTest)
enable_testing()

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)

# Vcpkg directory and toolchain file
set(VCPKG_DIR "${CMAKE_SOURCE_DIR}/src/dep/Client/Client_C++/dep/vcpkg")
set(VCPKG_TOOLCHAIN_FILE "${VCPKG_DIR}/scripts/buildsystems/vcpkg.cmake")

# Add vcpkg toolchain if it exists
if (EXISTS ${VCPKG_TOOLCHAIN_FILE})
    message(STATUS "Using vcpkg toolchain from ${VCPKG_TOOLCHAIN_FILE}")
    set(CMAKE_TOOLCHAIN_FILE ${VCPKG_TOOLCHAIN_FILE})
else()
    message(FATAL_ERROR "Vcpkg not found! Run vcpkg setup before building.")
endif()

# Source directory
set(SOURCE_DIR "${CMAKE_SOURCE_DIR}/src")

# Output directories
set(OUTPUT_LINUX "${CMAKE_BINARY_DIR}/bin/myapp_linux")
set(OUTPUT_WINDOWS "${CMAKE_BINARY_DIR}/bin/myapp_windows")

# Set up vcpkg and install dependencies
find_package(jsoncpp CONFIG REQUIRED)
find_package(cpprestsdk CONFIG REQUIRED)

# Target for Linux build
add_executable(myapp_linux ${SOURCE_DIR}/main.cpp)
target_link_libraries(myapp_linux PRIVATE jsoncpp_lib cpprest)
set_target_properties(myapp_linux PROPERTIES OUTPUT_NAME "myapp_linux")
add_custom_target(linux_build
    COMMAND ${CMAKE_COMMAND} --build . --target myapp_linux
    COMMENT "Building for Linux"
)

# Target for Windows build
add_executable(myapp_windows ${SOURCE_DIR}/main.cpp)
target_link_libraries(myapp_windows PRIVATE jsoncpp_lib cpprest)
set_target_properties(myapp_windows PROPERTIES OUTPUT_NAME "myapp_windows")
add_custom_target(windows_build
    COMMAND ${CMAKE_COMMAND} --build . --target myapp_windows
    COMMENT "Building for Windows"
)

# Custom linting and testing commands (Python environment setup assumed)
add_custom_target(lint
    COMMAND . venv/bin/activate && flake8 src/ && flake8 tests/
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Running code linting"
)

add_custom_target(test
    COMMAND . venv/bin/activate && PYTHONPATH=${CMAKE_SOURCE_DIR}/src/Server python3 -m unittest tests/*.py
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Running tests"
)

# Clean target to remove build files and vcpkg directory
add_custom_target(clean
    COMMAND ${CMAKE_COMMAND} -E rm -rf ${VCPKG_DIR} ${CMAKE_BINARY_DIR}/bin
    COMMENT "Cleaning up..."
)