from pyverilog.vparser.parser import parse
from pyverilog.vparser.ast import Node, InstanceList, Instance, PortArg
from graphviz import Digraph

def print_and_create_ast_graph(node, graph, indent=0, parent_id=None):
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

    node_id = str(id(node))
    graph.node(node_id, label=label, shape='box', style='rounded,filled', color='lightblue')

    if parent_id:
        graph.edge(parent_id, node_id)

    if isinstance(node, InstanceList):
        for inst in node.instances:
            if isinstance(inst, Instance):
                for port in inst.portlist:
                    if isinstance(port, PortArg):
                        if hasattr(port.argname, 'name'):
                            temp_port_argname = port.argname.name
                        else:
                            temp_port_argname = port.argname
                        print(f"{indent_str}  Internal port: {port.portname}, External wire: {temp_port_argname}")
                        label += f"\n{port.portname} -> {port.argname}"

    if hasattr(node, 'children'):
        for child in node.children():
            print_and_create_ast_graph(child, graph, indent + 1, node_id)

# Load the Verilog file and define macros

flattened_verilog_file = "output/flattened_design.v"

# Parse the preprocessed file
ast, _ = parse([flattened_verilog_file])

# Generate AST visualization
print("Abstract Syntax Tree Structure:")
graph = Digraph(format='png')
graph.attr(rankdir='TB')

print_and_create_ast_graph(ast, graph)

# Render and save the AST diagram
filename_ast = "output/ast_structure_1"
graph.render(filename=filename_ast, format='svg')
print(f"AST structure saved as '{filename_ast}.svg'")
