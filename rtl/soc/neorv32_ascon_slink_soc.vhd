-- NEORV32 + Ascon-AEAD128 accelerator SoC for the Tang Nano 20K -- STREAM DATA PLANE.
--
-- This is the AXI4-Stream variant of rtl/soc/neorv32_ascon_soc.vhd. The proven
-- MMIO SoC is left untouched; build whichever you want.
--
-- What is different, and why
-- --------------------------
-- The accelerator's engine (ascon_aead128_axis) was always AXI4-Stream native.
-- In the MMIO SoC its stream was driven by a CPU store:
--
--     wire s_tvalid = din_ctl_wr;     -- a beat fires when the CPU writes a register
--
-- so every 4 payload bytes cost two bus transactions, and measurement showed the
-- accelerator spent 97.8% of its busy time waiting for the CPU rather than doing
-- cryptography.
--
-- Here the payload path is:
--
--     DMEM -> DMA -> SLINK TX FIFO -> s_axis -> Ascon -> m_axis -> SLINK RX FIFO -> DMA -> DMEM
--
-- The CPU writes key/nonce/lengths/START over XBUS, kicks the DMA, and waits.
-- It never touches a payload byte. Simulation of the resulting datapath (see
-- tools/verify_slink_plane.py) gives 118 busy cycles for the ad16_pt32 case
-- against 4948 on the MMIO path -- and the crypto share of busy time rises from
-- 2.2% to 75%, i.e. the design becomes compute-bound instead of interface-bound.
--
-- SLINK maps almost 1:1 onto AXI4-Stream (32-bit data, valid/ready/last), which
-- is why this is a small amount of glue rather than a new bus. The one thing
-- SLINK cannot carry per beat is the accelerator's tuser (AD vs message) and
-- tkeep (byte mask) -- ascon_slink_shim derives both from the AD_LEN/TEXT_LEN
-- control registers plus a byte counter, which is precisely what lets a DMA with
-- a constant destination address drive the whole payload.
--
-- STATUS: the Verilog datapath (shim + engine) is verified against the golden
-- model in simulation. This VHDL top has NOT been elaborated or fitted here --
-- run `make soc-check` (GHDL elaborate) and then the full build. Area is the live
-- risk: the MMIO SoC already needed RISCV_ISA_M disabled to fit the GW2AR-18,
-- and this adds SLINK + DMA.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library neorv32;

entity neorv32_ascon_slink_soc is
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

architecture rtl of neorv32_ascon_slink_soc is
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

  -- SLINK <-> accelerator payload plane
  signal slink_tx_dat : std_ulogic_vector(31 downto 0);
  signal slink_tx_dst : std_ulogic_vector(3 downto 0);
  signal slink_tx_val : std_ulogic;
  signal slink_tx_lst : std_ulogic;
  signal slink_tx_rdy : std_ulogic;

  signal slink_rx_dat : std_ulogic_vector(31 downto 0);
  signal slink_rx_src : std_ulogic_vector(3 downto 0);
  signal slink_rx_val : std_ulogic;
  signal slink_rx_lst : std_ulogic;
  signal slink_rx_rdy : std_ulogic;

  component ascon_aead128_slink_wb is
    port (
      clk            : in  std_ulogic;
      rst_n          : in  std_ulogic;
      wb_adr_i       : in  std_ulogic_vector(31 downto 0);
      wb_dat_i       : in  std_ulogic_vector(31 downto 0);
      wb_dat_o       : out std_ulogic_vector(31 downto 0);
      wb_we_i        : in  std_ulogic;
      wb_sel_i       : in  std_ulogic_vector(3 downto 0);
      wb_stb_i       : in  std_ulogic;
      wb_cyc_i       : in  std_ulogic;
      wb_ack_o       : out std_ulogic;
      wb_err_o       : out std_ulogic;
      slink_tx_dat_i : in  std_ulogic_vector(31 downto 0);
      slink_tx_val_i : in  std_ulogic;
      slink_tx_rdy_o : out std_ulogic;
      slink_rx_dat_o : out std_ulogic_vector(31 downto 0);
      slink_rx_val_o : out std_ulogic;
      slink_rx_rdy_i : in  std_ulogic;
      slink_rx_lst_o : out std_ulogic;
      slink_rx_src_o : out std_ulogic_vector(3 downto 0)
    );
  end component;
