// Copyright (c) rAthena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

// Lua 5.4 (3rdparty/lua, MIT), compiled here as C++ in one translation unit.
//
// One file rather than a library, so neither build needed a new target:
// the Makefile and CMake both already compile every .cpp under src/map.
// As C++, Lua raises its errors as exceptions rather than longjmp, which is
// what makes it safe to call from this code base: a longjmp across C++ frames
// would skip their destructors.
//
// Only what the sandbox in skill_lua.cpp opens is compiled: no io, os,
// package (require) or debug library, and no linit.c, which would link them.

#include "../../3rdparty/lua/src/lapi.c"
#include "../../3rdparty/lua/src/lcode.c"
#include "../../3rdparty/lua/src/lctype.c"
#include "../../3rdparty/lua/src/ldebug.c"
#include "../../3rdparty/lua/src/ldo.c"
#include "../../3rdparty/lua/src/ldump.c"
#include "../../3rdparty/lua/src/lfunc.c"
#include "../../3rdparty/lua/src/lgc.c"
#include "../../3rdparty/lua/src/llex.c"
#include "../../3rdparty/lua/src/lmem.c"
#include "../../3rdparty/lua/src/lobject.c"
#include "../../3rdparty/lua/src/lopcodes.c"
#include "../../3rdparty/lua/src/lparser.c"
#include "../../3rdparty/lua/src/lstate.c"
#include "../../3rdparty/lua/src/lstring.c"
#include "../../3rdparty/lua/src/ltable.c"
#include "../../3rdparty/lua/src/ltm.c"
#include "../../3rdparty/lua/src/lundump.c"
#include "../../3rdparty/lua/src/lvm.c"
#include "../../3rdparty/lua/src/lzio.c"

#include "../../3rdparty/lua/src/lauxlib.c"
#include "../../3rdparty/lua/src/lbaselib.c"
#include "../../3rdparty/lua/src/lmathlib.c"
#include "../../3rdparty/lua/src/lstrlib.c"
#include "../../3rdparty/lua/src/ltablib.c"
#include "../../3rdparty/lua/src/lutf8lib.c"
