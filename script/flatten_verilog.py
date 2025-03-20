import subprocess
import argparse

parser = argparse.ArgumentParser(description="Generate a Verilog schematic diagram.")
parser.add_argument("-input_file", required=True, help="Path to the input Verilog file")
parser.add_argument("-output", required=True, help="Path to the output schematic file (without extension)")
parser.add_argument("-macros", required=True, help="Please give the macros for the verilog file, if any.")

args = parser.parse_args()

macros = args.macros
macros = macros.split()
# Preprocess the Verilog file using iverilog
subprocess.run(['iverilog', '-E'] + [f'-D{macro}' for macro in macros] + [args.input_file, '-o', args.output], check=True)