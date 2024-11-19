import subprocess
verilog_file = "design/design.v"
flattened_verilog_file = "output/flattened_design.v"
macros = ["RUMI_PLL", "PLL_SIM"]

# Preprocess the Verilog file using iverilog
subprocess.run(['iverilog', '-E'] + [f'-D{macro}' for macro in macros] + [verilog_file, '-o', flattened_verilog_file], check=True)
