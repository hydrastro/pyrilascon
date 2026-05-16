`include "ascon_accel_regs.vh"
`include "ascon_accel_axis_defs.vh"

module tangnano9k_ascon_aead128_axis128_4rpc_top(
  input  wire clk,
  input  wire rst_n,
  output wire [5:0] led
);
  reg [23:0] heartbeat_q;
  reg [7:0]  state_q;
  reg [5:0]  op_idx_q;
  reg [3:0]  rd_idx_q;
  reg        enc_pass_q;
  reg        dec_pass_q;
  reg        fail_q;
  reg        done_q;

  reg         bus_valid_r;
  reg         bus_write_r;
  reg [7:0]   bus_addr_r;
  reg [31:0]  bus_wdata_r;
  wire [31:0] bus_rdata_w;
  wire        bus_ready_w;
  wire        irq_w;

  reg [127:0] s_axis_tdata_r;
  reg [15:0]  s_axis_tkeep_r;
  reg         s_axis_tvalid_r;
  reg         s_axis_tlast_r;
  reg [3:0]   s_axis_tuser_r;
  wire        s_axis_tready_w;

  wire [127:0] m_axis_tdata_w;
  wire [15:0]  m_axis_tkeep_w;
  wire         m_axis_tvalid_w;
  reg          m_axis_tready_r;
  wire         m_axis_tlast_w;
  wire [3:0]   m_axis_tuser_w;

  localparam [7:0] ST_RESET        = 8'd0;
  localparam [7:0] ST_ENC_CFG      = 8'd1;
  localparam [7:0] ST_ENC_STREAM   = 8'd2;
  localparam [7:0] ST_ENC_START    = 8'd3;
  localparam [7:0] ST_ENC_POLL     = 8'd4;
  localparam [7:0] ST_ENC_READ_CT  = 8'd5;
  localparam [7:0] ST_ENC_READ_TAG = 8'd6;
  localparam [7:0] ST_DEC_CFG      = 8'd7;
  localparam [7:0] ST_DEC_STREAM   = 8'd8;
  localparam [7:0] ST_DEC_START    = 8'd9;
  localparam [7:0] ST_DEC_POLL     = 8'd10;
  localparam [7:0] ST_DEC_READ_PT  = 8'd11;
  localparam [7:0] ST_DONE         = 8'd12;

  localparam [5:0] ENC_CFG_OPS = 6'd14;
  localparam [5:0] DEC_CFG_OPS = 6'd18;
  localparam [5:0] STREAM_OPS  = 6'd3;
  localparam [3:0] TEXT_BEATS  = 4'd2;

  function [7:0] cfg_addr;
    input [5:0] idx;
    begin
      case (idx)
        6'd0:  cfg_addr = `ASCON_REG_CONTROL;
        6'd1:  cfg_addr = `ASCON_REG_MODE;
        6'd2:  cfg_addr = `ASCON_REG_AD_LEN;
        6'd3:  cfg_addr = `ASCON_REG_TEXT_LEN;
        6'd4:  cfg_addr = `ASCON_REG_OUT_LEN;
        6'd5:  cfg_addr = `ASCON_REG_CUSTOM_LEN;
        6'd6:  cfg_addr = `ASCON_REG_KEY0;
        6'd7:  cfg_addr = `ASCON_REG_KEY1;
        6'd8:  cfg_addr = `ASCON_REG_KEY2;
        6'd9:  cfg_addr = `ASCON_REG_KEY3;
        6'd10: cfg_addr = `ASCON_REG_NONCE0;
        6'd11: cfg_addr = `ASCON_REG_NONCE1;
        6'd12: cfg_addr = `ASCON_REG_NONCE2;
        6'd13: cfg_addr = `ASCON_REG_NONCE3;
        default: cfg_addr = `ASCON_REG_CONTROL;
      endcase
    end
  endfunction

  function [31:0] cfg_data;
    input [5:0] idx;
    begin
      case (idx)
        6'd0:  cfg_data = `ASCON_CONTROL_CLEAR;
        6'd1:  cfg_data = `ASCON_MODE_AEAD128;
        6'd2:  cfg_data = 32'd5;
        6'd3:  cfg_data = 32'd26;
        6'd4:  cfg_data = 32'd0;
        6'd5:  cfg_data = 32'd0;
        6'd6:  cfg_data = 32'h03020100;
        6'd7:  cfg_data = 32'h07060504;
        6'd8:  cfg_data = 32'h0b0a0908;
        6'd9:  cfg_data = 32'h0f0e0d0c;
        6'd10: cfg_data = 32'h13121110;
        6'd11: cfg_data = 32'h17161514;
        6'd12: cfg_data = 32'h1b1a1918;
        6'd13: cfg_data = 32'h1f1e1d1c;
        default: cfg_data = 32'h00000000;
      endcase
    end
  endfunction

  function [7:0] dec_cfg_addr;
    input [5:0] idx;
    begin
      if (idx < ENC_CFG_OPS) begin
        dec_cfg_addr = cfg_addr(idx);
      end else begin
        case (idx)
          6'd14: dec_cfg_addr = `ASCON_REG_TAG0;
          6'd15: dec_cfg_addr = `ASCON_REG_TAG1;
          6'd16: dec_cfg_addr = `ASCON_REG_TAG2;
          6'd17: dec_cfg_addr = `ASCON_REG_TAG3;
          default: dec_cfg_addr = `ASCON_REG_CONTROL;
        endcase
      end
    end
  endfunction

  function [31:0] dec_cfg_data;
    input [5:0] idx;
    begin
      if (idx < ENC_CFG_OPS) begin
        dec_cfg_data = cfg_data(idx);
      end else begin
        case (idx)
          6'd14: dec_cfg_data = 32'hab66db04;
          6'd15: dec_cfg_data = 32'h1f10d2df;
          6'd16: dec_cfg_data = 32'hab4ff809;
          6'd17: dec_cfg_data = 32'h91fadaf6;
          default: dec_cfg_data = 32'h00000000;
        endcase
      end
    end
  endfunction

  function [127:0] enc_stream_data;
    input [5:0] idx;
    begin
      case (idx)
        6'd0: enc_stream_data = 128'h00000000000000000000003332314441; // AD123
        6'd1: enc_stream_data = 128'h64726168204e4f435341206f6c6c6568; // first 16 PT bytes
        6'd2: enc_stream_data = 128'h0000000000006c65646f6d2065726177; // final 10 PT bytes
        default: enc_stream_data = 128'h0;
      endcase
    end
  endfunction

  function [127:0] dec_stream_data;
    input [5:0] idx;
    begin
      case (idx)
        6'd0: dec_stream_data = 128'h00000000000000000000003332314441;
        6'd1: dec_stream_data = 128'h359947c8b877a859abebb16de8e5d595;
        6'd2: dec_stream_data = 128'h000000000000e3ad96765b1455538ea8;
        default: dec_stream_data = 128'h0;
      endcase
    end
  endfunction

  function [15:0] stream_keep;
    input [5:0] idx;
    begin
      case (idx)
        6'd0: stream_keep = 16'h001f;
        6'd1: stream_keep = 16'hffff;
        6'd2: stream_keep = 16'h03ff;
        default: stream_keep = 16'h0000;
      endcase
    end
  endfunction

  function stream_last;
    input [5:0] idx;
    begin
      stream_last = (idx == 6'd0) || (idx == 6'd2);
    end
  endfunction

  function [3:0] stream_user;
    input [5:0] idx;
    begin
      stream_user = (idx == 6'd0) ? `ASCON_AXIS_USER_AD : `ASCON_AXIS_USER_TEXT;
    end
  endfunction

  function [127:0] expected_ct_beat;
    input [3:0] idx;
    begin
      case (idx)
        4'd0: expected_ct_beat = 128'h359947c8b877a859abebb16de8e5d595;
        4'd1: expected_ct_beat = 128'h000000000000e3ad96765b1455538ea8;
        default: expected_ct_beat = 128'h0;
      endcase
    end
  endfunction

  function [127:0] expected_pt_beat;
    input [3:0] idx;
    begin
      case (idx)
        4'd0: expected_pt_beat = 128'h64726168204e4f435341206f6c6c6568;
        4'd1: expected_pt_beat = 128'h0000000000006c65646f6d2065726177;
        default: expected_pt_beat = 128'h0;
      endcase
    end
  endfunction

  function [15:0] expected_keep;
    input [3:0] idx;
    begin
      expected_keep = (idx == 4'd0) ? 16'hffff : 16'h03ff;
    end
  endfunction

  function [31:0] expected_tag_word;
    input [3:0] idx;
    begin
      case (idx)
        4'd0: expected_tag_word = 32'hab66db04;
        4'd1: expected_tag_word = 32'h1f10d2df;
        4'd2: expected_tag_word = 32'hab4ff809;
        4'd3: expected_tag_word = 32'h91fadaf6;
        default: expected_tag_word = 32'h00000000;
      endcase
    end
  endfunction

  ascon_accel_axis128_aead128_4rpc_top dut_i (
    .clk_i(clk),
    .rstn_i(rst_n),
    .bus_valid_i(bus_valid_r),
    .bus_write_i(bus_write_r),
    .bus_addr_i(bus_addr_r),
    .bus_wdata_i(bus_wdata_r),
    .bus_wstrb_i(4'hf),
    .bus_rdata_o(bus_rdata_w),
    .bus_ready_o(bus_ready_w),
    .irq_o(irq_w),
    .s_axis_tdata(s_axis_tdata_r),
    .s_axis_tkeep(s_axis_tkeep_r),
    .s_axis_tvalid(s_axis_tvalid_r),
    .s_axis_tready(s_axis_tready_w),
    .s_axis_tlast(s_axis_tlast_r),
    .s_axis_tuser(s_axis_tuser_r),
    .m_axis_tdata(m_axis_tdata_w),
    .m_axis_tkeep(m_axis_tkeep_w),
    .m_axis_tvalid(m_axis_tvalid_w),
    .m_axis_tready(m_axis_tready_r),
    .m_axis_tlast(m_axis_tlast_w),
    .m_axis_tuser(m_axis_tuser_w)
  );

  always @* begin
    bus_valid_r = 1'b0;
    bus_write_r = 1'b0;
    bus_addr_r = `ASCON_REG_STATUS;
    bus_wdata_r = 32'h00000000;
    s_axis_tdata_r = 128'h0;
    s_axis_tkeep_r = 16'h0000;
    s_axis_tvalid_r = 1'b0;
    s_axis_tlast_r = 1'b0;
    s_axis_tuser_r = `ASCON_AXIS_USER_NONE;
    m_axis_tready_r = 1'b0;

    case (state_q)
      ST_ENC_CFG: begin
        bus_valid_r = 1'b1;
        bus_write_r = 1'b1;
        bus_addr_r = cfg_addr(op_idx_q);
        bus_wdata_r = cfg_data(op_idx_q);
      end
      ST_ENC_STREAM: begin
        s_axis_tvalid_r = 1'b1;
        s_axis_tdata_r = enc_stream_data(op_idx_q);
        s_axis_tkeep_r = stream_keep(op_idx_q);
        s_axis_tlast_r = stream_last(op_idx_q);
        s_axis_tuser_r = stream_user(op_idx_q);
      end
      ST_ENC_START: begin
        bus_valid_r = 1'b1;
        bus_write_r = 1'b1;
        bus_addr_r = `ASCON_REG_CONTROL;
        bus_wdata_r = `ASCON_CONTROL_START;
      end
      ST_ENC_POLL, ST_DEC_POLL: begin
        bus_valid_r = 1'b1;
        bus_write_r = 1'b0;
        bus_addr_r = `ASCON_REG_STATUS;
      end
      ST_ENC_READ_CT, ST_DEC_READ_PT: begin
        m_axis_tready_r = 1'b1;
      end
      ST_ENC_READ_TAG: begin
        bus_valid_r = 1'b1;
        bus_write_r = 1'b0;
        case (rd_idx_q)
          4'd0: bus_addr_r = `ASCON_REG_TAG0;
          4'd1: bus_addr_r = `ASCON_REG_TAG1;
          4'd2: bus_addr_r = `ASCON_REG_TAG2;
          default: bus_addr_r = `ASCON_REG_TAG3;
        endcase
      end
      ST_DEC_CFG: begin
        bus_valid_r = 1'b1;
        bus_write_r = 1'b1;
        bus_addr_r = dec_cfg_addr(op_idx_q);
        bus_wdata_r = dec_cfg_data(op_idx_q);
      end
      ST_DEC_STREAM: begin
        s_axis_tvalid_r = 1'b1;
        s_axis_tdata_r = dec_stream_data(op_idx_q);
        s_axis_tkeep_r = stream_keep(op_idx_q);
        s_axis_tlast_r = stream_last(op_idx_q);
        s_axis_tuser_r = stream_user(op_idx_q);
      end
      ST_DEC_START: begin
        bus_valid_r = 1'b1;
        bus_write_r = 1'b1;
        bus_addr_r = `ASCON_REG_CONTROL;
        bus_wdata_r = `ASCON_CONTROL_START | `ASCON_CONTROL_DECRYPT;
      end
      default: begin
      end
    endcase
  end

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      heartbeat_q <= 24'd0;
      state_q <= ST_RESET;
      op_idx_q <= 6'd0;
      rd_idx_q <= 4'd0;
      enc_pass_q <= 1'b0;
      dec_pass_q <= 1'b0;
      fail_q <= 1'b0;
      done_q <= 1'b0;
    end else begin
      heartbeat_q <= heartbeat_q + 24'd1;

      case (state_q)
        ST_RESET: begin
          op_idx_q <= 6'd0;
          rd_idx_q <= 4'd0;
          enc_pass_q <= 1'b0;
          dec_pass_q <= 1'b0;
          fail_q <= 1'b0;
          done_q <= 1'b0;
          state_q <= ST_ENC_CFG;
        end

        ST_ENC_CFG: begin
          if (op_idx_q == ENC_CFG_OPS - 1) begin
            op_idx_q <= 6'd0;
            state_q <= ST_ENC_STREAM;
          end else begin
            op_idx_q <= op_idx_q + 6'd1;
          end
        end

        ST_ENC_STREAM: begin
          if (s_axis_tready_w) begin
            if (op_idx_q == STREAM_OPS - 1) begin
              op_idx_q <= 6'd0;
              state_q <= ST_ENC_START;
            end else begin
              op_idx_q <= op_idx_q + 6'd1;
            end
          end
        end

        ST_ENC_START: begin
          state_q <= ST_ENC_POLL;
        end

        ST_ENC_POLL: begin
          if ((bus_rdata_w & `ASCON_STATUS_ERROR) != 32'h0) begin
            fail_q <= 1'b1;
            state_q <= ST_DONE;
          end else if ((bus_rdata_w & `ASCON_STATUS_DONE) != 32'h0) begin
            rd_idx_q <= 4'd0;
            state_q <= ST_ENC_READ_CT;
          end
        end

        ST_ENC_READ_CT: begin
          if (m_axis_tvalid_w) begin
            if ((m_axis_tuser_w != `ASCON_AXIS_USER_TEXT) ||
                ((m_axis_tdata_w & {{96{1'b1}}, 32'hffff_ffff}) != (expected_ct_beat(rd_idx_q) & (rd_idx_q == 0 ? 128'hffff_ffff_ffff_ffff_ffff_ffff_ffff_ffff : 128'h0000_0000_0000_ffff_ffff_ffff_ffff_ffff))) ||
                (m_axis_tkeep_w != expected_keep(rd_idx_q))) begin
              fail_q <= 1'b1;
            end
            if ((rd_idx_q == TEXT_BEATS - 1) || m_axis_tlast_w) begin
              rd_idx_q <= 4'd0;
              state_q <= ST_ENC_READ_TAG;
            end else begin
              rd_idx_q <= rd_idx_q + 4'd1;
            end
          end
        end

        ST_ENC_READ_TAG: begin
          if (bus_rdata_w != expected_tag_word(rd_idx_q)) begin
            fail_q <= 1'b1;
          end
          if (rd_idx_q == 4'd3) begin
            enc_pass_q <= ~fail_q;
            op_idx_q <= 6'd0;
            rd_idx_q <= 4'd0;
            state_q <= ST_DEC_CFG;
          end else begin
            rd_idx_q <= rd_idx_q + 4'd1;
          end
        end

        ST_DEC_CFG: begin
          if (op_idx_q == DEC_CFG_OPS - 1) begin
            op_idx_q <= 6'd0;
            state_q <= ST_DEC_STREAM;
          end else begin
            op_idx_q <= op_idx_q + 6'd1;
          end
        end

        ST_DEC_STREAM: begin
          if (s_axis_tready_w) begin
            if (op_idx_q == STREAM_OPS - 1) begin
              op_idx_q <= 6'd0;
              state_q <= ST_DEC_START;
            end else begin
              op_idx_q <= op_idx_q + 6'd1;
            end
          end
        end

        ST_DEC_START: begin
          state_q <= ST_DEC_POLL;
        end

        ST_DEC_POLL: begin
          if ((bus_rdata_w & `ASCON_STATUS_ERROR) != 32'h0) begin
            fail_q <= 1'b1;
            state_q <= ST_DONE;
          end else if ((bus_rdata_w & `ASCON_STATUS_DONE) != 32'h0) begin
            if ((bus_rdata_w & `ASCON_STATUS_TAG_VALID) == 32'h0) begin
              fail_q <= 1'b1;
            end
            rd_idx_q <= 4'd0;
            state_q <= ST_DEC_READ_PT;
          end
        end

        ST_DEC_READ_PT: begin
          if (m_axis_tvalid_w) begin
            if ((m_axis_tuser_w != `ASCON_AXIS_USER_TEXT) ||
                ((m_axis_tdata_w & (rd_idx_q == 0 ? 128'hffff_ffff_ffff_ffff_ffff_ffff_ffff_ffff : 128'h0000_0000_0000_ffff_ffff_ffff_ffff_ffff)) !=
                 (expected_pt_beat(rd_idx_q) & (rd_idx_q == 0 ? 128'hffff_ffff_ffff_ffff_ffff_ffff_ffff_ffff : 128'h0000_0000_0000_ffff_ffff_ffff_ffff_ffff))) ||
                (m_axis_tkeep_w != expected_keep(rd_idx_q))) begin
              fail_q <= 1'b1;
            end
            if ((rd_idx_q == TEXT_BEATS - 1) || m_axis_tlast_w) begin
              dec_pass_q <= ~fail_q;
              done_q <= 1'b1;
              state_q <= ST_DONE;
            end else begin
              rd_idx_q <= rd_idx_q + 4'd1;
            end
          end
        end

        ST_DONE: begin
          done_q <= 1'b1;
        end

        default: begin
          state_q <= ST_RESET;
        end
      endcase
    end
  end

  // LEDs are active-low on Tang Nano 9K.
  assign led[0] = ~heartbeat_q[23];
  assign led[1] = ~enc_pass_q;
  assign led[2] = ~dec_pass_q;
  assign led[3] = ~fail_q;
  assign led[4] = ~done_q;
  assign led[5] = ~(done_q & enc_pass_q & dec_pass_q & ~fail_q);
endmodule
