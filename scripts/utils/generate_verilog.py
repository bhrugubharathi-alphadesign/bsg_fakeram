import os
import math

################################################################################
# GENERATE VERILOG VIEW
#
# Generate a .v (functional model) and .bb.v (black-box) file for a given SRAM.
# Dispatch is on mem.macro_class: 1RW (default), 1R1W, NR1W, NRW.
################################################################################

def generate_verilog(mem, tmChkExpand=False):
  mc = getattr(mem, 'macro_class', '1RW')
  if mc == '1R1W':
    _gen_verilog_1r1w(mem, tmChkExpand)
  elif mc == 'NR1W':
    _gen_verilog_nr1w(mem, tmChkExpand)
  elif mc == 'NRW':
    _gen_verilog_nrw(mem, tmChkExpand)
  else:
    _gen_verilog_1rw(mem, tmChkExpand)

def generate_verilog_bb(mem):
  mc = getattr(mem, 'macro_class', '1RW')
  if mc == '1R1W':
    _gen_bb_1r1w(mem)
  elif mc == 'NR1W':
    _gen_bb_nr1w(mem)
  elif mc == 'NRW':
    _gen_bb_nrw(mem)
  else:
    _gen_bb_1rw(mem)


# ---------------------------------------------------------------------------
# 1RW
# ---------------------------------------------------------------------------

SH_LINE = '      $setuphold (posedge clk, {sig}, 0, 0, notifier);\n'

def _gen_verilog_1rw(mem, tmChkExpand=False):
  name  = str(mem.name)
  depth = int(mem.depth)
  bits  = int(mem.width_in_bits)
  addr_width = math.ceil(math.log2(depth))
  crpt_on_x = 1

  setuphold_checks  = SH_LINE.format(sig='       we_in')
  setuphold_checks += SH_LINE.format(sig='       ce_in')
  if tmChkExpand:
    for i in range(addr_width): setuphold_checks += SH_LINE.format(sig=f'  addr_in[{i}]')
    for i in range(      bits): setuphold_checks += SH_LINE.format(sig=f'    wd_in[{i}]')
    for i in range(      bits): setuphold_checks += SH_LINE.format(sig=f'w_mask_in[{i}]')
  else:
    setuphold_checks += SH_LINE.format(sig='     addr_in')
    setuphold_checks += SH_LINE.format(sig='       wd_in')
    setuphold_checks += SH_LINE.format(sig='   w_mask_in')

  fout = os.sep.join([mem.results_dir, name + '.v'])
  with open(fout, 'w') as f:
    f.write(VLOG_1RW_TEMPLATE.format(name=name, data_width=bits, depth=depth,
      addr_width=addr_width, crpt_on_x=crpt_on_x, setuphold_checks=setuphold_checks))

def _gen_bb_1rw(mem):
  name  = str(mem.name)
  depth = int(mem.depth)
  bits  = int(mem.width_in_bits)
  addr_width = math.ceil(math.log2(depth))
  fout = os.sep.join([mem.results_dir, name + '.bb.v'])
  with open(fout, 'w') as f:
    f.write(VLOG_1RW_BB_TEMPLATE.format(name=name, data_width=bits, depth=depth,
      addr_width=addr_width, crpt_on_x=1))


# ---------------------------------------------------------------------------
# 1R1W  — separate rd_addr_in / wr_addr_in
# ---------------------------------------------------------------------------

