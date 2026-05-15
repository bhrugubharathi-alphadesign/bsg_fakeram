import csv


REQUIRED_FIELDS = (
  'tech_node_nm',
  'capacity_bytes',
  'associativity',
  'output_width_bits',
  'access_time_ns',
  'cycle_time_ns',
  'dyn_read_energy_nj',
  'dyn_write_energy_nj',
  'standby_leakage_per_bank_mw',
  'area_mm2',
  'fo4_ps',
  'width_um',
  'height_um',
)


def read_pcacti_csv(path):
  with open(path, newline='') as fid:
    rows = list(csv.DictReader(fid))
  if len(rows) != 1:
    raise ValueError(f"expected exactly one P-CACTI result row in {path}, found {len(rows)}")
  row = rows[0]
  missing = [field for field in REQUIRED_FIELDS if field not in row]
  if missing:
    raise ValueError(f"P-CACTI result {path} missing fields: {', '.join(missing)}")
  return row
