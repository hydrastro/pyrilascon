-- Tang Nano 9K NEORV32 + ASCON CFS top.
-- Boots through the NEORV32 UART bootloader and exposes the stream-native ASCON
-- AEAD128 accelerator through the CFS MMIO window at 0xffeb0000.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library neorv32;
use neorv32.neorv32_package.all;

entity tangnano9k_neorv32_ascon_top is
  port (
    clk     : in  std_ulogic;
    rst_n   : in  std_ulogic;
    uart_rx : in  std_ulogic;
    uart_tx : out std_ulogic;
    led_n   : out std_ulogic_vector(5 downto 0)
  );
end entity tangnano9k_neorv32_ascon_top;

architecture rtl of tangnano9k_neorv32_ascon_top is
  signal heartbeat : unsigned(24 downto 0) := (others => '0');
  signal cfs_out   : std_ulogic_vector(255 downto 0);
begin

  process(clk, rst_n)
  begin
    if rst_n = '0' then
      heartbeat <= (others => '0');
    elsif rising_edge(clk) then
      heartbeat <= heartbeat + 1;
    end if;
  end process;

  -- Tang Nano 9K user LEDs are active-low.
  -- cfs_out(0): ASCON IRQ, cfs_out(1): AXI bridge error,
  -- cfs_out(2): selected CFS sub-window, cfs_out(3): selected window ready.
  led_n(0) <= not heartbeat(24);
  led_n(1) <= not cfs_out(0);
  led_n(2) <= not cfs_out(1);
  led_n(3) <= not cfs_out(2);
  led_n(4) <= not cfs_out(3);
  led_n(5) <= '1';

  neorv32_top_i : entity neorv32.neorv32_top
    generic map (
      CLOCK_FREQUENCY  => 27_000_000,
      BOOT_MODE_SELECT => 2,          -- internal UART bootloader

      -- Keep the CPU deliberately small for GW1NR-9 bring-up.
      RISCV_ISA_Zicntr => true,       -- cycle counter required by benchmark firmware
      CPU_FAST_SHIFT_EN => false,

      -- Internal memories. Firmware executable is uploaded by the bootloader.
      IMEM_EN          => true,
      IMEM_SIZE        => 32*1024,
      IMEM_OUTREG_EN   => true,
      DMEM_EN          => true,
      DMEM_SIZE        => 16*1024,
      DMEM_OUTREG_EN   => true,

      -- Board IO and ASCON CFS.
      IO_UART0_EN      => true,
      IO_UART0_RX_FIFO => 16,
      IO_UART0_TX_FIFO => 16,
      IO_CFS_EN        => true
    )
    port map (
      clk_i       => clk,
      rstn_i      => rst_n,
      uart0_txd_o => uart_tx,
      uart0_rxd_i => uart_rx,
      cfs_in_i    => (others => '0'),
      cfs_out_o   => cfs_out
    );

end architecture rtl;
