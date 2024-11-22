from pyverilog.vparser.parser import parse
from pyverilog.vparser.ast import Node, InstanceList, Instance, PortArg
from graphviz import Digraph

def create_schematic_from_ast(ast):
    """
    Generate a schematic diagram based on the parsed AST, clustering input ports.
    
    Args:
    - ast: Parsed abstract syntax tree from the Verilog file.
    """
    # Initialize a Graphviz Digraph for the schematic
    schematic = Digraph(format='svg')
    schematic.attr(rankdir='LR')  # Left-to-right layout, orthogonal edges

    # Cluster for input ports
    with schematic.subgraph(name="cluster_inputs") as inputs_cluster:
        inputs_cluster.attr(style="solid", color="blue", label="Inputs", fontsize="12")
        
        # Traverse the AST to extract input ports
        def add_input_ports(node):
            if (node.__class__.__name__ == 'Input'):
                port_name = node.name
                inputs_cluster.node(port_name, shape="ellipse", style="filled", color="lightgrey")

            if hasattr(node, 'children'):
                for child in node.children():
                    add_input_ports(child)

        # Traverse the AST to find module instances and their port connections
        def traverse_ast_for_schematic(node):
            if isinstance(node, InstanceList):
                for inst in node.instances:
                    if isinstance(inst, Instance):
                        instance_name = inst.name
                        module_name = inst.module
                        instance_label = f"{module_name}\\n({instance_name})"

                        # Add a node for the instance
                        schematic.node(instance_name, label=instance_label, shape='box', style='rounded,filled', color='lightblue')

                        # Add edges for each port connection
                        for port in inst.portlist:
                            if isinstance(port, PortArg):
                                external_wire = port.argname.name if hasattr(port.argname, 'name') else str(port.argname)
                                internal_port = port.portname
                                # Add a connection edge
                                schematic.edge(external_wire, f"{instance_name}:{internal_port}", label=f"{internal_port}", arrowhead="vee", color="black")

            # Recursively traverse child nodes
            if hasattr(node, 'children'):
                for child in node.children():
                    traverse_ast_for_schematic(child)

        # Start traversing from the root node to populate inputs cluster
        add_input_ports(ast)
        traverse_ast_for_schematic(ast)

    # Save the schematic
    filename_schematic = "output/verilog_schematic_with_inputs"
    schematic.render(filename=filename_schematic, format='svg', cleanup=True)
    print(f"Schematic saved as '{filename_schematic}.svg'")

# File containing the preprocessed Verilog
flattened_verilog_file = "output/flattened_design.v"

# Parse the preprocessed file
ast, _ = parse([flattened_verilog_file])

# Generate schematic from AST
create_schematic_from_ast(ast)
