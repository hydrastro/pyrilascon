// Minimal NEORV32 UART sanity test - isolates "does any program print?" from the
// benchmark. Uses the bootloader's existing UART config (no re-setup) and loops
// forever printing a marker, so any capture window catches it.
#include <neorv32.h>

int main(void) {
  uint32_t n = 0u;
  while (1) {
    neorv32_uart0_puts("HELLO_NEORV32 ");
    neorv32_uart0_putc((char)('0' + (int)(n % 10u)));
    neorv32_uart0_puts("\r\n");
    n++;
    for (volatile uint32_t d = 0u; d < 2000000u; d++) { }
  }
  return 0;
}
