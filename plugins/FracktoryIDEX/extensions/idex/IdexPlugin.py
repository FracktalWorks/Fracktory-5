from typing import List, Optional, Any, Dict, Union

#importing classes to modofy
from UM.Extension import Extension
from cura.CuraActions import CuraActions
from cura.CuraApplication import CuraApplication
from cura.BuildVolume import BuildVolume
from cura.MultiplyObjectsJob import MultiplyObjectsJob
from cura.Operations.SetParentOperation import SetParentOperation
from cura.Scene.CuraSceneNode import CuraSceneNode
from cura.Settings.SimpleModeSettingsManager import SimpleModeSettingsManager

from UM.i18n import i18nCatalog
from UM.Logger import Logger
from ...IDEXutils.PrintModeManager import PrintModeManager

from UM.FlameProfiler import pyqtSlot
from UM.Scene.Selection import Selection
from UM.Operations.GroupedOperation import GroupedOperation
from UM.Operations.RemoveSceneNodeOperation import RemoveSceneNodeOperation
from cura.Operations.SetParentOperation import SetParentOperation
from UM.Operations.TranslateOperation import TranslateOperation

from UM.Qt.QtApplication import QtApplication  # The class we're inheriting from.
from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal, pyqtProperty, QEvent, pyqtEnum, QCoreApplication
from UM.Decorators import override
from UM.Application import Application
from cura.Settings.GlobalStack import GlobalStack
from cura.Scene.CuraSceneNode import CuraSceneNode
from UM.Scene.GroupDecorator import GroupDecorator
from cura.Scene.BuildPlateDecorator import BuildPlateDecorator
from cura.Scene.ConvexHullDecorator import ConvexHullDecorator
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
import os
from UM.Message import Message
from UM.Mesh.ReadMeshJob import ReadMeshJob
from cura.Scene.BlockSlicingDecorator import BlockSlicingDecorator
from cura.Scene.SliceableObjectDecorator import SliceableObjectDecorator
from cura.Arranging.Nest2DArrange import Nest2DArrange
from UM.Operations.AddSceneNodeOperation import AddSceneNodeOperation
from UM.Scene.SceneNode import SceneNode
from UM.Math.Vector import Vector

#Imports for BuildVolume
from typing import List, Optional, TYPE_CHECKING, Any, Set, cast, Iterable, Dict
from UM.Scene.Iterator.BreadthFirstIterator import BreadthFirstIterator

#Imports for MultiplyObjectsJob
from cura.Arranging.GridArrange import GridArrange
import copy

#Imports for StartSliceJob
from UM.Settings.ContainerStack import ContainerStack
from UM.Settings.Interfaces import ContainerInterface
from UM.Job import Job


from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("cura")


i18n_catalog = i18nCatalog("BCN3DIdex")


#Monkey patching the base classes to include the IDEX methods
@pyqtSlot()
def deleteSelection(self) -> None:
    """Delete all selected objects."""

    # FRACKTAL IDEX INCLUSION
    if CuraApplication.getInstance().getGlobalContainerStack():
        if CuraApplication.getInstance().getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
            print_mode = Application.getInstance().getGlobalContainerStack().getProperty("print_mode", "value")
            if print_mode == "duplication" or print_mode == "mirror":
                Message("You cannot delete objects in IDEX mode. Please change to another mode.", title="You can not delete objects in IDEX mode").show()
                return

    if not CuraApplication.getInstance().getController().getToolsEnabled():
        return

    removed_group_nodes = [] #type: List[SceneNode]
    op = GroupedOperation()
    nodes = Selection.getAllSelectedObjects()
    for node in nodes:
        #FRACKTAL IDEX INCLUSION
        if CuraApplication.getInstance().getGlobalContainerStack():
            if CuraApplication.getInstance().getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
                from ...IDEXutils.Bcn3dIdexSupport import removeDuplitedNode
                op = removeDuplitedNode(op, node)


        op.addOperation(RemoveSceneNodeOperation(node))
        group_node = node.getParent()
        if group_node and group_node.callDecoration("isGroup") and group_node not in removed_group_nodes:
            remaining_nodes_in_group = list(set(group_node.getChildren()) - set(nodes))
            if len(remaining_nodes_in_group) == 1:
                removed_group_nodes.append(group_node)
                op.addOperation(SetParentOperation(remaining_nodes_in_group[0], group_node.getParent()))
                op.addOperation(RemoveSceneNodeOperation(group_node))

        # Reset the print information
        CuraApplication.getInstance().getController().getScene().sceneChanged.emit(node)

    op.push()

