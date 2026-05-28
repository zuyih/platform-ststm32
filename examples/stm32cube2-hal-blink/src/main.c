#include "stm32c5xx_hal.h"
#include "stm32c5xx_hal_gpio.h"
#include "stm32c5xx_hal_rcc.h"

/* User LED of the NUCLEO-C562RE board. Override from `platformio.ini` for a
   different wiring, e.g.
     build_flags =
       -DLED_GPIO_PORT=HAL_GPIOB
       -DLED_GPIO_PIN=HAL_GPIO_PIN_0
       "-DLED_GPIO_CLK_ENABLE()=HAL_RCC_GPIOB_EnableClock()"
*/
#ifndef LED_GPIO_PORT
#define LED_GPIO_PORT                          HAL_GPIOA
#endif
#ifndef LED_GPIO_PIN
#define LED_GPIO_PIN                           HAL_GPIO_PIN_5
#endif
#ifndef LED_GPIO_CLK_ENABLE
#define LED_GPIO_CLK_ENABLE()                  HAL_RCC_GPIOA_EnableClock()
#endif

int main(void)
{
  /* Also configures the SysTick used by HAL_Delay() */
  HAL_Init();

  LED_GPIO_CLK_ENABLE();

  const hal_gpio_config_t led_config = {
    .mode = HAL_GPIO_MODE_OUTPUT,
    .pull = HAL_GPIO_PULL_NO,
    .speed = HAL_GPIO_SPEED_FREQ_LOW,
    .output_type = HAL_GPIO_OUTPUT_PUSHPULL,
    .init_state = HAL_GPIO_PIN_RESET,
  };

  HAL_GPIO_Init(LED_GPIO_PORT, LED_GPIO_PIN, &led_config);

  while (1)
  {
    HAL_GPIO_TogglePin(LED_GPIO_PORT, LED_GPIO_PIN);

    HAL_Delay(1000);
  }
}

/* The startup code only provides a weak alias to the default handler, so the
   HAL time base has to be driven from here. */
void SysTick_Handler(void)
{
  HAL_IncTick();
}
