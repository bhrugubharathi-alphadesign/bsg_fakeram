"""Generic shape-aware Verilog generator.

Emits a behavioural model `<name>.v` and a black-box stub `<name>.bb.v`
for any decomposable port shape `(rw, r, w)`. Pin names follow the unified
convention defined in utils.port_shape:

    rw port i  -> rw_addr_in_{i}, rw_rd_out_{i}, rw_wd_in_{i},
                  rw_w_mask_in_{i}, rw_we_in_{i}
    r  port i  -> r_addr_in_{i},  r_rd_out_{i}
    w  port i  -> w_addr_in_{i},  w_wd_in_{i}, w_w_mask_in_{i}, w_we_in_{i}

shared       -> clk, ce_in

The behavioural body is one always block per port (read-before-write per
Verilog non-blocking semantics). Multi-write conflicts to the same address
in the same cycle have racy semantics — that's accepted for a fakeram
functional stub, the same as the legacy NRW template.
"""
import os
import math

from utils.port_shape import all_port_pins


_SH_LINE = '      $setuphold (posedge clk, {sig}, 0, 0, notifier);\n'


def _addr_width(depth: int) -> int:
    return max(1, math.ceil(math.log2(depth)))


def _port_decl(shape) -> str:
    """Comma-separated module port name list, in canonical order."""
    parts = []
    for kind, pins in all_port_pins(shape):
        if kind == 'rw':
            parts += [pins['rd'], pins['addr'], pins['wd'], pins['wmask'], pins['we']]
        elif kind == 'r':
            parts += [pins['rd'], pins['addr']]
        elif kind == 'w':
            parts += [pins['wd'], pins['wmask'], pins['addr'], pins['we']]
    parts += ['clk', 'ce_in']
    return ',\n   '.join(parts)


def _io_decl(shape) -> str:
    """Verilog input/output declarations matching the port list."""
    lines = []
    for kind, pins in all_port_pins(shape):
        if kind == 'rw':
            lines.append(f'   output reg [BITS-1:0]    {pins["rd"]};')
            lines.append(f'   input  [ADDR_WIDTH-1:0]  {pins["addr"]};')
            lines.append(f'   input  [BITS-1:0]        {pins["wd"]};')
            lines.append(f'   input  [BITS-1:0]        {pins["wmask"]};')
            lines.append(f'   input                    {pins["we"]};')
        elif kind == 'r':
            lines.append(f'   output reg [BITS-1:0]    {pins["rd"]};')
            lines.append(f'   input  [ADDR_WIDTH-1:0]  {pins["addr"]};')
        elif kind == 'w':
            lines.append(f'   input  [ADDR_WIDTH-1:0]  {pins["addr"]};')
            lines.append(f'   input  [BITS-1:0]        {pins["wd"]};')
            lines.append(f'   input  [BITS-1:0]        {pins["wmask"]};')
            lines.append(f'   input                    {pins["we"]};')
    lines += [
        '   input                    clk;',
        '   input                    ce_in;',
    ]
    return '\n'.join(lines)


def _always_blocks(shape) -> str:
    """One always block per port. Reads use read-before-write semantics."""
    blocks = []
    for kind, pins in all_port_pins(shape):
        if kind == 'rw':
            blocks.append(
f'''   always @(posedge clk) begin
      if (ce_in) begin
         if ({pins["we"]})
            mem[{pins["addr"]}] <= ({pins["wd"]} & {pins["wmask"]}) | (mem[{pins["addr"]}] & ~{pins["wmask"]});
         {pins["rd"]} <= mem[{pins["addr"]}];
      end else
         {pins["rd"]} <= 'x;
   end''')
        elif kind == 'r':
            blocks.append(
f'''   always @(posedge clk) begin
      if (ce_in)
         {pins["rd"]} <= mem[{pins["addr"]}];
      else
         {pins["rd"]} <= 'x;
   end''')
        elif kind == 'w':
            blocks.append(
f'''   always @(posedge clk) begin
      if (ce_in && {pins["we"]})
         mem[{pins["addr"]}] <= ({pins["wd"]} & {pins["wmask"]}) | (mem[{pins["addr"]}] & ~{pins["wmask"]});
   end''')
    return '\n\n'.join(blocks)


def _first_read_pin(shape) -> str | None:
    """Pin name of the first read output, for the (posedge clk *> ...) arc."""
    for kind, pins in all_port_pins(shape):
        if kind in ('rw', 'r'):
            return pins['rd']
    return None