@pyqtSlot()
def centerSelection(self) -> None:
    """Center all objects in the selection"""

    operation = GroupedOperation()
    for node in Selection.getAllSelectedObjects():
        current_node = node
        parent_node = current_node.getParent()
        while parent_node and parent_node.callDecoration("isGroup"):
            current_node = parent_node
            parent_node = current_node.getParent()

        # Find out where the bottom of the object is
        bbox = current_node.getBoundingBox()
        if bbox:
            center_y = current_node.getWorldPosition().y - bbox.bottom
        else:
            center_y = 0

        # Move the object so that it's bottom is on to of the buildplate
        center_operation = TranslateOperation(current_node, Vector(0, center_y, 0), set_position = True)

        #FRACKTAL IDEX INCLUSION
        if CuraApplication.getInstance().getGlobalContainerStack():
            if CuraApplication.getInstance().getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
                from ...IDEXutils.Bcn3dIdexSupport import recaltulateDuplicatedNodeCenterMoveOperation
                center_operation = recaltulateDuplicatedNodeCenterMoveOperation(center_operation, current_node)

        operation.addOperation(center_operation)
    operation.push()

CuraActions.deleteSelection = deleteSelection
CuraActions.centerSelection = centerSelection




@pyqtSlot()
def closeApplication(self) -> None:
    Logger.log("i", "Close application")

    #FRACKTAL IDEX INCLUSION
    if self.getGlobalContainerStack():
        if self.getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
            from ...IDEXutils.Bcn3dIdexSupport import closeApplication
            closeApplication(self.getGlobalContainerStack())

    # Workaround: Before closing the window, remove the global stack.
    # This is necessary because as the main window gets closed, hundreds of QML elements get updated which often
    # request the global stack. However as the Qt-side of the Machine Manager is being dismantled, the conversion of
    # the Global Stack to a QObject fails.
    # If instead we first take down the global stack, PyQt will just convert `None` to `null` which succeeds, and
    # the QML code then gets `null` as the global stack and can deal with that as it deems fit.
    self.getMachineManager().setActiveMachine(None)

    QtApplication.getInstance().closeAllWindows()

    main_window = self.getMainWindow()
    if main_window is not None:
        main_window.close()

    QtApplication.closeAllWindows()
    QCoreApplication.quit()

@override(Application)
def setGlobalContainerStack(self, stack: Optional["GlobalStack"]) -> None:
    self._setLoadingHint(self._i18n_catalog.i18nc("@info:progress", "Initializing Active Machine..."))

    #FRACKTAL IDEX INCLUSION
    if self.getGlobalContainerStack():
        if self.getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
            from ...IDEXutils.Bcn3dIdexSupport import extractAndSavePrintMode
            extractAndSavePrintMode(stack)

    QtApplication.setGlobalContainerStack(stack)

@pyqtSlot()
def groupSelected(self) -> None:
    # Create a group-node
    group_node = CuraSceneNode()
    group_decorator = GroupDecorator()
    group_node.addDecorator(group_decorator)
    group_node.addDecorator(ConvexHullDecorator())
    group_node.addDecorator(BuildPlateDecorator(self.getMultiBuildPlateModel().activeBuildPlate))
    group_node.setParent(self.getController().getScene().getRoot())
    group_node.setSelectable(True)
    center = Selection.getSelectionCenter()
    group_node.setPosition(center)
    group_node.setCenterPosition(center)

    # Remove nodes that are directly parented to another selected node from the selection so they remain parented
    selected_nodes = Selection.getAllSelectedObjects().copy()
    for node in selected_nodes:
        parent = node.getParent()
        if parent is not None and parent in selected_nodes and not parent.callDecoration("isGroup"):
            Selection.remove(node)

    #FRACKTAL IDEX INCLUSION
    if self.getGlobalContainerStack():
        if self.getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
            from ...IDEXutils.Bcn3dIdexSupport import duplicatedGroupSelected
            duplicatedGroupSelected(self.getController(), group_node, Selection, SetParentOperation)

    # Move selected nodes into the group-node
    Selection.applyOperation(SetParentOperation, group_node)

    # Deselect individual nodes and select the group-node instead
    for node in group_node.getChildren():
        Selection.remove(node)
    Selection.add(group_node)

