import math
from pathlib import Path
from xml.etree import ElementTree as ET


PCACTI_TECH_PROFILES = {
  7: {
    'transistor_type': 'finfet',
    'technology_node': '0.007',
    'device': 'xmls/devices/finfet_7nm_std.xml',
    'near_threshold': True,
  },
  14: {
    'transistor_type': 'cmos',
    'technology_node': '0.014',
    'device': 'xmls/devices/cmos_14nm_std.xml',
    'near_threshold': True,
  },
  22: {
    'transistor_type': 'cmos',
    'technology_node': '0.022',
    'device': 'xmls/devices/cmos_22nm_hp.xml',
    'near_threshold': False,
  },
}


def write_pcacti_config(mem, pcacti_dir, output_file):
  """Write a P-CACTI XML config for one Memory instance."""
  pcacti_dir = Path(pcacti_dir)
  output_file = Path(output_file)
  profile = _pcacti_profile(mem, pcacti_dir)

  device_file = pcacti_dir / profile['device']
  sram_cell_file = output_file.with_name('pcacti_sram_cell.xml')
  _write_sram_cell_config(sram_cell_file, device_file, profile['transistor_type'])

  block_size_bytes = _model_block_size(mem.width_in_bytes)
  cache_size_bytes = _model_cache_size(mem.total_size, mem.num_banks, block_size_bytes)
  bus_width_bits = mem.width_in_bytes * 8
  rw_ports, r_ports, w_ports = _model_port_counts(mem)

  root = ET.Element('cache_config')
  _text(root, 'transistor_type', profile['transistor_type'])
  _text(root, 'technology_node', profile['technology_node'])
  _text(root, 'operating_voltage', _operating_voltage(mem.process.voltage, profile))
  _text(root, 'temperature', '300')
  _text(root, 'cache_size', str(cache_size_bytes))
  _text(root, 'block_size', str(block_size_bytes))
  _text(root, 'associativity', '1')

  devices = ET.SubElement(root, 'devices')
  for array_name in ('data_array', 'tag_array'):
    array = ET.SubElement(devices, array_name)
    _text(array, 'cell', str(device_file))
    _text(array, 'peripheral', str(device_file))
  _text(devices, 'dram', str(device_file))

  _text(root, 'sram_cell', str(sram_cell_file))

  ports = ET.SubElement(root, 'ports')
  _text(ports, 'read_write_port', str(rw_ports))
  _text(ports, 'exclusive_read_port', str(r_ports))
  _text(ports, 'exclusive_write_port', str(w_ports))
  _text(ports, 'single_ended_read_ports', '0')

  _text(root, 'cache_model', 'UCA')
  _text(root, 'uca_bank_count', str(mem.num_banks))
  _text(root, 'nuca_bank_count', '0')
  _text(root, 'bus_width', str(bus_width_bits))
  _text(root, 'memory_type', mem.cache_type)
  _text(root, 'tag_size', 'default')
  _text(root, 'access_mode', 'normal')

  objective = ET.SubElement(root, 'objective_function')
  _text(objective, 'optimize', 'NONE')
  _objective(objective, 'design_objective',
             weights=(0, 0, 0, 100, 0),
             deviations=(20, 100000, 100000, 100000, 100000))
  _objective(objective, 'nuca_design_objective',
             weights=(100, 100, 0, 0, 100),
             deviations=(10, 10000, 10000, 10000, 10000))

  interconnects = ET.SubElement(root, 'interconnects')
  _text(interconnects, 'source', 'RonHo2003')
  _text(interconnects, 'wire_signalling', 'default')
  wire_type = ET.SubElement(interconnects, 'wire_type')
  _text(wire_type, 'inside_mat', 'global')
  _text(wire_type, 'outside_mat', 'global')
  _text(interconnects, 'projection', 'conservative')

  _text(root, 'core_count', '8')
  _text(root, 'cache_level', 'L3')
  _text(root, 'add_ecc', 'true')
  _text(root, 'print_level', 'DETAILED')
  _text(root, 'print_input_parameters', 'false')
  _text(root, 'force_cache_config', 'false')
  _text(root, 'Ndwl', '1')
  _text(root, 'Ndbl', '1')
  _text(root, 'Nspd', '0')
  _text(root, 'Ndcm', '1')
  _text(root, 'Ndsam1', '0')
  _text(root, 'Ndsam2', '0')
  _text(root, 'page_size', '8192')
  _text(root, 'burst_length', '8')
  _text(root, 'internal_prefetch_width', '8')

  ET.indent(root, space='  ')
  tree = ET.ElementTree(root)
  tree.write(output_file, encoding='utf-8', xml_declaration=True)


