-- ================================================================================ --
-- NEORV32 CFS replacement: pyrilascon stream-native ASCON accelerator
-- -------------------------------------------------------------------------------- --
-- This alternative CFS wrapper exposes the stream-native AEAD128 system through a
-- single NEORV32 CFS address window.  It deliberately uses the canonical NEORV32
-- entity name `neorv32_cfs`; compile either this file or neorv32_cfs_ascon.vhd,
-- never both, as the active CFS replacement.
--
-- Address map relative to the NEORV32 CFS base address 0xffeb0000:
--   0x000..0x0ff  frozen ASCON CSR/control ABI
--   0x100..0x1ff  CPU-driven AXI-stream MMIO bridge
--
-- Firmware build for this wrapper should define:
--   ASCON_ACCEL_BASE_ADDR           = 0xffeb0000
--   ASCON_ACCEL_AXIS_MMIO_BASE_ADDR = 0xffeb0100
-- ================================================================================ --

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library neorv32;
use neorv32.neorv32_package.all;

entity neorv32_cfs is
  port (
    -- global control --
    clk_i     : in  std_ulogic;
    rstn_i    : in  std_ulogic;

    -- CPU access --
    bus_req_i : in  bus_req_t;
    bus_rsp_o : out bus_rsp_t;

    -- CPU interrupt --
    irq_o     : out std_ulogic;

    -- external IO conduit --
    cfs_in_i  : in  std_ulogic_vector(255 downto 0);
    cfs_out_o : out std_ulogic_vector(255 downto 0)
  );
end neorv32_cfs;

architecture neorv32_cfs_stream_axis_mmio_rtl of neorv32_cfs is

  component ascon_accel_stream_aead128_axis_mmio_system is
    generic (
      DATA_BYTES     : integer := 16;
      DATA_WIDTH     : integer := 128;
      MAX_TEXT_BYTES : integer := 1024;
      MAX_TEXT_BITS  : integer := 8192;
      RX_FIFO_DEPTH  : integer := 4
    );
    port (
      clk_i               : in  std_ulogic;
      rstn_i              : in  std_ulogic;
      csr_bus_valid_i     : in  std_ulogic;
      csr_bus_write_i     : in  std_ulogic;
      csr_bus_addr_i      : in  std_ulogic_vector(7 downto 0);
      csr_bus_wdata_i     : in  std_ulogic_vector(31 downto 0);
      csr_bus_wstrb_i     : in  std_ulogic_vector(3 downto 0);
      csr_bus_rdata_o     : out std_ulogic_vector(31 downto 0);
      csr_bus_ready_o     : out std_ulogic;
      axis_bus_valid_i    : in  std_ulogic;
      axis_bus_write_i    : in  std_ulogic;
      axis_bus_addr_i     : in  std_ulogic_vector(7 downto 0);
      axis_bus_wdata_i    : in  std_ulogic_vector(31 downto 0);
      axis_bus_wstrb_i    : in  std_ulogic_vector(3 downto 0);
      axis_bus_rdata_o    : out std_ulogic_vector(31 downto 0);
      axis_bus_ready_o    : out std_ulogic;
      irq_o               : out std_ulogic;
      axis_bridge_error_o : out std_ulogic
    );
  end component;

  signal axis_window_sel : std_ulogic;

  signal csr_valid       : std_ulogic;
  signal csr_rdata       : std_ulogic_vector(31 downto 0);
  signal csr_ready       : std_ulogic;

  signal axis_valid      : std_ulogic;
  signal axis_rdata      : std_ulogic_vector(31 downto 0);
  signal axis_ready      : std_ulogic;

  signal cfs_rdata       : std_ulogic_vector(31 downto 0);
  signal cfs_ready       : std_ulogic;
  signal accel_irq       : std_ulogic;
  signal axis_error      : std_ulogic;

begin

  -- CFS byte address bit 8 selects between the two local MMIO windows.
  -- The low eight address bits index registers inside the selected window.
  axis_window_sel <= bus_req_i.addr(8);
  csr_valid       <= bus_req_i.stb and not axis_window_sel;
  axis_valid      <= bus_req_i.stb and axis_window_sel;

  stream_system_i : ascon_accel_stream_aead128_axis_mmio_system
    generic map (
      DATA_BYTES     => 16,
      DATA_WIDTH     => 128,
      MAX_TEXT_BYTES => 64,
      MAX_TEXT_BITS  => 512,
      RX_FIFO_DEPTH  => 4
    )
    port map (
      clk_i               => clk_i,
      rstn_i              => rstn_i,
      csr_bus_valid_i     => csr_valid,
      csr_bus_write_i     => bus_req_i.rw,
      csr_bus_addr_i      => bus_req_i.addr(7 downto 0),
      csr_bus_wdata_i     => bus_req_i.data,
      csr_bus_wstrb_i     => bus_req_i.ben,
      csr_bus_rdata_o     => csr_rdata,
      csr_bus_ready_o     => csr_ready,
      axis_bus_valid_i    => axis_valid,
      axis_bus_write_i    => bus_req_i.rw,
      axis_bus_addr_i     => bus_req_i.addr(7 downto 0),
      axis_bus_wdata_i    => bus_req_i.data,
      axis_bus_wstrb_i    => bus_req_i.ben,
      axis_bus_rdata_o    => axis_rdata,
      axis_bus_ready_o    => axis_ready,
      irq_o               => accel_irq,
      axis_bridge_error_o => axis_error
    );

  irq_o <= accel_irq;

  cfs_rdata <= axis_rdata when axis_window_sel = '1' else csr_rdata;
  cfs_ready <= axis_ready when axis_window_sel = '1' else csr_ready;

  -- Conduit outputs are not required for normal operation, but expose a tiny
  -- debug vector for board bring-up: IRQ, bridge error, window select, ready.
  cfs_out_o <= (255 downto 4 => '0') & cfs_ready & axis_window_sel & axis_error & accel_irq;

  -- NEORV32 internal-bus response.  The underlying pyrilascon bus is
  -- single-cycle-ready, so acknowledge each CFS access on the next cycle while
  -- returning data from the selected local window.
  bus_access : process(rstn_i, clk_i)
  begin
    if (rstn_i = '0') then
      bus_rsp_o <= rsp_terminate_c;
    elsif rising_edge(clk_i) then
      bus_rsp_o.ack  <= bus_req_i.stb;
      bus_rsp_o.err  <= '0';
      bus_rsp_o.data <= cfs_rdata;
    end if;
  end process bus_access;

end neorv32_cfs_stream_axis_mmio_rtl;
