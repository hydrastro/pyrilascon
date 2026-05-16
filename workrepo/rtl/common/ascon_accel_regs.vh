`ifndef ASCON_ACCEL_REGS_VH
`define ASCON_ACCEL_REGS_VH

// Generated from ascon_arch/register_map.py. Do not edit manually.
`define ASCON_ACCEL_ABI_VERSION 32'd1

// Register offsets, byte-addressed.
`define ASCON_REG_CONTROL           8'h00
`define ASCON_REG_STATUS            8'h04
`define ASCON_REG_MODE              8'h08
`define ASCON_REG_CAPABILITIES      8'h0C
`define ASCON_REG_AD_LEN            8'h10
`define ASCON_REG_TEXT_LEN          8'h14
`define ASCON_REG_OUT_LEN           8'h18
`define ASCON_REG_CUSTOM_LEN        8'h1C
`define ASCON_REG_KEY0              8'h20
`define ASCON_REG_KEY1              8'h24
`define ASCON_REG_KEY2              8'h28
`define ASCON_REG_KEY3              8'h2C
`define ASCON_REG_NONCE0            8'h30
`define ASCON_REG_NONCE1            8'h34
`define ASCON_REG_NONCE2            8'h38
`define ASCON_REG_NONCE3            8'h3C
`define ASCON_REG_DATA_IN           8'h40
`define ASCON_REG_DATA_IN_CTRL      8'h44
`define ASCON_REG_DATA_OUT          8'h48
`define ASCON_REG_DATA_OUT_CTRL     8'h4C
`define ASCON_REG_TAG0              8'h60
`define ASCON_REG_TAG1              8'h64
`define ASCON_REG_TAG2              8'h68
`define ASCON_REG_TAG3              8'h6C
`define ASCON_REG_CYCLE_COUNT_LO    8'h70
`define ASCON_REG_CYCLE_COUNT_HI    8'h74
`define ASCON_REG_ERROR_CODE        8'h78
`define ASCON_REG_ABI_VERSION       8'h7C

// CONTROL bit masks.
`define ASCON_CONTROL_START          32'h00000001
`define ASCON_CONTROL_DECRYPT        32'h00000002
`define ASCON_CONTROL_HASH           32'h00000004
`define ASCON_CONTROL_XOF            32'h00000008
`define ASCON_CONTROL_CXOF           32'h00000010
`define ASCON_CONTROL_CLEAR          32'h00000100
`define ASCON_CONTROL_IRQ_ENABLE     32'h00010000

// STATUS bit masks.
`define ASCON_STATUS_BUSY            32'h00000001
`define ASCON_STATUS_DONE            32'h00000002
`define ASCON_STATUS_TAG_VALID       32'h00000004
`define ASCON_STATUS_ERROR           32'h00000008
`define ASCON_STATUS_IN_READY        32'h00000010
`define ASCON_STATUS_OUT_VALID       32'h00000020

// DATA_IN_CTRL / DATA_OUT_CTRL bit masks.
`define ASCON_DATA_LAST              32'h00000001
`define ASCON_DATA_VALID             32'h00000002
`define ASCON_DATA_AD                32'h00000004
`define ASCON_DATA_TEXT              32'h00000008
`define ASCON_DATA_CUSTOM            32'h00000010
`define ASCON_DATA_KEEP_SHIFT   8
`define ASCON_DATA_KEEP_MASK    32'h0000000F

// MODE values.
`define ASCON_MODE_AEAD128     4'd0
`define ASCON_MODE_AEAD128A    4'd1
`define ASCON_MODE_AEAD128PQ   4'd2
`define ASCON_MODE_HASH        4'd3
`define ASCON_MODE_HASHA       4'd4
`define ASCON_MODE_XOF         4'd5
`define ASCON_MODE_XOFA        4'd6
`define ASCON_MODE_CXOF128     4'd7

// CAPABILITIES bit masks.
`define ASCON_CAP_AEAD128                32'h00000001
`define ASCON_CAP_AEAD128A               32'h00000002
`define ASCON_CAP_AEAD128PQ              32'h00000004
`define ASCON_CAP_HASH                   32'h00000008
`define ASCON_CAP_HASHA                  32'h00000010
`define ASCON_CAP_XOF                    32'h00000020
`define ASCON_CAP_XOFA                   32'h00000040
`define ASCON_CAP_CXOF128                32'h00000080
`define ASCON_CAP_DECRYPT_BUFFERED       32'h00010000
`define ASCON_CAP_CONSTTIME_TAG_COMPARE  32'h00020000
`define ASCON_CAP_RAND_COUNTER_HARDENING 32'h00040000
`define ASCON_CAP_FAULT_DETECTION        32'h00080000
`define ASCON_CAP_STREAMING_BYTEMASK     32'h00100000
`define ASCON_CAP_CYCLE_COUNTER          32'h00200000
`define ASCON_CAP_AXI_STREAM_DATA        32'h00400000

// ERROR_CODE values.
`define ASCON_ERROR_NONE               32'd0
`define ASCON_ERROR_UNSUPPORTED_MODE   32'd1
`define ASCON_ERROR_BAD_LENGTH         32'd2
`define ASCON_ERROR_STREAM_PROTOCOL    32'd3
`define ASCON_ERROR_TAG_INVALID        32'd4
`define ASCON_ERROR_FAULT_DETECTED     32'd5

`endif
