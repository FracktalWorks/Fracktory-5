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
        if self._enabled and key == "prime_tower_enable" and value:
            self.updatePrimeTowerSize()

    def updatePrimeTowerSize(self):
        # Always get the latest container stack in case it changed (e.g., printer/profile switch)
        self._container_stack = self._application.getGlobalContainerStack()
        if self._container_stack is None:
            err_msg = catalog.i18n("Failed to set prime_tower_size: No active container stack.")
            self.showUserMessage(err_msg)
            return
        root = self._scene.getRoot()
        max_z = 0
        for node in BreadthFirstIterator(root):
            if node.callDecoration("isSliceable"):
                bbox = node.getBoundingBox()
                if bbox:
                    max_z = max(max_z, bbox.top)
        # Prime tower size scaling
        min_size = 15
        max_size = 35
        z_min = 10
        z_max = 300
        if max_z <= z_min:
            tower_size = min_size
        elif max_z >= z_max:
            tower_size = max_size
        else:
            tower_size = min_size + (max_z - z_min) * (max_size - min_size) / (z_max - z_min)
        # Additional parameters scaling
        # base_height: 2-6mm
        min_base_height = 2
        max_base_height = 6
        if max_z <= z_min:
            base_height = min_base_height
        elif max_z >= z_max:
            base_height = max_base_height
        else:
            base_height = min_base_height + (max_z - z_min) * (max_base_height - min_base_height) / (z_max - z_min)
        # base_size: 18-36mm
        min_base_size = 5
        max_base_size = 15
        if max_z <= z_min:
            base_size = min_base_size
        elif max_z >= z_max:
            base_size = max_base_size
        else:
            base_size = min_base_size + (max_z - z_min) * (max_base_size - min_base_size) / (z_max - z_min)

        try:
            self._container_stack.setProperty("prime_tower_size", "value", tower_size)
            self._container_stack.setProperty("prime_tower_base_height", "value", base_height)
            self._container_stack.setProperty("prime_tower_base_size", "value", base_size)
            self._container_stack.propertyChanged.emit("prime_tower_size", "value")
            self._container_stack.propertyChanged.emit("prime_tower_base_height", "value")
            self._container_stack.propertyChanged.emit("prime_tower_base_size", "value")
            msg = catalog.i18n(
                f"Set prime_tower_size to {tower_size:.2f}mm, base_height to {base_height:.2f}mm, base_size to {base_size:.2f}mm for model Z height {max_z:.2f}mm."
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