@pyqtSlot()
def ungroupSelected(self) -> None:
    selected_objects = Selection.getAllSelectedObjects().copy()
    for node in selected_objects:
        if node.callDecoration("isGroup"):
            op = GroupedOperation()

            group_parent = node.getParent()
            children = node.getChildren().copy()
            for child in children:
                # Ungroup only 1 level deep
                if child.getParent() != node:
                    continue

                # Set the parent of the children to the parent of the group-node
                op.addOperation(SetParentOperation(child, group_parent))

                # Add all individual nodes to the selection
                Selection.add(child)

            #FRACKTAL IDEX INCLUSION
            if self.getGlobalContainerStack():
                if self.getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
                    from ...IDEXutils.Bcn3dIdexSupport import onDuplicatedgroupSelected
                    op = onDuplicatedgroupSelected(op, node)

            op.push()
            # Note: The group removes itself from the scene once all its children have left it,
            # see GroupDecorator._onChildrenChanged


def _readMeshFinished(self, job):
    global_container_stack = self.getGlobalContainerStack()
    if not global_container_stack:
        Logger.log("w", "Can't load meshes before a printer is added.")
        return
    if not self._volume:
        Logger.log("w", "Can't load meshes before the build volume is initialized")
        return

    nodes = job.getResult()
    if nodes is None:
        Logger.error("Read mesh job returned None. Mesh loading must have failed.")
        return
    file_name = job.getFileName()
    file_name_lower = file_name.lower()
    file_extension = file_name_lower.split(".")[-1]
    self._currently_loading_files.remove(file_name)

    self.fileLoaded.emit(file_name)
    target_build_plate = self.getMultiBuildPlateModel().activeBuildPlate

    root = self.getController().getScene().getRoot()
    fixed_nodes = []
    for node_ in DepthFirstIterator(root):
        if node_.callDecoration("isSliceable") and node_.callDecoration("getBuildPlateNumber") == target_build_plate:
            fixed_nodes.append(node_)

    default_extruder_position = self.getMachineManager().defaultExtruderPosition
    default_extruder_id = self._global_container_stack.extruderList[int(default_extruder_position)].getId()

    select_models_on_load = self.getPreferences().getValue("cura/select_models_on_load")

    nodes_to_arrange = []  # type: List[CuraSceneNode]
    
    fixed_nodes = []
    for node_ in DepthFirstIterator(self.getController().getScene().getRoot()):
        # Only count sliceable objects
        if node_.callDecoration("isSliceable"):
            fixed_nodes.append(node_)

    for original_node in nodes:
        # Create a CuraSceneNode just if the original node is not that type
        if isinstance(original_node, CuraSceneNode):
            node = original_node
        else:
            node = CuraSceneNode()
            node.setMeshData(original_node.getMeshData())
            node.source_mime_type = original_node.source_mime_type

            # Setting meshdata does not apply scaling.
            if original_node.getScale() != Vector(1.0, 1.0, 1.0):
                node.scale(original_node.getScale())

        node.setSelectable(True)
        node.setName(os.path.basename(file_name))
        self.getBuildVolume().checkBoundsAndUpdate(node)

        is_non_sliceable = "." + file_extension in self._non_sliceable_extensions

        if is_non_sliceable:
            # Need to switch first to the preview stage and then to layer view
            self.callLater(lambda: (self.getController().setActiveStage("PreviewStage"),
                                    self.getController().setActiveView("SimulationView")))

            block_slicing_decorator = BlockSlicingDecorator()
            node.addDecorator(block_slicing_decorator)
        else:
            sliceable_decorator = SliceableObjectDecorator()
            node.addDecorator(sliceable_decorator)

        scene = self.getController().getScene()

        # If there is no convex hull for the node, start calculating it and continue.
        if not node.getDecorator(ConvexHullDecorator):
            node.addDecorator(ConvexHullDecorator())
        for child in node.getAllChildren():
            if not child.getDecorator(ConvexHullDecorator):
                child.addDecorator(ConvexHullDecorator())

        if file_extension != "3mf":
            if node.callDecoration("isSliceable"):
                # Ensure that the bottom of the bounding box is on the build plate
                if node.getBoundingBox():
                    center_y = node.getWorldPosition().y - node.getBoundingBox().bottom
                else:
                    center_y = 0

                node.translate(Vector(0, center_y, 0))

                nodes_to_arrange.append(node)

        # This node is deep copied from some other node which already has a BuildPlateDecorator, but the deepcopy
        # of BuildPlateDecorator produces one that's associated with build plate -1. So, here we need to check if
        # the BuildPlateDecorator exists or not and always set the correct build plate number.
        build_plate_decorator = node.getDecorator(BuildPlateDecorator)
        if build_plate_decorator is None:
            build_plate_decorator = BuildPlateDecorator(target_build_plate)
            node.addDecorator(build_plate_decorator)
        build_plate_decorator.setBuildPlateNumber(target_build_plate)

        operation = AddSceneNodeOperation(node, scene.getRoot())
        operation.push()

        #FRACKTAL IDEX INCLUSION
        if self.getGlobalContainerStack():
            if self.getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
                from ...IDEXutils.Bcn3dIdexSupport import onReadMeshFinished
                nodes_to_arrange = onReadMeshFinished(nodes_to_arrange, node, scene)


        node.callDecoration("setActiveExtruder", default_extruder_id)
        scene.sceneChanged.emit(node)

        if select_models_on_load:
            Selection.add(node)
    try:
        arranger = Nest2DArrange(nodes_to_arrange, self.getBuildVolume(), fixed_nodes)
        arranger.arrange()
    except:
        Logger.logException("e", "Failed to arrange the models")

    # Ensure that we don't have any weird floaty objects (CURA-7855)
    for node in nodes_to_arrange:
        node.translate(Vector(0, -node.getBoundingBox().bottom, 0), SceneNode.TransformSpace.World)

    self.fileCompleted.emit(file_name)