def _gen_verilog_1r1w(mem, tmChkExpand=False):
  name  = str(mem.name)
  depth = int(mem.depth)
  bits  = int(mem.width_in_bits)
  aw    = math.ceil(math.log2(depth))

  sh  = SH_LINE.format(sig='          we_in')
  sh += SH_LINE.format(sig='          ce_in')
  if tmChkExpand:
    for i in range(aw):   sh += SH_LINE.format(sig=f'  rd_addr_in[{i}]')
    for i in range(aw):   sh += SH_LINE.format(sig=f'  wr_addr_in[{i}]')
    for i in range(bits): sh += SH_LINE.format(sig=f'       wd_in[{i}]')
    for i in range(bits): sh += SH_LINE.format(sig=f'   w_mask_in[{i}]')
  else:
    sh += SH_LINE.format(sig='     rd_addr_in')
    sh += SH_LINE.format(sig='     wr_addr_in')
    sh += SH_LINE.format(sig='          wd_in')
    sh += SH_LINE.format(sig='      w_mask_in')

  fout = os.sep.join([mem.results_dir, name + '.v'])
  with open(fout, 'w') as f:
    f.write(VLOG_1R1W_TEMPLATE.format(name=name, data_width=bits, depth=depth,
      addr_width=aw, crpt_on_x=1, setuphold_checks=sh))

def _gen_bb_1r1w(mem):
  name  = str(mem.name)
  depth = int(mem.depth)
  bits  = int(mem.width_in_bits)
  aw    = math.ceil(math.log2(depth))
  fout  = os.sep.join([mem.results_dir, name + '.bb.v'])
  with open(fout, 'w') as f:
    f.write(VLOG_1R1W_BB_TEMPLATE.format(name=name, data_width=bits, depth=depth,
      addr_width=aw, crpt_on_x=1))


# ---------------------------------------------------------------------------
# NR1W  — N independent read ports + 1 write port
# ---------------------------------------------------------------------------

def _gen_verilog_nr1w(mem, tmChkExpand=False):
  name  = str(mem.name)
  depth = int(mem.depth)
  bits  = int(mem.width_in_bits)
  aw    = math.ceil(math.log2(depth))
  nr    = int(getattr(mem, 'num_r_ports', 2))

  # Port declarations (string-built)
  port_list = []
  for i in range(nr):
    port_list += [f'   rd_out_{i}', f'   rd_addr_in_{i}']
  port_list += ['   wd_in', '   w_mask_in', '   wr_addr_in', '   we_in', '   clk', '   ce_in']
  port_decl = ',\n'.join(port_list)

  io_decl_lines = []
  for i in range(nr):
    io_decl_lines.append(f'   output reg [BITS-1:0]   rd_out_{i};')
    io_decl_lines.append(f'   input  [ADDR_WIDTH-1:0] rd_addr_in_{i};')
  io_decl_lines += [
    f'   input  [BITS-1:0]        wd_in;',
    f'   input  [BITS-1:0]        w_mask_in;',
    f'   input  [ADDR_WIDTH-1:0]  wr_addr_in;',
    f'   input                    we_in;',
    f'   input                    clk;',
    f'   input                    ce_in;',
  ]
  io_decl = '\n'.join(io_decl_lines)

  read_assigns = '\n'.join(
    f'         rd_out_{i} <= mem[rd_addr_in_{i}];' for i in range(nr))

  sh  = SH_LINE.format(sig='          we_in')
  sh += SH_LINE.format(sig='          ce_in')
  for i in range(nr):
    sh += SH_LINE.format(sig=f'  rd_addr_in_{i}')
  if tmChkExpand:
    for i in range(aw):   sh += SH_LINE.format(sig=f'  wr_addr_in[{i}]')
    for i in range(bits): sh += SH_LINE.format(sig=f'       wd_in[{i}]')
    for i in range(bits): sh += SH_LINE.format(sig=f'   w_mask_in[{i}]')
  else:
    sh += SH_LINE.format(sig='     wr_addr_in')
    sh += SH_LINE.format(sig='          wd_in')
    sh += SH_LINE.format(sig='      w_mask_in')

  fout = os.sep.join([mem.results_dir, name + '.v'])
  with open(fout, 'w') as f:
    f.write(VLOG_NR1W_TEMPLATE.format(
      name=name, data_width=bits, depth=depth, addr_width=aw, crpt_on_x=1,
      port_decl=port_decl, io_decl=io_decl,
      read_assigns=read_assigns, setuphold_checks=sh))

