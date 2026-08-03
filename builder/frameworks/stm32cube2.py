# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
STM32Cube HAL2

Second generation of the STM32Cube embedded software libraries, introduced with
STM32CubeC5. Both the API and the package layout differ from the classic
STM32Cube packages handled by `stm32cube.py`:

    <family>xx_drivers/hal        HAL sources and headers (flat, .c next to .h)
    <family>xx_drivers/ll         LL API (header only in this generation)
    <family>xx_drivers/templates  default <family>xx_hal_conf.h, stm32_assert.h
    <family>xx_dfp/Include        device headers (<family>xx.h, system_*.h)
    <family>xx_dfp/Source         startup_<product_line>.c, Templates/system_*.c
    arch/cmsis/CMSIS/Core/Include CMSIS core

https://github.com/STMicroelectronics/STM32CubeC5
"""

import os
import shutil
import sys

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()

MCU = board.get("build.mcu", "")
MCU_FAMILY = MCU[0:7]

PRODUCT_LINE = board.get("build.product_line", "")
assert PRODUCT_LINE, "Missing MCU or Product Line field"

FRAMEWORK_DIR = platform.get_package_dir("framework-stm32cube%s" % MCU[5:7])
LDSCRIPTS_DIR = platform.get_package_dir("tool-ldscripts-ststm32")
assert all(os.path.isdir(d) for d in (FRAMEWORK_DIR, LDSCRIPTS_DIR))

DRIVERS_DIR = os.path.join(FRAMEWORK_DIR, "%sxx_drivers" % MCU_FAMILY)
DFP_DIR = os.path.join(FRAMEWORK_DIR, "%sxx_dfp" % MCU_FAMILY)
HAL_DIR = os.path.join(DRIVERS_DIR, "hal")
TEMPLATES_DIR = os.path.join(DRIVERS_DIR, "templates", "common")
CMSIS_CORE_DIR = os.path.join(
    FRAMEWORK_DIR, "arch", "cmsis", "CMSIS", "Core", "Include"
)

if not os.path.isdir(DRIVERS_DIR):
    sys.stderr.write(
        "Error: `%s` doesn't contain a HAL2 package. Use the `stm32cube` "
        "framework for classic STM32Cube packages.\n" % FRAMEWORK_DIR
    )
    env.Exit(1)


def get_linker_script(board_mcu):
    # Memory layouts only depend on the device and its flash size, so linker
    # scripts are named after the part number with the package and temperature
    # range digits replaced by an "x", the same way the device family package
    # names them: stm32c562ret6 -> STM32C562XE_FLASH.ld
    ldscript_name = "%sX%s_FLASH.ld" % (board_mcu[0:9].upper(), board_mcu[10:11].upper())

    ldscript = os.path.join(LDSCRIPTS_DIR, MCU_FAMILY, ldscript_name)
    if os.path.isfile(ldscript):
        return ldscript

    # Fall back to the scripts shipped with the device family package
    dfp_ldscript = os.path.join(
        DFP_DIR, "Source", "Templates", "gcc", "linker", ldscript_name.lower()
    )
    if os.path.isfile(dfp_ldscript):
        return dfp_ldscript

    sys.stderr.write(
        "Error: Cannot find a linker script for `%s` (looked for `%s`)!\n"
        % (MCU, ldscript_name)
    )
    env.Exit(1)


def generate_hal_config_file():
    conf_h_path = os.path.join(HAL_DIR, "%sxx_hal_conf.h" % MCU_FAMILY)
    template_h_path = os.path.join(TEMPLATES_DIR, "%sxx_hal_conf.h" % MCU_FAMILY)

    if board.get("build.stm32cube.custom_config_header", "no") == "yes":
        if os.path.isfile(conf_h_path):
            os.remove(conf_h_path)
        return

    if os.path.isfile(conf_h_path):
        return

    if not os.path.isfile(template_h_path):
        sys.stderr.write(
            "Error: Cannot find peripheral template file to configure framework!\n"
        )
        env.Exit(1)

    shutil.copy(template_h_path, conf_h_path)


machine_flags = [
    "-mthumb",
    "-mcpu=%s" % board.get("build.cpu"),
]

cpppath = [
    "$PROJECT_SRC_DIR",
    "$PROJECT_INCLUDE_DIR",
    CMSIS_CORE_DIR,
    os.path.join(DFP_DIR, "Include"),
    HAL_DIR,
    os.path.join(DRIVERS_DIR, "ll"),
]

# `stm32_assert.h` is only pulled in when the asserts are enabled. Keep the
# folder last so that a project can still override the shipped defaults.
if board.get("build.stm32cube.custom_config_header", "no") == "no":
    cpppath.append(TEMPLATES_DIR)

env.Append(
    ASFLAGS=machine_flags,
    ASPPFLAGS=[
        "-x", "assembler-with-cpp",
    ],

    CCFLAGS=machine_flags + [
        "-Os",  # optimize for size
        "-ffunction-sections",  # place each function in its own section
        "-fdata-sections",
        "-Wall",
        "-nostdlib",
    ],

    CPPDEFINES=[
        ("F_CPU", "$BOARD_F_CPU"),
    ],

    CPPPATH=cpppath,

    CXXFLAGS=[
        "-fno-rtti",
        "-fno-exceptions"
    ],

    LINKFLAGS=machine_flags + [
        "-Os",
        "-Wl,--gc-sections,--relax",
        "--specs=nano.specs",
        "--specs=nosys.specs",
    ],

    LIBPATH=[
        os.path.join(LDSCRIPTS_DIR, MCU_FAMILY),
    ],

    LIBS=["c", "gcc", "m", "stdc++", "nosys"],
)

if not board.get("build.ldscript", ""):
    env.Replace(LDSCRIPT_PATH=get_linker_script(MCU))

#
# Target: Build HAL Library
#

libs = []

# Generate a default <family>xx_hal_conf.h
generate_hal_config_file()

env.BuildSources(
    os.path.join("$BUILD_DIR", "FrameworkHALDriver"),
    HAL_DIR,
    src_filter="+<*.c>",
)

#
# CMSIS device library (startup code and system configuration)
#

if board.get("build.stm32cube.custom_system_setup", "no") == "no":
    sources_path = os.path.join(DFP_DIR, "Source")
    startup_file = board.get(
        "build.stm32cube.startup_file", "startup_%s.c" % PRODUCT_LINE.lower()
    )
    system_file = board.get(
        "build.stm32cube.system_file", "system_%sxx.c" % MCU_FAMILY
    )

    if not os.path.isfile(os.path.join(sources_path, startup_file)):
        print(
            "Warning! Cannot find the default startup file for `%s`. "
            "Ignore this warning if the startup code is part of your project." % MCU
        )

    libs.append(
        env.BuildLibrary(
            os.path.join("$BUILD_DIR", "FrameworkCMSISDevice"),
            sources_path,
            src_filter=[
                "-<*>",
                "+<%s>" % startup_file,
                "+<Templates/%s>" % system_file,
            ],
        )
    )

env.Append(LIBS=libs)
