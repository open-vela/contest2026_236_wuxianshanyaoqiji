cmake_minimum_required(VERSION 3.16)
project(passport_preview C CXX ASM)
set(LV_CONF_PATH "${CMAKE_CURRENT_SOURCE_DIR}/lv_conf.h" CACHE STRING "" FORCE)
set(LV_CONF_BUILD_DISABLE_EXAMPLES ON CACHE BOOL "" FORCE)
set(LV_CONF_BUILD_DISABLE_DEMOS ON CACHE BOOL "" FORCE)
set(LV_CONF_BUILD_DISABLE_THORVG_INTERNAL ON CACHE BOOL "" FORCE)
add_subdirectory(${LVGL_SOURCE} lvgl)
add_executable(passport_preview main.c
    ../../app/passport_companion/main/companion_ui.c
    ../../app/passport_companion/main/companion_character.c
    ../../app/passport_companion/main/companion_font.c
    ../../app/passport_companion/main/companion_status_font.c)
target_include_directories(passport_preview PRIVATE . ../../app/passport_companion/main)
target_link_libraries(passport_preview PRIVATE lvgl m)
