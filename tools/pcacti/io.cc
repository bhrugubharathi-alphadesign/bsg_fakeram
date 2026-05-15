/*------------------------------------------------------------
 *                              CACTI 6.5
 *         Copyright 2008 Hewlett-Packard Development Corporation
 *                         All Rights Reserved
 *
 * Permission to use, copy, and modify this software and its documentation is
 * hereby granted only under the following terms and conditions.  Both the
 * above copyright notice and this permission notice must appear in all copies
 * of the software, derivative works or modified versions, and any portions
 * thereof, and both notices must appear in supporting documentation.
 *
 * Users of this software agree to the terms and conditions set forth herein, and
 * hereby grant back to Hewlett-Packard Company and its affiliated companies ("HP")
 * a non-exclusive, unrestricted, royalty-free right and license under any changes, 
 * enhancements or extensions  made to the core functions of the software, including 
 * but not limited to those affording compatibility with other hardware or software
 * environments, but excluding applications which incorporate this software.
 * Users further agree to use their best efforts to return to HP any such changes,
 * enhancements or extensions that they make and inform HP of noteworthy uses of
 * this software.  Correspondence should be provided to HP at:
 *
 *                       Director of Intellectual Property Licensing
 *                       Office of Strategy and Technology
 *                       Hewlett-Packard Company
 *                       1501 Page Mill Road
 *                       Palo Alto, California  94304
 *
 * This software may be distributed (but not offered for sale or transferred
 * for compensation) to third parties, provided such third parties agree to
 * abide by the terms and conditions of this notice.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND HP DISCLAIMS ALL
 * WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS.   IN NO EVENT SHALL HP 
 * CORPORATION BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL
 * DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR
 * PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
 * ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
 * SOFTWARE.
 *------------------------------------------------------------*/

#include <fstream>
#include <iostream>
#include <sstream>
#include <stdlib.h>	// Majid
#include <stdio.h>	// Majid

#include "io.h"
#include "area.h"
#include "basic_circuit.h"
#include "parameter.h"
#include "Ucache.h"
#include "nuca.h"
#include "crossbar.h"
#include "arbiter.h"
#include "xmlParser.h"	// Majid

using namespace std;



