# BSG Black-box SRAM Generator

This project is desgined to generate black-boxed SRAMs for use in CAD flows
where either an SRAM generator is not avaible or doesn't exist.

## Setup

The black-box SRAM generator uses both modeling backends:

- P-CACTI from the vendored `tools/pcacti` source for sub-22 nm nodes with
  checked-in P-CACTI characterization data.
- Legacy HP CACTI from `tools/cacti` for 22 nm and larger nodes.

To build both tools, run:

```
$ make tools
```

## Usage

### Configuration File

The input to the BSG Black-box SRAM generator is a simple JSON file that
contains some information about the technology node you are targeting as well
as the size and names of SRAMs you would like to generate. Below is an example
JSON file that can be found in `./example_cfgs/pcacti7.cfg`:

```
{
  "tech_nm": 7,
  "voltage": 0.45,
  "metalPrefix": "M",
  "pinWidth_nm": 40,
  "pinHeight_nm": 80,
  "pinPitch_nm": 60,
  "snapWidth_nm": 1,
  "snapHeight_nm": 1,
  "flipPins": true,
  "srams": [
    {
      "name": "fakeram7_256x32_1rw",
      "width": 32,
      "depth": 256,
      "banks": 1,
      "type": "ram",
      "port_shape": {"rw": 1, "r": 0, "w": 0, "decomposable": true}
    }
  ]
}
```

`tech_nm` - The name of the target technology node (in nm). With the default
`--model_backend auto`, nodes below 22 nm use P-CACTI and nodes at 22 nm or
larger use legacy CACTI. The checked-in P-CACTI profiles currently include
7 nm FinFET, 14 nm CMOS, and 22 nm CMOS; auto mode still routes 22 nm to legacy
CACTI to preserve the contiguous CACTI 22-90 nm coverage.

`voltage` - Nominal operating voltage for the tech node. P-CACTI-backed nodes
must match a characterized device point from the selected P-CACTI profile
exactly, for example 7 nm at 0.45 V or 0.3 V and 14 nm at 0.8 V or 0.55 V.

`metalPrefix` - The string that prefixes metal layers.

`pinWidth_nm` - The width of the signal pins (in nm).

`pinPitch_nm` - The minimum pin pitch for signal pins (in nm). All pins will
have a pitch that is a multuple of this pitch. The first pin will be a
multiple of this pitch from the bottom edge of the macro too.

`snapWidth_nm` - (Optional : 1) Snap the width of the generated memory to a
multiple of the given value.

`snapHeight_nm` - (Optional : 1) Snap the height of the generated memory to a
multiple of the given value.

`flipPins` - (Optional : false) Flip the pins. If set to false then metal 1 is
assumed to be vertical. This means that signal pins will be on metal 4 and the
supply straps (also on metal 4) will be horizontal. If set to true then metal 1
is assumed to be horizontal. This means that signal pins will be on metal 3 and
the supply straps (on metal 4) will be vertical.

`srams` - A list of SRAMs to generate. Each sram should have a `name`, `width`
(or the number of bits per word), `depth` (or number of words), `banks`, and a
`port_shape` object with `rw`, `r`, and `w` port counts.


### Running the Generator

Now that you have a configuration file, it is time to run the generator. The
main makefile target is:

```
$ make tools
$ make run CONFIG=<path to config file>
```

The backend can be forced for comparison:

```
$ ./scripts/run.py <path to config file> --model_backend pcacti
$ ./scripts/run.py <path to config file> --model_backend cacti
```

More details on the P-CACTI integration are in
`docs/pcacti_integration.md`.

If you'd perfer, you can open up the Makefile and set `CONFIG` rather than
setting it on the command line.

All of the generated files can be found in the `./results` directory. Inside
this directory will be a directory for each SRAM which contains the .lef, .lib
and v file, plus the backend input and report files used for area, power, and
timing. P-CACTI runs leave `pcacti.xml` and `pcacti.csv`; legacy CACTI runs
leave `cacti.cfg` and `cacti.cfg.out`.

### Comparison with standard SRAMs generated with OpenRAM compiler

#### Generated Fakerams (Eg:- fakeram130_1024x8)

![](docs/images/fakeram.png)

![](docs/images/fakeram_io.png)

- The generated fakerams are 1rw RAMs 
- All pins are on the left side and they are all on Metal 3.
- Pins:
  - 1x chip enable 
  - 1x write enable
  - 1x clock 
  - 1x address-in port
  - 1x data-in-data-out port
  - 1x write-mask-in port (bit masked).

![](docs/images/fakeram_power.png)

- Power rails are vertical (can be made horizontal in the config file) - Alternate VDD and GND rails.
- Metal layers 1, 2, 3 and 4 are blocked, metal 5 is free for routing over.

#### Standard SRAMs compiled with OpenRAM (Eg:- [sky130_sram_1kbyte_1rw1r_8x1024_8](https://github.com/efabless/sky130_sram_macros/tree/main/sky130_sram_1kbyte_1rw1r_8x1024_8))

![](docs/images/openram.png)

![](docs/images/openram_pins.png)

- 1rw1r RAMs
- Pins cover all 4 sides
- I/O pins use Metal 3 (on left and right sides) & Metal 4 (on top and bottom sides)
- Pins:
  - 2x clock 
  - 2x chip select
  - 1x write enable
  - 2x address-in port
  - 1x data-out port
  - 1x data-in-data-out port
  - 1x write-mask pin/port (byte masked)

- Power pins are in a ring format along the macro edge utilizing Metal 3 (Horizontal) & Metal 4 (Vertical)
- Metal layers 1, 2, 3 and 4 are blocked, metal 5 is free for routing over.



## Feedback

Feedback is always welcome! We ask that you submit a GitHub issue for any bugs,
improvements, or new features you would like to see. We are also receptive to
outside contributions but please be mindful of sensitive information that is
commonly associated with licensed IP.

