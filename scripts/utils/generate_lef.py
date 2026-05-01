import os
import sys
import math

################################################################################
# GENERATE LEF VIEW
#
# Generate a .lef file based on the given SRAM.
# Dispatches on mem.macro_class for correct pin names and counts.
################################################################################

def generate_lef( mem ):
    mc = getattr(mem, 'macro_class', '1RW')
    pin_groups = _build_pin_groups(mem, mc)
    _write_lef(mem, pin_groups)


def _build_pin_groups(mem, mc):
    """
    Return a list of pin groups, each group being a list of (pin_name, is_input).
    Groups are separated by spacing gaps in the LEF layout.
    """
    bits = int(mem.width_in_bits)
    aw   = math.ceil(math.log2(int(mem.depth)))
    nr   = int(getattr(mem, 'num_r_ports', 1))

    if mc == '1R1W':
        return [
            [('w_mask_in[%d]' % i, True)  for i in range(bits)],
            [('rd_out[%d]'    % i, False) for i in range(bits)],
            [('wd_in[%d]'     % i, True)  for i in range(bits)],
            [('rd_addr_in[%d]'% i, True)  for i in range(aw)],
            [('wr_addr_in[%d]'% i, True)  for i in range(aw)],
            [('we_in', True), ('ce_in', True), ('clk', True)],
        ]
    elif mc == 'NR1W':
        groups = []
        for i in range(nr):
            groups.append([('rd_out_%d[%d]'     % (i, b), False) for b in range(bits)])
            groups.append([('rd_addr_in_%d[%d]' % (i, b), True)  for b in range(aw)])
        groups.append([('w_mask_in[%d]' % b, True) for b in range(bits)])
        groups.append([('wd_in[%d]'     % b, True) for b in range(bits)])
        groups.append([('wr_addr_in[%d]'% b, True) for b in range(aw)])
        groups.append([('we_in', True), ('ce_in', True), ('clk', True)])
        return groups
    elif mc == 'NRW':
        groups = []
        for i in range(nr):
            groups.append([('rw_rd_out_%d[%d]'   % (i, b), False) for b in range(bits)])
            groups.append([('rw_wd_in_%d[%d]'     % (i, b), True)  for b in range(bits)])
            groups.append([('rw_w_mask_in_%d[%d]' % (i, b), True)  for b in range(bits)])
            groups.append([('rw_addr_in_%d[%d]'   % (i, b), True)  for b in range(aw)])
            groups.append([('rw_we_in_%d' % i, True)])
        groups.append([('ce_in', True), ('clk', True)])
        return groups
    else:  # 1RW (default)
        return [
            [('w_mask_in[%d]' % i, True)  for i in range(bits)],
            [('rd_out[%d]'    % i, False) for i in range(bits)],
            [('wd_in[%d]'     % i, True)  for i in range(bits)],
            [('addr_in[%d]'   % i, True)  for i in range(aw)],
            [('we_in', True), ('ce_in', True), ('clk', True)],
        ]


