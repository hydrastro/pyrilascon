`ifndef ASCON_AEAD128_STREAM_V
`define ASCON_AEAD128_STREAM_V

`include "ascon_accel_regs.vh"
`include "ascon_accel_axis_defs.vh"

// -----------------------------------------------------------------------------
// Unified AEAD128 AXI Stream backend.
//
// This is the firmware/SoC-facing stream backend wrapper.  It keeps one stable
// top-level module for the frozen control-plane ABI while delegating to the two
// policy-specific implementations:
//   * decrypt_i == 0: unbounded streaming encryption backend;
//   * decrypt_i == 1: buffered authenticated decrypt backend.
//
// Decryption intentionally uses a bounded quarantine buffer because safe AEAD
// decrypt must not expose plaintext until the tag has been verified.  Future DMA
// versions can replace that buffer with an external quarantine region without
// changing the top-level control/data-plane contract used here.
// -----------------------------------------------------------------------------
module ascon_aead128_stream #(
  parameter integer DATA_BYTES     = 16,
  parameter integer DATA_WIDTH     = DATA_BYTES * 8,
  parameter integer MAX_TEXT_BYTES = 1024,
  parameter integer MAX_TEXT_BITS  = MAX_TEXT_BYTES * 8
) (
  input  wire                    clk_i,
  input  wire                    rstn_i,
  input  wire                    start_i,
  input  wire                    clear_i,
  input  wire                    decrypt_i,
  input  wire [3:0]              mode_i,
  input  wire [31:0]             ad_len_i,
  input  wire [31:0]             text_len_i,
  input  wire [31:0]             out_len_i,
  input  wire [31:0]             custom_len_i,
  input  wire [127:0]            key_i,
  input  wire [127:0]            nonce_i,
  input  wire [127:0]            expected_tag_i,

  input  wire [DATA_WIDTH-1:0]   s_axis_tdata,
  input  wire [DATA_BYTES-1:0]   s_axis_tkeep,
  input  wire                    s_axis_tvalid,
  output wire                    s_axis_tready,
  input  wire                    s_axis_tlast,
  input  wire [3:0]              s_axis_tuser,

  output wire [DATA_WIDTH-1:0]   m_axis_tdata,
  output wire [DATA_BYTES-1:0]   m_axis_tkeep,
  output wire                    m_axis_tvalid,
  input  wire                    m_axis_tready,
  output wire                    m_axis_tlast,
  output wire [3:0]              m_axis_tuser,

  output wire                    busy_o,
  output wire                    done_o,
  output wire                    tag_valid_o,
  output wire                    error_o,
  output wire [31:0]             error_code_o,
  output wire [127:0]            generated_tag_o
);

  reg op_decrypt_q;

  wire start_encrypt_w;
  wire start_decrypt_w;

  wire enc_s_axis_tready_w;
  wire [DATA_WIDTH-1:0] enc_m_axis_tdata_w;
  wire [DATA_BYTES-1:0] enc_m_axis_tkeep_w;
  wire enc_m_axis_tvalid_w;
  wire enc_m_axis_tlast_w;
  wire [3:0] enc_m_axis_tuser_w;
  wire enc_busy_w;
  wire enc_done_w;
  wire enc_tag_valid_w;
  wire enc_error_w;
  wire [31:0] enc_error_code_w;
  wire [127:0] enc_generated_tag_w;

  wire dec_s_axis_tready_w;
  wire [DATA_WIDTH-1:0] dec_m_axis_tdata_w;
  wire [DATA_BYTES-1:0] dec_m_axis_tkeep_w;
  wire dec_m_axis_tvalid_w;
  wire dec_m_axis_tlast_w;
  wire [3:0] dec_m_axis_tuser_w;
  wire dec_busy_w;
  wire dec_done_w;
  wire dec_tag_valid_w;
  wire dec_error_w;
  wire [31:0] dec_error_code_w;
  wire [127:0] dec_generated_tag_w;

  assign start_encrypt_w = start_i && !decrypt_i;
  assign start_decrypt_w = start_i && decrypt_i;

  always @(posedge clk_i or negedge rstn_i) begin
    if (!rstn_i) begin
      op_decrypt_q <= 1'b0;
    end else if (clear_i) begin
      op_decrypt_q <= 1'b0;
    end else if (start_i) begin
      op_decrypt_q <= decrypt_i;
    end
  end

  ascon_aead128_stream_encrypt #(
    .DATA_BYTES(DATA_BYTES),
    .DATA_WIDTH(DATA_WIDTH)
  ) encrypt_i (
    .clk_i(clk_i),
    .rstn_i(rstn_i),
    .start_i(start_encrypt_w),
    .clear_i(clear_i),
    .decrypt_i(1'b0),
    .mode_i(mode_i),
    .ad_len_i(ad_len_i),
    .text_len_i(text_len_i),
    .out_len_i(out_len_i),
    .custom_len_i(custom_len_i),
    .key_i(key_i),
    .nonce_i(nonce_i),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tkeep(s_axis_tkeep),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(enc_s_axis_tready_w),
    .s_axis_tlast(s_axis_tlast),
    .s_axis_tuser(s_axis_tuser),
    .m_axis_tdata(enc_m_axis_tdata_w),
    .m_axis_tkeep(enc_m_axis_tkeep_w),
    .m_axis_tvalid(enc_m_axis_tvalid_w),
    .m_axis_tready(m_axis_tready),
    .m_axis_tlast(enc_m_axis_tlast_w),
    .m_axis_tuser(enc_m_axis_tuser_w),
    .busy_o(enc_busy_w),
    .done_o(enc_done_w),
    .tag_valid_o(enc_tag_valid_w),
    .error_o(enc_error_w),
    .error_code_o(enc_error_code_w),
    .generated_tag_o(enc_generated_tag_w)
  );

  ascon_aead128_stream_decrypt_buffered #(
    .DATA_BYTES(DATA_BYTES),
    .DATA_WIDTH(DATA_WIDTH),
    .MAX_TEXT_BYTES(MAX_TEXT_BYTES),
    .MAX_TEXT_BITS(MAX_TEXT_BITS)
  ) decrypt_buffered_i (
    .clk_i(clk_i),
    .rstn_i(rstn_i),
    .start_i(start_decrypt_w),
    .clear_i(clear_i),
    .decrypt_i(1'b1),
    .mode_i(mode_i),
    .ad_len_i(ad_len_i),
    .text_len_i(text_len_i),
    .out_len_i(out_len_i),
    .custom_len_i(custom_len_i),
    .key_i(key_i),
    .nonce_i(nonce_i),
    .expected_tag_i(expected_tag_i),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tkeep(s_axis_tkeep),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(dec_s_axis_tready_w),
    .s_axis_tlast(s_axis_tlast),
    .s_axis_tuser(s_axis_tuser),
    .m_axis_tdata(dec_m_axis_tdata_w),
    .m_axis_tkeep(dec_m_axis_tkeep_w),
    .m_axis_tvalid(dec_m_axis_tvalid_w),
    .m_axis_tready(m_axis_tready),
    .m_axis_tlast(dec_m_axis_tlast_w),
    .m_axis_tuser(dec_m_axis_tuser_w),
    .busy_o(dec_busy_w),
    .done_o(dec_done_w),
    .tag_valid_o(dec_tag_valid_w),
    .error_o(dec_error_w),
    .error_code_o(dec_error_code_w),
    .generated_tag_o(dec_generated_tag_w)
  );

  assign s_axis_tready = op_decrypt_q ? dec_s_axis_tready_w : enc_s_axis_tready_w;

  assign m_axis_tdata  = op_decrypt_q ? dec_m_axis_tdata_w  : enc_m_axis_tdata_w;
  assign m_axis_tkeep  = op_decrypt_q ? dec_m_axis_tkeep_w  : enc_m_axis_tkeep_w;
  assign m_axis_tvalid = op_decrypt_q ? dec_m_axis_tvalid_w : enc_m_axis_tvalid_w;
  assign m_axis_tlast  = op_decrypt_q ? dec_m_axis_tlast_w  : enc_m_axis_tlast_w;
  assign m_axis_tuser  = op_decrypt_q ? dec_m_axis_tuser_w  : enc_m_axis_tuser_w;

  assign busy_o          = op_decrypt_q ? dec_busy_w          : enc_busy_w;
  assign done_o          = op_decrypt_q ? dec_done_w          : enc_done_w;
  assign tag_valid_o     = op_decrypt_q ? dec_tag_valid_w     : enc_tag_valid_w;
  assign error_o         = op_decrypt_q ? dec_error_w         : enc_error_w;
  assign error_code_o    = op_decrypt_q ? dec_error_code_w    : enc_error_code_w;
  assign generated_tag_o = op_decrypt_q ? dec_generated_tag_w : enc_generated_tag_w;

endmodule

`endif // ASCON_AEAD128_STREAM_V
