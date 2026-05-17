`ifndef ASCON_ACCEL_AXIS_DEFS_VH
`define ASCON_ACCEL_AXIS_DEFS_VH

// AXI4-Stream tuser segment identifiers used by the pyrilascon data plane.
// DATA is little-endian within each 32-bit tdata word. tkeep[0] marks tdata[7:0].
`define ASCON_AXIS_USER_NONE    4'h0
`define ASCON_AXIS_USER_AD      4'h1
`define ASCON_AXIS_USER_TEXT    4'h2
`define ASCON_AXIS_USER_CUSTOM  4'h3

`endif
