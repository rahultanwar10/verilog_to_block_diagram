ACTUAL_DESIGN_DIR = /mnt/c/Users/rahusi/Work/cm4/
DESIGN_DIR= design
SCRIPT_DIR= script
OUTPUT_DIR= output


SCRIPTS := $(wildcard $(SCRIPT_DIR)/*.py)
VERILOG_FILES := $(shell find $(ACTUAL_DESIGN_DIR) -type f \( -name "*.v" -o -name "*.sv" \))
FLATTENED_FILES := $(patsubst %, $(OUTPUT_DIR)/flatten_verilog_files/%_flattened_verilog.v, $(notdir $(basename $(VERILOG_FILES))))
# FLATTENED_FILES += $(patsubst $(DESIGN_DIR)/%.sv, $(OUTPUT_DIR)/flatten_verilog_files/%_flattened_verilog.v, $(notdir $(basename $(VERILOG_FILES))))
SCHEMATIC_FILES := $(patsubst $(OUTPUT_DIR)/flatten_verilog_files/%_flattened_verilog.v, $(OUTPUT_DIR)/schematic_files/%_schematic.svg, $(FLATTENED_FILES))
AST_LOG_FILES := $(patsubst $(OUTPUT_DIR)/flatten_verilog_files/%_flattened_verilog.v, $(OUTPUT_DIR)/ast_files/%_ast.log, $(FLATTENED_FILES))

print:
	@echo $(VERILOG_FILES)
	@echo $(FLATTENED_FILES)
	@echo $(SCHEMATIC_FILES)
	@echo $(AST_LOG_FILES)

all: create_output_dir copy_design_files generate_schematic ast

create_output_dir:
	@mkdir -p $(OUTPUT_DIR)/flatten_verilog_files
	@mkdir -p $(OUTPUT_DIR)/schematic_files
	@mkdir -p $(OUTPUT_DIR)/ast_files

copy_design_files:
	@for file in $(VERILOG_FILES); do \
		basename=$$(basename $$file); \
		cp $$file $(DESIGN_DIR)/$${basename%.*}.v; \
	done

generate_schematic: $(SCHEMATIC_FILES)

ast: $(AST_LOG_FILES)

flattened_verilog: $(FLATTENED_FILES)

$(OUTPUT_DIR)/schematic_files/%_schematic.svg: $(OUTPUT_DIR)/flatten_verilog_files/%_flattened_verilog.v $(SCRIPT_DIR)/generate_schematic.py
	python3 $(SCRIPT_DIR)/generate_schematic.py -input_file $< -output $(basename $@) -design_dir $(DESIGN_DIR) | tee $<_schematic.log
	mv parser.out $(OUTPUT_DIR)
	mv parsetab.py $(OUTPUT_DIR)

$(OUTPUT_DIR)/ast_files/%_ast.log: $(OUTPUT_DIR)/flatten_verilog_files/%_flattened_verilog.v $(SCRIPT_DIR)/ast_understanding.py
	python3 $(SCRIPT_DIR)/ast_understanding.py -input_file $< | tee $@
	mv parser.out $(OUTPUT_DIR)
	mv parsetab.py $(OUTPUT_DIR)

$(OUTPUT_DIR)/flatten_verilog_files/%_flattened_verilog.v: $(DESIGN_DIR)/%.v $(SCRIPT_DIR)/flatten_verilog.py
	python3 $(SCRIPT_DIR)/flatten_verilog.py -input_file $< -output $@

clean:
	rm -rf $(OUTPUT_DIR)/*
	rm -rf $(DESIGN_DIR)/*
