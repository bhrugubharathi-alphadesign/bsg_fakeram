export TOP_DIR := $(shell git rev-parse --show-toplevel)

export PCACTI_BUILD_DIR := $(TOP_DIR)/tools/pcacti
export CACTI_BUILD_DIR := $(TOP_DIR)/tools/cacti
CACTI_COMMIT := 1ffd8dfb10303d306ecd8d215320aea07651e878

CONFIG := $(TOP_DIR)/example_cfgs/pcacti7.cfg

OUT_DIR := $(TOP_DIR)/results

.PHONY: run clean tools pcacti_tools cacti_tools clean_tools

run:
	./scripts/run.py $(CONFIG) --output_dir $(OUT_DIR)

view.%:
	klayout ./$(OUT_DIR)/$*/$*.lef &

clean:
	rm -rf $(OUT_DIR)

#=======================================
# TOOLS
#=======================================

tools: pcacti_tools cacti_tools

pcacti_tools:
	$(MAKE) -C $(PCACTI_BUILD_DIR)

cacti_tools: $(CACTI_BUILD_DIR)/cacti

$(CACTI_BUILD_DIR)/.bsg_fakeram_patched:
	mkdir -p $(@D)
	test -d $(CACTI_BUILD_DIR)/.git || git clone https://github.com/HewlettPackard/Cacti.git $(CACTI_BUILD_DIR)
	cd $(CACTI_BUILD_DIR) && git checkout $(CACTI_COMMIT)
	cd $(CACTI_BUILD_DIR) && if git apply --check $(TOP_DIR)/patches/cacti.patch; then git apply $(TOP_DIR)/patches/cacti.patch; elif git apply --reverse --check $(TOP_DIR)/patches/cacti.patch; then true; else exit 1; fi
	sh $(TOP_DIR)/patches/nmlimitremoval_patch.sh
	touch $@

$(CACTI_BUILD_DIR)/cacti: $(CACTI_BUILD_DIR)/.bsg_fakeram_patched
	$(MAKE) -C $(CACTI_BUILD_DIR) -j4

clean_tools:
	$(MAKE) -C $(PCACTI_BUILD_DIR) clean
	rm -f $(PCACTI_BUILD_DIR)/pcacti_report.txt
	rm -f $(PCACTI_BUILD_DIR)/pcacti_detailed_report.txt
	rm -f $(PCACTI_BUILD_DIR)/pcacti.csv
	rm -f $(PCACTI_BUILD_DIR)/out.csv
	rm -rf $(CACTI_BUILD_DIR)
