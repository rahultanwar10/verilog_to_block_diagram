from pyverilog.vparser.parser import parse
from pyverilog.vparser.ast import Node, InstanceList, Instance, PortArg
from graphviz import Digraph
import argparse

def print_and_create_ast(node, indent=0):
    """
    Recursively prints the structure of the AST node, and simultaneously creates nodes and edges in a Graphviz graph.
    
    Args:
    - node: The current AST node.
    - graph: The Graphviz Digraph object.
    - indent: Current indentation level for printing.
    - parent_id: The ID of the parent node, used to connect edges in the graph.
    """
    indent_str = "  " * indent
    print(f"{indent_str}{node.__class__.__name__}", end="")
    label = node.__class__.__name__

    if hasattr(node, 'name'):
        print(f" (name: {node.name})")
        label += f"\nname: {node.name}"
    elif hasattr(node, 'varname'):
        print(f" (varname: {node.varname})")
        label += f"\nvarname: {node.varname}"
    elif hasattr(node, 'value'):
        print(f" (value: {node.value})")
        label += f"\nvalue: {node.value}"
    else:
        print("")

    if isinstance(node, InstanceList):
        for inst in node.instances:
            if isinstance(inst, Instance):
                for port in inst.portlist:
                    if isinstance(port, PortArg):
                        # print(f'vars() = {vars(port)}')
                        if hasattr(port.argname, "var"):
                            temp_port_argname = port.argname.var
                        elif hasattr(port.argname, "name"):
                            temp_port_argname = port.argname.name
                        else:
                            temp_port_argname = port.argname
                        print(f"{indent_str}  Internal port: {port.portname}, External wire: {temp_port_argname}")
                        label += f"\n{port.portname} -> {port.argname}"

    if hasattr(node, 'children'):
        for child in node.children():
            print_and_create_ast(child, indent + 1)

parser = argparse.ArgumentParser(description="Generate a Verilog schematic diagram.")
parser.add_argument("-input_file", required=True, help="Path to the input Verilog file")
args = parser.parse_args()

# Parse the preprocessed file
ast, _ = parse([args.input_file])

print_and_create_ast(ast)