def _gen_bb_nr1w(mem):
  name  = str(mem.name)
  depth = int(mem.depth)
  bits  = int(mem.width_in_bits)
  aw    = math.ceil(math.log2(depth))
  nr    = int(getattr(mem, 'num_r_ports', 2))

  port_list = []
  for i in range(nr):
    port_list += [f'   rd_out_{i}', f'   rd_addr_in_{i}']
  port_list += ['   wd_in', '   w_mask_in', '   wr_addr_in', '   we_in', '   clk', '   ce_in']
  port_decl = ',\n'.join(port_list)

  io_decl_lines = []
  for i in range(nr):
    io_decl_lines.append(f'   output reg [BITS-1:0]   rd_out_{i};')
    io_decl_lines.append(f'   input  [ADDR_WIDTH-1:0] rd_addr_in_{i};')
  io_decl_lines += [
    f'   input  [BITS-1:0]        wd_in;',
    f'   input  [BITS-1:0]        w_mask_in;',
    f'   input  [ADDR_WIDTH-1:0]  wr_addr_in;',
    f'   input                    we_in;',
    f'   input                    clk;',
    f'   input                    ce_in;',
  ]
  io_decl = '\n'.join(io_decl_lines)

  fout = os.sep.join([mem.results_dir, name + '.bb.v'])
  with open(fout, 'w') as f:
    f.write(VLOG_NR1W_BB_TEMPLATE.format(
      name=name, data_width=bits, depth=depth, addr_width=aw, crpt_on_x=1,
      port_decl=port_decl, io_decl=io_decl))


# ---------------------------------------------------------------------------
# NRW  — N true-dual-port read-write ports
# ---------------------------------------------------------------------------

def _gen_verilog_nrw(mem, tmChkExpand=False):
  name  = str(mem.name)
  depth = int(mem.depth)
  bits  = int(mem.width_in_bits)
  aw    = math.ceil(math.log2(depth))
  nr    = int(getattr(mem, 'num_r_ports', 2))

  port_list = []
  for i in range(nr):
    port_list += [f'   rw_rd_out_{i}', f'   rw_addr_in_{i}', f'   rw_wd_in_{i}',
                  f'   rw_w_mask_in_{i}', f'   rw_we_in_{i}']
  port_list += ['   clk', '   ce_in']
  port_decl = ',\n'.join(port_list)

  io_decl_lines = []
  for i in range(nr):
    io_decl_lines.append(f'   output reg [BITS-1:0]   rw_rd_out_{i};')
    io_decl_lines.append(f'   input  [ADDR_WIDTH-1:0] rw_addr_in_{i};')
    io_decl_lines.append(f'   input  [BITS-1:0]        rw_wd_in_{i};')
    io_decl_lines.append(f'   input  [BITS-1:0]        rw_w_mask_in_{i};')
    io_decl_lines.append(f'   input                    rw_we_in_{i};')
  io_decl_lines += ['   input                    clk;', '   input                    ce_in;']
  io_decl = '\n'.join(io_decl_lines)

  # Sequential always block per port
  always_blocks = []
  for i in range(nr):
    blk = f'''\
   always @(posedge clk) begin
      if (ce_in) begin
         if (rw_we_in_{i})
            mem[rw_addr_in_{i}] <= (rw_wd_in_{i} & rw_w_mask_in_{i}) | (mem[rw_addr_in_{i}] & ~rw_w_mask_in_{i});
         rw_rd_out_{i} <= mem[rw_addr_in_{i}];
      end else
         rw_rd_out_{i} <= 'x;
   end'''
    always_blocks.append(blk)
  always_body = '\n\n'.join(always_blocks)

  sh = SH_LINE.format(sig='   ce_in')
  for i in range(nr):
    sh += SH_LINE.format(sig=f'   rw_we_in_{i}')
    sh += SH_LINE.format(sig=f'   rw_addr_in_{i}')
    sh += SH_LINE.format(sig=f'   rw_wd_in_{i}')
    sh += SH_LINE.format(sig=f'   rw_w_mask_in_{i}')

  fout = os.sep.join([mem.results_dir, name + '.v'])
  with open(fout, 'w') as f:
    f.write(VLOG_NRW_TEMPLATE.format(
      name=name, data_width=bits, depth=depth, addr_width=aw, crpt_on_x=1,
      port_decl=port_decl, io_decl=io_decl,
      always_body=always_body, setuphold_checks=sh))

