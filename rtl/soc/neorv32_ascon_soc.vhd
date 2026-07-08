-- NEORV32 + Ascon-AEAD128 accelerator SoC for the Tang Nano 20K.
-- NEORV32 core (bootloader boot, IMEM/DMEM, UART0, GPIO, counters) with the
-- generated Ascon accelerator on the external Wishbone bus (XBUS) via
-- rtl/soc/ascon_aead128_wb.v -> ascon_aead128_axis_mmio (model-verified datapath).
-- See docs/NEORV32_INTEGRATION.md for the full build sequence.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library neorv32;

entity neorv32_ascon_soc is
  generic (
    CLOCK_FREQUENCY : natural := 27_000_000;
    IMEM_SIZE       : natural := 16*1024;
    DMEM_SIZE       : natural := 8*1024
  );
  port (
    clk_i       : in  std_ulogic;
    uart0_txd_o : out std_ulogic;
    uart0_rxd_i : in  std_ulogic;
    led_o       : out std_ulogic_vector(5 downto 0)
  );
end entity;

architecture rtl of neorv32_ascon_soc is
  signal por_cnt : unsigned(7 downto 0) := (others => '0');
  signal rstn    : std_ulogic;
  signal xbus_adr  : std_ulogic_vector(31 downto 0);
  signal xbus_dato : std_ulogic_vector(31 downto 0);
  signal xbus_dati : std_ulogic_vector(31 downto 0);
  signal xbus_we   : std_ulogic;
  signal xbus_sel  : std_ulogic_vector(3 downto 0);
  signal xbus_stb  : std_ulogic;
  signal xbus_cyc  : std_ulogic;
  signal xbus_ack  : std_ulogic;
  signal gpio_out  : std_ulogic_vector(31 downto 0);

  component ascon_aead128_wb is
    port (
      clk      : in  std_ulogic;
      rst_n    : in  std_ulogic;
      wb_adr_i : in  std_ulogic_vector(31 downto 0);
      wb_dat_i : in  std_ulogic_vector(31 downto 0);
      wb_dat_o : out std_ulogic_vector(31 downto 0);
      wb_we_i  : in  std_ulogic;
      wb_sel_i : in  std_ulogic_vector(3 downto 0);
      wb_stb_i : in  std_ulogic;
      wb_cyc_i : in  std_ulogic;
      wb_ack_o : out std_ulogic;
      wb_err_o : out std_ulogic
    );
  end component;
begin
  process(clk_i) begin
    if rising_edge(clk_i) then
      if por_cnt /= x"FF" then por_cnt <= por_cnt + 1; end if;
    end if;
  end process;
  -- power-on reset only (reset via re-flashing the bitstream, which reconfigures
  -- the FPGA). A button reset was removed: the board's button pin/polarity held
  -- the SoC in reset.
  rstn <= '1' when (por_cnt = x"FF") else '0';

  neorv32_top_inst : entity neorv32.neorv32_top
  generic map (
    CLOCK_FREQUENCY  => CLOCK_FREQUENCY,
    BOOT_MODE_SELECT => 0,
    RISCV_ISA_C      => true,
    RISCV_ISA_M      => false,         -- firmware is rv32i (soft mul/div); saves LUTs to fit GW2AR-18
    RISCV_ISA_Zicntr => true,
    IMEM_EN          => true,
    IMEM_SIZE        => IMEM_SIZE,
    DMEM_EN          => true,
    DMEM_SIZE        => DMEM_SIZE,
    IO_GPIO_NUM      => 8,
    IO_CLINT_EN      => true,
    IO_UART0_EN      => true,
    XBUS_EN          => true,
    XBUS_REGSTAGE_EN => false
  )
  port map (
    clk_i       => clk_i,
    rstn_i      => rstn,
    xbus_adr_o  => xbus_adr,
    xbus_dat_o  => xbus_dato,
    xbus_dat_i  => xbus_dati,
    xbus_we_o   => xbus_we,
    xbus_sel_o  => xbus_sel,
    xbus_stb_o  => xbus_stb,
    xbus_cyc_o  => xbus_cyc,
    xbus_ack_i  => xbus_ack,
    xbus_err_i  => '0',
    gpio_o      => gpio_out,
    uart0_txd_o => uart0_txd_o,
    uart0_rxd_i => uart0_rxd_i
  );

  ascon_inst : ascon_aead128_wb
  port map (
    clk      => clk_i,
    rst_n    => rstn,
    wb_adr_i => xbus_adr,
    wb_dat_i => xbus_dato,
    wb_dat_o => xbus_dati,
    wb_we_i  => xbus_we,
    wb_sel_i => xbus_sel,
    wb_stb_i => xbus_stb,
    wb_cyc_i => xbus_cyc,
    wb_ack_o => xbus_ack,
    wb_err_o => open
  );

  led_o <= not gpio_out(5 downto 0);
end architecture;
