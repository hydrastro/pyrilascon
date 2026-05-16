-- ================================================================================ --
-- NEORV32 CFS replacement: pyrilascon ASCON accelerator
-- -------------------------------------------------------------------------------- --
-- This file intentionally uses the canonical NEORV32 entity name `neorv32_cfs`.
-- Add it to the NEORV32 `neorv32` VHDL library instead of the stock
-- rtl/core/neorv32_cfs.vhd template.
--
-- The CFS bus is translated into the frozen pyrilascon 32-bit MMIO ABI.
-- CFS byte address 0x0000 maps to accelerator register offset 0x00.
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

architecture neorv32_cfs_rtl of neorv32_cfs is

  component ascon_accel_mmio_aead128_top is
    port (
      clk_i       : in  std_ulogic;
      rstn_i      : in  std_ulogic;
      bus_valid_i : in  std_ulogic;
      bus_write_i : in  std_ulogic;
      bus_addr_i  : in  std_ulogic_vector(7 downto 0);
      bus_wdata_i : in  std_ulogic_vector(31 downto 0);
      bus_wstrb_i : in  std_ulogic_vector(3 downto 0);
      bus_rdata_o : out std_ulogic_vector(31 downto 0);
      bus_ready_o : out std_ulogic;
      irq_o       : out std_ulogic
    );
  end component;

  signal mmio_valid  : std_ulogic;
  signal mmio_write  : std_ulogic;
  signal mmio_addr   : std_ulogic_vector(7 downto 0);
  signal mmio_wdata  : std_ulogic_vector(31 downto 0);
  signal mmio_wstrb  : std_ulogic_vector(3 downto 0);
  signal mmio_rdata  : std_ulogic_vector(31 downto 0);
  signal mmio_ready  : std_ulogic;
  signal mmio_irq    : std_ulogic;

begin

  -- The CFS is byte addressed. The frozen accelerator ABI currently occupies
  -- offsets 0x00..0x7c, so the low eight address bits are sufficient.
  mmio_valid <= bus_req_i.stb;
  mmio_write <= bus_req_i.rw;
  mmio_addr  <= bus_req_i.addr(7 downto 0);
  mmio_wdata <= bus_req_i.data;
  mmio_wstrb <= bus_req_i.ben;

  ascon_accel_i : ascon_accel_mmio_aead128_top
    port map (
      clk_i       => clk_i,
      rstn_i      => rstn_i,
      bus_valid_i => mmio_valid,
      bus_write_i => mmio_write,
      bus_addr_i  => mmio_addr,
      bus_wdata_i => mmio_wdata,
      bus_wstrb_i => mmio_wstrb,
      bus_rdata_o => mmio_rdata,
      bus_ready_o => mmio_ready,
      irq_o       => mmio_irq
    );

  irq_o <= mmio_irq;

  -- Conduit outputs are not required for the memory-mapped accelerator, but
  -- expose the interrupt status for quick board-level debugging if desired.
  cfs_out_o <= (255 downto 1 => '0') & mmio_irq;

  -- NEORV32 internal-bus response. The CFS bus expects every access to be
  -- acknowledged, normally in the cycle after STB. Our accelerator ABI is
  -- single-cycle-ready, so we register the response here.
  bus_access : process(rstn_i, clk_i)
  begin
    if (rstn_i = '0') then
      bus_rsp_o <= rsp_terminate_c;
    elsif rising_edge(clk_i) then
      bus_rsp_o.ack  <= bus_req_i.stb;
      bus_rsp_o.err  <= '0';
      bus_rsp_o.data <= mmio_rdata;
    end if;
  end process bus_access;

end neorv32_cfs_rtl;
