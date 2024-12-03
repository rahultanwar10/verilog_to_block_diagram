from pyverilog.vparser.parser import parse
from pyverilog.vparser.ast import Node, InstanceList, Instance, PortArg
from graphviz import Digraph
import argparse

node_name_mapping = {"input":{}, "wire":{"input":{}, "output":{}}, "output":{}}

def extract_always_block_code(filename, start_lineno):
    with open(filename, 'r') as file:
        lines = file.readlines()
    block_code = []
    nested_count = 0
    capturing = False
    for i, line in enumerate(lines):
        if i + 1 >= start_lineno:
            capturing = True
        if capturing:
            block_code.append(line)
            if 'begin' in line:
                nested_count += 1
            if 'end' in line:
                nested_count -= 1
                if nested_count == 0:
                    break
    return ''.join(block_code)

def extract_assign_statement_code(filename, start_lineno):
    with open(filename, 'r') as file:
        lines = file.readlines()
    return lines[start_lineno - 1]

def create_schematic_from_ast(ast):
    # Initialize a Graphviz Digraph for the schematic
    schematic = Digraph(format='svg')
    # schematic.attr(rankdir='LR', nodesep="1.0", ranksep="1.0", splines="ortho")  # Left-to-right layout, orthogonal edges
    # schematic.attr(rankdir='LR', nodesep="1.0", ranksep="1.0")  # Left-to-right layout, orthogonal edges
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

    with schematic.subgraph(name="cluster_outputs") as outputs_cluster:
        outputs_cluster.attr(style="solid", color="blue", label="Outputs", fontsize="12")
    
        # Traverse the AST to extract input ports
        def add_output_ports(node):
            if (node.__class__.__name__ == 'Output'):
                port_name = node.name
                node_name = "output_" + str(node.name)
                outputs_cluster.node(node_name, label=str(port_name), shape="ellipse", style="filled", color="lightgrey")
                node_name_mapping["output"][port_name] = node_name

            if hasattr(node, 'children'):
                for child in node.children():
                    add_output_ports(child)

        # Start traversing from the root node to populate inputs cluster
        add_output_ports(ast)

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
                    node_name = str(instance_label) + str(internal_port)
                    instance_cluster.node(node_name, label=internal_port, shape="ellipse", style="filled", color="lightgrey")
                    if (port.argname == None):
                        external_wire = str(port.argname)
                    elif hasattr(port.argname, "var"):
                        external_wire = str(port.argname.var)
                    elif hasattr(port.argname, "name"):
                        external_wire = str(port.argname.name)
                    if str(external_wire) in node_name_mapping["input"]:
                        schematic.edge(f'{node_name_mapping["input"][str(external_wire)]}:e', f'{node_name}:w', label=f"{external_wire}", arrowhead="vee", color="black")
                    elif external_wire in node_name_mapping["wire"]["output"]:
                        if isinstance(node_name_mapping["wire"]["output"][external_wire], list):
                            for target_node in node_name_mapping["wire"]["output"][external_wire]:
                                schematic.edge(f'{target_node}:e', f'{node_name}:w', label=f"{external_wire}", arrowhead="vee", color="black")
                        else:
                            schematic.edge(f'{node_name_mapping["wire"]["output"][external_wire]}:e', f'{node_name}:w', label=f"{external_wire}", arrowhead="vee", color="black")
                    elif external_wire in node_name_mapping["wire"]["input"]:
                        if isinstance(node_name_mapping["wire"]["input"][external_wire], list):
                            for target_node in node_name_mapping["wire"]["input"][external_wire]:
                                schematic.edge(f'{node_name}:e', f'{target_node}:w', label=f"{external_wire}", arrowhead="vee", color="black")
                        else:
                            schematic.edge(f'{node_name}:e', f'{node_name_mapping["wire"]["input"][external_wire]}:w', label=f"{external_wire}", arrowhead="vee", color="black")
                    elif external_wire in node_name_mapping["output"]:
                        schematic.edge(f'{node_name}:e', f'{node_name_mapping["output"][str(external_wire)]}:w', label=f"{external_wire}", arrowhead="vee", color="black")
                    if external_wire in node_name_mapping["wire"]["output"] and not isinstance(node_name_mapping["wire"]["output"][external_wire], list):
                        node_name_mapping["wire"]["output"][external_wire] = [node_name_mapping["wire"]["output"][external_wire]]
                        node_name_mapping["wire"]["output"][external_wire].append(node_name)
                    elif external_wire in node_name_mapping["wire"]["output"] and isinstance(node_name_mapping["wire"]["output"][external_wire], list):
                        node_name_mapping["wire"]["output"][external_wire].append(node_name)
                    else:
                        node_name_mapping["wire"]["output"][external_wire] = node_name

        # Recursively traverse child nodes
        if hasattr(node, 'children'):
            for child in node.children():
                traverse_ast_for_schematic(child)

    traverse_ast_for_schematic(ast)

    def l_value_extractor(node):
        # print(f'vars in L value = {vars(node)}')
        # print(f'node in l_value_extractor = {node}')
        if hasattr(node, 'name'):
            return str(node.name)
        if hasattr(node, 'children'):
            for child in node.children():
                result = l_value_extractor(child)
                if result is not None:  # Return as soon as a non-None result is found
                    return result

    def signal_extractor(node, signal_dict=None):
        if signal_dict is None:
            signal_dict = {"input": set(), "output": set()}

        # Check for signal direction based on node attributes
        if (node.__class__.__name__ == 'Lvalue'):
            signal_name = l_value_extractor(node)
            signal_dict["output"].add(signal_name)
        elif hasattr(node, 'name'):
            signal_dict["input"].add(node.name)

        # Recursively process child nodes
        if hasattr(node, 'children'):
            for child in node.children():
                signal_extractor(child, signal_dict)

        return signal_dict

    def add_always_blocks_to_schematic(node):
        if node.__class__.__name__ == 'Always':
            # Extract the always block code as the node label
            always_code = extract_always_block_code(args.input_file,node.lineno)
            always_code = always_code.replace("\n", "\\l")
            always_node_name = f"always_{id(node)}"
            
            # Add the Always block as a node
            schematic.node(always_node_name, label=always_code, shape="box", style="rounded,filled", color="lightblue", fontsize="10", fontname="Courier")
            signal_names = signal_extractor(node)
            signal_names['input'] -= signal_names['output']
            for input_signal in signal_names["input"]:
                if input_signal in node_name_mapping["wire"]["input"] and not isinstance(node_name_mapping["wire"]["input"][input_signal], list):
                    node_name_mapping["wire"]["input"][input_signal] = [node_name_mapping["wire"]["input"][input_signal]]
                    node_name_mapping["wire"]["input"][input_signal].append(always_node_name)
                elif input_signal in node_name_mapping["wire"]["input"] and isinstance(node_name_mapping["wire"]["input"][input_signal], list):
                    node_name_mapping["wire"]["input"][input_signal].append(always_node_name)
                else:
                    node_name_mapping["wire"]["input"][input_signal] = always_node_name
                if input_signal in node_name_mapping["input"]:
                    schematic.edge(f'{node_name_mapping["input"][input_signal]}:e', f'{always_node_name}:w', label=f"{input_signal}", arrowhead="vee", color="black")
                elif input_signal in node_name_mapping["wire"]["output"]:
                    if isinstance(node_name_mapping["wire"]["output"][input_signal], list):
                        for target_node in node_name_mapping["wire"]["output"][input_signal]:
                            schematic.edge(f'{target_node}:e', f'{always_node_name}:w', label=f"{input_signal}", arrowhead="vee", color="black")
                    else:
                        schematic.edge(f'{node_name_mapping["wire"]["output"][input_signal]}:e', f'{always_node_name}:w', label=f"{input_signal}", arrowhead="vee", color="black")

            for output_signal in signal_names["output"]:
                if output_signal in node_name_mapping["wire"]["output"] and not isinstance(node_name_mapping["wire"]["output"][output_signal], list):
                    node_name_mapping["wire"]["output"][output_signal] = [node_name_mapping["wire"]["output"][output_signal]]
                    node_name_mapping["wire"]["output"][output_signal].append(always_node_name)
                elif output_signal in node_name_mapping["wire"]["output"] and isinstance(node_name_mapping["wire"]["output"][output_signal], list):
                    node_name_mapping["wire"]["output"][output_signal].append(always_node_name)
                else:
                    node_name_mapping["wire"]["output"][output_signal] = always_node_name
                if output_signal in node_name_mapping["wire"]["input"]:
                    if isinstance(node_name_mapping["wire"]["input"][output_signal], list):
                        for target_node in node_name_mapping["wire"]["input"][output_signal]:
                            schematic.edge(f'{always_node_name}:e', f'{target_node}:w', label=f"{output_signal}", arrowhead="vee", color="black")
                    else:
                        schematic.edge(f'{always_node_name}:e', f'{node_name_mapping["wire"]["input"][output_signal]}:w', label=f"{output_signal}", arrowhead="vee", color="black")
                elif output_signal in node_name_mapping["output"]:
                    schematic.edge(f'{always_node_name}:e', f'{node_name_mapping["output"][output_signal]}:w', label=f"{output_signal}", arrowhead="vee", color="black")

        # Recursively traverse child nodes
        if hasattr(node, 'children'):
            for child in node.children():
                add_always_blocks_to_schematic(child)

    # Add this call after other AST processing
    add_always_blocks_to_schematic(ast)

    def add_assign_statements_to_schematic(node):
        if node.__class__.__name__ == 'Assign':
            # Extract the always block code as the node label
            assign_code = extract_assign_statement_code(args.input_file,node.lineno)
            # always_code = node.to_verilog() if hasattr(node, 'to_verilog') else "Always Block"
            assign_node_name = f"assign_{id(node)}"
            
            # Add the Always block as a node
            schematic.node(assign_node_name, label=assign_code, shape="box", style="rounded,filled", color="lightblue", fontsize="10", fontname="Courier")
            signal_names = signal_extractor(node)
            signal_names['input'] -= signal_names['output']
            for input_signal in signal_names["input"]:
                if input_signal in node_name_mapping["wire"]["input"] and not isinstance(node_name_mapping["wire"]["input"][input_signal], list):
                    node_name_mapping["wire"]["input"][input_signal] = [node_name_mapping["wire"]["input"][input_signal]]
                    node_name_mapping["wire"]["input"][input_signal].append(assign_node_name)
                elif input_signal in node_name_mapping["wire"]["input"] and isinstance(node_name_mapping["wire"]["input"][input_signal], list):
                    node_name_mapping["wire"]["input"][input_signal].append(assign_node_name)
                else:
                    node_name_mapping["wire"]["input"][input_signal] = assign_node_name
                if input_signal in node_name_mapping["input"]:
                    schematic.edge(f'{node_name_mapping["input"][input_signal]}:e', f'{assign_node_name}:w', label=f"{input_signal}", arrowhead="vee", color="black")
                elif input_signal in node_name_mapping["wire"]["output"]:
                    if isinstance(node_name_mapping["wire"]["output"][input_signal], list):
                        for target_node in node_name_mapping["wire"]["output"][input_signal]:
                            schematic.edge(f'{target_node}:e', f'{assign_node_name}:w', label=f"{input_signal}", arrowhead="vee", color="black")
                    else:
                        schematic.edge(f'{node_name_mapping["wire"]["output"][input_signal]}:e', f'{assign_node_name}:w', label=f"{input_signal}", arrowhead="vee", color="black")

            for output_signal in signal_names["output"]:
                if output_signal in node_name_mapping["wire"]["output"] and not isinstance(node_name_mapping["wire"]["output"][output_signal], list):
                    node_name_mapping["wire"]["output"][output_signal] = [node_name_mapping["wire"]["output"][output_signal]]
                    node_name_mapping["wire"]["output"][output_signal].append(assign_node_name)
                elif output_signal in node_name_mapping["wire"]["output"] and isinstance(node_name_mapping["wire"]["output"][output_signal], list):
                    node_name_mapping["wire"]["output"][output_signal].append(assign_node_name)
                else:
                    node_name_mapping["wire"]["output"][output_signal] = assign_node_name
                if output_signal in node_name_mapping["wire"]["input"]:
                    if isinstance(node_name_mapping["wire"]["input"][output_signal], list):
                        for target_node in node_name_mapping["wire"]["input"][output_signal]:
                            schematic.edge(f'{assign_node_name}:e', f'{target_node}:w', label=f"{output_signal}", arrowhead="vee", color="black")
                    else:
                        schematic.edge(f'{assign_node_name}:e', f'{node_name_mapping["wire"]["input"][output_signal]}:w', label=f"{output_signal}", arrowhead="vee", color="black")
                elif output_signal in node_name_mapping["output"]:
                    schematic.edge(f'{assign_node_name}:e', f'{node_name_mapping["output"][output_signal]}:w', label=f"{output_signal}", arrowhead="vee", color="black")

        # Recursively traverse child nodes
        if hasattr(node, 'children'):
            for child in node.children():
                add_assign_statements_to_schematic(child)

    # Add this call after other AST processing
    add_assign_statements_to_schematic(ast)

    # Save the schematic
    filename_schematic = args.output
    schematic.render(filename=filename_schematic, format='svg', cleanup=True)
    print(f"Schematic saved as '{filename_schematic}.svg'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Verilog schematic diagram.")
    parser.add_argument("-input_file", required=True, help="Path to the input Verilog file")
    parser.add_argument("-output", required=True, help="Path to the output schematic file (without extension)")

    args = parser.parse_args()

    # Parse the Verilog file
    ast, _ = parse([args.input_file])

    # Generate schematic from AST
    create_schematic_from_ast(ast)
    # print(f'node_name_mapping = {node_name_mapping}')