/* Parses "cache.cfg" file */
void InputParameter::parse_cfg(const string & in_file)
{
  FILE *fp = fopen(in_file.c_str(), "r");
  char line[5000];
  char jk[5000];
  char temp_var[5000];

  if(!fp) {
    cout << in_file << " is missing!\n";
    exit(-1);
  }

	/******************** MAJID BEGIN ********************/
	
	XMLNode xMainNode = XMLNode::openFileHelper(in_file.c_str(), "cache_config");
	
	if ( xMainNode.getChildNode("transistor_type").isEmpty() ) {
		cerr << "XML ERROR: <transistor_type> in the '" << in_file <<"' file is missing.\n";
		exit(0);
	} else if ( xMainNode.getChildNode("transistor_type").nText() == 0 ) {
		cerr << "XML ERROR: <transistor_type> in the '" << in_file <<"' file does not have a value.\n";
		cerr << "Please specify either 'finfet' or 'cmos' as the transistor type." << endl;
		exit(0);
	} else {
		strcpy(temp_var,xMainNode.getChildNode("transistor_type").getText(0));
		for (int i = 0; temp_var[i]; i++) { temp_var[i] = tolower(temp_var[i]); }
		if (!strncmp("finfet", temp_var, strlen("finfet"))) {
			is_finfet = 1;
		} else if (!strncmp("cmos", temp_var, strlen("cmos"))) {
			is_finfet = 0;
		} else {
			cerr << "ERROR: Invalid transistor type!\nSupported transistor types: 'finfet', 'cmos'.\n";
			exit(0);
		}
	}
	
	if ( xMainNode.getChildNode("technology_node").isEmpty() ) {
		cerr << "XML ERROR: <technology_node> in the '" << in_file <<"' file is missing.\n";
		exit(0);
	} else if ( xMainNode.getChildNode("technology_node").nText() == 0 ) {
		cerr << "XML ERROR: <technology_node> in the '" << in_file <<"' file does not have a value.\n";
		exit(0);
	} else {
		strcpy(temp_var,xMainNode.getChildNode("technology_node").getText(0));
		sscanf(temp_var, "%lf", &(F_sz_um));
		F_sz_nm = F_sz_um*1000;
	}
	
	if ( xMainNode.getChildNode("operating_voltage").isEmpty() ) {
		cerr << "XML ERROR: <operating_voltage> in the '" << in_file <<"' file is missing.\n";
		exit(0);
	} else if ( xMainNode.getChildNode("operating_voltage").nText() == 0 ) {
		cerr << "XML ERROR: <operating_voltage> in the '" << in_file <<"' file does not have a value.\n";
		cerr << "Please specify either 'super-threshold' or 'near-threshold' as the operating voltage." << endl;
		exit(0);
	} else {
		strcpy(temp_var,xMainNode.getChildNode("operating_voltage").getText(0));
		for (int i = 0; temp_var[i]; i++) { temp_var[i] = tolower(temp_var[i]); }
		if (!strncmp("near-threshold", temp_var, strlen("near-threshold"))) {
			is_near_threshold = 1;
		} else if (!strncmp("super-threshold", temp_var, strlen("super-threshold"))) {
			is_near_threshold = 0;
		} else {
			cerr << "ERROR: Invalid operating voltage!\nSupported operating voltages: 'super-threshold', 'near-threshold'.\n";
			exit(0);
		}
	}
	
	if ( xMainNode.getChildNode("temperature").isEmpty() ) {
		cerr << "XML ERROR: <temperature> in the '" << in_file <<"' file is missing.\n";
		exit(0);
	} else if ( xMainNode.getChildNode("temperature").nText() == 0 ) {
		cerr << "XML ERROR: <temperature> in the '" << in_file <<"' file does not have a value.\n";
		cerr << "Please specify a number between 300 and 400, which is a multiple of 10." << endl;
		exit(0);
	} else {
		strcpy(temp_var,xMainNode.getChildNode("temperature").getText(0));
		sscanf(temp_var, "%u", &(temp));
		if (temp < 300 || temp > 400 || temp%10 != 0) {
			cerr << "ERROR: " << temp << "K is not a valid temperature." << endl;
			cerr << "The temperature must be a multiple of 10 between 300K and 400K." << endl;
			exit(0);
		}
	}
	
	strcpy(temp_var,xMainNode.getChildNode("cache_size").getText(0));
	sscanf(temp_var, "%u", &(cache_sz));
	
	strcpy(temp_var,xMainNode.getChildNode("block_size").getText(0));
	sscanf(temp_var, "%u", &(line_sz));
	
	strcpy(temp_var,xMainNode.getChildNode("associativity").getText(0));
	sscanf(temp_var, "%u", &(assoc));
	
	strcpy(data_array_cell_tech_file,xMainNode.getChildNode("devices").getChildNode("data_array").getChildNode("cell").getText(0));
	strcpy(data_array_peri_tech_file,xMainNode.getChildNode("devices").getChildNode("data_array").getChildNode("peripheral").getText(0));
	strcpy(tag_array_cell_tech_file,xMainNode.getChildNode("devices").getChildNode("tag_array").getChildNode("cell").getText(0));
	strcpy(tag_array_peri_tech_file,xMainNode.getChildNode("devices").getChildNode("tag_array").getChildNode("peripheral").getText(0));

	string sram_cell_file = xMainNode.getChildNode("sram_cell").getText(0);
	XMLNode SRAM_cell_conf_node = XMLNode::openFileHelper(sram_cell_file.c_str(),"sram_cell");
	strcpy(temp_var,SRAM_cell_conf_node.getChildNode("type").getText(0));
	if (!strncmp("6T", temp_var, strlen("6T"))) {
		sram_cell_design.setType(std_6T);
	} else if (!strncmp("8T", temp_var, strlen("8T"))) {
		sram_cell_design.setType(std_8T);
	} else {
		cerr << "ERROR: Invalid SRAM cell type!\n";
		exit(0);
	}
	
	if ( !SRAM_cell_conf_node.getChildNode("dual_gate_control").isEmpty() ) {
		if ( SRAM_cell_conf_node.getChildNode("dual_gate_control").nText() == 0 ) {
			cout << "XML ERROR: <dual_gate_control> in the '" << sram_cell_file <<"' file does not have a value.\n";
			cerr << "Please specify either 'true' or 'false' for the dual_gate_control." << endl;
			exit(0);
		} else {
			strcpy(temp_var,SRAM_cell_conf_node.getChildNode("dual_gate_control").getText(0));
			for (int i = 0; temp_var[i]; i++) { temp_var[i] = tolower(temp_var[i]); }
			if (!strncmp("true", temp_var, strlen("true"))) {
				sram_cell_design.setDGcontrol(true);
			} else if (!strncmp("false", temp_var, strlen("false"))) {
				sram_cell_design.setDGcontrol(false);
			} else {
				cerr << "ERROR: Invalid value for the dual_gate_control in '" << sram_cell_file <<"' file!\n";
				exit(0);
			}
		}
	} else {
		sram_cell_design.setDGcontrol(false);
	}
	
	XMLNode SRAM_leak_power = SRAM_cell_conf_node.getChildNode("leakage_power");
	if ( !SRAM_leak_power.getChildNode("bitline").isEmpty() ) {
		if ( SRAM_leak_power.getChildNode("bitline").nText() > 0 ) {
			strcpy(temp_var,SRAM_leak_power.getChildNode("bitline").getText(0));
			double pleak;
			sscanf(temp_var, "%lf", &(pleak));
			sram_cell_design.setPleakAccTx(pleak);
		}
	}
	if ( !SRAM_leak_power.getChildNode("cc_inverters").isEmpty() ) {
		if ( SRAM_leak_power.getChildNode("cc_inverters").nText() > 0 ) {
			strcpy(temp_var,SRAM_leak_power.getChildNode("cc_inverters").getText(0));
			double pleak;
			sscanf(temp_var, "%lf", &(pleak));
			sram_cell_design.setPleakCCInv(pleak);
		}
	}
	
	int Nfins[5];
	double Lphys[5], Ioffs[5];
	XMLNode SRAM_transistor_parameters = SRAM_cell_conf_node.getChildNode("transistor_parameters");
	if ( is_finfet ) {
		strcpy(temp_var,SRAM_transistor_parameters.getChildNode("acc").getChildNode("num_of_fins").getText(0));
		sscanf(temp_var,"%d",&(Nfins[0]));
		strcpy(temp_var,SRAM_transistor_parameters.getChildNode("pup").getChildNode("num_of_fins").getText(0));
		sscanf(temp_var,"%d",&(Nfins[1]));
		strcpy(temp_var,SRAM_transistor_parameters.getChildNode("pdn").getChildNode("num_of_fins").getText(0));
		sscanf(temp_var,"%d",&(Nfins[2]));
		if (sram_cell_design.getType() == std_8T) {
			strcpy(temp_var,SRAM_transistor_parameters.getChildNode("iso").getChildNode("num_of_fins").getText(0));
			sscanf(temp_var,"%d",&(Nfins[3]));
			strcpy(temp_var,SRAM_transistor_parameters.getChildNode("rac").getChildNode("num_of_fins").getText(0));
			sscanf(temp_var,"%d",&(Nfins[4]));
		}
	} else {
		Nfins[0] = 0; Nfins[1] = 0; Nfins[2] = 0; Nfins[3] = 0; Nfins[4] = 0;
	}
	
	XMLNode SRAM_transistor_definition = XMLNode::openFileHelper(SRAM_transistor_parameters.getChildNode("acc").getChildNode("device_type").getText(0),"device_definition");
	strcpy(temp_var,SRAM_transistor_definition.getChildNode("geometries").getChildNode("Lphy").getText(0));
	sscanf(temp_var,"%lf",&(Lphys[0]));
	char temperature[10];
	sprintf(temperature,"%d",g_ip->temp);
	if (is_near_threshold)
		strcpy(temp_var,SRAM_transistor_definition.getChildNode("currents").getChildNode("OFF_current").getChildNode("NMOS").getChildNode("near_threshold").getChildNodeWithAttribute("temp","val",temperature).getText(0));
	else
		strcpy(temp_var,SRAM_transistor_definition.getChildNode("currents").getChildNode("OFF_current").getChildNode("NMOS").getChildNode("super_threshold").getChildNodeWithAttribute("temp","val",temperature).getText(0));
	sscanf(temp_var,"%lf",&(Ioffs[0]));

	SRAM_transistor_definition = XMLNode::openFileHelper(SRAM_transistor_parameters.getChildNode("pup").getChildNode("device_type").getText(0),"device_definition");
	strcpy(temp_var,SRAM_transistor_definition.getChildNode("geometries").getChildNode("Lphy").getText(0));
	sscanf(temp_var,"%lf",&(Lphys[1]));
	if(is_near_threshold)
		strcpy(temp_var,SRAM_transistor_definition.getChildNode("currents").getChildNode("OFF_current").getChildNode("PMOS").getChildNode("near_threshold").getChildNodeWithAttribute("temp","val",temperature).getText(0));
	else
		strcpy(temp_var,SRAM_transistor_definition.getChildNode("currents").getChildNode("OFF_current").getChildNode("PMOS").getChildNode("super_threshold").getChildNodeWithAttribute("temp","val",temperature).getText(0));
	sscanf(temp_var,"%lf",&(Ioffs[1]));
	
	SRAM_transistor_definition = XMLNode::openFileHelper(SRAM_transistor_parameters.getChildNode("pdn").getChildNode("device_type").getText(0),"device_definition");
	strcpy(temp_var,SRAM_transistor_definition.getChildNode("geometries").getChildNode("Lphy").getText(0));
	sscanf(temp_var,"%lf",&(Lphys[2]));
	if(is_near_threshold)
		strcpy(temp_var,SRAM_transistor_definition.getChildNode("currents").getChildNode("OFF_current").getChildNode("NMOS").getChildNode("near_threshold").getChildNodeWithAttribute("temp","val",temperature).getText(0));
	else
		strcpy(temp_var,SRAM_transistor_definition.getChildNode("currents").getChildNode("OFF_current").getChildNode("NMOS").getChildNode("super_threshold").getChildNodeWithAttribute("temp","val",temperature).getText(0));
	sscanf(temp_var,"%lf",&(Ioffs[2]));
	
	if (sram_cell_design.getType() == std_8T) {
		SRAM_transistor_definition = XMLNode::openFileHelper(SRAM_transistor_parameters.getChildNode("iso").getChildNode("device_type").getText(0),"device_definition");
		strcpy(temp_var,SRAM_transistor_definition.getChildNode("geometries").getChildNode("Lphy").getText(0));
		sscanf(temp_var,"%lf",&(Lphys[3]));
		if (is_near_threshold)
			strcpy(temp_var,SRAM_transistor_definition.getChildNode("currents").getChildNode("OFF_current").getChildNode("NMOS").getChildNode("near_threshold").getChildNodeWithAttribute("temp","val",temperature).getText(0));
		else
			strcpy(temp_var,SRAM_transistor_definition.getChildNode("currents").getChildNode("OFF_current").getChildNode("NMOS").getChildNode("super_threshold").getChildNodeWithAttribute("temp","val",temperature).getText(0));
		sscanf(temp_var,"%lf",&(Ioffs[3]));

		SRAM_transistor_definition = XMLNode::openFileHelper(SRAM_transistor_parameters.getChildNode("rac").getChildNode("device_type").getText(0),"device_definition");
		strcpy(temp_var,SRAM_transistor_definition.getChildNode("geometries").getChildNode("Lphy").getText(0));
		sscanf(temp_var,"%lf",&(Lphys[4]));
		if (is_near_threshold)
			strcpy(temp_var,SRAM_transistor_definition.getChildNode("currents").getChildNode("OFF_current").getChildNode("NMOS").getChildNode("near_threshold").getChildNodeWithAttribute("temp","val",temperature).getText(0));
		else
			strcpy(temp_var,SRAM_transistor_definition.getChildNode("currents").getChildNode("OFF_current").getChildNode("NMOS").getChildNode("super_threshold").getChildNodeWithAttribute("temp","val",temperature).getText(0));
		sscanf(temp_var,"%lf",&(Ioffs[4]));
	}
	
	sram_cell_design.setTransistorParams(Nfins, Lphys, Ioffs);

	XMLNode ports_node = xMainNode.getChildNode("ports");
	strcpy(temp_var,ports_node.getChildNode("read_write_port").getText(0));
	sscanf(temp_var, "%u", &(num_rw_ports));
	strcpy(temp_var,ports_node.getChildNode("exclusive_read_port").getText(0));
	sscanf(temp_var, "%u", &(num_rd_ports));
	strcpy(temp_var,ports_node.getChildNode("exclusive_write_port").getText(0));
	sscanf(temp_var, "%u", &(num_wr_ports));
	strcpy(temp_var,ports_node.getChildNode("single_ended_read_ports").getText(0));
	sscanf(temp_var, "%u", &(num_se_rd_ports));
	
	strcpy(temp_var,xMainNode.getChildNode("cache_model").getText(0));
	if (!strncmp("UCA", temp_var, strlen("UCA"))) {
		nuca = 0;
	} else {
		nuca = 1;
	}
	
	strcpy(temp_var,xMainNode.getChildNode("uca_bank_count").getText(0));
	sscanf(temp_var, "%u", &(nbanks));
	
	strcpy(temp_var,xMainNode.getChildNode("nuca_bank_count").getText(0));
	sscanf(temp_var, "%d", &(nuca_bank_count));
	if (nuca_bank_count != 0) {
		force_nuca_bank = 1;
	}
	
	strcpy(temp_var,xMainNode.getChildNode("bus_width").getText(0));
	sscanf(temp_var, "%u", &(out_w));

	strcpy(temp_var,xMainNode.getChildNode("memory_type").getText(0));
	if (!strncmp("cache", temp_var, sizeof("cache"))) {
		is_cache = true;
	} else {
		is_cache = false;
	}
	if (!strncmp("main memory", temp_var, sizeof("main memory"))) {
		is_main_mem = true;
	} else {
		is_main_mem = false;
	}

	strcpy(temp_var,xMainNode.getChildNode("tag_size").getText(0));
	if (!strncmp("default", temp_var, sizeof("default"))) {
		specific_tag = false;
		tag_w = 42;
		// the acutal value is calculated later based on the cache size,
		// bank count, and associativity
	} else {
		specific_tag = true;
		sscanf(temp_var, "%u", &(tag_w));
	}
	
	strcpy(temp_var,xMainNode.getChildNode("access_mode").getText(0));
	if (!strncmp("fast", temp_var, strlen("fast"))) {
		access_mode = 2;
	} else if (!strncmp("sequential", temp_var, strlen("sequential"))) {
		access_mode = 1;
	} else if(!strncmp("normal", temp_var, strlen("normal"))) {
		access_mode = 0;
	} else {
		cout << "ERROR: Invalid access mode!\n";
		exit(0);
	}

	XMLNode objectiveFuncNode=xMainNode.getChildNode("objective_function");
	strcpy(temp_var,objectiveFuncNode.getChildNode("optimize").getText(0));
	if(!strncmp("ED^2", temp_var, strlen("ED^2"))) {
		ed = 2;
	} else if(!strncmp("ED", temp_var, strlen("ED"))) {
		ed = 1;
	} else {
		ed = 0;
	}
	XMLNode designObjectiveNode=objectiveFuncNode.getChildNode("design_objective");
	strcpy(temp_var,designObjectiveNode.getChildNode("weights").getChildNode("delay").getText(0));
	sscanf(temp_var, "%d", &(delay_wt));
	strcpy(temp_var,designObjectiveNode.getChildNode("weights").getChildNode("dynamic_power").getText(0));
	sscanf(temp_var, "%d", &(dynamic_power_wt));
	strcpy(temp_var,designObjectiveNode.getChildNode("weights").getChildNode("leakage_power").getText(0));
	sscanf(temp_var, "%d", &(leakage_power_wt));
	strcpy(temp_var,designObjectiveNode.getChildNode("weights").getChildNode("cycle_time").getText(0));
	sscanf(temp_var, "%d", &(cycle_time_wt));
	strcpy(temp_var,designObjectiveNode.getChildNode("weights").getChildNode("area").getText(0));
	sscanf(temp_var, "%d", &(area_wt));
	strcpy(temp_var,designObjectiveNode.getChildNode("deviations").getChildNode("delay").getText(0));
	sscanf(temp_var, "%d", &(delay_dev));
	strcpy(temp_var,designObjectiveNode.getChildNode("deviations").getChildNode("dynamic_power").getText(0));
	sscanf(temp_var, "%d", &(dynamic_power_dev));
	strcpy(temp_var,designObjectiveNode.getChildNode("deviations").getChildNode("leakage_power").getText(0));
	sscanf(temp_var, "%d", &(leakage_power_dev));
	strcpy(temp_var,designObjectiveNode.getChildNode("deviations").getChildNode("cycle_time").getText(0));
	sscanf(temp_var, "%d", &(cycle_time_dev));
	strcpy(temp_var,designObjectiveNode.getChildNode("deviations").getChildNode("area").getText(0));
	sscanf(temp_var, "%d", &(area_dev));
	
	designObjectiveNode=objectiveFuncNode.getChildNode("nuca_design_objective");
	strcpy(temp_var,designObjectiveNode.getChildNode("weights").getChildNode("delay").getText(0));
	sscanf(temp_var, "%d", &(delay_wt_nuca));
	strcpy(temp_var,designObjectiveNode.getChildNode("weights").getChildNode("dynamic_power").getText(0));
	sscanf(temp_var, "%d", &(dynamic_power_wt_nuca));
	strcpy(temp_var,designObjectiveNode.getChildNode("weights").getChildNode("leakage_power").getText(0));
	sscanf(temp_var, "%d", &(leakage_power_wt_nuca));
	strcpy(temp_var,designObjectiveNode.getChildNode("weights").getChildNode("cycle_time").getText(0));
	sscanf(temp_var, "%d", &(cycle_time_wt_nuca));
	strcpy(temp_var,designObjectiveNode.getChildNode("weights").getChildNode("area").getText(0));
	sscanf(temp_var, "%d", &(area_wt_nuca));
	strcpy(temp_var,designObjectiveNode.getChildNode("deviations").getChildNode("delay").getText(0));
	sscanf(temp_var, "%d", &(delay_dev_nuca));
	strcpy(temp_var,designObjectiveNode.getChildNode("deviations").getChildNode("dynamic_power").getText(0));
	sscanf(temp_var, "%d", &(dynamic_power_dev_nuca));
	strcpy(temp_var,designObjectiveNode.getChildNode("deviations").getChildNode("leakage_power").getText(0));
	sscanf(temp_var, "%d", &(leakage_power_dev_nuca));
	strcpy(temp_var,designObjectiveNode.getChildNode("deviations").getChildNode("cycle_time").getText(0));
	sscanf(temp_var, "%d", &(cycle_time_dev_nuca));
	strcpy(temp_var,designObjectiveNode.getChildNode("deviations").getChildNode("area").getText(0));
	sscanf(temp_var, "%d", &(area_dev_nuca));
	
	XMLNode interconnectsInfoNode=xMainNode.getChildNode("interconnects");
	strcpy(temp_var,interconnectsInfoNode.getChildNode("source").getText(0));
	if (!strncmp("ITRS2012", temp_var, strlen("ITRS2012"))) {
		is_itrs2012 = true;
	} else if (!strncmp("RonHo2003", temp_var, strlen("RonHo2003"))) {
		is_itrs2012 = false;
	} else {
		cout << "ERROR: Invalid interconnect source!\n";
		exit(0);
	}
	strcpy(temp_var,interconnectsInfoNode.getChildNode("wire_signalling").getText(0));
	if (!strncmp("default", temp_var, strlen("default"))) {
		force_wiretype = 0;
		wt = Global;
	} else if (!(strncmp("Global_10", temp_var, strlen("Global_10")))) {
		force_wiretype = 1;
		wt = Global_10;
	} else if (!(strncmp("Global_20", temp_var, strlen("Global_20")))) {
		force_wiretype = 1;
		wt = Global_20;
	} else if (!(strncmp("Global_30", temp_var, strlen("Global_30")))) {
		force_wiretype = 1;
		wt = Global_30;
	} else if (!(strncmp("Global_5", temp_var, strlen("Global_5")))) {
		force_wiretype = 1;
		wt = Global_5;
	} else if (!(strncmp("Global", temp_var, strlen("Global")))) {
		force_wiretype = 1;
		wt = Global;
	} else {
		wt = Low_swing;
		force_wiretype = 1;
	}
	strcpy(temp_var,interconnectsInfoNode.getChildNode("wire_type").getChildNode("inside_mat").getText(0));
	if (!strncmp("global", temp_var, strlen("global"))) {
		wire_is_mat_type = 2;
	} else if (!strncmp("local", temp_var, strlen("local"))) {
		wire_is_mat_type = 0;
	} else {
		wire_is_mat_type = 1;
	}
	strcpy(temp_var,interconnectsInfoNode.getChildNode("wire_type").getChildNode("outside_mat").getText(0));
	if (!strncmp("global", temp_var, strlen("global"))) {
		wire_os_mat_type = 2;
	} else {
		wire_os_mat_type = 1;
	}
	strcpy(temp_var,interconnectsInfoNode.getChildNode("projection").getText(0));
	if (!strncmp("aggressive", temp_var, strlen("aggressive"))) {
		ic_proj_type = 0;
	} else {
		ic_proj_type = 1;
	}
	
	strcpy(temp_var,xMainNode.getChildNode("core_count").getText(0));
	sscanf(temp_var, "%d", &(cores));
	if (cores > 16) {
		printf("No. of cores should be less than 16!\n");
	}
	
	strcpy(temp_var,xMainNode.getChildNode("cache_level").getText(0));
	if (!strncmp("L2", temp_var, strlen("L2"))) {
		cache_level = 0;
	} else {
		cache_level = 1;
	}
	
	strcpy(temp_var,xMainNode.getChildNode("add_ecc").getText(0));
	if (!strncmp("true", temp_var, strlen("true"))) {
		add_ecc_b_ = true;
	} else {
		add_ecc_b_ = false;
	}
	
	strcpy(temp_var,xMainNode.getChildNode("print_level").getText(0));
	if (!strncmp("DETAILED", temp_var, strlen("DETAILED"))) {
		print_detail = 1;
	} else {
		print_detail = 0;
	}
	
	strcpy(temp_var,xMainNode.getChildNode("print_input_parameters").getText(0));
	if (!strncmp("true", temp_var, strlen("true"))) {
		print_input_args = true;
	} else {
		print_input_args = false;
	}
	
	strcpy(temp_var,xMainNode.getChildNode("force_cache_config").getText(0));
	if (!strncmp("true", temp_var, strlen("true"))) {
		force_cache_config = true;
	} else {
		force_cache_config = false;
	}
	
	strcpy(temp_var,xMainNode.getChildNode("Ndbl").getText(0));
	sscanf(temp_var, "%d", &(ndbl));
	
	strcpy(temp_var,xMainNode.getChildNode("Ndwl").getText(0));
	sscanf(temp_var, "%d", &(ndwl));
	
	strcpy(temp_var,xMainNode.getChildNode("Nspd").getText(0));
	sscanf(temp_var, "%d", &(nspd));
	
	strcpy(temp_var,xMainNode.getChildNode("Ndsam1").getText(0));
	sscanf(temp_var, "%d", &(ndsam1));
	
	strcpy(temp_var,xMainNode.getChildNode("Ndsam2").getText(0));
	sscanf(temp_var, "%d", &(ndsam2));
	
	strcpy(temp_var,xMainNode.getChildNode("Ndcm").getText(0));
	sscanf(temp_var, "%d", &(ndcm));
	
	strcpy(temp_var,xMainNode.getChildNode("page_size").getText(0));
	sscanf(temp_var, "%u", &(page_sz_bits));
	
	strcpy(temp_var,xMainNode.getChildNode("burst_length").getText(0));
	sscanf(temp_var, "%u", &(burst_len));
	
	strcpy(temp_var,xMainNode.getChildNode("internal_prefetch_width").getText(0));
	sscanf(temp_var, "%u", &(int_prefetch_w));

	/********************  MAJID END  ********************/

	data_arr_ram_cell_tech_type = 0;
	data_arr_peri_global_tech_type = 0;
	tag_arr_ram_cell_tech_type = 0;
	tag_arr_peri_global_tech_type = 0;

	////////////////////////////////////////////////////////////
  
  rpters_in_htree = true;
  fclose(fp);
}

  void
