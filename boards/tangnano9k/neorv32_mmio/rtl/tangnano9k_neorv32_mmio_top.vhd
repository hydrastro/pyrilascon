-- ============================================================================
-- Tang Nano 9K NEORV32 + ASCON CFS — corrected top
--
-- Drop in as boards/tangnano9k/neorv32_mmio/rtl/tangnano9k_neorv32_mmio_top.vhd
--
-- Why this file exists:
--   The original top had `BOOT_MODE_SELECT => 2` with a misleading comment
--   claiming "internal UART bootloader". In the checked-out NEORV32 (commit
--   f62ca43), the semantics are:
--     0 = boot via internal bootloader (UART upload flow)
--     1 = boot from custom address
--     2 = boot from initialised IMEM image (ROM, baked into bitstream)
--   With value 2, NEORV32 instantiates a 32 KB behavioural-VHDL ROM from
--   neorv32_imem_image.vhd. The open-source Gowin flow (yosys+apicula+
--   nextpnr-himbaechel) does not reliably infer that as BSRAM, falling back
--   to LUT-as-ROM and blowing the GW1NR-9C utilisation budget.
--   That is the failure you saw at PnR.
--
-- Fix: BOOT_MODE_SELECT => 0 (the genuine bootloader) plus slim memories.
--      This mirrors the configuration of the `plain` board target that
--      previously produced a working .fs.
-- ============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library neorv32;
use neorv32.neorv32_package.all;

entity tangnano9k_neorv32_mmio_top is
  port (
    clk     : in  std_ulogic;
    rst_n   : in  std_ulogic;
    uart_rx : in  std_ulogic;
    uart_tx : out std_ulogic;
    led_n   : out std_ulogic_vector(5 downto 0)
  );
end entity tangnano9k_neorv32_mmio_top;

architecture rtl of tangnano9k_neorv32_mmio_top is
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
  led_n(0) <= not heartbeat(24);     -- ~0.4 Hz heartbeat, confirms clk is alive
  led_n(1) <= not cfs_out(0);        -- ASCON IRQ
  led_n(2) <= not cfs_out(1);
  led_n(3) <= not cfs_out(2);
  led_n(4) <= not cfs_out(3);
  led_n(5) <= '1';

  neorv32_top_i : entity neorv32.neorv32_top
    generic map (
      CLOCK_FREQUENCY  => 27_000_000,
      BOOT_MODE_SELECT => 0,           -- internal UART bootloader (FIXED)

      -- Keep the CPU minimal for GW1NR-9 bring-up.
      RISCV_ISA_Zicntr  => true,       -- cycle counter required by benchmark firmware
      CPU_FAST_SHIFT_EN => false,

      -- Slim internal memories. Firmware text+rodata = 13.8 KB, bss+heap = 768 B.
      IMEM_EN          => true,
      IMEM_SIZE        => 16*1024,     -- was 32 KB
      IMEM_OUTREG_EN   => false,
      DMEM_EN          => true,
      DMEM_SIZE        => 8*1024,      -- was 16 KB
      DMEM_OUTREG_EN   => false,

      -- Board IO and ASCON CFS.
      IO_UART0_EN      => true,
      IO_UART0_RX_FIFO => 1,           -- min permitted by NEORV32 generic
      IO_UART0_TX_FIFO => 1,
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

end architecture rtl;p
