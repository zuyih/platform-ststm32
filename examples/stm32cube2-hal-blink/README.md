How to build PlatformIO based project
=====================================

This example uses the second generation of the STM32Cube libraries (`stm32cube2`,
introduced with STM32CubeC5). Its HAL API is *not* source compatible with the
classic `stm32cube` framework — see `examples/stm32cube-hal-blink` for that one.

1. [Install PlatformIO Core](https://docs.platformio.org/page/core.html)
2. Download [development platform with examples](https://github.com/platformio/platform-ststm32/archive/develop.zip)
3. Extract ZIP archive
4. Run these commands:

```shell
# Change directory to example
$ cd platform-ststm32/examples/stm32cube2-hal-blink

# Build project
$ pio run

# Upload firmware
$ pio run --target upload

# Build specific environment
$ pio run -e nucleo_c562re

# Upload firmware for the specific environment
$ pio run -e nucleo_c562re --target upload

# Clean build files
$ pio run --target clean
```