InputParameter::display_ip()
{
  cout << "\n----------------------------------------"; // Alireza
  cout << "\n            Input Parameters            "; // Alireza
  cout << "\n----------------------------------------" << endl; // Alireza
  cout << "Cache size                    : " << cache_sz << "B" << endl; // unit. -Alireza
  cout << "Block size                    : " << line_sz  << "B" << endl; // unit. -Alireza
  cout << "Associativity                 : " << assoc << endl;
  cout << "Read only ports               : " << num_rd_ports << endl;
  cout << "Write only ports              : " << num_wr_ports << endl;
  cout << "Read write ports              : " << num_rw_ports << endl;
  cout << "Single ended read ports       : " << num_se_rd_ports << endl;
  cout << "Cache banks (UCA)             : " << nbanks << endl;
  cout << "Technology                    : " << F_sz_nm << "nm" << endl; // changed to nm. -Alireza
  cout << "Transistor type               : " << (is_finfet ? "FinFET" : "CMOS" ) << endl; // Alireza
  cout << "Operating voltage             : " << (is_near_threshold ? "Near-threshold" : "Super-threshold" ) << endl; // Alireza
  if (g_ip->sram_cell_design.getType()==std_6T) { // Alireza
    cout << "SRAM cell type                : " << "Standard 6T" << endl;
  } else if (g_ip->sram_cell_design.getType()==std_8T) {
    cout << "SRAM cell type                : " << "Standard 8T" << endl;
  }
  cout << "Temperature                   : " << temp << "K" << endl; // Alireza
  cout << "Tag size                      : " << tag_w << endl;
  if (is_cache) {
    cout << "cache type                    : " << "Cache" << endl;
  } else if (is_main_mem) {
    cout << "cache type                    : " << "Main Memory" << endl; // Alireza
  } else { // Alireza
    cout << "cache type                    : " << "Scratch RAM" << endl;
  }
  //cout << "Model as memory               : " << is_main_mem << endl;  // Alireza
  cout << "Access mode                   : " << access_mode << endl;
  cout << "Data array cell type          : " << data_arr_ram_cell_tech_type << endl;
  cout << "Data array peripheral type    : " << data_arr_peri_global_tech_type << endl;
  cout << "Tag array cell type           : " << tag_arr_ram_cell_tech_type << endl;
  cout << "Tag array peripheral type     : " << tag_arr_peri_global_tech_type << endl;
  cout << "Design objective (UCA wt)     : " << delay_wt << " "
                                                << dynamic_power_wt << " " << leakage_power_wt << " " << cycle_time_wt
                                                << " " << area_wt << endl;
  cout << "Design objective (UCA dev)    : " << delay_dev << " "
                                                << dynamic_power_dev << " " << leakage_power_dev << " " << cycle_time_dev
                                                << " " << area_dev << endl;
  cout << "Design objective (NUCA wt)    : " << delay_wt_nuca << " "
                                                << dynamic_power_wt_nuca << " " << leakage_power_wt_nuca << " " << cycle_time_wt_nuca
                                                << " " << area_wt_nuca << endl;
  cout << "Design objective (NUCA dev)   : " << delay_dev_nuca << " "
                                                << dynamic_power_dev_nuca << " " << leakage_power_dev_nuca << " " << cycle_time_dev_nuca
                                                << " " << area_dev_nuca << endl;
  cout << "Cache model                   : " << (nuca ? "NUCA" : "UCA" ) << endl; // Alireza
  cout << "Nuca bank                     : " << nuca_bank_count << endl;
  cout << "Wire inside mat               : " << wire_is_mat_type << endl;
  cout << "Wire outside mat              : " << wire_os_mat_type << endl;
  cout << "Interconnect projection       : " << ic_proj_type << endl;
  cout << "Wire signalling               : " << force_wiretype << endl;
  cout << "Cores                         : " << cores << endl;
  cout << "Print details                 : " << (print_detail ? "Yes" : "No" ) << endl; // Alireza
  cout << "ECC overhead                  : " << (add_ecc_b_ ? "Yes" : "No" ) << endl; // Alireza
  cout << "Page size                     : " << page_sz_bits << endl;
  cout << "Burst length                  : " << burst_len << endl;
  cout << "Internal prefetch width       : " << int_prefetch_w << endl;
  cout << "Force cache config            : " << (g_ip->force_cache_config ? "Yes" : "No" ) << endl; // Alireza
  if (g_ip->force_cache_config) {
    cout << "Ndwl                          : " << g_ip->ndwl << endl;
    cout << "Ndbl                          : " << g_ip->ndbl << endl;
    cout << "Nspd                          : " << g_ip->nspd << endl;
    cout << "Ndcm                          : " << g_ip->ndcm << endl;
    cout << "Ndsam1                        : " << g_ip->ndsam1 << endl;
    cout << "Ndsam2                        : " << g_ip->ndsam2 << endl;
  }
}



