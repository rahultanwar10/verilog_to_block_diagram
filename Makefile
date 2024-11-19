DESIGN_DIR= design
SCRIPT_DIR= script
OUTPUT_DIR= output

all: generate_schematic

generate_schematic: flattened_verilog
	python3 $(SCRIPT_DIR)/generate_schematic.py | tee $(OUTPUT_DIR)/build.log
	mv parser.out $(OUTPUT_DIR)
	mv parsetab.py $(OUTPUT_DIR)

ast: flattened_verilog
	python3 $(SCRIPT_DIR)/ast_understanding.py | tee $(OUTPUT_DIR)/build.log
	mv parser.out $(OUTPUT_DIR)
	mv parsetab.py $(OUTPUT_DIR)

flattened_verilog:
	python3 $(SCRIPT_DIR)/flatten_verilog.py

clean:
	rm -rf $(OUTPUT_DIR)/*