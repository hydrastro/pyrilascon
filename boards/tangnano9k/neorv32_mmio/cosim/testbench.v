// ============================================================================
// ASCON-on-NEORV32 co-simulation testbench (Icarus Verilog).
// Drives clock+reset into the NEORV32 wrapper; prints UART output to stdout
// and to neorv32_ascon_tb.log; halts on PASS / FAIL or after a timeout.
// ============================================================================

`timescale 1 ns / 100 ps

module neorv32_ascon_tb;
  localparam real CLK_PERIOD_NS = 37.037;          // 27 MHz
  localparam integer MAX_SIM_NS = 2_000_000_000;   // 2 s simulated time

  reg clk;
  reg rstn;
  wire uart_txd;
  wire [7:0] char_data;
  wire char_valid;

  initial clk = 1'b0;
  always #(CLK_PERIOD_NS/2.0) clk = ~clk;

  initial begin
    rstn = 1'b0;
    #1000;
    rstn = 1'b1;
  end

  neorv32_verilog_wrapper dut_i (
    .clk_i       (clk),
    .rstn_i      (rstn),
    .uart0_rxd_i (1'b1),
    .uart0_txd_o (uart_txd)
  );

  uart_sim_receiver #(
    .CLOCK_FREQ (27_000_000),
    .BAUD_RATE  (19_200)
  ) uart_rx (
    .clk_i   (clk),
    .txd_i   (uart_txd),
    .data_o  (char_data),
    .valid_o (char_valid)
  );

  // Capture chars to stdout+log, watch for PASS/FAIL banners.
  integer log_fp;
  reg [8*8-1:0] window;            // rolling 8-byte window

  initial begin
    log_fp = $fopen("neorv32_ascon_tb.log", "w");
    window = 0;
    $display("[TB] NEORV32 + ASCON co-simulation start");
  end

  always @(posedge clk) begin
    if (char_valid) begin
      $write("%c", char_data);
      $fwrite(log_fp, "%c", char_data);
      $fflush(log_fp);
      window = {window[8*7-1:0], char_data};
      // Match "PASS" followed by newline, or "FAIL"
      if (window[31:0] == "PASS" && (char_data == "\n" || char_data == "\r")) begin
        $display("\n[TB] firmware signaled PASS");
        $fclose(log_fp);
        $finish;
      end
      if (window[31:0] == "FAIL") begin
        $display("\n[TB] firmware signaled FAIL");
        $fclose(log_fp);
        $finish;
      end
    end
  end

  initial begin
    #(MAX_SIM_NS);
    $display("\n[TB] simulation timed out at %0d ns", MAX_SIM_NS);
    $fclose(log_fp);
    $finish;
  end

endmodule

// ----------------------------------------------------------------------------
// Standard 8-N-1 UART receiver (oversamples 16x). Same function as NEORV32's
// sim_uart_rx.vhd, re-implemented in Verilog for the all-Verilog flow.
// ----------------------------------------------------------------------------
module uart_sim_receiver #(
  parameter integer CLOCK_FREQ = 27_000_000,
  parameter integer BAUD_RATE  = 19_200
) (
  input  wire       clk_i,
  input  wire       txd_i,
  output reg  [7:0] data_o,
  output reg        valid_o
);
  localparam integer DIVIDER = CLOCK_FREQ / BAUD_RATE;

  reg [15:0] cnt;
  reg [3:0]  bitcnt;
  reg [7:0]  shreg;
  reg        busy;
  reg [2:0]  sync;

  initial begin
    cnt = 0; bitcnt = 0; shreg = 0; busy = 0; sync = 3'b111;
    data_o = 0; valid_o = 0;
  end

  always @(posedge clk_i) sync <= {sync[1:0], txd_i};

  always @(posedge clk_i) begin
    valid_o <= 1'b0;
    if (!busy) begin
      if (sync[2] == 1'b1 && sync[1] == 1'b0) begin
        busy   <= 1'b1;
        bitcnt <= 4'd0;
        cnt    <= DIVIDER + DIVIDER/2;
      end
    end else begin
      if (cnt == 0) begin
        cnt <= DIVIDER;
        if (bitcnt < 4'd8) begin
          shreg  <= {sync[2], shreg[7:1]};   // LSB first
          bitcnt <= bitcnt + 4'd1;
        end else begin
          data_o  <= shreg;
          valid_o <= 1'b1;
          busy    <= 1'b0;
        end
      end else begin
        cnt <= cnt - 16'd1;
      end
    end
  end
endmodule