powerComponents operator+(const powerComponents & x, const powerComponents & y)
{
  powerComponents z;

  z.dynamic = x.dynamic + y.dynamic;
  z.leakage = x.leakage + y.leakage;

  return z;
}



powerDef operator+(const powerDef & x, const powerDef & y)
{
  powerDef z;

  z.readOp  = x.readOp  + y.readOp;
  z.writeOp = x.writeOp + y.writeOp;

  return z;
}



uca_org_t cacti_interface(const string & infile_name)
{
  uca_org_t fin_res;
//  uca_org_t result;
  fin_res.valid = false;

  g_ip = new InputParameter();
  g_ip->parse_cfg(infile_name);
  
  if (g_ip->error_checking() == false) { cout << "ERROR: Invalid input parameters!\n", exit(0); }
  if (g_ip->print_input_args) g_ip->display_ip();

  init_tech_params(g_ip->F_sz_um, false);
  if (g_ip->print_input_args) g_tp.display(); // Alireza
  
  Wire winit; // Do not delete this line. It initializes wires.
  
  //g_ip->sram_cell_design.print_transistor_params();
  //cout << g_ip->sram_cell_design.getPleakCCInv(g_tp.sram_cell.Vdd, g_tp.sram_cell.H_fin) << endl;
  //cout << g_ip->sram_cell_design.getPleakAccTx(g_tp.sram_cell.Vdd, g_tp.sram_cell.H_fin) << endl;

  if (g_ip->nuca == 1)
  {
    Nuca n(&g_tp.peri_global);
    n.sim_nuca();
  }
//  g_ip->display_ip();
  solve(&fin_res);

  output_UCA(&fin_res);
  //output_summary_of_results(&fin_res);
  output_summary_of_results_file(&fin_res);

  delete (g_ip);
  return fin_res;
}


uca_org_t cacti_interface(
    int cache_size,
    int line_size,
    int associativity,
    int rw_ports,
    int excl_read_ports,
    int excl_write_ports,
    int single_ended_read_ports,
    int banks,
    double tech_node, // in nm
    int page_sz,
    int burst_length,
    int pre_width,
    int output_width,
    int specific_tag,
    int tag_width,
    int access_mode, //0 normal, 1 seq, 2 fast
    int cache, //scratch ram or cache
    int main_mem,
    int obj_func_delay,
    int obj_func_dynamic_power,
    int obj_func_leakage_power,
    int obj_func_area,
    int obj_func_cycle_time,
    int dev_func_delay,
    int dev_func_dynamic_power,
    int dev_func_leakage_power,
    int dev_func_area,
    int dev_func_cycle_time,
    int ed_ed2_none, // 0 - ED, 1 - ED^2, 2 - use weight and deviate
    int temp,
    int wt, //0 - default(search across everything), 1 - global, 2 - 5% delay penalty, 3 - 10%, 4 - 20 %, 5 - 30%, 6 - low-swing 
    int data_arr_ram_cell_tech_flavor_in, // 0-4
    int data_arr_peri_global_tech_flavor_in, 
    int tag_arr_ram_cell_tech_flavor_in,
    int tag_arr_peri_global_tech_flavor_in,
    int interconnect_projection_type_in, // 0 - aggressive, 1 - normal
    int wire_inside_mat_type_in, 
    int wire_outside_mat_type_in, 
    int is_nuca, // 0 - UCA, 1 - NUCA
    int core_count,
    int cache_level, // 0 - L2, 1 - L3
    int nuca_bank_count,
    int nuca_obj_func_delay,
    int nuca_obj_func_dynamic_power,
    int nuca_obj_func_leakage_power,
    int nuca_obj_func_area,
    int nuca_obj_func_cycle_time,
    int nuca_dev_func_delay,
    int nuca_dev_func_dynamic_power,
    int nuca_dev_func_leakage_power,
    int nuca_dev_func_area,
    int nuca_dev_func_cycle_time,
    int REPEATERS_IN_HTREE_SEGMENTS_in,//TODO for now only wires with repeaters are supported
    int p_input) 
{
  g_ip = new InputParameter();
  g_ip->add_ecc_b_ = true;

  g_ip->data_arr_ram_cell_tech_type    = data_arr_ram_cell_tech_flavor_in;
  g_ip->data_arr_peri_global_tech_type = data_arr_peri_global_tech_flavor_in;
  g_ip->tag_arr_ram_cell_tech_type     = tag_arr_ram_cell_tech_flavor_in;
  g_ip->tag_arr_peri_global_tech_type  = tag_arr_peri_global_tech_flavor_in;

  g_ip->ic_proj_type     = interconnect_projection_type_in;
  g_ip->wire_is_mat_type = wire_inside_mat_type_in;
  g_ip->wire_os_mat_type = wire_outside_mat_type_in;
  g_ip->burst_len        = burst_length;
  g_ip->int_prefetch_w   = pre_width;
  g_ip->page_sz_bits     = page_sz;

  g_ip->cache_sz            = cache_size;
  g_ip->line_sz             = line_size;
  g_ip->assoc               = associativity;
  g_ip->nbanks              = banks;
  g_ip->out_w               = output_width;
  g_ip->specific_tag        = specific_tag;
  if (tag_width == 0) {
    g_ip->tag_w = 42; 
  }
  else {
    g_ip->tag_w               = tag_width;
  }

  g_ip->access_mode         = access_mode;
  g_ip->delay_wt = obj_func_delay;
  g_ip->dynamic_power_wt = obj_func_dynamic_power;
  g_ip->leakage_power_wt = obj_func_leakage_power;
  g_ip->area_wt = obj_func_area;
  g_ip->cycle_time_wt    = obj_func_cycle_time;
  g_ip->delay_dev = dev_func_delay;
  g_ip->dynamic_power_dev = dev_func_dynamic_power;
  g_ip->leakage_power_dev = dev_func_leakage_power;
  g_ip->area_dev = dev_func_area;
  g_ip->cycle_time_dev    = dev_func_cycle_time;
  g_ip->ed = ed_ed2_none;

  switch(wt) {
    case (0):
      g_ip->force_wiretype = 0;
      g_ip->wt = Global;
      break;
    case (1):
      g_ip->force_wiretype = 1;
      g_ip->wt = Global;
      break;
    case (2):
      g_ip->force_wiretype = 1;
      g_ip->wt = Global_5;
      break;
    case (3):
      g_ip->force_wiretype = 1;
      g_ip->wt = Global_10;
      break;
    case (4):
      g_ip->force_wiretype = 1;
      g_ip->wt = Global_20;
      break;
    case (5):
      g_ip->force_wiretype = 1;
      g_ip->wt = Global_30;
      break;
    case (6):
      g_ip->force_wiretype = 1;
      g_ip->wt = Low_swing;
      break;
    default:
      cout << "Unknown wire type!\n";
      exit(0);
  }

  g_ip->delay_wt_nuca = nuca_obj_func_delay;
  g_ip->dynamic_power_wt_nuca = nuca_obj_func_dynamic_power;
  g_ip->leakage_power_wt_nuca = nuca_obj_func_leakage_power;
  g_ip->area_wt_nuca = nuca_obj_func_area;
  g_ip->cycle_time_wt_nuca    = nuca_obj_func_cycle_time;
  g_ip->delay_dev_nuca = dev_func_delay;
  g_ip->dynamic_power_dev_nuca = nuca_dev_func_dynamic_power;
  g_ip->leakage_power_dev_nuca = nuca_dev_func_leakage_power;
  g_ip->area_dev_nuca = nuca_dev_func_area;
  g_ip->cycle_time_dev_nuca    = nuca_dev_func_cycle_time;
  g_ip->nuca = is_nuca;
  g_ip->nuca_bank_count = nuca_bank_count;
  if(nuca_bank_count > 0) {
    g_ip->force_nuca_bank = 1;
  }
  g_ip->cores = core_count;
  g_ip->cache_level = cache_level;

  g_ip->temp = temp;

  g_ip->F_sz_nm         = tech_node;
  g_ip->F_sz_um         = tech_node / 1000;
  g_ip->is_main_mem     = (main_mem != 0) ? true : false;
  g_ip->is_cache        = (cache != 0) ? true : false;
  g_ip->rpters_in_htree = (REPEATERS_IN_HTREE_SEGMENTS_in != 0) ? true : false;

  g_ip->num_rw_ports    = rw_ports;
  g_ip->num_rd_ports    = excl_read_ports;
  g_ip->num_wr_ports    = excl_write_ports;
  g_ip->num_se_rd_ports = single_ended_read_ports;
  g_ip->print_detail = 1;
  g_ip->nuca = 0;

  g_ip->wt = Global_5;
  g_ip->force_cache_config = false;
  g_ip->force_wiretype = false;
  g_ip->print_input_args = p_input;


  uca_org_t fin_res;
  fin_res.valid = false;

  if (g_ip->error_checking() == false) exit(0);
  if (g_ip->print_input_args) 
    g_ip->display_ip();
  init_tech_params(g_ip->F_sz_um, false);
  Wire winit; // Do not delete this line. It initializes wires.

  if (g_ip->nuca == 1)
  {
    Nuca n(&g_tp.peri_global);
    n.sim_nuca();
  }
  solve(&fin_res);

  output_UCA(&fin_res);
  //output_summary_of_results(&fin_res);

  delete (g_ip);
  return fin_res;
}



