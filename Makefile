DESIGN_DIR= design
SCRIPT_DIR= script
OUTPUT_DIR= output

SCRIPTS := $(wildcard $(SCRIPT_DIR)/*.py)
VERILOG_FILES := $(wildcard $(DESIGN_DIR)/*.v)
FLATTENED_FILES := $(patsubst $(DESIGN_DIR)/%.v, $(OUTPUT_DIR)/%_flattened_verilog.v, $(VERILOG_FILES))
SCHEMATIC_FILES := $(patsubst $(OUTPUT_DIR)/%_flattened_verilog.v, $(OUTPUT_DIR)/%_schematic.svg, $(FLATTENED_FILES))
AST_LOG_FILES := $(patsubst $(OUTPUT_DIR)/%_flattened_verilog.v, $(OUTPUT_DIR)/%_ast.log, $(FLATTENED_FILES))

all: generate_schematic ast

generate_schematic: $(SCHEMATIC_FILES)

ast: $(AST_LOG_FILES)

flattened_verilog: $(FLATTENED_FILES)

$(OUTPUT_DIR)/%_schematic.svg: $(OUTPUT_DIR)/%_flattened_verilog.v $(SCRIPT_DIR)/generate_schematic.py
	python3 $(SCRIPT_DIR)/generate_schematic.py -input_file $< -output $(basename $@) | tee $<_schematic.log
	mv parser.out $(OUTPUT_DIR)
	mv parsetab.py $(OUTPUT_DIR)

$(OUTPUT_DIR)/%_ast.log: $(OUTPUT_DIR)/%_flattened_verilog.v $(SCRIPT_DIR)/ast_understanding.py
	python3 $(SCRIPT_DIR)/ast_understanding.py -input_file $< | tee $@
	mv parser.out $(OUTPUT_DIR)
	mv parsetab.py $(OUTPUT_DIR)

$(OUTPUT_DIR)/%_flattened_verilog.v: $(DESIGN_DIR)/%.v $(SCRIPT_DIR)/flatten_verilog.py
	python3 $(SCRIPT_DIR)/flatten_verilog.py -input_file $< -output $@

clean:
	rm -rf $(OUTPUT_DIR)/*