CuraApplication.groupSelected = groupSelected
CuraApplication.ungroupSelected = ungroupSelected
CuraApplication.closeApplication = closeApplication
CuraApplication._readMeshFinished = _readMeshFinished

def updateNodeBoundaryCheck(self):
        """For every sliceable node, update node._outside_buildarea"""

        if not self._global_container_stack:
            return

        root = self._application.getController().getScene().getRoot()
        nodes = cast(List[SceneNode], list(cast(Iterable, BreadthFirstIterator(root))))
        group_nodes = []  # type: List[SceneNode]

        build_volume_bounding_box = self.getBoundingBox()
        if build_volume_bounding_box:
            # It's over 9000!
            # We set this to a very low number, as we do allow models to intersect the build plate.
            # This means the model gets cut off at the build plate.
            build_volume_bounding_box = build_volume_bounding_box.set(bottom=-9001)
        else:
            # No bounding box. This is triggered when running Cura from command line with a model for the first time
            # In that situation there is a model, but no machine (and therefore no build volume.
            return

        for node in nodes:
            # Need to check group nodes later
            if node.callDecoration("isGroup"):
                group_nodes.append(node)  # Keep list of affected group_nodes

            if node.callDecoration("isSliceable") or node.callDecoration("isGroup"):
                if not isinstance(node, CuraSceneNode):
                    continue

                if node.collidesWithBbox(build_volume_bounding_box):
                    node.setOutsideBuildArea(True)
                    continue

                if node.collidesWithAreas(self.getDisallowedAreas()):
                    node.setOutsideBuildArea(True)
                    continue
                # If the entire node is below the build plate, still mark it as outside.
                node_bounding_box = node.getBoundingBox()
                if node_bounding_box and node_bounding_box.top < 0 and not node.getParent().callDecoration("isGroup"):
                    node.setOutsideBuildArea(True)
                    continue
                # Mark the node as outside build volume if the set extruder is disabled
                extruder_position = node.callDecoration("getActiveExtruderPosition")
                try:
                    if not self._global_container_stack.extruderList[int(extruder_position)].isEnabled and not node.callDecoration("isGroup"):
                        node.setOutsideBuildArea(True)
                        continue
                except IndexError:  # Happens when the extruder list is too short. We're not done building the printer in memory yet.
                    continue
                except TypeError:  # Happens when extruder_position is None. This object has no extruder decoration.
                    continue

                node.setOutsideBuildArea(False)

        #FRACKTAL IDEX INCLUSION
        if CuraApplication.getInstance().getGlobalContainerStack():
            if CuraApplication.getInstance().getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
                from ...IDEXutils.Bcn3dIdexSupport import updateNodeBoundaryCheckForDuplicated
                updateNodeBoundaryCheckForDuplicated()

        # Group nodes should override the _outside_buildarea property of their children.
        for group_node in group_nodes:
            children = group_node.getAllChildren()

            # Check if one or more children are non-printable and if so, set the parent as non-printable:
            for child_node in children:
                if child_node.isOutsideBuildArea():
                    group_node.setOutsideBuildArea(True)
                    break

            # Apply results of the check to all children of the group:
            for child_node in children:
                child_node.setOutsideBuildArea(group_node.isOutsideBuildArea())

