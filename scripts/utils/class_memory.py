import math
import os
import subprocess
from pathlib import Path
from utils.cacti_config import write_cacti_config
from utils.cacti_results import read_cacti_cfg_out
from utils.pcacti_config import PCACTI_TECH_PROFILES, write_pcacti_config
from utils.pcacti_results import read_pcacti_csv
from utils.port_shape import from_sram_data

################################################################################
# MEMORY CLASS
#
# Stores the information about a specific memory being generated. Takes a
# process object plus one of the items in the "srams" list of the JSON
# configuration, then runs the selected modeling backend to fill in the rest
# of the data.
#
# bsg_fakeram dispatches every artifact (Verilog/LEF/Liberty/memlib/techmap)
# on `mem.shape : PortShape(rw, r, w)` — the canonical port-shape descriptor
# emitted by the cfg producer. The cfg MUST carry a `port_shape` field; this
# class hard-fails on cfg entries that don't, rather than silently falling
# back to a 1RW interpretation as the legacy code used to.
################################################################################

class Memory:

  def __init__( self, process, sram_data , output_dir = None, cacti_dir = None, pcacti_dir = None, model_backend = 'auto'):

    self.process        = process
    self.name           = str(sram_data['name'])
    self.width_in_bits  = int(sram_data['width'])
    self.depth          = int(sram_data['depth'])
    self.num_banks      = int(sram_data['banks'])
    self.cache_type     = str(sram_data['type']) if 'type' in sram_data else 'ram'

    self.shape          = from_sram_data(sram_data)
    self.rw_ports       = self.shape.rw
    self.r_ports        = self.shape.r
    self.w_ports        = self.shape.w

    self.width_in_bytes = math.ceil(self.width_in_bits / 8.0)
    self.total_size     = self.width_in_bytes * self.depth
    if output_dir:
      p = str(Path(output_dir).expanduser().resolve(strict=False))
      self.results_dir = os.sep.join([p, self.name])
    else:
      self.results_dir = os.sep.join([os.getcwd(), 'results', self.name])
    if not os.path.exists( self.results_dir ):
      os.makedirs( self.results_dir )
    self.model_backend = self.__select_model_backend(model_backend)
    self.cacti_dir = self.__tool_dir(cacti_dir, 'CACTI_BUILD_DIR', 'tools/cacti')
    self.pcacti_dir = self.__tool_dir(pcacti_dir, 'PCACTI_BUILD_DIR', 'tools/pcacti')

    if self.model_backend == 'pcacti':
      model_data = self.__run_pcacti()
    elif self.model_backend == 'cacti':
      model_data = self.__run_cacti()
    else:
      raise ValueError(f"unknown model backend '{self.model_backend}'")

    self.tech_node_nm                = int(float(model_data['tech_node_nm']))
    self.capacity_bytes              = int(float(model_data['capacity_bytes']))
    self.associativity               = int(float(model_data['associativity']))
    self.output_width_bits           = int(float(model_data['output_width_bits']))
    self.access_time_ns              = float(model_data['access_time_ns'])
    self.cycle_time_ns               = float(model_data['cycle_time_ns'])
    self.dyn_read_energy_nj          = float(model_data['dyn_read_energy_nj'])
    self.dyn_write_energy_nj         = float(model_data['dyn_write_energy_nj'])
    self.standby_leakage_per_bank_mW = float(model_data['standby_leakage_per_bank_mw'])
    self.area_mm2                    = float(model_data['area_mm2'])
    self.fo4_ps                      = float(model_data['fo4_ps'])
    self.width_um                    = float(model_data['width_um'])
    self.height_um                   = float(model_data['height_um'])

    self.cap_input_pf = 0.005

    self.tech_node_um = self.tech_node_nm / 1000.0

    print(f'Original {self.name} size = {self.width_um} x {self.height_um}')
    self.width_um = (math.ceil((self.width_um*1000.0)/self.process.snapWidth_nm)*self.process.snapWidth_nm)/1000.0
    self.height_um = (math.ceil((self.height_um*1000.0)/self.process.snapHeight_nm)*self.process.snapHeight_nm)/1000.0
    self.area_um2 = self.width_um * self.height_um

    self.pin_dynamic_power_mW = self.dyn_write_energy_nj

    self.t_setup_ns = 0.050  ;# arbitrary 50ps setup
    self.t_hold_ns  = 0.050  ;# arbitrary 50ps hold

  def __tool_dir(self, selected, env_var, default_relative):
    if selected is None:
      selected = os.environ.get(env_var)
    if selected is None:
      selected = Path(__file__).resolve().parents[2] / default_relative
    return str(Path(selected).expanduser().resolve(strict=False))

  def __select_model_backend(self, requested):
    if requested not in ('auto', 'pcacti', 'cacti'):
      raise ValueError(f"model_backend must be one of auto, pcacti, or cacti; got '{requested}'")
    tech_nm = int(self.process.tech_nm)
    if requested != 'auto':
      if requested == 'cacti' and tech_nm < 22:
        raise ValueError(
          f"legacy CACTI is not the right backend for {tech_nm} nm ({self.name}); "
          "use P-CACTI for nodes below 22 nm."
        )
      return requested

    if tech_nm < 22:
      if tech_nm not in PCACTI_TECH_PROFILES:
        supported = ', '.join(str(node) for node in sorted(node for node in PCACTI_TECH_PROFILES if node < 22))
        raise ValueError(
          f"no P-CACTI characterization profile for {tech_nm} nm ({self.name}). "
          f"Auto backend uses P-CACTI below 22 nm; available sub-22 profiles: {supported} nm."
        )
      return 'pcacti'
    return 'cacti'

  def __run_cacti( self ):
    cacti_dir = Path(self.cacti_dir)
    cacti_bin = cacti_dir / 'cacti'
    if not cacti_bin.is_file():
      raise FileNotFoundError(f"legacy CACTI binary not found: {cacti_bin}. Run `make tools` first.")

    cfg = Path(self.results_dir) / 'cacti.cfg'
    detailed = Path(self.results_dir) / 'cacti_detailed_report.txt'
    result_csv = Path(self.results_dir) / 'cacti.cfg.out'

    write_cacti_config(self, cfg)
    result_csv.unlink(missing_ok=True)

    with open(detailed, 'w') as stdout:
      proc = subprocess.run(
        [str(cacti_bin), '-infile', str(cfg)],
        cwd=str(cacti_dir),
        stdout=stdout,
        stderr=subprocess.PIPE,
        text=True,
      )
    if proc.returncode != 0:
      detail = detailed.read_text().strip()
      message = proc.stderr.strip() or detail
      raise RuntimeError(f"legacy CACTI failed for {self.name}: {message}")
    if not result_csv.is_file():
      raise FileNotFoundError(f"legacy CACTI did not write expected result CSV: {result_csv}")

    return read_cacti_cfg_out(result_csv)

  def __run_pcacti( self ):
    pcacti_dir = Path(self.pcacti_dir)
    pcacti_bin = pcacti_dir / 'cacti'
    if not pcacti_bin.is_file():
      raise FileNotFoundError(f"P-CACTI binary not found: {pcacti_bin}. Run `make tools` first.")

    cfg = Path(self.results_dir) / 'pcacti.xml'
    detailed = Path(self.results_dir) / 'pcacti_detailed_report.txt'
    result_report = Path(self.results_dir) / 'pcacti_report.txt'
    result_csv = Path(self.results_dir) / 'pcacti.csv'

    write_pcacti_config(self, pcacti_dir, cfg)
    for stale in (result_report, result_csv):
      stale.unlink(missing_ok=True)

    with open(detailed, 'w') as stdout:
      proc = subprocess.run(
        [str(pcacti_bin), '-infile', str(cfg)],
        cwd=self.results_dir,
        stdout=stdout,
        stderr=subprocess.PIPE,
        text=True,
      )
    if proc.returncode != 0:
      detail = detailed.read_text().strip()
      message = proc.stderr.strip() or detail
      raise RuntimeError(f"P-CACTI failed for {self.name}: {message}")
    if not result_csv.is_file():
      raise FileNotFoundError(f"P-CACTI did not write expected result CSV: {result_csv}")

    return read_pcacti_csv(result_csv)