bool InputParameter::error_checking()
{
  int  A;
  bool seq_access  = false;
  fast_access = true;
  
  ///if ( (is_finfet && F_sz_nm != 7) || (!is_finfet && F_sz_nm == 7) ) // Alireza
  ///  return false;
  
  /// near-threshold only valid for finfet
  /// finfet just supports hp devices?
  /// finfet just supports 5nm (just HP), 7nm (just HP), and maybe 32nm
  /// near-threshold not yet
  
  switch (access_mode)
  {
    case 0:
      seq_access  = false;
      fast_access = false;
      break;
    case 1:
      seq_access  = true;
      fast_access = false;
      break;
    case 2:
      seq_access  = false;
      fast_access = true;
      break;
  }

  if(is_main_mem)
  {
    if(ic_proj_type == 0)
    {
      cerr << "DRAM model supports only conservative interconnect projection!\n\n";
      return false;
    }
  }

  uint32_t B = line_sz;

  if (B < 1)
  {
    cerr << "Block size must >= 1" << endl;
    return false;
  }
  else if (B*8 < out_w)
  {
    cerr << "Block size must be at least " << out_w/8 << endl;
    return false;
  }

  if (F_sz_um <= 0)
  {
    cerr << "Feature size must be > 0" << endl;
    return false;
  }
  else if (F_sz_um > 0.091)
  {
    cerr << "Feature size must be <= 90 nm" << endl;
    return false;
  }


  uint32_t RWP  = num_rw_ports;
  uint32_t ERP  = num_rd_ports;
  uint32_t EWP  = num_wr_ports;
  uint32_t NSER = num_se_rd_ports;

//  // If multiple banks and multiple ports are specified, then if number of ports is less than or equal to
//  // the number of banks, we assume that the multiple ports are implemented via the multiple banks.
//  // In such a case we assume that each bank has 1 RWP port. 
//  if ((RWP + ERP + EWP) <= nbanks)
//  {
//    RWP  = 1;
//    ERP  = 0;
//    EWP  = 0;
//    NSER = 0;
//  }
//  else if ((RWP < 0) || (EWP < 0) || (ERP < 0))
//  {
//    cerr << "Ports must >=0" << endl;
//    return false;
//  }
//  else if (RWP > 2)
//  {
//    cerr << "Maximum of 2 read/write ports" << endl;
//    return false;
//  }

  //  The number of ports specified at input is per bank
  if ((RWP+ERP+EWP) < 1)
  {
    cerr << "Must have at least one port" << endl;
    return false;
  }

  if (is_pow2(nbanks) == false)
  {
    cerr << "Number of subbanks should be greater than or equal to 1 and should be a power of 2" << endl;
    return false;
  }

  int C = cache_sz/nbanks;
  if (C < 64)
  {
    cerr << "Cache size must >=64" << endl;
    return false;
  }

  if (assoc == 0)
  {
    A = C/B;
    fully_assoc = true;
  }
  else
  {
    if (assoc == 1)
    {
      A = 1;
      fully_assoc = false;
    }
    else
    {
      fully_assoc = false;
      A = assoc;
      if (is_pow2(A) == false)
      {
        cerr << "Associativity must be a power of 2" << endl;
        return false;
      }
    }
  }

  if (C/(B*A) <= 1 && !fully_assoc)
  {
    cerr << "Number of sets is too small: " << endl;
    cerr << " Need to either increase cache size, or decrease associativity or block size" << endl;
    cerr << " (or use fully associative cache)" << endl;
    return false;
  }

  block_sz = B;

  /*dt: testing sequential access mode*/
  if(seq_access)
  {
    tag_assoc  = A;
    data_assoc = 1;
    is_seq_acc = true;
  }
  else
  {
    tag_assoc  = A;
    data_assoc = A;
    is_seq_acc = false;
  }

  if (fully_assoc)
  {
    data_assoc = 1;
  }
  num_rw_ports    = RWP;
  num_rd_ports    = ERP;
  num_wr_ports    = EWP;
  num_se_rd_ports = NSER;
  nsets           = C/(B*A);

  if (temp < 300 || temp > 400 || temp%10 != 0)
  {
    cerr << temp << " Temperature must be between 300 and 400 Kelvin and multiple of 10." << endl;
    return false;
  }

  if (nsets < 1)
  {
    cerr << "Less than one set..." << endl;
    return false;
  }

  return true;
}



