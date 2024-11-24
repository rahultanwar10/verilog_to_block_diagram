from pyverilog.vparser.parser import parse
from pyverilog.vparser.ast import Node, InstanceList, Instance, PortArg
from graphviz import Digraph

node_name_mapping = {"input":{}}

def create_schematic_from_ast(ast):
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
                node_name = "input_" + str(node.name)
                inputs_cluster.node(node_name, label=str(port_name), shape="ellipse", style="filled", color="lightgrey")
                node_name_mapping["input"][port_name] = node_name

            if hasattr(node, 'children'):
                for child in node.children():
                    add_input_ports(child)

        # Start traversing from the root node to populate inputs cluster
        add_input_ports(ast)

    # Traverse the AST to find module instances and their port connections
    def traverse_ast_for_schematic(node):
        if isinstance(node, InstanceList):
            inst = node.instances[0]
            instance_name = inst.name
            module_name = inst.module
            instance_label = f"{module_name}\\n({instance_name})"
            cluster_name = f"cluster_{instance_name}"
            
            # Add a node for the instance
            with schematic.subgraph(name=cluster_name) as instance_cluster:
                instance_cluster.attr(style="solid", color="blue", label=instance_label, fontsize="12")
                for port in inst.portlist:
                    internal_port = port.portname
                    instance_cluster.node(internal_port, shape="ellipse", style="filled", color="lightgrey")
                    if (port.argname == None):
                        external_wire = str(port.argname)
                    elif hasattr(port.argname, "var"):
                        external_wire = str(port.argname.var)
                    elif hasattr(port.argname, "name"):
                        external_wire = str(port.argname.name)
                    if str(external_wire) in node_name_mapping["input"]:
                        schematic.edge(node_name_mapping["input"][str(external_wire)], internal_port, label=f"{external_wire}", arrowhead="vee", color="black")
                    else:
                        schematic.edge(external_wire, internal_port, label=f"{external_wire}", arrowhead="vee", color="black")

        # Recursively traverse child nodes
        if hasattr(node, 'children'):
            for child in node.children():
                traverse_ast_for_schematic(child)

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
