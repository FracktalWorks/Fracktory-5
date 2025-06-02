# AutoPrimeTowerSize.py
# Plugin to automatically set prime tower size based on model Z height

from UM.Extension import Extension
from cura.CuraApplication import CuraApplication
from UM.Scene.Iterator.BreadthFirstIterator import BreadthFirstIterator
from UM.Scene.SceneNode import SceneNode
from UM.Message import Message
from UM.PluginRegistry import PluginRegistry
from UM.i18n import i18nCatalog
import threading

catalog = i18nCatalog("AutoPrimeTowerSize")

class AutoPrimeTowerSizePlugin(Extension):
    def __init__(self):
        super().__init__()
        self._application = CuraApplication.getInstance()
        self._scene = self._application.getController().getScene()
        self._container_stack = self._application.getGlobalContainerStack()
        self._enabled = True
        self._message = None
        self._update_timer = None
        self.addMenuItem(catalog.i18n("Recalculate Prime Tower Size"), self.updatePrimeTowerSize)
        self.addMenuItem(catalog.i18n("Enable Auto Prime Tower Size"), self.enablePlugin)
        self.addMenuItem(catalog.i18n("Disable Auto Prime Tower Size"), self.disablePlugin)
        # Listen for file load/complete events like OrientationPlugin
        self._currently_loading_files = set()
        self._application.fileLoaded.connect(self._onFileLoaded)
        self._application.fileCompleted.connect(self._onFileCompleted)
        if self._container_stack is not None:
            self._container_stack.propertyChanged.connect(self.onSettingChanged)
        # Listen for scene changes at the Scene object level, not the root node
        self._scene.sceneChanged.connect(self._onSceneChanged)

    def setVersion(self, version):
        pass

    def enablePlugin(self):
        self._enabled = True
        self.showUserMessage(catalog.i18n("AutoPrimeTowerSize enabled."))
        self.updatePrimeTowerSize()

    def disablePlugin(self):
        self._enabled = False
        self.showUserMessage(catalog.i18n("AutoPrimeTowerSize disabled."))

    def _onFileLoaded(self, file_name):
        self._currently_loading_files.add(file_name)

    def _onFileCompleted(self, file_name):
        if file_name in self._currently_loading_files:
            self._currently_loading_files.remove(file_name)
            if self._enabled:
                self.updatePrimeTowerSize()
            # Connect to meshDataChanged and transformationChanged for all sliceable nodes
            root = self._scene.getRoot()
            for node in BreadthFirstIterator(root):
                if node.callDecoration("isSliceable"):
                    try:
                        node.meshDataChanged.disconnect(self._onNodeMeshOrTransformChanged)
                    except Exception:
                        pass
                    try:
                        node.transformationChanged.disconnect(self._onNodeMeshOrTransformChanged)
                    except Exception:
                        pass
                    node.meshDataChanged.connect(self._onNodeMeshOrTransformChanged)
                    node.transformationChanged.connect(self._onNodeMeshOrTransformChanged)

    def _onNodeMeshOrTransformChanged(self, node):
        if self._enabled:
            self._debounceUpdatePrimeTowerSize()

    def _debounceUpdatePrimeTowerSize(self, delay=2.5):
        if self._update_timer is not None:
            self._update_timer.cancel()
        self._update_timer = threading.Timer(delay, self._debouncedUpdatePrimeTowerSize)
        self._update_timer.start()

    def _debouncedUpdatePrimeTowerSize(self):
        self._update_timer = None
        self.updatePrimeTowerSize()

    def onSettingChanged(self, key, value):
        if not self._enabled:
            return
        # Update when prime tower is enabled
        if key == "prime_tower_enable" and value:
            self.updatePrimeTowerSize()
        # Update when print mode is set to dual (extruder count == 2)
        if key == "print_mode" and value == "dual":
            self.updatePrimeTowerSize()
        # Update when machine_extruder_count is set to 2 or more
        if key == "machine_extruder_count" and int(value) >= 2:
            self.updatePrimeTowerSize()

    def updatePrimeTowerSize(self):
        # Always get the latest container stack in case it changed (e.g., printer/profile switch)
        self._container_stack = self._application.getGlobalContainerStack()
        if self._container_stack is None:
            err_msg = catalog.i18n("Failed to set prime_tower_size: No active container stack.")
            self.showUserMessage(err_msg)
            return
        # Only activate if prime tower is enabled and at least one part is loaded
        if not self._container_stack.getProperty("prime_tower_enable", "value"):
            return
        root = self._scene.getRoot()
        has_sliceable = any(
            node.callDecoration("isSliceable") and node.getBoundingBox() is not None
            for node in BreadthFirstIterator(root)
        )
        if not has_sliceable:
            return
        root = self._scene.getRoot()
        # Calculate global bounding box from all sliceable nodes
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')
        for node in BreadthFirstIterator(root):
            if node.callDecoration("isSliceable"):
                bbox = node.getBoundingBox()
                if bbox:
                    min_x = min(min_x, bbox.left)
                    max_x = max(max_x, bbox.right)
                    # Fix: Cura's Y axis is front (smaller) to back (larger), but front/back may be swapped depending on orientation
                    # Ensure min_y is always the minimum of bbox.front and bbox.back, and max_y is always the maximum
                    min_y = min(min_y, bbox.front, bbox.back)
                    max_y = max(max_y, bbox.front, bbox.back)
                    min_z = min(min_z, bbox.bottom)
                    max_z = max(max_z, bbox.top)
        if min_x < float('inf'):
            # Fix Y size calculation to always be positive
            y_size = abs(max_y - min_y)

        # Prime tower size scaling
        min_size = 15
        max_size = 35
        z_min = 20
        z_max = 300
        # Use the global bounding box Z for prime tower calculation
        global_height = max_z
        if global_height <= z_min:
            tower_size = min_size
        elif global_height >= z_max:
            tower_size = max_size
        else:
            tower_size = min_size + (global_height - z_min) * (max_size - min_size) / (z_max - z_min)
        # Additional parameters scaling
        # base_height: 2-6mm
        min_base_height = 2
        max_base_height = 6
        if global_height <= z_min:
            base_height = min_base_height
        elif global_height >= z_max:
            base_height = max_base_height
        else:
            base_height = min_base_height + (global_height - z_min) * (max_base_height - min_base_height) / (z_max - z_min)
        # base_size: 5-15mm
        min_base_size = 5
        max_base_size = 15
        if global_height <= z_min:
            base_size = min_base_size
        elif global_height >= z_max:
            base_size = max_base_size
        else:
            base_size = min_base_size + (global_height - z_min) * (max_base_size - min_base_size) / (z_max - z_min)

        # --- Prime tower position logic ---
        try:
            bed_x = float(self._container_stack.getProperty("machine_width", "value"))
            bed_y = float(self._container_stack.getProperty("machine_depth", "value"))
        except Exception:
            bed_x = 220.0  # fallback default
            bed_y = 220.0
        # Place tower just outside the global bounding box, to the right (X+), with a small offset
        offset = 0  # mm
        # Calculate the actual diameter of the prime tower (including base)
        actual_tower_diameter = tower_size + base_size
        # For center-back of bounding box:
        bbox_center_x = (min_x + max_x) / 2.0
        # Place the tower just behind the maximum Y (most positive, i.e., back/Y-) of the bounding box
        # Adjust for tangent placement: prime_tower_position_x is left tangent, prime_tower_position_y is back tangent

        #Prime Tower in Front:
        # intended_x = bbox_center_x + tower_size/2  # left tangent of tower aligns with center X minus half diameter
        # intended_y = max_y + actual_tower_diameter + offset  # back tangent of tower is just behind the part

        #Prime Tower in Back:
        # Center X, left tangent
        intended_x = bbox_center_x + tower_size / 2
        # Back Y, back tangent (behind the part)
        intended_y = min_y - offset - actual_tower_diameter / 2

        # Convert to bed-origin coordinates
        prime_tower_position_x = bed_x / 2 + intended_x
        prime_tower_position_y = bed_y / 2 - intended_y
        # Clamp to bed area (only once, after conversion)
        edge_offset = 5.0  # mm, keep tower away from bed edge
        prime_tower_position_x = max(edge_offset, min(prime_tower_position_x, bed_x - actual_tower_diameter - edge_offset))
        prime_tower_position_y = max(edge_offset, min(prime_tower_position_y, bed_y - actual_tower_diameter - edge_offset))

        try:
            self._container_stack.setProperty("prime_tower_size", "value", tower_size)
            self._container_stack.setProperty("prime_tower_base_height", "value", base_height)
            self._container_stack.setProperty("prime_tower_base_size", "value", base_size)
            self._container_stack.setProperty("prime_tower_position_x", "value", prime_tower_position_x)
            self._container_stack.setProperty("prime_tower_position_y", "value", prime_tower_position_y)
            self._container_stack.propertyChanged.emit("prime_tower_size", "value")
            self._container_stack.propertyChanged.emit("prime_tower_base_height", "value")
            self._container_stack.propertyChanged.emit("prime_tower_base_size", "value")
            self._container_stack.propertyChanged.emit("prime_tower_position_x", "value")
            self._container_stack.propertyChanged.emit("prime_tower_position_y", "value")
            msg = catalog.i18n(
                f"Set prime_tower_size to {tower_size:.2f}mm, base_height to {base_height:.2f}mm, base_size to {base_size:.2f}mm for global model Z height {global_height:.2f}mm.\n" +
                f"Set prime_tower_position_x to {prime_tower_position_x:.2f}mm, prime_tower_position_y to {prime_tower_position_y:.2f}mm.\n" 
            )
            self.showUserMessage(msg)
        except Exception as e:
            err_msg = catalog.i18n(f"Failed to set prime tower parameters: {e}")
            self.showUserMessage(err_msg)

    def showUserMessage(self, text):
        if self._message:
            self._message.hide()
        self._message = Message(text, title=catalog.i18n("AutoPrimeTowerSize"))
        self._message.show()

    def _onSceneChanged(self, *args, **kwargs):
        # Only reconnect and update if there are new sliceable nodes or a real change
        root = self._scene.getRoot()
        seen = set()
        for node in BreadthFirstIterator(root):
            if node.callDecoration("isSliceable"):
                if id(node) not in seen:
                    seen.add(id(node))
                    try:
                        node.meshDataChanged.disconnect(self._onNodeMeshOrTransformChanged)
                    except Exception:
                        pass
                    try:
                        node.transformationChanged.disconnect(self._onNodeMeshOrTransformChanged)
                    except Exception:
                        pass
                    node.meshDataChanged.connect(self._onNodeMeshOrTransformChanged)
                    node.transformationChanged.connect(self._onNodeMeshOrTransformChanged)
        # Only update if the number of sliceable nodes has changed
        if not hasattr(self, '_last_sliceable_count') or self._last_sliceable_count != len(seen):
            self._last_sliceable_count = len(seen)
            if self._enabled:
                self.updatePrimeTowerSize()