BuildVolume.updateNodeBoundaryCheck = updateNodeBoundaryCheck

def run(self) -> None:
    status_message = Message(i18n_catalog.i18nc("@info:status", "Multiplying and placing objects"), lifetime = 0,
                                dismissable = False, progress = 0,
                                title = i18n_catalog.i18nc("@info:title", "Placing Objects"))
    status_message.show()
    scene = Application.getInstance().getController().getScene()

    global_container_stack = Application.getInstance().getGlobalContainerStack()
    if global_container_stack is None:
        return  # We can't do anything in this case.

    root = scene.getRoot()

    processed_nodes: List[SceneNode] = []
    nodes = []

    fixed_nodes = []
    for node_ in DepthFirstIterator(root):
        # Only count sliceable objects
        if node_.callDecoration("isSliceable"):
            fixed_nodes.append(node_)
    nodes_to_add_without_arrange = []
    for node in self._objects:
        # If object is part of a group, multiply group
        current_node = node
        while current_node.getParent() and current_node.getParent().callDecoration("isGroup"):
            current_node = current_node.getParent()

        if current_node in processed_nodes:
            continue
        processed_nodes.append(current_node)

        for _ in range(self._count):
            new_node = copy.deepcopy(node)
            # Same build plate
            build_plate_number = current_node.callDecoration("getBuildPlateNumber")
            new_node.callDecoration("setBuildPlateNumber", build_plate_number)
            for child in new_node.getChildren():
                child.callDecoration("setBuildPlateNumber", build_plate_number)
            if not current_node.getParent().callDecoration("isSliceable"):
                nodes.append(new_node)
            else:
                # The node we're trying to place has another node that is sliceable as a parent.
                # As such, we shouldn't arrange it (but it should be added to the scene!)
                nodes_to_add_without_arrange.append(new_node)
                new_node.setParent(current_node.getParent())

    found_solution_for_all = True
    group_operation = GroupedOperation()
    if nodes:

        #FRACKTAL IDEX INCLUSION
        if CuraApplication.getInstance().getGlobalContainerStack():
            if CuraApplication.getInstance().getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
                from ...IDEXutils.Bcn3dIdexSupport import idexMultiplyObjectsJob
                group_operation = idexMultiplyObjectsJob(group_operation, nodes, scene)

        if self._grid_arrange:
            arranger = GridArrange(nodes, Application.getInstance().getBuildVolume(), fixed_nodes)
        else:
            arranger = Nest2DArrange(nodes, Application.getInstance().getBuildVolume(), fixed_nodes, factor=1000)

        group_operation, not_fit_count = arranger.createGroupOperationForArrange(add_new_nodes_in_scene=True)

    if nodes_to_add_without_arrange:
        for nested_node in nodes_to_add_without_arrange:
            group_operation.addOperation(AddSceneNodeOperation(nested_node, nested_node.getParent()))
            # Move the node a tiny bit so it doesn't overlap with the existing one.
            # This doesn't fix it if someone creates more than one duplicate, but it at least shows that something
            # happened (and after moving it, it's clear that there are more underneath)
            group_operation.addOperation(TranslateOperation(nested_node, Vector(2.5, 2.5, 2.5)))

    group_operation.push()
    status_message.hide()

    if not found_solution_for_all:
        no_full_solution_message = Message(
            i18n_catalog.i18nc("@info:status", "Unable to find a location within the build volume for all objects"),
            title = i18n_catalog.i18nc("@info:title", "Placing Object"),
            message_type = Message.MessageType.WARNING)
        no_full_solution_message.show()

