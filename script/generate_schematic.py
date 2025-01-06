from pyverilog.vparser.parser import parse
from pyverilog.vparser.ast import Node, InstanceList, Instance, PortArg, Wire, ModuleDef, Partselect, Decl
from graphviz import Digraph
import argparse
import os
import subprocess
import re

node_name_mapping = {"input":{}, "wire":{"input":{}, "output":{}}, "output":{}}
declared_variables = {}

def grep_module_in_files(module_name):
    """Find the file containing the given module name."""
    design_folder = args.design_dir
    try:
        # Use grep to find the module in files
        result = subprocess.run(
            ["grep", "-rl", f"module {module_name}", design_folder],
            capture_output=True, text=True, check=True
        )
        file_paths = result.stdout.strip().split('\n')
        # Check if there are multiple definitions
        if len(file_paths) > 1:
            raise ValueError(
                f"Error: Multiple definitions of module '{module_name}' found in files:\n" +
                "\n".join(file_paths)
            )
        return file_paths[0] if file_paths else None
    except subprocess.CalledProcessError:
        # grep returns non-zero exit code if no match is found
        return None

def extract_ports_from_file(file_path, module_name):
    
    # Parse the file using Pyverilog
    ast, _ = parse([file_path])

    ports = {}

    # Traverse the AST to find the module definition matching the module_name
    for description in ast.children():
        for module in description.children():
            if module.__class__.__name__ == "ModuleDef" and module.name == module_name:
                # Extract ports for the specific module
                for port in module.portlist.ports:
                    # print(f'port.first.__class__.__name__ = {port.first.__class__.__name__}')
                    port_name = port.first.name
                    port_type = "input" if port.first.__class__.__name__ == "Inout" else port.first.__class__.__name__.lower()
                    ports[port_name] = port_type

    return ports

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
    # schematic.attr(rankdir='LR', nodesep="1.0", ranksep="1.0")
    schematic.attr(rankdir='LR')  # Left-to-right layout, orthogonal edges

    # list all wire and inputs in a dictionary 
    def all_decalared_signals(node):
        if node.__class__.__name__ in ('Input', 'Inout', 'Output', 'Wire', 'Reg'):
            port_name = node.name
            if node.width == None:
                declared_variables[port_name] = 0
            else:
                declared_variables[port_name] = {}
                declared_variables[port_name]['msb'] = node.width.msb
                declared_variables[port_name]['lsb'] = node.width.lsb
        if hasattr(node, 'children'):
            for child in node.children():
                all_decalared_signals(child)

    all_decalared_signals(ast)

    # Cluster for input ports
    with schematic.subgraph(name="cluster_inputs") as inputs_cluster:
        inputs_cluster.attr(style="solid", color="blue", label="Inputs", fontsize="12")
        
        # Traverse the AST to extract input ports
        def add_input_ports(node):
            if (node.__class__.__name__ == 'Input'):
                port_name = node.name
                node_name = "input_" + str(node.name)
                inputs_cluster.node(node_name, label=str(port_name), shape="box", style="rounded,filled", color="lightgrey")
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
                outputs_cluster.node(node_name, label=str(port_name), shape="box", style="rounded,filled", color="lightgrey")
                node_name_mapping["output"][port_name] = node_name

            if hasattr(node, 'children'):
                for child in node.children():
                    add_output_ports(child)

        # Start traversing from the root node to populate inputs cluster
        add_output_ports(ast)

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

    def add_wire_statements_to_schematic(node):
        if node.__class__.__name__ == 'Decl':
            # print(f'vars(Decl) = {vars(node)}')
            wire_code = extract_assign_statement_code(args.input_file,node.lineno)
            signal_names = signal_extractor(node)
            if (len(signal_names['output']) != 0):
                # print(f'signal_names = {signal_names} and length of output = {len(signal_names['output'])}')
                signal_names['input'] -= signal_names['output']
                wire_node_name = f"wire_{id(node)}"
            
                schematic.node(wire_node_name, label=wire_code, shape="box", style="rounded,filled", color="lightblue", fontsize="10", fontname="Courier")
                for input_signal in signal_names["input"]:
                    if input_signal in node_name_mapping["wire"]["input"] and not isinstance(node_name_mapping["wire"]["input"][input_signal], list):
                        node_name_mapping["wire"]["input"][input_signal] = [node_name_mapping["wire"]["input"][input_signal]]
                        node_name_mapping["wire"]["input"][input_signal].append(wire_node_name)
                    elif input_signal in node_name_mapping["wire"]["input"] and isinstance(node_name_mapping["wire"]["input"][input_signal], list):
                        node_name_mapping["wire"]["input"][input_signal].append(wire_node_name)
                    else:
                        node_name_mapping["wire"]["input"][input_signal] = wire_node_name
                    if input_signal in node_name_mapping["input"]:
                        schematic.edge(f'{node_name_mapping["input"][input_signal]}:e', f'{wire_node_name}:w', label=f"{input_signal}", arrowhead="vee", color="black")
                    elif input_signal in node_name_mapping["wire"]["output"]:
                        if isinstance(node_name_mapping["wire"]["output"][input_signal], list):
                            for target_node in node_name_mapping["wire"]["output"][input_signal]:
                                schematic.edge(f'{target_node}:e', f'{wire_node_name}:w', label=f"{input_signal}", arrowhead="vee", color="black")
                        else:
                            schematic.edge(f'{node_name_mapping["wire"]["output"][input_signal]}:e', f'{wire_node_name}:w', label=f"{input_signal}", arrowhead="vee", color="black")

                for output_signal in signal_names["output"]:
                    if output_signal in node_name_mapping["wire"]["output"] and not isinstance(node_name_mapping["wire"]["output"][output_signal], list):
                        node_name_mapping["wire"]["output"][output_signal] = [node_name_mapping["wire"]["output"][output_signal]]
                        node_name_mapping["wire"]["output"][output_signal].append(wire_node_name)
                    elif output_signal in node_name_mapping["wire"]["output"] and isinstance(node_name_mapping["wire"]["output"][output_signal], list):
                        node_name_mapping["wire"]["output"][output_signal].append(wire_node_name)
                    else:
                        node_name_mapping["wire"]["output"][output_signal] = wire_node_name
                    if output_signal in node_name_mapping["wire"]["input"]:
                        if isinstance(node_name_mapping["wire"]["input"][output_signal], list):
                            for target_node in node_name_mapping["wire"]["input"][output_signal]:
                                schematic.edge(f'{wire_node_name}:e', f'{target_node}:w', label=f"{output_signal}", arrowhead="vee", color="black")
                        else:
                            schematic.edge(f'{wire_node_name}:e', f'{node_name_mapping["wire"]["input"][output_signal]}:w', label=f"{output_signal}", arrowhead="vee", color="black")
                    elif output_signal in node_name_mapping["output"]:
                        schematic.edge(f'{wire_node_name}:e', f'{node_name_mapping["output"][output_signal]}:w', label=f"{output_signal}", arrowhead="vee", color="black")

        # Recursively traverse child nodes
        if hasattr(node, 'children'):
            for child in node.children():
                add_wire_statements_to_schematic(child)

    # Add this call after other AST processing
    add_wire_statements_to_schematic(ast)

    # Traverse the AST to find module instances and their port connections
    def add_instance_to_schematic(node):
        if isinstance(node, InstanceList):
            inst = node.instances[0]
            instance_name = inst.name
            module_name = inst.module
            instance_label = f"{module_name}\\n({instance_name})"
            cluster_name = f"cluster_{instance_name}"
            ports_position = {}
            file_with_module = grep_module_in_files(module_name)
            # print(f'file_with_module = {file_with_module}')
            if file_with_module != None:
                # if file exists then take input output signal information from the file
                ports_position = extract_ports_from_file(file_with_module, module_name)
            else:
                for port in inst.portlist:
                    internal_port = port.portname
                    if hasattr(port.argname, "var"):
                        external_wire = str(port.argname.var)
                    elif hasattr(port.argname, "name"):
                        external_wire = str(port.argname.name)
                    else:
                        external_wire = str(port.argname)

                    if (external_wire == "None"):
                        ports_position[internal_port] = 'middle'
                    elif external_wire in node_name_mapping["output"]:
                        ports_position[internal_port] = 'output'
                    elif external_wire in node_name_mapping["input"]:
                        ports_position[internal_port] = 'input'
                    elif external_wire in node_name_mapping['wire']["input"]:
                        ports_position[internal_port] = 'output'
                    else:
                        ports_position[internal_port] = 'input'
                    
            # to determine if external wire has a width and it is not equal to decalaration statement.
            for port in inst.portlist:
                if hasattr(port.argname, "var"):
                    external_wire = str(port.argname.var)
                elif hasattr(port.argname, "name"):
                    external_wire = str(port.argname.name)
                else:
                    external_wire = str(port.argname)

                
                    
            # Add a node for the instance
            with schematic.subgraph(name=cluster_name) as instance_cluster:
                instance_cluster.attr(style="solid", color="blue", label=instance_label, fontsize="12")
                temp_input = None
                temp_middle = None
                temp_output = None
                for port_name in ports_position:
                    node_name = str(instance_label) + str(port_name)
                    if (ports_position[port_name] == 'input'):
                        temp_input = node_name
                        # print(f'port_name = {port_name} and ports_position[port_name] = {ports_position[port_name]}')
                        with instance_cluster.subgraph(name="cluster_inputs") as input_group:
                            input_group.attr(style="invis")  # Group inputs
                            input_group.node(node_name, label=port_name, shape='box', style="rounded,filled", color='lightgrey')
                    elif (ports_position[port_name] == 'middle'):
                        temp_middle = node_name
                        with instance_cluster.subgraph(name="cluster_middle") as middle_group:
                            middle_group.attr(style="invis")  # Group middle
                            middle_group.node(node_name, label=port_name, shape='box', style="rounded,filled", color='lightgrey')
                    elif (ports_position[port_name] == 'output'):
                        temp_output = node_name
                        with instance_cluster.subgraph(name="cluster_outputs") as output_group:
                            output_group.attr(style="invis")  # Group outputs
                            output_group.node(node_name, label=port_name, shape='box', style="rounded,filled", color='lightgrey')
                # print(f'temp_middle = {temp_middle}')
                if (temp_middle != None) and (temp_input != None) and (temp_output != None):
                    # print(f'in the if statement: temp_input = {temp_input}, temp_middle = {temp_middle} and temp_output = {temp_output}')
                    schematic.edge(temp_input, temp_middle, style='invis')
                    schematic.edge(temp_middle, temp_output, style='invis')
                elif (temp_output != None) and (temp_input != None):
                    # print(f'in the else statement: temp_input = {temp_input}, temp_middle = {temp_middle} and temp_output = {temp_output}')
                    schematic.edge(temp_input, temp_output, style='invis')
                    # schematic.edge(temp_input, temp_output, style='invis')
                temp_input = None
                temp_middle = None
                temp_output = None
                for port in inst.portlist:
                    internal_port = port.portname
                    node_name = str(instance_label) + str(internal_port)
                    # instance_cluster.node(node_name, label=internal_port, shape="box", style="rounded,filled", color="lightgrey")
                    if hasattr(port.argname, "var"):
                        external_wire = str(port.argname.var)
                    elif hasattr(port.argname, "name"):
                        external_wire = str(port.argname.name)
                    else:
                        external_wire = str(port.argname)

                    temp_msb = 0
                    temp_lsb = 0
                    dec_msb = 0
                    dec_lsb = 0

                    if (port.argname != None) and (hasattr(port.argname, "msb")):
                        temp_msb = port.argname.msb
                        temp_lsb = port.argname.lsb
                        dec_msb = declared_variables[external_wire]['msb']
                        dec_lsb = declared_variables[external_wire]['lsb']
                        # print(f'external_wire = {external_wire} has the port width. temp_msb = {temp_msb}, dec_msb = {dec_msb}, temp_lsb = {temp_lsb}, dec_lsb = {dec_lsb}')
                    
                    if (temp_lsb != dec_lsb) or (temp_msb != dec_msb):
                        node_name_bus = external_wire + '_bus'
                        instance_cluster.node(node_name_bus, shape='box', style="rounded,filled", color='black')
                        schematic.edge(f'{node_name}:e', f'{node_name_bus}:w', arrowhead="vee", color="black")
                        node_name = node_name_bus
                        node_name_mapping["wire"]["output"][external_wire] = node_name
                        external_wire = internal_port + external_wire


                    if str(external_wire) in node_name_mapping["input"]:
                        pass
                        schematic.edge(f'{node_name_mapping["input"][str(external_wire)]}:e', f'{node_name}:w', label=f"{external_wire}", arrowhead="vee", color="black")
                    elif external_wire in node_name_mapping["wire"]["output"]:
                        if isinstance(node_name_mapping["wire"]["output"][external_wire], list):
                            for target_node in node_name_mapping["wire"]["output"][external_wire]:
                                pass
                                schematic.edge(f'{target_node}:e', f'{node_name}:w', label=f"{external_wire}", arrowhead="vee", color="black")
                        else:
                            pass
                            schematic.edge(f'{node_name_mapping["wire"]["output"][external_wire]}:e', f'{node_name}:w', label=f"{external_wire}", arrowhead="vee", color="black")
                    elif external_wire in node_name_mapping["wire"]["input"]:
                        if isinstance(node_name_mapping["wire"]["input"][external_wire], list):

                            for target_node in node_name_mapping["wire"]["input"][external_wire]:
                                pass
                                schematic.edge(f'{node_name}:e', f'{target_node}:w', label=f"{external_wire}", arrowhead="vee", color="black")
                        else:
                            pass
                            schematic.edge(f'{node_name}:e', f'{node_name_mapping["wire"]["input"][external_wire]}:w', label=f"{external_wire}", arrowhead="vee", color="black")
                    elif external_wire in node_name_mapping["output"]:
                        pass
                        schematic.edge(f'{node_name}:e', f'{node_name_mapping["output"][str(external_wire)]}:w', label=f"{external_wire}", arrowhead="vee", color="black")
                    # to put the wire names in node_name_mapping dictionary.
                    if (external_wire != 'None'):
                        if (ports_position[internal_port] == 'input'):
                            if external_wire in node_name_mapping["wire"]["input"] and not isinstance(node_name_mapping["wire"]["input"][external_wire], list):
                                node_name_mapping["wire"]["input"][external_wire] = [node_name_mapping["wire"]["input"][external_wire]]
                                node_name_mapping["wire"]["input"][external_wire].append(node_name)
                            elif external_wire in node_name_mapping["wire"]["input"] and isinstance(node_name_mapping["wire"]["input"][external_wire], list):
                                node_name_mapping["wire"]["input"][external_wire].append(node_name)
                            else:
                                node_name_mapping["wire"]["input"][external_wire] = node_name

                        elif (ports_position[internal_port] == 'output'):
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
                add_instance_to_schematic(child)

    add_instance_to_schematic(ast)

    # Save the schematic
    filename_schematic = args.output
    schematic.render(filename=filename_schematic, format='svg', cleanup=True)
    print(f"Schematic saved as '{filename_schematic}.svg'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Verilog schematic diagram.")
    parser.add_argument("-input_file", required=True, help="Path to the input Verilog file")
    parser.add_argument("-output", required=True, help="Path to the output schematic file (without extension)")
    parser.add_argument("-design_dir", required=True, help="Path to all the verilog ")

    args = parser.parse_args()

    # Parse the Verilog file
    ast, _ = parse([args.input_file])

    # Generate schematic from AST
    create_schematic_from_ast(ast)
    # print(f'node_name_mapping = {node_name_mapping}')
    # print(f'declared_variables = {declared_variables}')
