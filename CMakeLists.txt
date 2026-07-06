cmake_minimum_required(VERSION 3.21)

project(moza_effect_mvp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(MOZA_SDK_DIR "${CMAKE_CURRENT_SOURCE_DIR}/MOZA_SDK/1.0.1.8/MSVC2022-64")

add_executable(moza_effect_mvp
    src/main.cpp
)

target_include_directories(moza_effect_mvp PRIVATE
    "${MOZA_SDK_DIR}/include"
)

target_link_libraries(moza_effect_mvp PRIVATE
    "${MOZA_SDK_DIR}/lib/MOZA_SDK.lib"
    user32
)

target_compile_definitions(moza_effect_mvp PRIVATE
    NOMINMAX
    WIN32_LEAN_AND_MEAN
    DIRECTINPUT_VERSION=0x0800
    PROJECT_ROOT_PATH="${CMAKE_CURRENT_SOURCE_DIR}"
)

add_custom_command(TARGET moza_effect_mvp POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${MOZA_SDK_DIR}/bin/MOZA_SDK.dll"
        "$<TARGET_FILE_DIR:moza_effect_mvp>/MOZA_SDK.dll"
)

set_property(TARGET moza_effect_mvp PROPERTY
    VS_DEBUGGER_WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
)
