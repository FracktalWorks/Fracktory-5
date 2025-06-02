# Auto Prime Towers Plugin for Cura

This plugin automatically sets the prime tower size and position based on the global bounding box of all objects in the scene. It ensures the prime tower is always optimally placed and sized for dual extrusion and complex prints.

## Features
- Dynamically sets `prime_tower_size`, `prime_tower_base_height`, and `prime_tower_base_size` based on the tallest model in the scene
- Automatically places the prime tower at the center-back of the global bounding box, using tangent logic and bed-origin conversion
- Ensures the prime tower never overlaps with parts or touches the bed edge
- Listens for all scene and setting changes, including print mode and extruder enablement
- Only activates when the prime tower is enabled and at least one part is loaded
- Robust against missing container stack or Cura state changes
- Displays detailed bounding box and placement information in user messages
- Manual recalculation and enable/disable options via the Cura Extensions menu

## Installation
1. Copy the `AutoPrimeTowers` folder into your Cura `plugins` directory.
2. Restart Cura.
3. Enable the plugin in the Plugin Browser if needed.

## Customization
- You can adjust the scaling logic and placement logic in `AutoPrimeTowers.py` as needed.
- All logic is contained in a single file for easy modification.

## Author
Your Name

## Changelog
- v2.0 (2025-06-02): Major update to support dynamic position, robust event handling, and full scene/setting reactivity.