void output_data_csv(const uca_org_t & fin_res)
{
  fstream file("out.csv", ios::in);
  bool    print_index = file.fail();
  file.close();

  file.open("out.csv", ios::out|ios::app);
  if (file.fail() == true)
  {
    cerr << "File out.csv could not be opened successfully" << endl;
  }
  else
  {
    if (print_index == true)
    {
      file << "Tech node (nm), ";
      file << "Capacity (bytes), ";
      file << "Number of banks, ";
      file << "Associativity, ";
      file << "Output width (bits), ";
      file << "Access time (ns), ";
      file << "Random cycle time (ns), ";
      file << "Multisubbank interleave cycle time (ns), ";
      file << "Delay request network (ns), ";
      file << "Delay inside mat (ns), ";
      file << "Delay reply network (ns), ";
      file << "Tag array access time (ns), ";
      file << "Refresh period (microsec), ";
      file << "DRAM array availability (%), ";
      file << "Dynamic read energy (nJ), ";
      file << "Dynamic write energy (nJ), ";
      file << "Dynamic read power (mW), ";
      file << "Standby leakage per bank(mW), ";
      file << "Leakage per bank with leak power management (mW), ";
      file << "Refresh power as percentage of standby leakage, ";
      file << "Area (mm2), ";
      file << "Ndwl, ";
      file << "Ndbl, ";
      file << "Nspd, ";
      file << "Ndcm, ";
      file << "Ndsam_level_1, ";
      file << "Ndsam_level_2, ";
      file << "Ntwl, ";
      file << "Ntbl, ";
      file << "Ntspd, ";
      file << "Ntcm, ";
      file << "Ntsam_level_1, ";
      file << "Ntsam_level_2, ";
      file << "Area efficiency, ";
      file << "Resistance per unit micron (ohm-micron), ";
      file << "Capacitance per unit micron (fF per micron), ";
      file << "Unit-length wire delay (ps), ";
      file << "FO4 delay (ps), ";
      file << "delay route to bank (including crossb delay) (ps), ";
      file << "Crossbar delay (ps), ";
      file << "Dyn read energy per access from closed page (nJ), ";
      file << "Dyn read energy per access from open page (nJ), ";
      file << "Leak power of an subbank with page closed (mW), ";
      file << "Leak power of a subbank with page  open (mW), ";
      file << "Leak power of request and reply networks (mW), ";
      file << "Number of subbanks, ";
      file << "Page size in bits, ";
      file << "Activate power, ";
      file << "Read power, ";
      file << "Write power, ";
      file << "Precharge power, ";
      file << "tRCD, ";
      file << "CAS latency, ";
      file << "Precharge delay, ";
      file << "Perc dyn energy bitlines, ";
      file << "perc dyn energy wordlines, ";
      file << "perc dyn energy outside mat, ";
      file << "Area opt (perc), ";
      file << "Delay opt (perc), ";
      file << "Repeater opt (perc), ";
      file << "Aspect ratio" << endl;
    }
    file << g_ip->F_sz_nm << ", ";
    file << g_ip->cache_sz << ", ";
    file << g_ip->nbanks << ", ";
    file << g_ip->tag_assoc << ", ";
    file << g_ip->out_w << ", ";
    file << fin_res.access_time*1e+9 << ", ";
    file << fin_res.cycle_time*1e+9 << ", ";
    file << fin_res.data_array.multisubbank_interleave_cycle_time*1e+9 << ", ";
    file << fin_res.data_array.delay_request_network*1e+9 << ", ";
    file << fin_res.data_array.delay_inside_mat*1e+9 <<  ", ";
    file << fin_res.data_array.delay_reply_network*1e+9 << ", ";
    file << fin_res.tag_array.access_time*1e+9 << ", ";
    file << fin_res.data_array.dram_refresh_period*1e+6 << ", ";
    file << fin_res.data_array.dram_array_availability <<  ", ";
    file << fin_res.power.readOp.dynamic*1e+9 << ", ";
    file << fin_res.power.writeOp.dynamic*1e+9 << ", ";
    file << fin_res.power.readOp.dynamic*1000/fin_res.cycle_time << ", ";
    file << fin_res.power.readOp.leakage*1000 << ", ";
    file << fin_res.leak_power_with_sleep_transistors_in_mats*1000 << ", ";
    file << fin_res.data_array.refresh_power / fin_res.data_array.total_power.readOp.leakage << ", ";
    file << fin_res.area << ", ";
    file << fin_res.data_array.Ndwl << ", ";
    file << fin_res.data_array.Ndbl << ", ";
    file << fin_res.data_array.Nspd << ", ";
    file << fin_res.data_array.deg_bl_muxing << ", ";
    file << fin_res.data_array.Ndsam_lev_1 << ", ";
    file << fin_res.data_array.Ndsam_lev_2 << ", ";
    file << fin_res.tag_array.Ndwl << ", ";
    file << fin_res.tag_array.Ndbl << ", ";
    file << fin_res.tag_array.Nspd << ", ";
    file << fin_res.tag_array.deg_bl_muxing << ", ";
    file << fin_res.tag_array.Ndsam_lev_1 << ", ";
    file << fin_res.tag_array.Ndsam_lev_2 << ", ";
    file << fin_res.area_efficiency << ", ";
    file << g_tp.wire_inside_mat.R_per_um << ", ";
    file << g_tp.wire_inside_mat.C_per_um / 1e-15 << ", ";
    file << g_tp.unit_len_wire_del / 1e-12 << ", ";
    file << g_tp.FO4 / 1e-12 << ", ";
    file << fin_res.data_array.delay_route_to_bank / 1e-9 << ", ";
    file << fin_res.data_array.delay_crossbar / 1e-9 << ", ";
    file << fin_res.data_array.dyn_read_energy_from_closed_page / 1e-9 << ", ";
    file << fin_res.data_array.dyn_read_energy_from_open_page / 1e-9 << ", ";
    file << fin_res.data_array.leak_power_subbank_closed_page / 1e-3 << ", ";
    file << fin_res.data_array.leak_power_subbank_open_page / 1e-3 << ", ";
    file << fin_res.data_array.leak_power_request_and_reply_networks / 1e-3 << ", ";
    file << fin_res.data_array.number_subbanks << ", " ;
    file << fin_res.data_array.page_size_in_bits << ", " ;
    file << fin_res.data_array.activate_energy * 1e9 << ", " ;
    file << fin_res.data_array.read_energy * 1e9 << ", " ;
    file << fin_res.data_array.write_energy * 1e9 << ", " ;
    file << fin_res.data_array.precharge_energy * 1e9 << ", " ;
    file << fin_res.data_array.trcd * 1e9 << ", " ;
    file << fin_res.data_array.cas_latency * 1e9 << ", " ;
    file << fin_res.data_array.precharge_delay * 1e9 << ", " ;
    file << fin_res.data_array.all_banks_height / fin_res.data_array.all_banks_width << endl;
  }
  file.close();
}



