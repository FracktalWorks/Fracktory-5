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

def create_variants_for_printer(printer_definition_path):
    """Create nozzle variants for an existing printer definition."""
    # Load the printer definition
    printer_definition = load_definition(printer_definition_path)
    if not printer_definition:
        print(f"Error: Printer definition not found at '{printer_definition_path}'.")
        return

    # Determine if the printer is a dual-nozzle printer
    dual_nozzle = is_dual_nozzle_printer(printer_definition_path)

    # Extract printer name and create the variant folder
    printer_name = os.path.splitext(os.path.basename(printer_definition_path))[0]
    new_variant_folder = os.path.join(variants_folder, printer_name)
    os.makedirs(new_variant_folder, exist_ok=True)

    # Ask the user for the range of nozzle sizes
    nozzle_sizes = input("Enter the nozzle sizes to include (comma-separated, e.g., '0.25,0.4,0.6,0.8,1.0'): ").strip()
    nozzle_sizes = [float(size.strip()) for size in nozzle_sizes.split(",")]

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
        # Calculate settings based on trends
        layer_height_0 = round(size * (0.8 if size <= 0.3 else 0.75 if size <= 0.6 else 0.5), 2)
        nozzle_tip_outer_diameter = round(size * (2.5 if size <= 0.4 else 2.0), 2)
        skin_overlap = max(2, int(20 - (size * 18)))  # Decreases linearly with size, minimum value is 2

        variant_filename = f"{printer_name}_model_{size:.1f}.inst.cfg"
        variant_content = f"""[general]
definition = {printer_name}
name = Model {size:.1f} mm
version = 4

[metadata]
author = Fracktal Works
hardware_type = nozzle
setting_version = 23
type = variant

[values]
layer_height_0 = {layer_height_0}
machine_heat_zone_length = 20
machine_min_cool_heat_time_window = 120
machine_nozzle_cool_down_speed = 1
machine_nozzle_heat_up_speed = 0.5
machine_nozzle_id = Model {size:.1f} mm
machine_nozzle_size = {size:.1f}
machine_nozzle_tip_outer_diameter = {nozzle_tip_outer_diameter}
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