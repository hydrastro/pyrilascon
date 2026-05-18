// Tang Nano 9K UART smoke test - based on Lushay Labs reference design
module tangnano9k_uart_smoke_top(
  input  wire clk,
  input  wire rst_n,
  input  wire uart_rx,
  output reg  uart_tx,
  output wire [5:0] led_n
);
  localparam DELAY_FRAMES = 1406; // 27 MHz / 19200 baud

  // Message: "UART SMOKE 19200\r\n" (19 chars)
  localparam MSG_LEN = 19;
  reg [7:0] memory [0:18];
  initial begin
    memory[0]  = "U";
    memory[1]  = "A";
    memory[2]  = "R";
    memory[3]  = "T";
    memory[4]  = " ";
    memory[5]  = "S";
    memory[6]  = "M";
    memory[7]  = "O";
    memory[8]  = "K";
    memory[9]  = "E";
    memory[10] = " ";
    memory[11] = "1";
    memory[12] = "9";
    memory[13] = "2";
    memory[14] = "0";
    memory[15] = "0";
    memory[16] = 8'h0d;
    memory[17] = 8'h0a;
    memory[18] = " ";
  end

  reg [24:0] heartbeat = 0;
  reg [11:0] tx_counter = 0;
  reg [3:0]  tx_bit_idx = 0;
  reg [5:0]  mem_idx = 0;
  reg [2:0]  tx_state = 0;

  localparam IDLE  = 3'd0;
  localparam START = 3'd1;
  localparam DATA  = 3'd2;
  localparam STOP  = 3'd3;
  localparam NEXT  = 3'd4;

  initial uart_tx = 1'b1;

  assign led_n[0] = ~heartbeat[24];
  assign led_n[1] = ~heartbeat[23];
  assign led_n[2] = ~uart_tx;
  assign led_n[3] = (tx_state == IDLE);
  assign led_n[4] = ~(tx_state == DATA);
  assign led_n[5] = 1'b1;

  always @(posedge clk) begin
    heartbeat <= heartbeat + 1;

    case (tx_state)
      IDLE: begin
        uart_tx    <= 1'b1;
        tx_counter <= 0;
        tx_bit_idx <= 0;
        tx_state   <= START;
      end

      START: begin
        uart_tx <= 1'b0;
        if (tx_counter < DELAY_FRAMES - 1) begin
          tx_counter <= tx_counter + 1;
        end else begin
          tx_counter <= 0;
          tx_state   <= DATA;
        end
      end

      DATA: begin
        uart_tx <= memory[mem_idx][tx_bit_idx];
        if (tx_counter < DELAY_FRAMES - 1) begin
          tx_counter <= tx_counter + 1;
        end else begin
          tx_counter <= 0;
          if (tx_bit_idx == 7) begin
            tx_state <= STOP;
          end else begin
            tx_bit_idx <= tx_bit_idx + 1;
          end
        end
      end

      STOP: begin
        uart_tx <= 1'b1;
        if (tx_counter < DELAY_FRAMES - 1) begin
          tx_counter <= tx_counter + 1;
        end else begin
          tx_counter <= 0;
          tx_state   <= NEXT;
        end
      end

      NEXT: begin
        if (mem_idx == MSG_LEN - 1) begin
          mem_idx <= 0;
        end else begin
          mem_idx <= mem_idx + 1;
        end
        tx_state <= IDLE;
      end

      default: tx_state <= IDLE;
    endcase
  end
endmodule