def _write_sram_cell_config(output_file, device_file, transistor_type):
  root = ET.Element('sram_cell')
  _text(root, 'type', '6T')
  _text(root, 'dual_gate_control', 'false')
  _text(root, 'device_type', str(device_file))

  leakage = ET.SubElement(root, 'leakage_power')
  _text(leakage, 'bitline', '')
  _text(leakage, 'cc_inverters', '')

  transistors = ET.SubElement(root, 'transistor_parameters')
  for name in ('acc', 'pup', 'pdn'):
    node = ET.SubElement(transistors, name)
    if transistor_type == 'finfet':
      _text(node, 'num_of_fins', '1')
    _text(node, 'device_type', str(device_file))

  ET.indent(root, space='  ')
  tree = ET.ElementTree(root)
  tree.write(output_file, encoding='utf-8', xml_declaration=True)


def _pcacti_profile(mem, pcacti_dir):
  if mem.process.tech_nm not in PCACTI_TECH_PROFILES:
    supported = ', '.join(str(node) for node in sorted(PCACTI_TECH_PROFILES))
    raise ValueError(
      f"P-CACTI has no checked-in characterization profile for "
      f"{mem.process.tech_nm} nm ({mem.name}). Available profiles: {supported} nm."
    )
  profile = PCACTI_TECH_PROFILES[mem.process.tech_nm]
  if mem.num_banks < 1 or not _is_power_of_two(mem.num_banks):
    raise ValueError(f"sram '{mem.name}': banks must be a positive power of two")
  device_file = pcacti_dir / profile['device']
  if not device_file.is_file():
    raise FileNotFoundError(f"P-CACTI characterization file missing: {device_file}")
  return profile


def _operating_voltage(voltage, profile):
  if profile['near_threshold'] and float(voltage) <= 0.4:
    return 'near-threshold'
  return 'super-threshold'


def _model_block_size(width_in_bytes):
  # P-CACTI crashes for 4-byte lines in observed 7 nm smoke tests. Model
  # narrower memories with an 8-byte minimum while preserving the macro bus.
  return _next_power_of_two(max(8, int(width_in_bytes)))


def _model_cache_size(total_size, banks, block_size):
  min_size = max(int(total_size), int(banks) * 64, int(banks) * block_size * 4)
  return _next_power_of_two(min_size)


def _model_port_counts(mem):
  rw_ports = int(mem.rw_ports)
  r_ports = int(mem.r_ports)
  w_ports = int(mem.w_ports)
  if rw_ports + r_ports > 0:
    return rw_ports, r_ports, w_ports

  if w_ports < 1:
    raise ValueError(f"sram '{mem.name}': P-CACTI requires at least one modeled port")

  # P-CACTI asserts when the modeled SRAM has no read-capable port because it
  # always computes read energy. For write-only macros, model one write port as
  # read-write for PPA while preserving the actual generated macro port shape.
  return 1, 0, w_ports - 1


def _objective(parent, name, weights, deviations):
  node = ET.SubElement(parent, name)
  weight_node = ET.SubElement(node, 'weights')
  deviation_node = ET.SubElement(node, 'deviations')
  keys = ('delay', 'dynamic_power', 'leakage_power', 'cycle_time', 'area')
  for key, value in zip(keys, weights):
    _text(weight_node, key, str(value))
  for key, value in zip(keys, deviations):
    _text(deviation_node, key, str(value))


def _text(parent, name, value):
  child = ET.SubElement(parent, name)
  child.text = str(value)
  return child


def _next_power_of_two(value):
  value = max(1, int(math.ceil(value)))
  return 1 << (value - 1).bit_length()


def _is_power_of_two(value):
  value = int(value)
  return value > 0 and value & (value - 1) == 0
