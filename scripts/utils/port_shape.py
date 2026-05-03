"""Unified port-shape descriptor used across generate_* modules.

bsg_fakeram now generates one generic macro shape parameterised on
`(rw, r, w)` — the count of true read-write ports, exclusive-read ports, and
exclusive-write ports respectively. Every per-shape (1RW/1R1W/NR1W/NRW)
template that used to live in this codebase is a specialisation of that
generic shape; this module is the single source of truth for:

    - the canonical pin names emitted in Verilog/LEF/Liberty/memlib/techmap,
    - the dispatch-on-port-shape iteration order,
    - the validation that turns a JSON sram entry into a usable PortShape.

Pin naming convention (uniform — no legacy 1RW names anywhere):

    Always present:
        clk
        ce_in

    For each i in [0, rw):
        rw_addr_in_{i}      input  [ADDR-1:0]
        rw_rd_out_{i}       output [BITS-1:0]
        rw_wd_in_{i}        input  [BITS-1:0]
        rw_w_mask_in_{i}    input  [BITS-1:0]
        rw_we_in_{i}        input

    For each i in [0, r):
        r_addr_in_{i}       input  [ADDR-1:0]
        r_rd_out_{i}        output [BITS-1:0]

    For each i in [0, w):
        w_addr_in_{i}       input  [ADDR-1:0]
        w_wd_in_{i}         input  [BITS-1:0]
        w_w_mask_in_{i}     input  [BITS-1:0]
        w_we_in_{i}         input

Memlib port names mirror the pin convention:
        srsw "RW0".."RW{rw-1}"
        sr   "R0".."R{r-1}"
        sw   "W0".."W{w-1}"
all on a shared `clock posedge "CLK"`.

Techmap signals from Yosys memory_libmap follow the same scheme:
        PORT_RW{i}_{ADDR,RD_DATA,WR_DATA,WR_EN}
        PORT_R{i}_{ADDR,RD_DATA}
        PORT_W{i}_{ADDR,WR_DATA,WR_EN}
plus the shared `CLK_CLK`. `WR_EN` is mask-width and is wired to the
matching `*_w_mask_in_*` pin; `*_we_in_*` is derived as `|WR_EN`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortShape:
    rw: int
    r:  int
    w:  int

    @property
    def total_ports(self) -> int:
        return self.rw + self.r + self.w


def from_sram_data(sram_data: dict) -> PortShape:
    """Extract the PortShape from a cfg sram entry. Hard-fail if missing.

    The cfg producer (verific/ir_extraction/scripts/build_fakeram_cfg.py)
    is required to emit `port_shape: {rw, r, w, decomposable}` for every
    sram. Non-decomposable shapes are dropped at the cfg-producer level,
    so by the time bsg_fakeram sees the entry, decomposable should be true.
    """
    name = sram_data.get('name', '<unnamed>')
    if 'port_shape' not in sram_data:
        raise ValueError(
            f"sram '{name}': cfg entry has no 'port_shape' field. "
            "bsg_fakeram requires port-shape-aware cfgs (produced by "
            "verific/ir_extraction/scripts/build_fakeram_cfg.py)."
        )
    ps = sram_data['port_shape']
    for k in ('rw', 'r', 'w'):
        if k not in ps:
            raise ValueError(f"sram '{name}': port_shape missing '{k}'")
    if not ps.get('decomposable', True):
        raise ValueError(
            f"sram '{name}': port_shape.decomposable is false; "
            "bsg_fakeram cannot generate non-decomposable shapes. "
            "The cfg producer should drop these before reaching here."
        )
    rw, r, w = int(ps['rw']), int(ps['r']), int(ps['w'])
    if rw < 0 or r < 0 or w < 0:
        raise ValueError(f"sram '{name}': port counts must be non-negative")
    if rw + r + w == 0:
        raise ValueError(f"sram '{name}': port_shape has zero total ports")
    return PortShape(rw=rw, r=r, w=w)


# ---------------------------------------------------------------------------
# Pin name builders. One source of truth for every generator file.
# ---------------------------------------------------------------------------

def rw_pins(i: int) -> dict[str, str]:
    return {
        'addr':   f'rw_addr_in_{i}',
        'rd':     f'rw_rd_out_{i}',
        'wd':     f'rw_wd_in_{i}',
        'wmask':  f'rw_w_mask_in_{i}',
        'we':     f'rw_we_in_{i}',
    }


def r_pins(i: int) -> dict[str, str]:
    return {
        'addr':   f'r_addr_in_{i}',
        'rd':     f'r_rd_out_{i}',
    }


def w_pins(i: int) -> dict[str, str]:
    return {
        'addr':   f'w_addr_in_{i}',
        'wd':     f'w_wd_in_{i}',
        'wmask':  f'w_w_mask_in_{i}',
        'we':     f'w_we_in_{i}',
    }


def all_port_pins(shape: PortShape) -> list[tuple[str, dict[str, str]]]:
    """Return a list of (port_kind, pins) in canonical declaration order:
    rw0..rw{rw-1}, r0..r{r-1}, w0..w{w-1}. port_kind is 'rw' | 'r' | 'w'.
    """
    out: list[tuple[str, dict[str, str]]] = []
    for i in range(shape.rw):
        out.append(('rw', rw_pins(i)))
    for i in range(shape.r):
        out.append(('r', r_pins(i)))
    for i in range(shape.w):
        out.append(('w', w_pins(i)))
    return out


# Memlib / techmap port-name helpers (Yosys conventions).

def memlib_port_name(kind: str, i: int) -> str:
    """memlib-side port label, e.g. 'RW0', 'R3', 'W2'."""
    if kind == 'rw':
        return f'RW{i}'
    if kind == 'r':
        return f'R{i}'
    if kind == 'w':
        return f'W{i}'
    raise ValueError(f"unknown port kind {kind!r}")


def techmap_signal(kind: str, i: int, suffix: str) -> str:
    """Yosys techmap signal name for a (kind, i, suffix) triple.

    suffix is one of: ADDR, RD_DATA, WR_DATA, WR_EN.
    """
    return f'PORT_{memlib_port_name(kind, i)}_{suffix}'
