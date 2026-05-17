`include "ascon_accel_regs.vh"

module tangnano9k_ascon_aead128_mmio_slow_top(
  input  wire clk,
  input  wire rst_n,
  output wire [5:0] led
);
  reg [23:0] heartbeat_q;
  reg [6:0] state_q;
  reg [5:0] op_idx_q;
  reg [3:0] rd_idx_q;
  reg enc_pass_q;
  reg dec_pass_q;
  reg fail_q;
  reg done_q;
  reg activity_q;

  reg         bus_valid_r;
  reg         bus_write_r;
  reg [7:0]   bus_addr_r;
  reg [31:0]  bus_wdata_r;
  wire [31:0] bus_rdata_w;
  wire        bus_ready_w;
  wire        irq_w;

  localparam [6:0] ST_RESET        = 7'd0;
  localparam [6:0] ST_ENC_SETUP    = 7'd1;
  localparam [6:0] ST_ENC_POLL     = 7'd2;
  localparam [6:0] ST_ENC_READ_CT  = 7'd3;
  localparam [6:0] ST_ENC_READ_TAG = 7'd4;
  localparam [6:0] ST_DEC_SETUP    = 7'd5;
  localparam [6:0] ST_DEC_POLL     = 7'd6;
  localparam [6:0] ST_DEC_READ_PT  = 7'd7;
  localparam [6:0] ST_DONE         = 7'd8;

  localparam [5:0] ENC_OPS = 6'd33;
  localparam [5:0] DEC_OPS = 6'd37;

  function [31:0] data_ctrl;
    input is_last;
    input [3:0] keep;
    input [31:0] kind;
    begin
      data_ctrl = `ASCON_DATA_VALID | kind | ({28'h0000000, keep} << `ASCON_DATA_KEEP_SHIFT);
      if (is_last) begin
        data_ctrl = data_ctrl | `ASCON_DATA_LAST;
      end
    end
  endfunction

  function [7:0] enc_addr;
    input [5:0] idx;
    begin
      case (idx)
        6'd0:  enc_addr = `ASCON_REG_CONTROL;
        6'd1:  enc_addr = `ASCON_REG_MODE;
        6'd2:  enc_addr = `ASCON_REG_AD_LEN;
        6'd3:  enc_addr = `ASCON_REG_TEXT_LEN;
        6'd4:  enc_addr = `ASCON_REG_OUT_LEN;
        6'd5:  enc_addr = `ASCON_REG_CUSTOM_LEN;
        6'd6:  enc_addr = `ASCON_REG_KEY0;
        6'd7:  enc_addr = `ASCON_REG_KEY1;
        6'd8:  enc_addr = `ASCON_REG_KEY2;
        6'd9:  enc_addr = `ASCON_REG_KEY3;
        6'd10: enc_addr = `ASCON_REG_NONCE0;
        6'd11: enc_addr = `ASCON_REG_NONCE1;
        6'd12: enc_addr = `ASCON_REG_NONCE2;
        6'd13: enc_addr = `ASCON_REG_NONCE3;
        6'd14: enc_addr = `ASCON_REG_DATA_IN;
        6'd15: enc_addr = `ASCON_REG_DATA_IN_CTRL;
        6'd16: enc_addr = `ASCON_REG_DATA_IN;
        6'd17: enc_addr = `ASCON_REG_DATA_IN_CTRL;
        6'd18: enc_addr = `ASCON_REG_DATA_IN;
        6'd19: enc_addr = `ASCON_REG_DATA_IN_CTRL;
        6'd20: enc_addr = `ASCON_REG_DATA_IN;
        6'd21: enc_addr = `ASCON_REG_DATA_IN_CTRL;
        6'd22: enc_addr = `ASCON_REG_DATA_IN;
        6'd23: enc_addr = `ASCON_REG_DATA_IN_CTRL;
        6'd24: enc_addr = `ASCON_REG_DATA_IN;
        6'd25: enc_addr = `ASCON_REG_DATA_IN_CTRL;
        6'd26: enc_addr = `ASCON_REG_DATA_IN;
        6'd27: enc_addr = `ASCON_REG_DATA_IN_CTRL;
        6'd28: enc_addr = `ASCON_REG_DATA_IN;
        6'd29: enc_addr = `ASCON_REG_DATA_IN_CTRL;
        6'd30: enc_addr = `ASCON_REG_DATA_IN;
        6'd31: enc_addr = `ASCON_REG_DATA_IN_CTRL;
        6'd32: enc_addr = `ASCON_REG_CONTROL;
        default: enc_addr = `ASCON_REG_CONTROL;
      endcase
    end
  endfunction

  function [31:0] enc_data;
    input [5:0] idx;
    begin
      case (idx)
        6'd0:  enc_data = `ASCON_CONTROL_CLEAR;
        6'd1:  enc_data = `ASCON_MODE_AEAD128;
        6'd2:  enc_data = 32'd5;
        6'd3:  enc_data = 32'd26;
        6'd4:  enc_data = 32'd0;
        6'd5:  enc_data = 32'd0;
        6'd6:  enc_data = 32'h03020100;
        6'd7:  enc_data = 32'h07060504;
        6'd8:  enc_data = 32'h0b0a0908;
        6'd9:  enc_data = 32'h0f0e0d0c;
        6'd10: enc_data = 32'h13121110;
        6'd11: enc_data = 32'h17161514;
        6'd12: enc_data = 32'h1b1a1918;
        6'd13: enc_data = 32'h1f1e1d1c;
        6'd14: enc_data = 32'h32314441; // AD12
        6'd15: enc_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_AD);
        6'd16: enc_data = 32'h00000033; // 3
        6'd17: enc_data = data_ctrl(1'b1, 4'h1, `ASCON_DATA_AD);
        6'd18: enc_data = 32'h6c6c6568; // hell
        6'd19: enc_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_TEXT);
        6'd20: enc_data = 32'h5341206f; // o AS
        6'd21: enc_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_TEXT);
        6'd22: enc_data = 32'h204e4f43; // CON 
        6'd23: enc_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_TEXT);
        6'd24: enc_data = 32'h64726168; // hard
        6'd25: enc_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_TEXT);
        6'd26: enc_data = 32'h65726177; // ware
        6'd27: enc_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_TEXT);
        6'd28: enc_data = 32'h646f6d20; //  mod
        6'd29: enc_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_TEXT);
        6'd30: enc_data = 32'h00006c65; // el
        6'd31: enc_data = data_ctrl(1'b1, 4'h3, `ASCON_DATA_TEXT);
        6'd32: enc_data = `ASCON_CONTROL_START;
        default: enc_data = 32'h00000000;
      endcase
    end
  endfunction

  function [7:0] dec_addr;
    input [5:0] idx;
    begin
      if (idx < 6'd14) begin
        dec_addr = enc_addr(idx);
      end else begin
        case (idx)
          6'd14: dec_addr = `ASCON_REG_TAG0;
          6'd15: dec_addr = `ASCON_REG_TAG1;
          6'd16: dec_addr = `ASCON_REG_TAG2;
          6'd17: dec_addr = `ASCON_REG_TAG3;
          6'd18: dec_addr = `ASCON_REG_DATA_IN;
          6'd19: dec_addr = `ASCON_REG_DATA_IN_CTRL;
          6'd20: dec_addr = `ASCON_REG_DATA_IN;
          6'd21: dec_addr = `ASCON_REG_DATA_IN_CTRL;
          6'd22: dec_addr = `ASCON_REG_DATA_IN;
          6'd23: dec_addr = `ASCON_REG_DATA_IN_CTRL;
          6'd24: dec_addr = `ASCON_REG_DATA_IN;
          6'd25: dec_addr = `ASCON_REG_DATA_IN_CTRL;
          6'd26: dec_addr = `ASCON_REG_DATA_IN;
          6'd27: dec_addr = `ASCON_REG_DATA_IN_CTRL;
          6'd28: dec_addr = `ASCON_REG_DATA_IN;
          6'd29: dec_addr = `ASCON_REG_DATA_IN_CTRL;
          6'd30: dec_addr = `ASCON_REG_DATA_IN;
          6'd31: dec_addr = `ASCON_REG_DATA_IN_CTRL;
          6'd32: dec_addr = `ASCON_REG_DATA_IN;
          6'd33: dec_addr = `ASCON_REG_DATA_IN_CTRL;
          6'd34: dec_addr = `ASCON_REG_DATA_IN;
          6'd35: dec_addr = `ASCON_REG_DATA_IN_CTRL;
          6'd36: dec_addr = `ASCON_REG_CONTROL;
          default: dec_addr = `ASCON_REG_CONTROL;
        endcase
      end
    end
  endfunction

  function [31:0] dec_data;
    input [5:0] idx;
    begin
      if (idx < 6'd14) begin
        dec_data = enc_data(idx);
      end else begin
        case (idx)
          6'd14: dec_data = 32'hab66db04;
          6'd15: dec_data = 32'h1f10d2df;
          6'd16: dec_data = 32'hab4ff809;
          6'd17: dec_data = 32'h91fadaf6;
          6'd18: dec_data = 32'h32314441;
          6'd19: dec_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_AD);
          6'd20: dec_data = 32'h00000033;
          6'd21: dec_data = data_ctrl(1'b1, 4'h1, `ASCON_DATA_AD);
          6'd22: dec_data = 32'he8e5d595;
          6'd23: dec_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_TEXT);
          6'd24: dec_data = 32'habebb16d;
          6'd25: dec_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_TEXT);
          6'd26: dec_data = 32'hb877a859;
          6'd27: dec_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_TEXT);
          6'd28: dec_data = 32'h359947c8;
          6'd29: dec_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_TEXT);
          6'd30: dec_data = 32'h55538ea8;
          6'd31: dec_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_TEXT);
          6'd32: dec_data = 32'h96765b14;
          6'd33: dec_data = data_ctrl(1'b0, 4'hf, `ASCON_DATA_TEXT);
          6'd34: dec_data = 32'h0000e3ad;
          6'd35: dec_data = data_ctrl(1'b1, 4'h3, `ASCON_DATA_TEXT);
          6'd36: dec_data = `ASCON_CONTROL_START | `ASCON_CONTROL_DECRYPT;
          default: dec_data = 32'h00000000;
        endcase
      end
    end
  endfunction

  function [31:0] expected_ct_word;
    input [3:0] idx;
    begin
      case (idx)
        4'd0: expected_ct_word = 32'he8e5d595;
        4'd1: expected_ct_word = 32'habebb16d;
        4'd2: expected_ct_word = 32'hb877a859;
        4'd3: expected_ct_word = 32'h359947c8;
        4'd4: expected_ct_word = 32'h55538ea8;
        4'd5: expected_ct_word = 32'h96765b14;
        4'd6: expected_ct_word = 32'h0000e3ad;
        default: expected_ct_word = 32'h00000000;
      endcase
    end
  endfunction

  function [31:0] expected_pt_word;
    input [3:0] idx;
    begin
      case (idx)
        4'd0: expected_pt_word = 32'h6c6c6568;
        4'd1: expected_pt_word = 32'h5341206f;
        4'd2: expected_pt_word = 32'h204e4f43;
        4'd3: expected_pt_word = 32'h64726168;
        4'd4: expected_pt_word = 32'h65726177;
        4'd5: expected_pt_word = 32'h646f6d20;
        4'd6: expected_pt_word = 32'h00006c65;
        default: expected_pt_word = 32'h00000000;
      endcase
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

  always @* begin
    bus_valid_r = 1'b0;
    bus_write_r = 1'b0;
    bus_addr_r = 8'h00;
    bus_wdata_r = 32'h00000000;

    case (state_q)
      ST_ENC_SETUP: begin
        bus_valid_r = 1'b1;
        bus_write_r = 1'b1;
        bus_addr_r = enc_addr(op_idx_q);
        bus_wdata_r = enc_data(op_idx_q);
      end
      ST_ENC_POLL, ST_DEC_POLL: begin
        bus_valid_r = 1'b1;
        bus_write_r = 1'b0;
        bus_addr_r = `ASCON_REG_STATUS;
      end
      ST_ENC_READ_CT, ST_DEC_READ_PT: begin
        bus_valid_r = 1'b1;
        bus_write_r = 1'b0;
        bus_addr_r = `ASCON_REG_DATA_OUT;
      end
      ST_ENC_READ_TAG: begin
        bus_valid_r = 1'b1;
        bus_write_r = 1'b0;
        case (rd_idx_q)
          4'd0: bus_addr_r = `ASCON_REG_TAG0;
          4'd1: bus_addr_r = `ASCON_REG_TAG1;
          4'd2: bus_addr_r = `ASCON_REG_TAG2;
          4'd3: bus_addr_r = `ASCON_REG_TAG3;
          default: bus_addr_r = `ASCON_REG_TAG0;
        endcase
      end
      ST_DEC_SETUP: begin
        bus_valid_r = 1'b1;
        bus_write_r = 1'b1;
        bus_addr_r = dec_addr(op_idx_q);
        bus_wdata_r = dec_data(op_idx_q);
      end
      default: begin
      end
    endcase
  end

  ascon_accel_mmio_aead128_top dut_i (
    .clk_i(clk),
    .rstn_i(rst_n),
    .bus_valid_i(bus_valid_r),
    .bus_write_i(bus_write_r),
    .bus_addr_i(bus_addr_r),
    .bus_wdata_i(bus_wdata_r),
    .bus_wstrb_i(4'hf),
    .bus_rdata_o(bus_rdata_w),
    .bus_ready_o(bus_ready_w),
    .irq_o(irq_w)
  );

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
      activity_q <= 1'b0;
    end else begin
      heartbeat_q <= heartbeat_q + 24'd1;
      activity_q <= bus_valid_r;
      case (state_q)
        ST_RESET: begin
          op_idx_q <= 6'd0;
          rd_idx_q <= 4'd0;
          enc_pass_q <= 1'b0;
          dec_pass_q <= 1'b0;
          fail_q <= 1'b0;
          done_q <= 1'b0;
          state_q <= ST_ENC_SETUP;
        end

        ST_ENC_SETUP: begin
          if (op_idx_q == ENC_OPS - 1) begin
            op_idx_q <= 6'd0;
            state_q <= ST_ENC_POLL;
          end else begin
            op_idx_q <= op_idx_q + 6'd1;
          end
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
          if (bus_rdata_w != expected_ct_word(rd_idx_q)) begin
            fail_q <= 1'b1;
          end
          if (rd_idx_q == 4'd6) begin
            rd_idx_q <= 4'd0;
            state_q <= ST_ENC_READ_TAG;
          end else begin
            rd_idx_q <= rd_idx_q + 4'd1;
          end
        end

        ST_ENC_READ_TAG: begin
          if (bus_rdata_w != expected_tag_word(rd_idx_q)) begin
            fail_q <= 1'b1;
          end
          if (rd_idx_q == 4'd3) begin
            enc_pass_q <= ~(fail_q | (bus_rdata_w != expected_tag_word(rd_idx_q)));
            op_idx_q <= 6'd0;
            rd_idx_q <= 4'd0;
            state_q <= ST_DEC_SETUP;
          end else begin
            rd_idx_q <= rd_idx_q + 4'd1;
          end
        end

        ST_DEC_SETUP: begin
          if (op_idx_q == DEC_OPS - 1) begin
            op_idx_q <= 6'd0;
            state_q <= ST_DEC_POLL;
          end else begin
            op_idx_q <= op_idx_q + 6'd1;
          end
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
          if (bus_rdata_w != expected_pt_word(rd_idx_q)) begin
            fail_q <= 1'b1;
          end
          if (rd_idx_q == 4'd6) begin
            dec_pass_q <= ~(fail_q | (bus_rdata_w != expected_pt_word(rd_idx_q)));
            done_q <= 1'b1;
            state_q <= ST_DONE;
          end else begin
            rd_idx_q <= rd_idx_q + 4'd1;
          end
        end

        ST_DONE: begin
          done_q <= 1'b1;
        end

        default: state_q <= ST_RESET;
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