def _gen_bb_nrw(mem):
  name  = str(mem.name)
  depth = int(mem.depth)
  bits  = int(mem.width_in_bits)
  aw    = math.ceil(math.log2(depth))
  nr    = int(getattr(mem, 'num_r_ports', 2))

  port_list = []
  for i in range(nr):
    port_list += [f'   rw_rd_out_{i}', f'   rw_addr_in_{i}', f'   rw_wd_in_{i}',
                  f'   rw_w_mask_in_{i}', f'   rw_we_in_{i}']
  port_list += ['   clk', '   ce_in']
  port_decl = ',\n'.join(port_list)

  io_decl_lines = []
  for i in range(nr):
    io_decl_lines.append(f'   output reg [BITS-1:0]   rw_rd_out_{i};')
    io_decl_lines.append(f'   input  [ADDR_WIDTH-1:0] rw_addr_in_{i};')
    io_decl_lines.append(f'   input  [BITS-1:0]        rw_wd_in_{i};')
    io_decl_lines.append(f'   input  [BITS-1:0]        rw_w_mask_in_{i};')
    io_decl_lines.append(f'   input                    rw_we_in_{i};')
  io_decl_lines += ['   input                    clk;', '   input                    ce_in;']
  io_decl = '\n'.join(io_decl_lines)

  fout = os.sep.join([mem.results_dir, name + '.bb.v'])
  with open(fout, 'w') as f:
    f.write(VLOG_NRW_BB_TEMPLATE.format(
      name=name, data_width=bits, depth=depth, addr_width=aw, crpt_on_x=1,
      port_decl=port_decl, io_decl=io_decl))


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

VLOG_1RW_TEMPLATE = '''\
module {name}
(
   rd_out,
   addr_in,
   we_in,
   wd_in,
   w_mask_in,
   clk,
   ce_in
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

   output reg [BITS-1:0]    rd_out;
   input  [ADDR_WIDTH-1:0]  addr_in;
   input                    we_in;
   input  [BITS-1:0]        wd_in;
   input  [BITS-1:0]        w_mask_in;
   input                    clk;
   input                    ce_in;

   reg    [BITS-1:0]        mem [0:WORD_DEPTH-1];

   integer j;

   always @(posedge clk)
   begin
      if (ce_in)
      begin
         //if ((we_in !== 1\'b1 && we_in !== 1\'b0) && corrupt_mem_on_X_p)
         if (corrupt_mem_on_X_p &&
             ((^we_in === 1\'bx) || (^addr_in === 1\'bx))
            )
         begin
            // WEN or ADDR is unknown, so corrupt entire array (using unsynthesizeable for loop)
            for (j = 0; j < WORD_DEPTH; j = j + 1)
               mem[j] <= \'x;
            $display("warning: ce_in=1, we_in is %b, addr_in = %x in fakeram_d64_w8", we_in, addr_in);
         end
         else if (we_in)
         begin
            mem[addr_in] <= (wd_in & w_mask_in) | (mem[addr_in] & ~w_mask_in);
         end
         // read
         rd_out <= mem[addr_in];
      end
      else
      begin
         // Make sure read fails if ce_in is low
         rd_out <= \'x;
      end
   end

   // Timing check placeholders (will be replaced during SDF back-annotation)
   reg notifier;
   specify
      // Delay from clk to rd_out
      (posedge clk *> rd_out) = (0, 0);

      // Timing checks
      $width     (posedge clk,               0, 0, notifier);
      $width     (negedge clk,               0, 0, notifier);
      $period    (posedge clk,               0,    notifier);
{setuphold_checks}
   endspecify

endmodule
'''

