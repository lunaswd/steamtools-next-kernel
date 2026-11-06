# Some localized MSVC installations emit UTF-8 diagnostics while CMake's
# compiler-id probe decodes with the host OEM code page. An empty prefix breaks
# cmcldeps RC scans and leaks /showIncludes lines into Ninja dependency paths.
if(MSVC AND CMAKE_GENERATOR MATCHES "Ninja" AND NOT CMAKE_CL_SHOWINCLUDES_PREFIX)
    set(_probe_dir "${CMAKE_BINARY_DIR}/compiler-includes")
    file(MAKE_DIRECTORY "${_probe_dir}")
    file(WRITE "${_probe_dir}/kernel_include_probe.h" "/* dependency-prefix probe */\n")
    file(WRITE "${_probe_dir}/kernel_include_probe.cpp" "#include \"kernel_include_probe.h\"\n")
    execute_process(
        COMMAND "${CMAKE_CXX_COMPILER}" /nologo /showIncludes /c
                "${_probe_dir}/kernel_include_probe.cpp"
                "/Fo${_probe_dir}/kernel_include_probe.obj"
        OUTPUT_VARIABLE _probe_stdout
        ERROR_VARIABLE _probe_stderr
        RESULT_VARIABLE _probe_result
        ENCODING UTF-8
    )
    string(REGEX MATCH "[^\r\n]*[ \t]+[A-Za-z]:[^\r\n]*kernel_include_probe.h"
           _include_line "${_probe_stdout}${_probe_stderr}")
    string(REGEX REPLACE "[ \t]+[A-Za-z]:.*$" "" _prefix "${_include_line}")
    string(STRIP "${_prefix}" _prefix)
    if(NOT _probe_result EQUAL 0 OR NOT _prefix)
        message(FATAL_ERROR "MSVC include-prefix detection failed; use an x64 Developer terminal or a Visual Studio generator")
    endif()
    set(CMAKE_CL_SHOWINCLUDES_PREFIX "${_prefix}" CACHE STRING "MSVC include prefix" FORCE)
    message(STATUS "Detected localized MSVC include prefix: ${_prefix}")
endif()
