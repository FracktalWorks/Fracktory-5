"""
Variant Creator - A utility script for Fracktory-5 that generates printer nozzle variants.
Creates .cfg files for different nozzle sizes (regular and volcano) based on a printer definition.
Automatically calculates optimal settings for each nozzle variant and handles both single and dual-nozzle printers.
"""

import os
import json

# Define relative paths
definitions_folder = os.path.join("resources", "definitions")
variants_folder = os.path.join("resources", "variants", "fracktalworks")

def load_definition(file_path):
    """Load a JSON definition file."""
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r") as file:
        return json.load(file)

def is_dual_nozzle_printer(printer_definition_path):
    """Check if the printer is a dual-nozzle printer by resolving inheritance."""
    current_file = load_definition(printer_definition_path)
    while current_file:
        # Check for machine_extruder_count in the current definition
        machine_extruder_count = current_file.get("overrides", {}).get("machine_extruder_count", {}).get("default_value")
        if machine_extruder_count:
            return machine_extruder_count > 1

        # Check inheritance
        parent = current_file.get("inherits")
        if not parent:
            break
        parent_path = os.path.join(definitions_folder, f"{parent}.def.json")
        current_file = load_definition(parent_path)
    
    return False

def calculate_settings(nozzle_size, nozzle_type):
    """Calculate settings based on the nozzle size and type."""
    # Set layer_height_0 based on the nozzle size
    if nozzle_size >= 0.4:
        layer_height_0 = 0.3  # Fixed value for nozzle sizes 0.4 mm and above
    else:
        layer_height_0 = 0.2  # Fixed value for nozzle sizes below 0.4 mm

    # Set machine_nozzle_tip_outer_diameter based on the nozzle size
    if nozzle_size <= 0.6:
        machine_nozzle_tip_outer_diameter = round(nozzle_size * 2.5, 2)
    else:
        machine_nozzle_tip_outer_diameter = 2  # Capped at 2 for nozzle sizes >= 0.8 mm

    # Set skin_overlap based on the nozzle size
    skin_overlap = max(2, int(20 - (nozzle_size * 18)))  # Decreases linearly, minimum value is 2

    # Set machine_heat_zone_length based on the nozzle type
    machine_heat_zone_length = 20 if nozzle_type == "volcano" else 12

    return layer_height_0, machine_nozzle_tip_outer_diameter, skin_overlap, machine_heat_zone_length

def create_variants_for_printer(printer_definition_path):
    """Create nozzle variants for an existing printer definition."""
    # Load the printer definition
    printer_definition = load_definition(printer_definition_path)
    if not printer_definition:
        print(f"Error: Printer definition not found at '{printer_definition_path}'.")
        return

    # Get the printer ID from the definition
    printer_id = printer_definition.get("id")
    if not printer_id:
        print(f"Error: 'id' field not found in the printer definition at '{printer_definition_path}'.")
        return

    # Determine if the printer is a dual-nozzle printer
    dual_nozzle = is_dual_nozzle_printer(printer_definition_path)

    # Format the folder name and create the variant folder
    definition_file_name = os.path.basename(printer_definition_path).replace(".def.json", "")
    formatted_folder_name = " ".join(word.capitalize() for word in definition_file_name.split("_"))  # Capitalize and add spaces
    new_variant_folder = os.path.join(variants_folder, formatted_folder_name)
    os.makedirs(new_variant_folder, exist_ok=True)

    # Ask the user for the nozzle type
    nozzle_type = input("Enter the nozzle type (regular or volcano): ").strip().lower()
    if nozzle_type == "volcano":
        nozzle_sizes = [0.4, 0.6, 0.8, 1.0]  # Volcano nozzle sizes
    elif nozzle_type == "regular":
        nozzle_sizes = [0.25, 0.4, 0.6]  # Regular nozzle sizes
    else:
        print("Invalid nozzle type. Please enter 'regular' or 'volcano'.")
        return

    # Ask for additional parameters if needed
    if dual_nozzle:
        print("This is a dual-nozzle printer.")
        prime_tower_min_volume_formula = (
            "=0.9*layer_height*3.14*(((prime_tower_size/2)**2)- (((prime_tower_size/2)-(line_width*2))**2)) "
            "if extruder_nr == 0 else "
            "0.75*layer_height*3.14*((((prime_tower_size/2)-(line_width*2))**2)- (((prime_tower_size/2)-(line_width*4))**2))"
        )
    else:
        prime_tower_min_volume_formula = None

    # Create nozzle variants in .cfg format for each size
    for size in nozzle_sizes:
        # Calculate settings based on the nozzle size and type
        layer_height_0, machine_nozzle_tip_outer_diameter, skin_overlap, machine_heat_zone_length = calculate_settings(size, nozzle_type)

        variant_filename = f"{printer_id}_model_{size:g}.inst.cfg"  # Use :g to avoid trailing zeros
        variant_content = f"""[general]
definition = {printer_id}
name = Model {size:g} mm
version = 4

[metadata]
author = Fracktal Works
hardware_type = nozzle
setting_version = 23
type = variant

[values]
layer_height_0 = {layer_height_0}
machine_heat_zone_length = {machine_heat_zone_length}
machine_min_cool_heat_time_window = 120
machine_nozzle_cool_down_speed = 1
machine_nozzle_heat_up_speed = 0.5
machine_nozzle_id = Model {size:g} mm
machine_nozzle_size = {size:g}
machine_nozzle_tip_outer_diameter = {machine_nozzle_tip_outer_diameter}
skin_overlap = {skin_overlap}
"""
        # Add prime_tower_min_volume if the printer is dual-nozzle
        if dual_nozzle and prime_tower_min_volume_formula:
            variant_content += f"prime_tower_min_volume = {prime_tower_min_volume_formula}\n"

        # Write the variant file
        variant_path = os.path.join(new_variant_folder, variant_filename)
        with open(variant_path, "w") as variant_file:
            variant_file.write(variant_content)
        print(f"Nozzle variant created at: {variant_path}")

if __name__ == "__main__":
    # Get the path to the printer definition from the user
    printer_definition_path = input("Enter the path to the printer definition file: ").strip()
    create_variants_for_printer(printer_definition_path)