void output_UCA(uca_org_t *fr)
{
  //    if (NUCA) 
  if (0) {
    cout << "\n\n Detailed Bank Stats:\n";
    cout << "    Bank Size (bytes): %d\n" << 
                                     (int) (g_ip->cache_sz);
  }
  else {
    if (g_ip->data_arr_ram_cell_tech_type == 3) {
      cout << "\n---------- P-CACTI, Uniform Cache Access " <<
        "Logic Process Based DRAM Model ----------\n"; 
    }
    else if (g_ip->data_arr_ram_cell_tech_type == 4) {
      cout << "\n---------- P-CACTI, Uniform" <<
        "Cache Access Commodity DRAM Model ----------\n";
    }
    else {
      cout << "\n---------- P-CACTI, Uniform Cache Access "
        "SRAM Model ----------\n";
    }
    cout << "\nCache Parameters:\n";
    cout << "    Total cache size (bytes): " << 
      (int) (g_ip->cache_sz) << endl;
  }

  cout << "    Number of banks: " << (int) g_ip->nbanks << endl;
  if (g_ip->fully_assoc)
    cout << "    Associativity: fully associative\n";
  else {
    if (g_ip->tag_assoc == 1)
      cout << "    Associativity: direct mapped\n";
    else
      cout << "    Associativity: " << 
        g_ip->tag_assoc << endl;
  }


  cout << "    Block size (bytes): " << g_ip->line_sz << endl;
  cout << "    Read/write Ports: " <<
    g_ip->num_rw_ports << endl;
  cout << "    Read ports: " <<
    g_ip->num_rd_ports << endl;
  cout << "    Write ports: " <<
    g_ip->num_wr_ports << endl;;
  cout << "    Technology size (nm): " <<  
    g_ip->F_sz_nm << endl << endl;

  cout << "    Access time (ns): " << fr->access_time*1e9 << endl;
  cout << "    Cycle time (ns):  " << fr->cycle_time*1e9 << endl;
  if (g_ip->data_arr_ram_cell_tech_type >= 4) {
    cout << "    Precharge Delay (ns): " << fr->data_array2->precharge_delay*1e9 << endl;
    cout << "    Activate Energy (nJ): " << fr->data_array2->activate_energy*1e9 << endl;
    cout << "    Read Energy (nJ): " << fr->data_array2->read_energy*1e9 << endl;
    cout << "    Write Energy (nJ): " << fr->data_array2->write_energy*1e9 << endl;
    cout << "    Precharge Energy (nJ): " << fr->data_array2->precharge_energy*1e9 << endl;
    cout << "    Leakage Power Closed Page (mW): " << fr->data_array2->leak_power_subbank_closed_page*1e3 << endl;
    cout << "    Leakage Power Open Page (mW): " << fr->data_array2->leak_power_subbank_open_page*1e3 << endl;
    cout << "    Leakage Power I/O (mW): " << fr->data_array2->leak_power_request_and_reply_networks*1e3 << endl;
    cout << "    Refresh power (mW): " << 
      fr->data_array2->refresh_power*1e3 << endl; 
  }
  else {
    cout << "    Total dynamic read energy per access (nJ): " <<
      fr->power.readOp.dynamic*1e9 << endl;
    cout << "    Total dynamic write energy per access (nJ): " << // Alireza
      fr->power.writeOp.dynamic*1e9 << endl;                      // Alireza
    cout << "    Total leakage power of a bank"
      " (mW): " << fr->power.readOp.leakage*1e3 << endl;
  }

  if (g_ip->data_arr_ram_cell_tech_type ==3 || g_ip->data_arr_ram_cell_tech_type ==4)
  {
  }
  cout <<  "    Cache height x width (mm): " <<
    fr->cache_ht*1e-3 << " x " << fr->cache_len*1e-3 << endl;
  cout <<  "    Cache area (mm2): " <<
    fr->area*1e-3*1e-3 << endl << endl;


  cout << "    Best Ndwl : " << fr->data_array2->Ndwl << endl;
  cout << "    Best Ndbl : " << fr->data_array2->Ndbl << endl;
  cout << "    Best Nspd : " << fr->data_array2->Nspd << endl;
  cout << "    Best Ndcm : " << fr->data_array2->deg_bl_muxing << endl;
  cout << "    Best Ndsam L1 : " << fr->data_array2->Ndsam_lev_1 << endl;
  cout << "    Best Ndsam L2 : " << fr->data_array2->Ndsam_lev_2 << endl << endl;

  if (g_ip->is_cache && !g_ip->is_main_mem)
  {
    cout << "    Best Ntwl : " << fr->tag_array2->Ndwl << endl;
    cout << "    Best Ntbl : " << fr->tag_array2->Ndbl << endl;
    cout << "    Best Ntspd : " << fr->tag_array2->Nspd << endl;
    cout << "    Best Ntcm : " << fr->tag_array2->deg_bl_muxing << endl;
    cout << "    Best Ntsam L1 : " << fr->tag_array2->Ndsam_lev_1 << endl;
    cout << "    Best Ntsam L2 : " << fr->tag_array2->Ndsam_lev_2 << endl;
  }

  switch (fr->data_array2->wt) {
    case (0):
      cout <<  "    Data array, H-tree wire type: Delay optimized global wires\n";
      break;
    case (1):
      cout <<  "    Data array, H-tree wire type: Global wires with 5\% delay penalty\n";
      break;
    case (2):
      cout <<  "    Data array, H-tree wire type: Global wires with 10\% delay penalty\n";
      break;
    case (3):
      cout <<  "    Data array, H-tree wire type: Global wires with 20\% delay penalty\n";
      break;
    case (4):
      cout <<  "    Data array, H-tree wire type: Global wires with 30\% delay penalty\n";
      break;
    case (5):
      cout <<  "    Data array, wire type: Low swing wires\n";
      break;
    default:
      cout << "ERROR - Unknown wire type " << (int) fr->data_array2->wt <<endl;
      exit(0);
  }

  if (g_ip->is_cache) {
    switch (fr->tag_array2->wt) {
      case (0):
        cout <<  "    Tag array, H-tree wire type: Delay optimized global wires\n";
        break;
      case (1):
        cout <<  "    Tag array, H-tree wire type: Global wires with 5\% delay penalty\n";
        break;
      case (2):
        cout <<  "    Tag array, H-tree wire type: Global wires with 10\% delay penalty\n";
        break;
      case (3):
        cout <<  "    Tag array, H-tree wire type: Global wires with 20\% delay penalty\n";
        break;
      case (4):
        cout <<  "    Tag array, H-tree wire type: Global wires with 30\% delay penalty\n";
        break;
      case (5):
        cout <<  "    Tag array, wire type: Low swing wires\n";
        break;
      default:
        cout << "ERROR - Unknown wire type " << (int) fr->tag_array2->wt <<endl;
        exit(-1);
    }
  }

  if (g_ip->print_detail)
  {
    if(g_ip->fully_assoc) return;

    /* Delay stats */
    /* data array stats */ 
    cout << endl << "Time Components:" << endl << endl;

    cout << "  Data side (with Output driver) (ns): " <<
      fr->data_array2->access_time/1e-9 << endl;

    cout <<  "\tH-tree input delay (ns): " << 
      fr->data_array2->delay_route_to_bank * 1e9 +
      fr->data_array2->delay_input_htree * 1e9 << endl;

    cout <<  "\tDecoder + wordline delay (ns): " <<
      fr->data_array2->delay_row_predecode_driver_and_block * 1e9 +
      fr->data_array2->delay_row_decoder * 1e9 << endl;

    cout <<  "\tBitline delay (ns): " <<
      fr->data_array2->delay_bitlines/1e-9 << endl;

    cout <<  "\tSense Amplifier delay (ns): " <<
      fr->data_array2->delay_sense_amp * 1e9 << endl;


    cout <<  "\tH-tree output delay (ns): " <<
      fr->data_array2->delay_subarray_output_driver * 1e9 +
      fr->data_array2->delay_dout_htree * 1e9 << endl;

    if (g_ip->is_cache && !g_ip->is_main_mem)
    {
      /* tag array stats */
      cout << endl << "  Tag side (with Output driver) (ns): " <<
        fr->tag_array2->access_time/1e-9 << endl;

      cout <<  "\tH-tree input delay (ns): " << 
        fr->tag_array2->delay_route_to_bank * 1e9 +
        fr->tag_array2->delay_input_htree * 1e9 << endl;

      cout <<  "\tDecoder + wordline delay (ns): " <<
        fr->tag_array2->delay_row_predecode_driver_and_block * 1e9 +
        fr->tag_array2->delay_row_decoder * 1e9 << endl;

      cout <<  "\tBitline delay (ns): " <<
        fr->tag_array2->delay_bitlines/1e-9 << endl;

      cout <<  "\tSense Amplifier delay (ns): " <<
        fr->tag_array2->delay_sense_amp * 1e9 << endl;

      cout <<  "\tComparator delay (ns): " <<
        fr->tag_array2->delay_comparator * 1e9 << endl;

      cout <<  "\tH-tree output delay (ns): " << 
        fr->tag_array2->delay_subarray_output_driver * 1e9 +
        fr->tag_array2->delay_dout_htree * 1e9 << endl;
    }

    /* Energy/Power stats */
    cout << endl << endl << "Power Components:" << endl << endl;
    cout << "  Data array: Total dynamic read energy/access  (nJ): " <<
      fr->data_array2->power.readOp.dynamic * 1e9 << endl;
    cout << "\tTotal leakage read/write power of a bank (mW): " <<
        fr->data_array2->power.readOp.leakage * 1e3 << endl;
    cout << "\tTotal energy in H-tree (that includes both "
      "address and data transfer) (nJ): " << 
        (fr->data_array2->power_addr_input_htree.readOp.dynamic +
         fr->data_array2->power_data_output_htree.readOp.dynamic +
         fr->data_array2->power_routing_to_bank.readOp.dynamic) * 1e9 << endl;

    cout << "\tOutput Htree Energy (nJ): " <<
      fr->data_array2->power_data_output_htree.readOp.dynamic * 1e9 << endl;
    cout <<  "\tDecoder (nJ): " <<
      fr->data_array2->power_row_predecoder_drivers.readOp.dynamic * 1e9 +
      fr->data_array2->power_row_predecoder_blocks.readOp.dynamic * 1e9 << endl;
    cout <<  "\tWordline (nJ): " <<
      fr->data_array2->power_row_decoders.readOp.dynamic * 1e9 << endl;
    cout <<  "\tBitline mux & associated drivers (nJ): " <<
      fr->data_array2->power_bit_mux_predecoder_drivers.readOp.dynamic * 1e9 +
      fr->data_array2->power_bit_mux_predecoder_blocks.readOp.dynamic * 1e9 +
      fr->data_array2->power_bit_mux_decoders.readOp.dynamic * 1e9 << endl;
    cout <<  "\tSense amp mux & associated drivers (nJ): " <<
      fr->data_array2->power_senseamp_mux_lev_1_predecoder_drivers.readOp.dynamic * 1e9 +
      fr->data_array2->power_senseamp_mux_lev_1_predecoder_blocks.readOp.dynamic * 1e9 +
      fr->data_array2->power_senseamp_mux_lev_1_decoders.readOp.dynamic * 1e9  +
      fr->data_array2->power_senseamp_mux_lev_2_predecoder_drivers.readOp.dynamic * 1e9 +
      fr->data_array2->power_senseamp_mux_lev_2_predecoder_blocks.readOp.dynamic * 1e9 +
      fr->data_array2->power_senseamp_mux_lev_2_decoders.readOp.dynamic * 1e9 << endl;
    cout <<  "\tBitlines (nJ): " <<
      fr->data_array2->power_bitlines.readOp.dynamic * 1e9 << endl;
    cout <<  "\tSense amplifier energy (nJ): " <<
      fr->data_array2->power_sense_amps.readOp.dynamic * 1e9 << endl;
    cout <<  "\tSub-array output driver (nJ): " <<
      fr->data_array2->power_output_drivers_at_subarray.readOp.dynamic * 1e9 << endl;

    if (g_ip->is_cache && !g_ip->is_main_mem)
    {
      cout << endl << "  Tag array:  Total dynamic read energy/access (nJ): " <<
        fr->tag_array2->power.readOp.dynamic * 1e9 << endl;
      cout << "\tTotal leakage read/write power of a bank (mW): " <<
          fr->tag_array2->power.readOp.leakage * 1e3 << endl;
      cout << "\tTotal energy in H-tree (that includes both "
        "address and data transfer) (nJ): " << 
          (fr->tag_array2->power_addr_input_htree.readOp.dynamic +
           fr->tag_array2->power_data_output_htree.readOp.dynamic +
           fr->tag_array2->power_routing_to_bank.readOp.dynamic) * 1e9 << endl;

      cout << "\tOutput Htree Energy (nJ): " <<
        fr->tag_array2->power_data_output_htree.readOp.dynamic * 1e9 << endl;
      cout <<  "\tDecoder (nJ): " <<
        fr->tag_array2->power_row_predecoder_drivers.readOp.dynamic * 1e9 +
        fr->tag_array2->power_row_predecoder_blocks.readOp.dynamic * 1e9 << endl;
      cout <<  "\tWordline (nJ): " <<
        fr->tag_array2->power_row_decoders.readOp.dynamic * 1e9 << endl;
      cout <<  "\tBitline mux & associated drivers (nJ): " <<
        fr->tag_array2->power_bit_mux_predecoder_drivers.readOp.dynamic * 1e9 +
        fr->tag_array2->power_bit_mux_predecoder_blocks.readOp.dynamic * 1e9 +
        fr->tag_array2->power_bit_mux_decoders.readOp.dynamic * 1e9 << endl;
      cout <<  "\tSense amp mux & associated drivers (nJ): " <<
        fr->tag_array2->power_senseamp_mux_lev_1_predecoder_drivers.readOp.dynamic * 1e9 +
        fr->tag_array2->power_senseamp_mux_lev_1_predecoder_blocks.readOp.dynamic * 1e9 +
        fr->tag_array2->power_senseamp_mux_lev_1_decoders.readOp.dynamic * 1e9  +
        fr->tag_array2->power_senseamp_mux_lev_2_predecoder_drivers.readOp.dynamic * 1e9 +
        fr->tag_array2->power_senseamp_mux_lev_2_predecoder_blocks.readOp.dynamic * 1e9 +
        fr->tag_array2->power_senseamp_mux_lev_2_decoders.readOp.dynamic * 1e9 << endl;
      cout <<  "\tBitlines (nJ): " <<
        fr->tag_array2->power_bitlines.readOp.dynamic * 1e9 << endl;
      cout <<  "\tSense amplifier energy (nJ): " <<
        fr->tag_array2->power_sense_amps.readOp.dynamic * 1e9 << endl;
      cout <<  "\tSub-array output driver (nJ): " <<
        fr->tag_array2->power_output_drivers_at_subarray.readOp.dynamic * 1e9 << endl;
    }

    cout << endl << endl <<  "Area Components:" << endl << endl;
    /* Data array area stats */
    cout <<  "  Data array: Area (mm2): " << fr->data_array2->area * 1e-6 << endl;
    cout <<  "\tHeight (mm): " <<
      fr->data_array2->all_banks_height*1e-3 << endl;
    cout <<  "\tWidth (mm): " <<
      fr->data_array2->all_banks_width*1e-3 << endl;
    if (g_ip->print_detail) {
      cout <<  "\tArea efficiency (Memory cell area/Total area) - " <<
        fr->data_array2->area_efficiency << " %" << endl;
      cout << "\t\tMAT Height (mm): " <<
        fr->data_array2->mat_height*1e-3 << endl;
      cout << "\t\tMAT Length (mm): " <<
        fr->data_array2->mat_length*1e-3 << endl;
      cout << "\t\tSubarray Height (mm): " <<
        fr->data_array2->subarray_height*1e-3 << endl;
      cout << "\t\tSubarray Length (mm): " <<
        fr->data_array2->subarray_length*1e-3 << endl;
    }

    /* Tag array area stats */
    if (g_ip->is_cache && !g_ip->is_main_mem)
    {
      cout << endl << "  Tag array: Area (mm2): " << fr->tag_array2->area * 1e-6 << endl;
      cout <<  "\tHeight (mm): " <<
        fr->tag_array2->all_banks_height*1e-3 << endl;
      cout <<  "\tWidth (mm): " <<
        fr->tag_array2->all_banks_width*1e-3 << endl;
      if (g_ip->print_detail)
      {
        cout <<  "\tArea efficiency (Memory cell area/Total area) - " <<
          fr->tag_array2->area_efficiency << " %" << endl;
        cout << "\t\tMAT Height (mm): " <<
          fr->tag_array2->mat_height*1e-3 << endl;
        cout << "\t\tMAT Length (mm): " <<
          fr->tag_array2->mat_length*1e-3 << endl;
        cout << "\t\tSubarray Height (mm): " <<
          fr->tag_array2->subarray_height*1e-3 << endl;
        cout << "\t\tSubarray Length (mm): " <<
          fr->tag_array2->subarray_length*1e-3 << endl;
      }
    }


    Wire wpr;
    wpr.print_wire();

    //cout << "FO4 = " << g_tp.FO4 << endl;
  }
}

