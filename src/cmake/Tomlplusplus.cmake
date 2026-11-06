# Defines tomlplusplus::tomlplusplus as a header-only interface target via
# FetchContent. Idempotent.
if(TARGET tomlplusplus::tomlplusplus)
    return()
endif()

include(FetchCache)
include(FetchContent)

FetchContent_Declare(
    tomlplusplus
    GIT_REPOSITORY https://github.com/marzer/tomlplusplus.git
    GIT_TAG        30172438cee64926dc41fdd9c11fb3ba5b2ba9de
    GIT_PROGRESS   TRUE
)
FetchContent_MakeAvailable(tomlplusplus)