MultiplyObjectsJob.run = run

def undo(self) -> None:
    """Undoes the set-parent operation, restoring the old parent."""

    #FRACKTAL IDEX INCLUSION
    if CuraApplication.getInstance().getGlobalContainerStack():
        if CuraApplication.getInstance().getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
            from ...IDEXutils.Bcn3dIdexSupport import setParentOperationUndo
            setParentOperationUndo(self._set_parent, self._parent, self._old_parent, self._node, Application.getInstance().getController().getScene().getRoot())
        else:
            self._set_parent(self._old_parent)

def redo(self) -> None:
    """Re-applies the set-parent operation."""

    #FRACKTAL IDEX INCLUSION
    
    if CuraApplication.getInstance().getGlobalContainerStack():
        if CuraApplication.getInstance().getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
            from ...IDEXutils.Bcn3dIdexSupport import setParentOperationRedo
            setParentOperationRedo(self._set_parent, self._parent, self._old_parent, self._node, Application.getInstance().getController().getScene().getRoot())
        else:
            self._set_parent(self._parent)

SetParentOperation.undo = undo
SetParentOperation.redo = redo

def isVisible(self) -> bool:

    #FRACKTAL IDEX INCLUSION
    if CuraApplication.getInstance().getGlobalContainerStack():
        if CuraApplication.getInstance().getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
            from ...IDEXutils.Bcn3dIdexSupport import curaSceneNodeIsVisible
            return curaSceneNodeIsVisible((SceneNode.isVisible(self) and self.callDecoration("getBuildPlateNumber") == CuraApplication.getInstance().getMultiBuildPlateModel().activeBuildPlate))
    
    return SceneNode.isVisible(self) and self.callDecoration("getBuildPlateNumber") == CuraApplication.getInstance().getMultiBuildPlateModel().activeBuildPlate

CuraSceneNode.isVisible = isVisible

def _updateIsProfileCustomized(self):
    user_setting_keys = set()

    if not self._machine_manager.activeMachine:
        return False

    global_stack = self._machine_manager.activeMachine

    # check user settings in the global stack

    #FRACKTAL IDEX INCLUSION
    if CuraApplication.getInstance().getGlobalContainerStack():
        if CuraApplication.getInstance().getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
            user_setting_keys.update(set([property for property in global_stack.userChanges.getAllKeys() if property != "print_mode"]))
        else:
            user_setting_keys.update(global_stack.userChanges.getAllKeys())

    # check user settings in the extruder stacks
    if global_stack.extruderList:
        for extruder_stack in global_stack.extruderList:
            user_setting_keys.update(extruder_stack.userChanges.getAllKeys())

    has_customized_user_settings = len(user_setting_keys) > 0

    if has_customized_user_settings != self._is_profile_customized:
        self._is_profile_customized = has_customized_user_settings
        self.isProfileCustomizedChanged.emit()

SimpleModeSettingsManager._updateIsProfileCustomized = _updateIsProfileCustomized