def _write_lef(mem, pin_groups):
    name            = mem.name
    w               = mem.width_um
    h               = mem.height_um
    min_pin_width   = mem.process.pinWidth_um
    pin_height      = mem.process.pinHeight_um
    min_pin_pitch   = mem.process.pinPitch_um
    metalPrefix     = mem.process.metalPrefix
    flip            = mem.process.flipPins.lower() == 'true'
    supply_pin_width     = min_pin_width * 4
    supply_pin_half_width = supply_pin_width / 2
    supply_pin_pitch     = min_pin_pitch * 8
    supply_pin_layer     = '%s4' % metalPrefix

    x_offset = 10 * min_pin_pitch
    y_offset = 10 * min_pin_pitch

    # Total pin count across all groups
    number_of_pins = sum(len(g) for g in pin_groups)
    number_of_tracks_available = math.floor((h - 2*y_offset) / min_pin_pitch)
    number_of_spare_tracks = number_of_tracks_available - number_of_pins

    print(f'Final {name} size = {w} x {h}')
    print(f'num pins: {number_of_pins}, available tracks: {number_of_tracks_available}')
    if number_of_spare_tracks < 0:
        print("ERROR: not enough tracks!")
        sys.exit(1)

    track_count = 1
    while number_of_spare_tracks > 0:
        track_count += 1
        number_of_spare_tracks = number_of_tracks_available - number_of_pins * track_count
    track_count -= 1

    pin_pitch   = min_pin_pitch * track_count
    num_gaps    = max(len(pin_groups) - 1, 1)
    group_pitch = math.floor(
        (number_of_tracks_available - number_of_pins * track_count) / num_gaps
    ) * mem.process.pinPitch_um

    fid = open(os.sep.join([mem.results_dir, name + '.lef']), 'w')

    # --- LEF header ---
    fid.write('VERSION 5.7 ;\n')
    fid.write('BUSBITCHARS "[]" ;\n')
    fid.write('MACRO %s\n' % name)
    fid.write('  FOREIGN %s 0 0 ;\n' % name)
    fid.write('  SYMMETRY X Y R90 ;\n')
    fid.write('  SIZE %.3f BY %.3f ;\n' % (w, h))
    fid.write('  CLASS BLOCK ;\n')

    # --- Signal pins ---
    y_step = y_offset
    for gi, group in enumerate(pin_groups):
        for pin_name, is_input in group:
            y_step = lef_add_pin(fid, mem, pin_name, is_input, y_step, pin_pitch)
        if gi < len(pin_groups) - 1:
            y_step += group_pitch - pin_pitch

    # --- Supply straps ---
    if flip:
        for rail, use, start in [('VSS', 'GROUND', x_offset), ('VDD', 'POWER', x_offset + supply_pin_pitch)]:
            x_step = start
            fid.write('  PIN %s\n' % rail)
            fid.write('    DIRECTION INOUT ;\n')
            fid.write('    USE %s ;\n' % use)
            fid.write('    PORT\n')
            fid.write('      LAYER %s ;\n' % supply_pin_layer)
            while x_step <= w - x_offset:
                fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (
                    x_step - supply_pin_half_width, y_offset,
                    x_step + supply_pin_half_width, h - y_offset))
                x_step += supply_pin_pitch * 2
            fid.write('    END\n')
            fid.write('  END %s\n' % rail)
    else:
        for rail, use, start in [('VSS', 'GROUND', y_offset), ('VDD', 'POWER', y_offset + supply_pin_pitch)]:
            y_s = start
            fid.write('  PIN %s\n' % rail)
            fid.write('    DIRECTION INOUT ;\n')
            fid.write('    USE %s ;\n' % use)
            fid.write('    PORT\n')
            fid.write('      LAYER %s ;\n' % supply_pin_layer)
            while y_s <= h - y_offset:
                fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (
                    x_offset, y_s - supply_pin_half_width,
                    w - x_offset, y_s + supply_pin_half_width))
                y_s += supply_pin_pitch * 2
            fid.write('    END\n')
            fid.write('  END %s\n' % rail)

    # --- Obstructions ---
    fid.write('  OBS\n')
    fid.write('    LAYER %s1 ;\n' % metalPrefix)
    fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w, h))
    fid.write('    LAYER %s2 ;\n' % metalPrefix)
    fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w, h))
    fid.write('    LAYER %s3 ;\n' % metalPrefix)

    if flip:
        fid.write('    RECT %.3f 0 %.3f %.3f ;\n' % (pin_height, w, h))
        prev_y = 0
        y_step = y_offset
        for gi, group in enumerate(pin_groups):
            for _ in group:
                fid.write('    RECT 0 %.3f %.3f %.3f ;\n' % (prev_y, pin_height, y_step - min_pin_width/2))
                prev_y = y_step + min_pin_width/2
                y_step += pin_pitch
            if gi < len(pin_groups) - 1:
                y_step += group_pitch - pin_pitch
        fid.write('    RECT 0 %.3f %.3f %.3f ;\n' % (prev_y, pin_height, h))
    else:
        fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w, h))

    fid.write('    LAYER %s4 ;\n' % metalPrefix)
    if flip:
        fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w, y_offset))
        fid.write('    RECT 0 %.3f %.3f %.3f ;\n' % (h - y_offset, w, h))
        prev_x = 0
        x_step = x_offset
        while x_step <= w - x_offset:
            fid.write('    RECT %.3f %.3f %.3f %.3f ;\n' % (
                prev_x, y_offset, x_step - supply_pin_half_width, h - y_offset))
            prev_x = x_step + supply_pin_half_width
            x_step += supply_pin_pitch
        fid.write('    RECT %.3f %.3f %.3f %.3f ;\n' % (prev_x, y_offset, w, h - y_offset))
    else:
        fid.write('    RECT %.3f 0 %.3f %.3f ;\n' % (min_pin_width, x_offset, h))
        fid.write('    RECT %.3f 0 %.3f %.3f ;\n' % (w - x_offset, w, h))
        prev_y = 0
        y_step = y_offset
        while y_step <= h - y_offset:
            fid.write('    RECT %.3f %.3f %.3f %.3f ;\n' % (x_offset, prev_y, w - x_offset, y_step - supply_pin_half_width))
            prev_y = y_step + supply_pin_half_width
            y_step += supply_pin_pitch
        fid.write('    RECT %.3f %.3f %.3f %.3f ;\n' % (x_offset, prev_y, w - x_offset, h))
        prev_y = 0
        y_step = y_offset
        for gi, group in enumerate(pin_groups):
            for _ in group:
                fid.write('    RECT 0 %.3f %.3f %.3f ;\n' % (prev_y, min_pin_width, y_step - min_pin_width/2))
                prev_y = y_step + min_pin_width/2
                y_step += pin_pitch
            if gi < len(pin_groups) - 1:
                y_step += group_pitch - pin_pitch
        fid.write('    RECT 0 %.3f %.3f %.3f ;\n' % (prev_y, min_pin_width, h))

    fid.write('    LAYER OVERLAP ;\n')
    fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w, h))
    fid.write('  END\n')
    fid.write('END %s\n\n' % name)
    fid.write('END LIBRARY\n')
    fid.close()


def lef_add_pin(fid, mem, pin_name, is_input, y, pitch):
    layer = mem.process.metalPrefix + ('3' if mem.process.flipPins.lower() == 'true' else '4')
    hpw = mem.process.pinWidth_um / 2.0
    ph  = mem.process.pinHeight_um

    fid.write('  PIN %s\n' % pin_name)
    fid.write('    DIRECTION %s ;\n' % ('INPUT' if is_input else 'OUTPUT'))
    fid.write('    USE SIGNAL ;\n')
    fid.write('    SHAPE ABUTMENT ;\n')
    fid.write('    PORT\n')
    fid.write('      LAYER %s ;\n' % layer)
    fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (0, y - hpw, ph, y + hpw))
    fid.write('    END\n')
    fid.write('  END %s\n' % pin_name)

    return y + pitch
