import os
import math
import time
import datetime

################################################################################
# GENERATE LIBERTY VIEW
#
# Generate a .lib file based on the given SRAM.
# Dispatches on mem.macro_class: 1RW (default), 1R1W, NR1W, NRW.
#
# The memory_read(address:) / memory_write(address:) annotations on bus groups
# are what Yosys's memory_libmap uses to match $mem_v2 port shapes. Getting
# these right is the key invariant this file must maintain:
#   1RW  -> shared addr_in, one memory_read + one memory_write on the same bus
#   1R1W -> separate rd_addr_in / wr_addr_in
#   NR1W -> N memory_read groups each with their own rd_addr_in_N
#   NRW  -> N pairs of (memory_read + memory_write) each with rw_addr_in_N
################################################################################

def generate_lib( mem ):
    mc = getattr(mem, 'macro_class', '1RW')
    if mc == '1R1W':
        _gen_lib_1r1w(mem)
    elif mc == 'NR1W':
        _gen_lib_nr1w(mem)
    elif mc == 'NRW':
        _gen_lib_nrw(mem)
    else:
        _gen_lib_1rw(mem)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _lib_params(mem):
    """Extract and return all scalar params used across all port-shape variants."""
    name              = str(mem.name)
    depth             = int(mem.depth)
    bits              = int(mem.width_in_bits)
    area              = float(mem.area_um2)
    x                 = float(mem.width_um)
    y                 = float(mem.height_um)
    leakage           = float(mem.standby_leakage_per_bank_mW)*1e3
    tsetup            = float(mem.t_setup_ns)
    thold             = float(mem.t_hold_ns)
    tcq               = float(mem.access_time_ns)
    clkpindynamic     = float(mem.pin_dynamic_power_mW)*1e3
    pindynamic        = float(mem.pin_dynamic_power_mW)*1e1
    min_driver_in_cap = float(mem.cap_input_pf)
    voltage           = float(mem.process.voltage)
    min_period        = float(mem.cycle_time_ns)
    fo4               = float(mem.fo4_ps)/1e3

    addr_width    = math.ceil(math.log2(depth))
    addr_width_m1 = addr_width - 1

    d = datetime.date.today()
    date = d.isoformat()
    current_time = time.strftime("%H:%M:%SZ", time.gmtime())

    min_slew = 1   * fo4
    max_slew = 25  * fo4
    min_load = 1   * min_driver_in_cap
    max_load = 100 * min_driver_in_cap

    slew_idx = '%.3f, %.3f' % (min_slew, max_slew)
    load_idx = '%.3f, %.3f' % (min_load, max_load)

    return dict(
        name=name, depth=depth, bits=bits, area=area, x=x, y=y,
        leakage=leakage, tsetup=tsetup, thold=thold, tcq=tcq,
        clkpindynamic=clkpindynamic, pindynamic=pindynamic,
        min_driver_in_cap=min_driver_in_cap, voltage=voltage,
        min_period=min_period, fo4=fo4,
        addr_width=addr_width, addr_width_m1=addr_width_m1,
        date=date, current_time=current_time,
        min_slew=min_slew, max_slew=max_slew,
        min_load=min_load, max_load=max_load,
        slew_idx=slew_idx, load_idx=load_idx,
    )


