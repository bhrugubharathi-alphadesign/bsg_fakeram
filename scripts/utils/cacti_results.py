def read_cacti_cfg_out(path):
  """Read the patched legacy CACTI CSV output as the common model-data shape."""
  with open(path, 'r') as fid:
    lines = [line.strip() for line in fid if line.strip()]
  if not lines:
    raise ValueError(f"legacy CACTI result is empty: {path}")

  values = [value.strip() for value in lines[-1].split(',')]
  if len(values) < 14:
    raise ValueError(f"legacy CACTI result {path} has {len(values)} fields; expected at least 14")

  return {
    'tech_node_nm': values[0],
    'capacity_bytes': values[1],
    'associativity': values[2],
    'output_width_bits': values[3],
    'access_time_ns': values[4],
    'cycle_time_ns': values[5],
    'dyn_read_energy_nj': values[7],
    'dyn_write_energy_nj': values[8],
    'standby_leakage_per_bank_mw': values[9],
    'area_mm2': values[10],
    'fo4_ps': values[11],
    'width_um': values[12],
    'height_um': values[13],
  }