def _setuphold_checks(shape, addr_width: int, bits: int, expand: bool) -> str:
    """Setuphold timing checks for ce_in and every input pin."""
    out = _SH_LINE.format(sig='   ce_in')
    for kind, pins in all_port_pins(shape):
        if kind == 'rw':
            out += _SH_LINE.format(sig=f'   {pins["we"]}')
            if expand:
                for i in range(addr_width):
                    out += _SH_LINE.format(sig=f'   {pins["addr"]}[{i}]')
                for i in range(bits):
                    out += _SH_LINE.format(sig=f'   {pins["wd"]}[{i}]')
                for i in range(bits):
                    out += _SH_LINE.format(sig=f'   {pins["wmask"]}[{i}]')
            else:
                out += _SH_LINE.format(sig=f'   {pins["addr"]}')
                out += _SH_LINE.format(sig=f'   {pins["wd"]}')
                out += _SH_LINE.format(sig=f'   {pins["wmask"]}')
        elif kind == 'r':
            if expand:
                for i in range(addr_width):
                    out += _SH_LINE.format(sig=f'   {pins["addr"]}[{i}]')
            else:
                out += _SH_LINE.format(sig=f'   {pins["addr"]}')
        elif kind == 'w':
            out += _SH_LINE.format(sig=f'   {pins["we"]}')
            if expand:
                for i in range(addr_width):
                    out += _SH_LINE.format(sig=f'   {pins["addr"]}[{i}]')
                for i in range(bits):
                    out += _SH_LINE.format(sig=f'   {pins["wd"]}[{i}]')
                for i in range(bits):
                    out += _SH_LINE.format(sig=f'   {pins["wmask"]}[{i}]')
            else:
                out += _SH_LINE.format(sig=f'   {pins["addr"]}')
                out += _SH_LINE.format(sig=f'   {pins["wd"]}')
                out += _SH_LINE.format(sig=f'   {pins["wmask"]}')
    return out


def _specify(shape, sh_checks: str) -> str:
    """Verilog specify block: timing arc per read output + setuphold checks."""
    arcs = []
    for kind, pins in all_port_pins(shape):
        if kind in ('rw', 'r'):
            arcs.append(f'      (posedge clk *> {pins["rd"]}) = (0, 0);')
    arc_block = '\n'.join(arcs) if arcs else ''
    return (
        '   reg notifier;\n'
        '   specify\n'
        + (arc_block + '\n' if arc_block else '')
        + '      $width  (posedge clk, 0, 0, notifier);\n'
        '      $width  (negedge clk, 0, 0, notifier);\n'
        '      $period (posedge clk, 0,    notifier);\n'
        + sh_checks
        + '   endspecify\n'
    )


def generate_verilog(mem, tmChkExpand: bool = False) -> None:
    name  = str(mem.name)
    depth = int(mem.depth)
    bits  = int(mem.width_in_bits)
    aw    = _addr_width(depth)
    shape = mem.shape

    body = (
        f'module {name}\n'
        f'(\n'
        f'   {_port_decl(shape)}\n'
        f');\n'
        f'   parameter BITS = {bits};\n'
        f'   parameter WORD_DEPTH = {depth};\n'
        f'   parameter ADDR_WIDTH = {aw};\n'
        f'   parameter corrupt_mem_on_X_p = 1;\n'
        f'\n'
        f'{_io_decl(shape)}\n'
        f'\n'
        f'   reg    [BITS-1:0]        mem [0:WORD_DEPTH-1];\n'
        f'\n'
        f'{_always_blocks(shape)}\n'
        f'\n'
        f'{_specify(shape, _setuphold_checks(shape, aw, bits, tmChkExpand))}'
        f'\n'
        f'endmodule\n'
    )

    out = os.sep.join([mem.results_dir, name + '.v'])
    with open(out, 'w') as f:
        f.write(body)


def generate_verilog_bb(mem) -> None:
    name  = str(mem.name)
    depth = int(mem.depth)
    bits  = int(mem.width_in_bits)
    aw    = _addr_width(depth)
    shape = mem.shape

    body = (
        f'module {name}\n'
        f'(\n'
        f'   {_port_decl(shape)}\n'
        f');\n'
        f'   parameter BITS = {bits};\n'
        f'   parameter WORD_DEPTH = {depth};\n'
        f'   parameter ADDR_WIDTH = {aw};\n'
        f'   parameter corrupt_mem_on_X_p = 1;\n'
        f'\n'
        f'{_io_decl(shape)}\n'
        f'\n'
        f'endmodule\n'
    )

    out = os.sep.join([mem.results_dir, name + '.bb.v'])
    with open(out, 'w') as f:
        f.write(body)