begin
  process(clk_i) begin
    if rising_edge(clk_i) then
      if por_cnt /= x"FF" then por_cnt <= por_cnt + 1; end if;
    end if;
  end process;
  rstn <= '1' when (por_cnt = x"FF") else '0';

  neorv32_top_inst : entity neorv32.neorv32_top
  generic map (
    CLOCK_FREQUENCY  => CLOCK_FREQUENCY,
    BOOT_MODE_SELECT => 0,
    RISCV_ISA_C      => true,
    RISCV_ISA_M      => false,         -- firmware is rv32i (soft mul/div); saves LUTs
    RISCV_ISA_Zicntr => true,
    IMEM_EN          => true,
    IMEM_SIZE        => IMEM_SIZE,
    DMEM_EN          => true,
    DMEM_SIZE        => DMEM_SIZE,
    IO_GPIO_NUM      => 8,
    IO_CLINT_EN      => true,
    IO_UART0_EN      => true,
    -- the data mover: reads DMEM, writes the SLINK TX register with a constant
    -- destination address (descriptor bit conf_dst_hi_c = 0)
    IO_DMA_EN        => true,
    -- the stream port. The RX FIFO must hold a whole result, or the engine
    -- back-pressures in its TX state and never raises done: MSG_MAX/4 = 8 words,
    -- so 16 gives headroom.
    IO_SLINK_EN      => true,
    IO_SLINK_RX_FIFO => 16,
    IO_SLINK_TX_FIFO => 16,
    XBUS_EN          => true,
    XBUS_REGSTAGE_EN => false
  )
  port map (
    clk_i          => clk_i,
    rstn_i         => rstn,
    xbus_adr_o     => xbus_adr,
    xbus_dat_o     => xbus_dato,
    xbus_dat_i     => xbus_dati,
    xbus_we_o      => xbus_we,
    xbus_sel_o     => xbus_sel,
    xbus_stb_o     => xbus_stb,
    xbus_cyc_o     => xbus_cyc,
    xbus_ack_i     => xbus_ack,
    xbus_err_i     => '0',
    slink_rx_dat_i => slink_rx_dat,
    slink_rx_src_i => slink_rx_src,
    slink_rx_val_i => slink_rx_val,
    slink_rx_lst_i => slink_rx_lst,
    slink_rx_rdy_o => slink_rx_rdy,
    slink_tx_dat_o => slink_tx_dat,
    slink_tx_dst_o => slink_tx_dst,
    slink_tx_val_o => slink_tx_val,
    slink_tx_lst_o => slink_tx_lst,
    slink_tx_rdy_i => slink_tx_rdy,
    gpio_o         => gpio_out,
    uart0_txd_o    => uart0_txd_o,
    uart0_rxd_i    => uart0_rxd_i
  );

  ascon_inst : ascon_aead128_slink_wb
  port map (
    clk            => clk_i,
    rst_n          => rstn,
    -- control plane
    wb_adr_i       => xbus_adr,
    wb_dat_i       => xbus_dato,
    wb_dat_o       => xbus_dati,
    wb_we_i        => xbus_we,
    wb_sel_i       => xbus_sel,
    wb_stb_i       => xbus_stb,
    wb_cyc_i       => xbus_cyc,
    wb_ack_o       => xbus_ack,
    wb_err_o       => open,
    -- payload plane
    slink_tx_dat_i => slink_tx_dat,
    slink_tx_val_i => slink_tx_val,
    slink_tx_rdy_o => slink_tx_rdy,
    slink_rx_dat_o => slink_rx_dat,
    slink_rx_val_o => slink_rx_val,
    slink_rx_rdy_i => slink_rx_rdy,
    slink_rx_lst_o => slink_rx_lst,
    slink_rx_src_o => slink_rx_src
  );

  -- slink_tx_dst / slink_tx_lst are unused: the shim derives tuser and tkeep from
  -- the AD_LEN/TEXT_LEN registers, precisely so that a DMA (which cannot vary the
  -- routing field per beat) can drive the whole payload unaided.

  led_o <= not gpio_out(5 downto 0);
end architecture;
