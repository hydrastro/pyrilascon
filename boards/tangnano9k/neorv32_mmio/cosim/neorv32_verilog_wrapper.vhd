-- ============================================================================
-- NEORV32 + ASCON-CFS wrapper for the all-Verilog co-simulation flow.
-- Mirrors the Tang Nano 9K board top: 27 MHz, BOOT_MODE_SELECT=2 (IMEM image),
-- 32 KB IMEM, 16 KB DMEM, UART0, IO_CFS_EN=true (binds to neorv32_cfs_ascon).
-- ============================================================================

library ieee;
use ieee.std_logic_1164.all;

library neorv32;
use neorv32.neorv32_package.all;

entity neorv32_verilog_wrapper is
  port (
    clk_i       : in  std_ulogic;
    rstn_i      : in  std_ulogic;
    uart0_txd_o : out std_ulogic;
    uart0_rxd_i : in  std_ulogic
  );
end entity;

architecture rtl of neorv32_verilog_wrapper is
begin
  neorv32_top_inst : neorv32_top
    generic map (
      CLOCK_FREQUENCY   => 27_000_000,
      BOOT_MODE_SELECT  => 2,
      RISCV_ISA_Zicntr  => true,
      CPU_FAST_SHIFT_EN => false,
      IMEM_EN           => true,
      IMEM_SIZE         => 32*1024,
      IMEM_OUTREG_EN    => false,
      DMEM_EN           => true,
      DMEM_SIZE         => 16*1024,
      DMEM_OUTREG_EN    => false,
      IO_UART0_EN       => true,
      IO_UART0_RX_FIFO  => 1,
      IO_UART0_TX_FIFO  => 1,
      IO_CFS_EN         => true
    )
    port map (
      clk_i       => clk_i,
      rstn_i      => rstn_i,
      uart0_txd_o => uart0_txd_o,
      uart0_rxd_i => uart0_rxd_i,
      cfs_in_i    => (others => '0'),
      cfs_out_o   => open
    );
end architecture;