def _write_lib_header(f, p):
    f.write('library(%s) {\n' % p['name'])
    f.write('    technology (cmos);\n')
    f.write('    delay_model : table_lookup;\n')
    f.write('    revision : 1.0;\n')
    f.write('    date : "%s %s";\n' % (p['date'], p['current_time']))
    f.write('    comment : "SRAM";\n')
    f.write('    time_unit : "1ns";\n')
    f.write('    voltage_unit : "1V";\n')
    f.write('    current_unit : "1uA";\n')
    f.write('    leakage_power_unit : "1uW";\n')
    f.write('    nom_process : 1;\n')
    f.write('    nom_temperature : 25.000;\n')
    f.write('    nom_voltage : %s;\n' % p['voltage'])
    f.write('    capacitive_load_unit (1,pf);\n\n')
    f.write('    pulling_resistance_unit : "1kohm";\n\n')
    f.write('    operating_conditions(tt_1.0_25.0) {\n')
    f.write('        process : 1;\n')
    f.write('        temperature : 25.000;\n')
    f.write('        voltage : %s;\n' % p['voltage'])
    f.write('        tree_type : balanced_tree;\n')
    f.write('    }\n\n')
    f.write('    /* default attributes */\n')
    f.write('    default_cell_leakage_power : 0;\n')
    f.write('    default_fanout_load : 1;\n')
    f.write('    default_inout_pin_cap : 0.0;\n')
    f.write('    default_input_pin_cap : 0.0;\n')
    f.write('    default_output_pin_cap : 0.0;\n')
    f.write('    default_input_pin_cap : 0.0;\n')
    f.write('    default_max_transition : %.3f;\n\n' % p['max_slew'])
    f.write('    default_operating_conditions : tt_1.0_25.0;\n')
    f.write('    default_leakage_power_density : 0.0;\n\n')
    f.write('    /* additional header data */\n')
    f.write('    slew_derate_from_library : 1.000;\n')
    f.write('    slew_lower_threshold_pct_fall : 20.000;\n')
    f.write('    slew_upper_threshold_pct_fall : 80.000;\n')
    f.write('    slew_lower_threshold_pct_rise : 20.000;\n')
    f.write('    slew_upper_threshold_pct_rise : 80.000;\n')
    f.write('    input_threshold_pct_fall : 50.000;\n')
    f.write('    input_threshold_pct_rise : 50.000;\n')
    f.write('    output_threshold_pct_fall : 50.000;\n')
    f.write('    output_threshold_pct_rise : 50.000;\n\n\n')
    name = p['name']
    f.write('    lu_table_template(%s_mem_out_delay_template) {\n' % name)
    f.write('        variable_1 : input_net_transition;\n')
    f.write('        variable_2 : total_output_net_capacitance;\n')
    f.write('            index_1 ("1000, 1001");\n')
    f.write('            index_2 ("1000, 1001");\n')
    f.write('    }\n')
    f.write('    lu_table_template(%s_mem_out_slew_template) {\n' % name)
    f.write('        variable_1 : total_output_net_capacitance;\n')
    f.write('            index_1 ("1000, 1001");\n')
    f.write('    }\n')
    f.write('    lu_table_template(%s_constraint_template) {\n' % name)
    f.write('        variable_1 : related_pin_transition;\n')
    f.write('        variable_2 : constrained_pin_transition;\n')
    f.write('            index_1 ("1000, 1001");\n')
    f.write('            index_2 ("1000, 1001");\n')
    f.write('    }\n')
    f.write('    power_lut_template(%s_energy_template_clkslew) {\n' % name)
    f.write('        variable_1 : input_transition_time;\n')
    f.write('            index_1 ("1000, 1001");\n')
    f.write('    }\n')
    f.write('    power_lut_template(%s_energy_template_sigslew) {\n' % name)
    f.write('        variable_1 : input_transition_time;\n')
    f.write('            index_1 ("1000, 1001");\n')
    f.write('    }\n')
    f.write('    library_features(report_delay_calculation);\n')
    f.write('    type (%s_DATA) {\n' % name)
    f.write('        base_type : array ;\n')
    f.write('        data_type : bit ;\n')
    f.write('        bit_width : %d;\n' % p['bits'])
    f.write('        bit_from : %d;\n' % (p['bits']-1))
    f.write('        bit_to : 0 ;\n')
    f.write('        downto : true ;\n')
    f.write('    }\n')
    f.write('    type (%s_ADDRESS) {\n' % name)
    f.write('        base_type : array ;\n')
    f.write('        data_type : bit ;\n')
    f.write('        bit_width : %d;\n' % p['addr_width'])
    f.write('        bit_from : %d;\n' % p['addr_width_m1'])
    f.write('        bit_to : 0 ;\n')
    f.write('        downto : true ;\n')
    f.write('    }\n')