VLOG_1RW_BB_TEMPLATE = '''\
module {name}
(
   rd_out,
   addr_in,
   we_in,
   wd_in,
   w_mask_in,
   clk,
   ce_in
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

   output reg [BITS-1:0]    rd_out;
   input  [ADDR_WIDTH-1:0]  addr_in;
   input                    we_in;
   input  [BITS-1:0]        wd_in;
   input  [BITS-1:0]        w_mask_in;
   input                    clk;
   input                    ce_in;

endmodule
'''

VLOG_1R1W_TEMPLATE = '''\
module {name}
(
   rd_out,
   rd_addr_in,
   wd_in,
   w_mask_in,
   wr_addr_in,
   we_in,
   clk,
   ce_in
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

   output reg [BITS-1:0]    rd_out;
   input  [ADDR_WIDTH-1:0]  rd_addr_in;
   input  [BITS-1:0]        wd_in;
   input  [BITS-1:0]        w_mask_in;
   input  [ADDR_WIDTH-1:0]  wr_addr_in;
   input                    we_in;
   input                    clk;
   input                    ce_in;

   reg    [BITS-1:0]        mem [0:WORD_DEPTH-1];

   always @(posedge clk)
   begin
      if (ce_in)
      begin
         // Read port (read-before-write: returns old data if rd_addr_in == wr_addr_in)
         rd_out <= mem[rd_addr_in];
         // Write port
         if (we_in)
            mem[wr_addr_in] <= (wd_in & w_mask_in) | (mem[wr_addr_in] & ~w_mask_in);
      end
      else
         rd_out <= \'x;
   end

   reg notifier;
   specify
      (posedge clk *> rd_out) = (0, 0);
      $width     (posedge clk,               0, 0, notifier);
      $width     (negedge clk,               0, 0, notifier);
      $period    (posedge clk,               0,    notifier);
{setuphold_checks}
   endspecify

endmodule
'''

VLOG_1R1W_BB_TEMPLATE = '''\
module {name}
(
   rd_out,
   rd_addr_in,
   wd_in,
   w_mask_in,
   wr_addr_in,
   we_in,
   clk,
   ce_in
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

   output reg [BITS-1:0]    rd_out;
   input  [ADDR_WIDTH-1:0]  rd_addr_in;
   input  [BITS-1:0]        wd_in;
   input  [BITS-1:0]        w_mask_in;
   input  [ADDR_WIDTH-1:0]  wr_addr_in;
   input                    we_in;
   input                    clk;
   input                    ce_in;

endmodule
'''

VLOG_NR1W_TEMPLATE = '''\
module {name}
(
{port_decl}
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

{io_decl}

   reg    [BITS-1:0]        mem [0:WORD_DEPTH-1];

   always @(posedge clk)
   begin
      if (ce_in)
      begin
         // Write port
         if (we_in)
            mem[wr_addr_in] <= (wd_in & w_mask_in) | (mem[wr_addr_in] & ~w_mask_in);
         // Read ports (read-before-write)
{read_assigns}
      end
   end

   reg notifier;
   specify
      (posedge clk *> rd_out_0) = (0, 0);
      $width  (posedge clk, 0, 0, notifier);
      $width  (negedge clk, 0, 0, notifier);
      $period (posedge clk, 0,    notifier);
{setuphold_checks}
   endspecify

endmodule
'''

VLOG_NR1W_BB_TEMPLATE = '''\
module {name}
(
{port_decl}
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

{io_decl}

endmodule
'''

VLOG_NRW_TEMPLATE = '''\
module {name}
(
{port_decl}
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

{io_decl}

   reg    [BITS-1:0]        mem [0:WORD_DEPTH-1];

{always_body}

   reg notifier;
   specify
      (posedge clk *> rw_rd_out_0) = (0, 0);
      $width  (posedge clk, 0, 0, notifier);
      $width  (negedge clk, 0, 0, notifier);
      $period (posedge clk, 0,    notifier);
{setuphold_checks}
   endspecify

endmodule
'''

VLOG_NRW_BB_TEMPLATE = '''\
module {name}
(
{port_decl}
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

{io_decl}

endmodule
'''
