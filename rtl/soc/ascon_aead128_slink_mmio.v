// ---------------------------------------------------------------------------
// ascon_aead128_slink_mmio
//
// The stream-native face of the Ascon-AEAD128 accelerator.
//
// Split of concerns
// -----------------
//   * CONTROL  travels over the CPU bus: key, nonce, lengths, start, tag, status.
//     A handful of accesses per operation -- their cost is irrelevant.
//   * PAYLOAD  travels over AXI4-Stream, fed by NEORV32's SLINK, which in turn is
//     fed by the DMA. The CPU never touches a payload byte.
//
// This is the whole point of the design. In the MMIO variant the stream's
// tvalid was driven by a CPU store (`s_tvalid = din_ctl_wr`), so every 4 bytes
// cost two bus transactions and the accelerator spent ~98% of its busy time
// waiting. Here tvalid comes from SLINK, so a beat can be accepted every cycle.
//
// Register map (byte offsets) -- a strict subset of the MMIO variant, minus the
// data-movement registers, which no longer exist:
//   0x00 CONTROL   START=1<<0, DECRYPT=1<<1, CLEAR=1<<8
//   0x04 STATUS    BUSY=1<<0, DONE=1<<1, TAGVALID=1<<2, ERR=1<<3
//   0x08 MODE
//   0x0C CAPABILITIES  AEAD128 | CYCLE_COUNTER | AXI_STREAM | SLINK_DATA_PLANE
//   0x10 AD_LEN    0x14 TEXT_LEN
//   0x20..0x2C KEY0..3      0x30..0x3C NONCE0..3
//   0x60..0x6C TAG0..3      0x70/0x74 CYCLE_COUNT lo/hi
//   0x78 ERROR     0x7C ABI
// ---------------------------------------------------------------------------
`default_nettype none

module ascon_aead128_slink_mmio #(
  parameter AD_MAX  = 32,
  parameter MSG_MAX = 32
) (
  input  wire        clk,
  input  wire        rst_n,

  // register interface (same shape as ascon_aead128_axis_mmio, so the existing
  // Wishbone/XBUS adapter is reused unchanged)
  input  wire        sel,
  input  wire        we,
  input  wire [7:0]  addr,
  input  wire [31:0] wdata,
  output reg  [31:0] rdata,
  output wire        ready,

  // NEORV32 SLINK TX -> accelerator payload in
  input  wire [31:0] slink_tx_dat_i,
  input  wire        slink_tx_val_i,
  output wire        slink_tx_rdy_o,

  // accelerator payload out -> NEORV32 SLINK RX
  output wire [31:0] slink_rx_dat_o,
  output wire        slink_rx_val_o,
  input  wire        slink_rx_rdy_i,
  output wire        slink_rx_lst_o,
  output wire [3:0]  slink_rx_src_o    // carries m_tkeep (informational)
);

  localparam [7:0] A_CONTROL=8'h00, A_STATUS=8'h04, A_MODE=8'h08, A_CAPS=8'h0C,
                   A_ADLEN=8'h10, A_TXTLEN=8'h14,
                   A_KEY0=8'h20, A_KEY1=8'h24, A_KEY2=8'h28, A_KEY3=8'h2C,
                   A_NON0=8'h30, A_NON1=8'h34, A_NON2=8'h38, A_NON3=8'h3C,
                   A_TAG0=8'h60, A_TAG1=8'h64, A_TAG2=8'h68, A_TAG3=8'h6C,
                   A_CYCLO=8'h70, A_CYCHI=8'h74, A_ERR=8'h78, A_ABI=8'h7C;

  localparam CTRL_START=32'h1, CTRL_DECRYPT=32'h2, CTRL_CLEAR=32'h100;
  localparam ST_BUSY=32'h1, ST_DONE=32'h2, ST_TAGV=32'h4, ST_ERR=32'h8;
  localparam ERR_NONE=8'd0, ERR_TAGINVALID=8'd4, ABIV=32'd1;
  // AEAD128 | CYCLE_COUNTER | AXI_STREAM_DATA | SLINK_DATA_PLANE
  localparam CAPBITS=(32'h1 | 32'h200000 | 32'h400000 | 32'h800000);

  reg  [2:0]   mode_r;
  reg  [127:0] key_r, nonce_r, tagin_r, tag_r;
  reg  [7:0]   adlen_r, txtlen_r;
  reg          decrypt_r, busy_r, done_r, tagvalid_r, error_r;
  reg  [7:0]   errcode_r;
  reg  [63:0]  cyc_run, cyc_lat;
  reg          counting, start_pulse;

  // Every register access completes in one cycle: nothing here stalls, because
  // nothing here moves payload.
  assign ready = 1'b1;

  // ---- shim: SLINK word stream -> tagged AXI4-Stream --------------------
  wire [31:0] s_tdata;
  wire [3:0]  s_tkeep;
  wire        s_tuser, s_tlast, s_tvalid, s_tready;

  ascon_slink_shim u_shim (
    .clk(clk), .rst_n(rst_n),
    .start_i(start_pulse), .ad_len_i(adlen_r), .msg_len_i(txtlen_r),
    .slink_dat_i(slink_tx_dat_i), .slink_val_i(slink_tx_val_i),
    .slink_rdy_o(slink_tx_rdy_o),
    .s_tdata(s_tdata), .s_tkeep(s_tkeep), .s_tuser(s_tuser),
    .s_tlast(s_tlast), .s_tvalid(s_tvalid), .s_tready(s_tready)
  );

  // ---- the verified stream-native engine --------------------------------
  wire [31:0]  m_tdata;
  wire [3:0]   m_tkeep;
  wire         m_tlast, m_tvalid;
  wire [127:0] eng_tag;
  wire         eng_valid, eng_done, eng_busy;

  ascon_aead128_axis #(.AD_MAX(AD_MAX), .MSG_MAX(MSG_MAX)) u_eng (
    .clk(clk), .rst_n(rst_n), .start_i(start_pulse), .decrypt_i(decrypt_r),
    .key_i(key_r), .nonce_i(nonce_r), .ad_len_i(adlen_r), .msg_len_i(txtlen_r),
    .tag_i(tagin_r),
    .s_tdata(s_tdata), .s_tkeep(s_tkeep), .s_tuser(s_tuser), .s_tlast(s_tlast),
    .s_tvalid(s_tvalid), .s_tready(s_tready),
    .m_tdata(m_tdata), .m_tkeep(m_tkeep), .m_tlast(m_tlast),
    .m_tvalid(m_tvalid), .m_tready(slink_rx_rdy_i),
    .tag_o(eng_tag), .valid_o(eng_valid), .done_o(eng_done), .busy_o(eng_busy)
  );

  // ---- payload out straight to SLINK RX ---------------------------------
  // Note the back-pressure path: the engine stalls in its TX state until SLINK
  // accepts each beat, so the RX FIFO must be at least MSG_MAX/4 words deep or
  // an unread FIFO would stall the engine before it can raise done.
  assign slink_rx_dat_o = m_tdata;
  assign slink_rx_val_o = m_tvalid;
  assign slink_rx_lst_o = m_tlast;
  assign slink_rx_src_o = m_tkeep;

  // ---- register reads ---------------------------------------------------
  always @(*) begin
    case (addr)
      A_STATUS:  rdata = (busy_r?ST_BUSY:0) | (done_r?ST_DONE:0) |
                         (tagvalid_r?ST_TAGV:0) | (error_r?ST_ERR:0);
      A_CAPS:    rdata = CAPBITS;
      A_MODE:    rdata = {29'b0, mode_r};
      A_ADLEN:   rdata = {24'b0, adlen_r};
      A_TXTLEN:  rdata = {24'b0, txtlen_r};
      A_KEY0:    rdata = key_r[31:0];    A_KEY1: rdata = key_r[63:32];
      A_KEY2:    rdata = key_r[95:64];   A_KEY3: rdata = key_r[127:96];
      A_NON0:    rdata = nonce_r[31:0];  A_NON1: rdata = nonce_r[63:32];
      A_NON2:    rdata = nonce_r[95:64]; A_NON3: rdata = nonce_r[127:96];
      A_TAG0:    rdata = tag_r[31:0];    A_TAG1: rdata = tag_r[63:32];
      A_TAG2:    rdata = tag_r[95:64];   A_TAG3: rdata = tag_r[127:96];
      A_CYCLO:   rdata = cyc_lat[31:0];
      A_CYCHI:   rdata = cyc_lat[63:32];
      A_ERR:     rdata = {24'b0, errcode_r};
      A_ABI:     rdata = ABIV;
      default:   rdata = 32'b0;
    endcase
  end

  // ---- register writes + engine bookkeeping ------------------------------
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      mode_r<=0; key_r<=0; nonce_r<=0; tagin_r<=0; tag_r<=0;
      adlen_r<=0; txtlen_r<=0;
      decrypt_r<=0; busy_r<=0; done_r<=0; tagvalid_r<=0; error_r<=0; errcode_r<=0;
      cyc_run<=0; cyc_lat<=0; counting<=0; start_pulse<=0;
    end else begin
      start_pulse <= 1'b0;
      if (counting) cyc_run <= cyc_run + 64'd1;

      if (eng_done) begin
        done_r <= 1'b1; tag_r <= eng_tag; busy_r <= 1'b0;
        counting <= 1'b0; cyc_lat <= cyc_run;
        if (decrypt_r && !eng_valid) begin
          error_r <= 1'b1; errcode_r <= ERR_TAGINVALID; tagvalid_r <= 1'b0;
        end else begin
          tagvalid_r <= 1'b1; errcode_r <= ERR_NONE;
        end
      end

      if (sel & we) begin
        case (addr)
          A_MODE:   mode_r   <= wdata[2:0];
          A_ADLEN:  adlen_r  <= wdata[7:0];
          A_TXTLEN: txtlen_r <= wdata[7:0];
          A_KEY0: key_r[31:0]<=wdata;   A_KEY1: key_r[63:32]<=wdata;
          A_KEY2: key_r[95:64]<=wdata;  A_KEY3: key_r[127:96]<=wdata;
          A_NON0: nonce_r[31:0]<=wdata; A_NON1: nonce_r[63:32]<=wdata;
          A_NON2: nonce_r[95:64]<=wdata;A_NON3: nonce_r[127:96]<=wdata;
          A_TAG0: tagin_r[31:0]<=wdata; A_TAG1: tagin_r[63:32]<=wdata;
          A_TAG2: tagin_r[95:64]<=wdata;A_TAG3: tagin_r[127:96]<=wdata;
          A_CONTROL: begin
            if (wdata & CTRL_CLEAR) begin
              busy_r<=0; done_r<=0; tagvalid_r<=0; error_r<=0; errcode_r<=0;
              counting<=0;
            end
            if (wdata & CTRL_START) begin
              decrypt_r   <= (wdata & CTRL_DECRYPT) ? 1'b1 : 1'b0;
              start_pulse <= 1'b1;
              busy_r      <= 1'b1; done_r <= 0; tagvalid_r <= 0; error_r <= 0;
              errcode_r   <= ERR_NONE;
              cyc_run     <= 0; counting <= 1'b1;
            end
          end
          default: ;
        endcase
      end
    end
  end

  // Tie off signals the engine exposes but this wrapper does not surface.
  wire _unused = &{eng_busy, 1'b0};

endmodule

`default_nettype wire