/***** Alireza - BEGIN *****/
void output_summary_of_results(uca_org_t *fr) {

  unsigned int cache_size = g_ip->cache_sz;
  string cache_size_unit = "B";
  if ( 1024 <= g_ip->cache_sz && g_ip->cache_sz < 1024*1024 ) {
    cache_size = g_ip->cache_sz / 1024;
    cache_size_unit = "KB";
  } else  if ( 1024*1024 <= g_ip->cache_sz && g_ip->cache_sz < 1024*1024*1024 ) {
    cache_size = g_ip->cache_sz / (1024*1024);
    cache_size_unit = "MB";
  }

  cout << fr->access_time*1e9 << "\t" << fr->power.readOp.dynamic*1e9 << "\t" << fr->power.writeOp.dynamic*1e9 << "\t" << fr->power.readOp.leakage*1e3 << "\t" << fr->area*1e-3*1e-3 << endl;
  
  cout << "-------------------------------------------------------------\n";
  
  cout << "---------- P-CACTI, Uniform Cache Access ----------\n";
  cout << "Cache size        : " << cache_size << cache_size_unit << endl; // unit. -Alireza
  cout << "Technology        : " << g_ip->F_sz_nm << "nm" << endl; // changed to nm. -Alireza
  cout << "Transistor type   : " << (g_ip->is_finfet ? "FinFET" : "CMOS" ) << endl; // Alireza
  cout << "Operating voltage : " << (g_ip->is_near_threshold ? "Near-threshold" : "Super-threshold" ) << endl; // Alireza
  if (g_ip->sram_cell_design.getType()==std_6T) { // Alireza
    cout << "SRAM cell type    : " << "Standard 6T" << endl;
  } else if (g_ip->sram_cell_design.getType()==std_8T) {
    cout << "SRAM cell type    : " << "Standard 8T" << endl;
  }
  cout << "Temperature       : " << g_ip->temp << "K" << endl; // Alireza
  if (g_ip->is_cache) {
    cout << "cache type        : " << "Cache" << endl;
  } else if (g_ip->is_main_mem) {
    cout << "cache type        : " << "Main Memory" << endl; // Alireza
  } else { // Alireza
    cout << "cache type        : " << "Scratch RAM" << endl;
  }
  
  cout << "-------------------------------------------------------------\n";
  
  cout << "Access time                           : " << fr->access_time*1e9 << " ns" << endl;
  cout << "Cycle time                            : " << fr->cycle_time*1e9 << " ns" << endl;
  if (g_ip->data_arr_ram_cell_tech_type < 4) {
    cout << "Total dynamic read energy per access  : " << fr->power.readOp.dynamic*1e9 << " nJ" << endl;
    cout << "Total dynamic write energy per access : " << fr->power.writeOp.dynamic*1e9 << " nJ" << endl;
    cout << "Total leakage power of a bank         : " << fr->power.readOp.leakage*1e3 << " mW" << endl;
  }
  cout << "Cache height x width                  : " << fr->cache_ht*1e-3 << " mm x " << fr->cache_len*1e-3 << " mm" << endl;
  cout << "Cache area                            : " << fr->area*1e-3*1e-3 << " mm2" << endl;
  
  cout << "-------------------------------------------------------------\n";

    cout << "Data Array Leakage Power Components:" << endl;
    cout << "\tTotal leakage power: " <<
        fr->data_array2->power.readOp.leakage * 1e3 << "mW" << endl;
    cout << "\tBank leakage power: " <<
        fr->data_array2->leak_power_bank * 1e3 << "mW" << endl;
    cout << "\tMat leakage power: " <<
        fr->data_array2->leak_power_mat * 1e3 << "mW" << endl;
    cout << "\tMemory array leakage power: " <<
        fr->data_array2->leak_power_mem_array * 1e3 << "mW" << endl;
    cout << "\tSRAM cell leakage power: " <<
        fr->data_array2->leak_power_sram_cell * 1e9 << "nW" << endl;

    cout << endl << "Subarray Statistics:" << endl;
    cout << "\tSubarray - Number of rows: " <<
        fr->data_array2->subarray_num_rows << endl;
    cout << "\tSubarray - Number of columns: " <<
        fr->data_array2->subarray_num_cols << endl;
    cout << "\tNumber of subarrays per Mat: " <<
        fr->data_array2->num_subarrays_per_mat << endl;
		  
  cout << "-------------------------------------------------------------\n";
  
  cout << "Best Ndwl     : " << fr->data_array2->Ndwl << endl;
  cout << "Best Ndbl     : " << fr->data_array2->Ndbl << endl;
  cout << "Best Nspd     : " << fr->data_array2->Nspd << endl;
  cout << "Best Ndcm     : " << fr->data_array2->deg_bl_muxing << endl;
  cout << "Best Ndsam L1 : " << fr->data_array2->Ndsam_lev_1 << endl;
  cout << "Best Ndsam L2 : " << fr->data_array2->Ndsam_lev_2 << endl;
  
  cout << "-------------------------------------------------------------\n";
}

void output_summary_of_results_file(uca_org_t *fr) {
  ofstream fout("pcacti_report.txt", ios::out);
  fout << "Access time                           : " << fr->access_time*1e9 << " ns" << endl;
  fout << "Cycle time                            : " << fr->cycle_time*1e9 << " ns" << endl;
  if (g_ip->data_arr_ram_cell_tech_type < 4) {
    fout << "Total dynamic read energy per access  : " << fr->power.readOp.dynamic*1e9 << " nJ" << endl;
    fout << "Total dynamic write energy per access : " << fr->power.writeOp.dynamic*1e9 << " nJ" << endl;
    fout << "Total leakage power of a bank         : " << fr->power.readOp.leakage*1e3 << " mW" << endl;
  }
  fout << "Cache height x width                  : " << fr->cache_ht*1e-3 << " mm x " << fr->cache_len*1e-3 << " mm" << endl;
  fout << "Cache area                            : " << fr->area*1e-3*1e-3 << " mm2" << endl;

  ofstream csv("pcacti.csv", ios::out);
  csv.precision(12);
  csv << "tech_node_nm,capacity_bytes,associativity,output_width_bits,";
  csv << "access_time_ns,cycle_time_ns,dyn_read_energy_nj,dyn_write_energy_nj,";
  csv << "standby_leakage_per_bank_mw,area_mm2,fo4_ps,width_um,height_um" << endl;
  csv << g_ip->F_sz_nm << ",";
  csv << g_ip->cache_sz << ",";
  csv << g_ip->tag_assoc << ",";
  csv << g_ip->out_w << ",";
  csv << fr->access_time*1e9 << ",";
  csv << fr->cycle_time*1e9 << ",";
  csv << fr->power.readOp.dynamic*1e9 << ",";
  csv << fr->power.writeOp.dynamic*1e9 << ",";
  csv << fr->power.readOp.leakage*1e3 << ",";
  csv << fr->area*1e-6 << ",";
  csv << g_tp.FO4*1e12 << ",";
  csv << fr->cache_len << ",";
  csv << fr->cache_ht << endl;
}

/****** Alireza - END ******/
