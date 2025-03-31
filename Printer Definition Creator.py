import os
import json

# Define relative paths
definitions_folder = os.path.join("resources", "definitions")
variants_folder = os.path.join("resources", "variants", "fracktalworks")

def is_dual_nozzle_printer(printer_definition_path):
    """Check if the printer is a dual-nozzle printer based on its definition file."""
    with open(printer_definition_path, "r") as file:
        data = json.load(file)
        return data.get("overrides", {}).get("machine_extruder_count", {}).get("default_value", 1) > 1

def create_printer_definition():
    # Get user input for the new printer
    printer_name = input("Enter the name of the new printer (e.g., 'new_printer'): ").strip()
    inherit_from = input("Enter the name of the printer to inherit from (e.g., 'base_fracktal_printer'): ").strip()

    # Paths for the new definition and variant files
    new_definition_path = os.path.join(definitions_folder, f"{printer_name}.def.json")
    new_variant_folder = os.path.join(variants_folder, printer_name)
    os.makedirs(new_variant_folder, exist_ok=True)

    # Check if the inherited printer exists
    inherit_path = os.path.join(definitions_folder, f"{inherit_from}.def.json")
    if not os.path.exists(inherit_path):
        print(f"Error: The printer '{inherit_from}' does not exist in the definitions folder.")
        return

    # Determine if the printer is a dual-nozzle printer
    dual_nozzle = is_dual_nozzle_printer(inherit_path)

    # Create the new printer definition
    new_definition = {
        "inherits": inherit_from,
        "id": printer_name,
        "name": printer_name.replace("_", " ").title(),
        "version": "1.0",
        "description": f"Definition for {printer_name.replace('_', ' ').title()}",
        "settings": {}
    }

    # Write the new definition to a file
    with open(new_definition_path, "w") as def_file:
        json.dump(new_definition, def_file, indent=4)
    print(f"Printer definition created at: {new_definition_path}")

    # Ask the user for the range of nozzle sizes
    nozzle_sizes = input("Enter the nozzle sizes to include (comma-separated, e.g., '0.25,0.4,0.6,0.8,1.0'): ").strip()
    nozzle_sizes = [float(size.strip()) for size in nozzle_sizes.split(",")]

    # Ask for additional parameters if needed
    if dual_nozzle:
        prime_tower_min_volume = input("Enter the prime tower minimum volume (e.g., '6') or leave blank to skip: ").strip()
    else:
        prime_tower_min_volume = None

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
        if dual_nozzle and prime_tower_min_volume:
            variant_content += f"prime_tower_min_volume = {prime_tower_min_volume}\n"

        # Write the variant file
        variant_path = os.path.join(new_variant_folder, variant_filename)
        with open(variant_path, "w") as variant_file:
            variant_file.write(variant_content)
        print(f"Nozzle variant created at: {variant_path}")

if __name__ == "__main__":
    create_printer_definition()