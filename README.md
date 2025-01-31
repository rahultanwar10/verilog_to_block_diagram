# Verilog_to_block_diagram
It is a python script written to create a simple schematic block diagram out of one verilog files or multiple verilog files.

## How to run?
### Prerequisites:
- Pyverilog
- Graphviz (solution of problems related to installation of graphviz will be added later)
- iverilog (required to flatten the system verilog files which has macros inside them, eg, `ifdef COMBO. This COMBO is known as macro and now there will be multiple verilog files or RTL depending on these macros. Please google it to understand it more clearly.) If you do not have any macro then please skip this. You may need to do some changes in the python script which will be explained later. Support for automatic detection of macros will be added later. I recommend you to install it because in that case you do not need to do any changes at all.

### To Run:
1. Please provide the path to a directory which contains all the verilog files in the first line of makefile
    - ACTUAL_DESIGN_DIR = your_path_of_directory

    It will first link all the verilog and system verilog files in the design directory and also rename the system verilog files to verilog files.
2. My verilog codes contain some macros, so, I have created script in such a way that first the verilog file will be flattened by giving those macros and then it will create a schematic block diagram. So in scripts directory, there is flatten_verilog.py file in which at line 10 an example variable is defined to give all the macros. You can mention all your macros here. Even if your verilog code does not have any macro then you can leave it as it is. iverilog will not error out anything and will not change the verilog file if it does not find the mentioned macro.
3. Use the following command to run the script: `make all`