class IdexPlugin(Extension):
    def __init__(self) -> None:
        super().__init__()
        Logger.info(f"IdexPlugin init")

        self._curaActions = CuraActions()
        self._application = CuraApplication.getInstance()
        self._i18n_catalog = None  # type: Optional[i18nCatalog]
        self._global_container_stack = self._application.getGlobalContainerStack()
        self.printModeManager = PrintModeManager.getInstance()
        self._application.globalContainerStackChanged.connect(self._onGlobalContainerStackChanged)

        self._settings_dict = {}  # type: Dict[str, Any]
        self._expanded_categories = []  # type: List[str]  # temporary list used while creating nested settings

        self._onGlobalContainerStackChanged()
        self.cura_actions =  CuraApplication.getInstance()._cura_actions


    def _onGlobalContainerStackChanged(self):

        self._global_container_stack = self._application.getGlobalContainerStack()

        if self._global_container_stack:
            if self._global_container_stack.getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
                self._global_container_stack.propertyChanged.connect(self._onPropertyChanged)
                # Calling _onPropertyChanged as an initialization
                self._onPropertyChanged("print_mode", "value")
            else:
                self._global_container_stack.propertyChanged.disconnect(self._onPropertyChanged)



    def _onPropertyChanged(self, key: str, property_name: str) -> None:
        if key == "print_mode" and property_name == "value":
            Logger.info(f"IdexPlugin: print_mode property changed")
            print_mode = self._global_container_stack.getProperty("print_mode", "value")
            left_extruder = self._global_container_stack.extruderList[0]
            right_extruder = self._global_container_stack.extruderList[1]

            try:
                left_extruder.enabledChanged.disconnect(self._onEnabledChangedLeft)
                right_extruder.enabledChanged.disconnect(self._onEnabledChangedRight)
            except Exception:
                # Just in case the connection didn't exists
                pass

            if print_mode == "singleT0":
                self._application.getMachineManager().setExtruderEnabled(0, True)
                self._application.getMachineManager().setExtruderEnabled(1, False)
                #HACK:
                # For some reason when goes to single 1, sometimes the disallowed areas are not updated
                # With this we make sure that is done
                if self._application and self._application._volume:
                    self._application._volume._updateDisallowedAreasAndRebuild()

            elif print_mode == "singleT1":
                self._application.getMachineManager().setExtruderEnabled(0, False)
                self._application.getMachineManager().setExtruderEnabled(1, True)

            elif print_mode == "dual":
                self._application.getMachineManager().setExtruderEnabled(0, True)
                self._application.getMachineManager().setExtruderEnabled(1, True)

            else:
                self._application.getMachineManager().setExtruderEnabled(0, True)
                self._application.getMachineManager().setExtruderEnabled(1, False)

                ##try to do ghost models 
                duplicated_nodes = PrintModeManager.getInstance().getDuplicatedNodes()
                for node_dup in duplicated_nodes:
                    node_dup._outside_buildarea = node_dup.node._outside_buildarea


            left_extruder.enabledChanged.connect(self._onEnabledChangedLeft)
            right_extruder.enabledChanged.connect(self._onEnabledChangedRight)

    def _onEnabledChangedLeft(self):
        print_mode = self._global_container_stack.getProperty("print_mode", "value")
        if print_mode == "singleT0":
            left_extruder = self._global_container_stack.extruderList[0]
            if not left_extruder.isEnabled:
                self._application.getMachineManager().setExtruderEnabled(0, True)

        elif print_mode == "singleT1":
            self._global_container_stack.setProperty("print_mode", "value", "dual")

        elif print_mode == "dual":
            self._global_container_stack.setProperty("print_mode", "value", "singleT1")

        else:
            left_extruder = self._global_container_stack.extruderList[0]
            if not left_extruder.isEnabled:
                self._application.getMachineManager().setExtruderEnabled(0, True)

    def _onEnabledChangedRight(self):
        print_mode = self._global_container_stack.getProperty("print_mode", "value")

        if print_mode == "singleT0":
            self._global_container_stack.setProperty("print_mode", "value", "dual")

        elif print_mode == "singleT1":
            right_extruder = self._global_container_stack.extruderList[1]
            if not right_extruder.isEnabled:
                self._application.getMachineManager().setExtruderEnabled(1, True)

        elif print_mode == "dual":
            self._global_container_stack.setProperty("print_mode", "value", "singleT0")

        else:
            right_extruder = self._global_container_stack.extruderList[1]
            if right_extruder.isEnabled:
                # When in duplication/mirror modes force the right extruder to be disabled
                self._application.getMachineManager().setExtruderEnabled(1, False)