def _write_clk_pin(f, p):
    name = p['name']
    f.write('    pin(clk)   {\n')
    f.write('        direction : input;\n')
    f.write('        capacitance : %.3f;\n' % (p['min_driver_in_cap']*5))
    f.write('        clock : true;\n')
    f.write('        min_period           : %.3f ;\n' % p['min_period'])
    f.write('        internal_power(){\n')
    f.write('            rise_power(%s_energy_template_clkslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % p['slew_idx'])
    f.write('                values ("%.3f, %.3f")\n' % (p['clkpindynamic'], p['clkpindynamic']))
    f.write('            }\n')
    f.write('            fall_power(%s_energy_template_clkslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % p['slew_idx'])
    f.write('                values ("%.3f, %.3f")\n' % (p['clkpindynamic'], p['clkpindynamic']))
    f.write('            }\n')
    f.write('        }\n')
    f.write('    }\n\n')


def _write_ce_pin(f, p):
    name = p['name']
    f.write('    pin(ce_in){\n')
    f.write('        direction : input;\n')
    f.write('        capacitance : %.3f;\n' % p['min_driver_in_cap'])
    _write_setup_hold(f, p, 'ce_in')
    _write_sig_power(f, p, None)
    f.write('    }\n')


def _write_we_pin(f, p, we_name='we_in'):
    f.write('    pin(%s){\n' % we_name)
    f.write('        direction : input;\n')
    f.write('        capacitance : %.3f;\n' % p['min_driver_in_cap'])
    _write_setup_hold(f, p, we_name)
    _write_sig_power(f, p, None)
    f.write('    }\n')


def _write_setup_hold(f, p, pin_name):
    name = p['name']
    for timing_type in ('setup_rising', 'hold_rising'):
        tval = p['tsetup'] if timing_type == 'setup_rising' else p['thold']
        f.write('        timing() {\n')
        f.write('            related_pin : clk;\n')
        f.write('            timing_type : %s ;\n' % timing_type)
        for constraint in ('rise_constraint', 'fall_constraint'):
            f.write('            %s(%s_constraint_template) {\n' % (constraint, name))
            f.write('                index_1 ("%s");\n' % p['slew_idx'])
            f.write('                index_2 ("%s");\n' % p['slew_idx'])
            f.write('                values ( \\\n')
            f.write('                  "%.3f, %.3f", \\\n' % (tval, tval))
            f.write('                  "%.3f, %.3f" \\\n'  % (tval, tval))
            f.write('                )\n')
            f.write('            }\n')
        f.write('        }\n')


def _write_sig_power(f, p, we_pin):
    name = p['name']
    for when, we_val in [('! (we_in)', None), ('we_in', None)] if we_pin is None else [('! (%s)' % we_pin, None), (we_pin, None)]:
        f.write('        internal_power(){\n')
        if we_pin is not None:
            f.write('            when : "(%s)";\n' % when)
        f.write('            rise_power(%s_energy_template_sigslew) {\n' % name)
        f.write('                index_1 ("%s");\n' % p['slew_idx'])
        f.write('                values ("%.3f, %.3f")\n' % (p['pindynamic'], p['pindynamic']))
        f.write('            }\n')
        f.write('            fall_power(%s_energy_template_sigslew) {\n' % name)
        f.write('                index_1 ("%s");\n' % p['slew_idx'])
        f.write('                values ("%.3f, %.3f")\n' % (p['pindynamic'], p['pindynamic']))
        f.write('            }\n')
        f.write('        }\n')
        if we_pin is None:
            break  # single power group for pins that don't condition on we_in


def _write_rd_bus(f, p, bus_name, addr_pin):
    """Write a read-data bus group with memory_read(address: addr_pin)."""
    name = p['name']
    f.write('    bus(%s)   {\n' % bus_name)
    f.write('        bus_type : %s_DATA;\n' % name)
    f.write('        direction : output;\n')
    f.write('        max_capacitance : %.3f;\n' % p['max_load'])
    f.write('        memory_read() {\n')
    f.write('            address : %s;\n' % addr_pin)
    f.write('        }\n')
    f.write('        timing() {\n')
    f.write('            related_pin : "clk" ;\n')
    f.write('            timing_type : rising_edge;\n')
    f.write('            timing_sense : non_unate;\n')
    for delay_type in ('cell_rise', 'cell_fall'):
        f.write('            %s(%s_mem_out_delay_template) {\n' % (delay_type, name))
        f.write('                index_1 ("%s");\n' % p['slew_idx'])
        f.write('                index_2 ("%s");\n' % p['load_idx'])
        f.write('                values ( \\\n')
        f.write('                  "%.3f, %.3f", \\\n' % (p['tcq'], p['tcq']))
        f.write('                  "%.3f, %.3f" \\\n'  % (p['tcq'], p['tcq']))
        f.write('                )\n')
        f.write('            }\n')
    for slew_type in ('rise_transition', 'fall_transition'):
        f.write('            %s(%s_mem_out_slew_template) {\n' % (slew_type, name))
        f.write('                index_1 ("%s");\n' % p['load_idx'])
        f.write('                values ("%.3f, %.3f")\n' % (p['min_slew'], p['max_slew']))
        f.write('            }\n')
    f.write('        }\n')
    f.write('    }\n')


def _write_addr_bus(f, p, bus_name):
    """Write an address input bus with setup/hold constraints."""
    name = p['name']
    f.write('    bus(%s)   {\n' % bus_name)
    f.write('        bus_type : %s_ADDRESS;\n' % name)
    f.write('        direction : input;\n')
    f.write('        capacitance : %.3f;\n' % p['min_driver_in_cap'])
    _write_setup_hold(f, p, bus_name)
    f.write('        internal_power(){\n')
    f.write('            rise_power(%s_energy_template_sigslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % p['slew_idx'])
    f.write('                values ("%.3f, %.3f")\n' % (p['pindynamic'], p['pindynamic']))
    f.write('            }\n')
    f.write('            fall_power(%s_energy_template_sigslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % p['slew_idx'])
    f.write('                values ("%.3f, %.3f")\n' % (p['pindynamic'], p['pindynamic']))
    f.write('            }\n')
    f.write('        }\n')
    f.write('    }\n')


def _write_wd_bus(f, p, bus_name, addr_pin, we_pin):
    """Write a write-data input bus with memory_write(address: addr_pin)."""
    name = p['name']
    f.write('    bus(%s)   {\n' % bus_name)
    f.write('        bus_type : %s_DATA;\n' % name)
    f.write('        memory_write() {\n')
    f.write('            address : %s;\n' % addr_pin)
    f.write('            clocked_on : "clk";\n')
    f.write('        }\n')
    f.write('        direction : input;\n')
    f.write('        capacitance : %.3f;\n' % p['min_driver_in_cap'])
    _write_setup_hold(f, p, bus_name)
    for when_clause in ('! (%s)' % we_pin, we_pin):
        f.write('        internal_power(){\n')
        f.write('            when : "(%s)";\n' % when_clause)
        f.write('            rise_power(%s_energy_template_sigslew) {\n' % name)
        f.write('                index_1 ("%s");\n' % p['slew_idx'])
        f.write('                values ("%.3f, %.3f")\n' % (p['pindynamic'], p['pindynamic']))
        f.write('            }\n')
        f.write('            fall_power(%s_energy_template_sigslew) {\n' % name)
        f.write('                index_1 ("%s");\n' % p['slew_idx'])
        f.write('                values ("%.3f, %.3f")\n' % (p['pindynamic'], p['pindynamic']))
        f.write('            }\n')
        f.write('        }\n')
    f.write('    }\n')


def _write_wmask_bus(f, p, bus_name, addr_pin, we_pin):
    """Write a write-mask input bus."""
    name = p['name']
    f.write('    bus(%s)   {\n' % bus_name)
    f.write('        bus_type : %s_DATA;\n' % name)
    f.write('        memory_write() {\n')
    f.write('            address : %s;\n' % addr_pin)
    f.write('            clocked_on : "clk";\n')
    f.write('        }\n')
    f.write('        direction : input;\n')
    f.write('        capacitance : %.3f;\n' % p['min_driver_in_cap'])
    _write_setup_hold(f, p, bus_name)
    for when_clause in ('! (%s)' % we_pin, we_pin):
        f.write('        internal_power(){\n')
        f.write('            when : "(%s)";\n' % when_clause)
        f.write('            rise_power(%s_energy_template_sigslew) {\n' % name)
        f.write('                index_1 ("%s");\n' % p['slew_idx'])
        f.write('                values ("%.3f, %.3f")\n' % (p['pindynamic'], p['pindynamic']))
        f.write('            }\n')
        f.write('            fall_power(%s_energy_template_sigslew) {\n' % name)
        f.write('                index_1 ("%s");\n' % p['slew_idx'])
        f.write('                values ("%.3f, %.3f")\n' % (p['pindynamic'], p['pindynamic']))
        f.write('            }\n')
        f.write('        }\n')
    f.write('    }\n')


def _write_lib_footer(f, p):
    f.write('    cell_leakage_power : %.3f;\n' % p['leakage'])
    f.write('}\n\n}\n')


# ---------------------------------------------------------------------------
# 1RW
# ---------------------------------------------------------------------------

def _gen_lib_1rw(mem):
    p = _lib_params(mem)
    name = p['name']
    fout = os.sep.join([mem.results_dir, name + '.lib'])
    with open(fout, 'w') as f:
        _write_lib_header(f, p)

        f.write('cell(%s) {\n' % name)
        f.write('    area : %.3f;\n' % p['area'])
        f.write('    interface_timing : true;\n')
        f.write('    memory() {\n')
        f.write('        type : ram;\n')
        f.write('        address_width : %d;\n' % p['addr_width'])
        f.write('        word_width : %d;\n' % p['bits'])
        f.write('    }\n')

        _write_clk_pin(f, p)
        _write_rd_bus(f, p, 'rd_out', 'addr_in')
        _write_we_pin(f, p, 'we_in')
        _write_ce_pin(f, p)
        _write_addr_bus(f, p, 'addr_in')
        _write_wd_bus(f, p, 'wd_in', 'addr_in', 'we_in')
        _write_wmask_bus(f, p, 'w_mask_in', 'addr_in', 'we_in')
        _write_lib_footer(f, p)


# ---------------------------------------------------------------------------
# 1R1W  — separate read / write address buses
# ---------------------------------------------------------------------------

def _gen_lib_1r1w(mem):
    p = _lib_params(mem)
    name = p['name']
    fout = os.sep.join([mem.results_dir, name + '.lib'])
    with open(fout, 'w') as f:
        _write_lib_header(f, p)

        f.write('cell(%s) {\n' % name)
        f.write('    area : %.3f;\n' % p['area'])
        f.write('    interface_timing : true;\n')
        f.write('    memory() {\n')
        f.write('        type : ram;\n')
        f.write('        address_width : %d;\n' % p['addr_width'])
        f.write('        word_width : %d;\n' % p['bits'])
        f.write('    }\n')

        _write_clk_pin(f, p)

        # Read port: rd_out driven by rd_addr_in
        _write_rd_bus(f, p, 'rd_out', 'rd_addr_in')
        _write_addr_bus(f, p, 'rd_addr_in')

        # Write port: wd_in / w_mask_in addressed by wr_addr_in
        _write_we_pin(f, p, 'we_in')
        _write_ce_pin(f, p)
        _write_addr_bus(f, p, 'wr_addr_in')
        _write_wd_bus(f, p, 'wd_in', 'wr_addr_in', 'we_in')
        _write_wmask_bus(f, p, 'w_mask_in', 'wr_addr_in', 'we_in')
        _write_lib_footer(f, p)


# ---------------------------------------------------------------------------
# NR1W  — N independent read ports + 1 write port
# ---------------------------------------------------------------------------

def _gen_lib_nr1w(mem):
    p = _lib_params(mem)
    name = p['name']
    nr   = int(getattr(mem, 'num_r_ports', 2))
    fout = os.sep.join([mem.results_dir, name + '.lib'])
    with open(fout, 'w') as f:
        _write_lib_header(f, p)

        f.write('cell(%s) {\n' % name)
        f.write('    area : %.3f;\n' % p['area'])
        f.write('    interface_timing : true;\n')
        f.write('    memory() {\n')
        f.write('        type : ram;\n')
        f.write('        address_width : %d;\n' % p['addr_width'])
        f.write('        word_width : %d;\n' % p['bits'])
        f.write('    }\n')

        _write_clk_pin(f, p)

        # N independent read ports
        for i in range(nr):
            _write_rd_bus(f, p, f'rd_out_{i}', f'rd_addr_in_{i}')
            _write_addr_bus(f, p, f'rd_addr_in_{i}')

        # Single write port
        _write_we_pin(f, p, 'we_in')
        _write_ce_pin(f, p)
        _write_addr_bus(f, p, 'wr_addr_in')
        _write_wd_bus(f, p, 'wd_in', 'wr_addr_in', 'we_in')
        _write_wmask_bus(f, p, 'w_mask_in', 'wr_addr_in', 'we_in')
        _write_lib_footer(f, p)


# ---------------------------------------------------------------------------
# NRW  — N true-dual-port read-write ports
# ---------------------------------------------------------------------------

def _gen_lib_nrw(mem):
    p  = _lib_params(mem)
    name = p['name']
    nr   = int(getattr(mem, 'num_r_ports', 2))
    fout = os.sep.join([mem.results_dir, name + '.lib'])
    with open(fout, 'w') as f:
        _write_lib_header(f, p)

        f.write('cell(%s) {\n' % name)
        f.write('    area : %.3f;\n' % p['area'])
        f.write('    interface_timing : true;\n')
        f.write('    memory() {\n')
        f.write('        type : ram;\n')
        f.write('        address_width : %d;\n' % p['addr_width'])
        f.write('        word_width : %d;\n' % p['bits'])
        f.write('    }\n')

        _write_clk_pin(f, p)

        for i in range(nr):
            we_pin = f'rw_we_in_{i}'
            addr   = f'rw_addr_in_{i}'
            _write_rd_bus(f, p, f'rw_rd_out_{i}', addr)
            _write_we_pin(f, p, we_pin)
            _write_addr_bus(f, p, addr)
            _write_wd_bus(f, p, f'rw_wd_in_{i}', addr, we_pin)
            _write_wmask_bus(f, p, f'rw_w_mask_in_{i}', addr, we_pin)

        _write_ce_pin(f, p)
        _write_lib_footer(f, p)
