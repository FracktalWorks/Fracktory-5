from typing import List, Optional, Any, Dict

from UM.Extension import Extension
from cura import CuraActions
from cura import CuraApplication
from cura.CuraApplication import CuraApplication
from UM.i18n import i18nCatalog
from UM.Logger import Logger
from cura.Utils.BCN3Dutils.PrintModeManager import PrintModeManager

from UM.FlameProfiler import pyqtSlot
from UM.Scene.Selection import Selection
from UM.Operations.GroupedOperation import GroupedOperation
from UM.Operations.RemoveSceneNodeOperation import RemoveSceneNodeOperation
from cura.Operations.SetParentOperation import SetParentOperation
from UM.Operations.TranslateOperation import TranslateOperation


from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("cura")


i18n_catalog = i18nCatalog("BCN3DIdex")


ParentCuraActions = CuraActions.CuraActions
class IdexCuraActions(CuraActions.CuraActions):
    @pyqtSlot()
    def deleteSelection(self) -> None:
        """Delete all selected objects."""

        # FRACKTAL IDEX INCLUSION
        if CuraApplication.getInstance().getGlobalContainerStack():
            if CuraApplication.getInstance().getGlobalContainerStack().getProperty("is_idex", "value"):  #If printer is not IDEX, do nothing
                from UM.Application import Application
                print_mode = Application.getInstance().getGlobalContainerStack().getProperty("print_mode", "value")
                if print_mode == "duplication" or print_mode == "mirror":
                    from UM.Message import Message
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
                    from cura.Utils.BCN3Dutils.Bcn3dIdexSupport import removeDuplitedNode
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
                    from cura.Utils.BCN3Dutils.Bcn3dIdexSupport import recaltulateDuplicatedNodeCenterMoveOperation
                    center_operation = recaltulateDuplicatedNodeCenterMoveOperation(center_operation, current_node)

            operation.addOperation(center_operation)
        operation.push()

CuraActions.CuraActions = IdexCuraActions


class IdexPlugin(Extension):
    def __init__(self) -> None:
        super().__init__()
        Logger.info(f"IdexPlugin init")

        self._curaActions = CuraActions.CuraActions()
        self._application = CuraApplication.getInstance()
        self._i18n_catalog = None  # type: Optional[i18nCatalog]
        self._global_container_stack = self._application.getGlobalContainerStack()
        self.printModeManager = PrintModeManager.getInstance()
        self._application.globalContainerStackChanged.connect(self._onGlobalContainerStackChanged)

        self._settings_dict = {}  # type: Dict[str, Any]
        self._expanded_categories = []  # type: List[str]  # temporary list used while creating nested settings

        self._onGlobalContainerStackChanged()
        self.cura_actions =  CuraApplication.getInstance()._cura_actions

        #application = CuraApplication.CuraApplication.getInstance()


    # def _onGlobalContainerStackChanged(self):

    #     self._global_container_stack = self._application.getGlobalContainerStack()

    #     if self._global_container_stack:
    #         self._global_container_stack.propertyChanged.connect(self._onPropertyChanged)

    #         # Calling _onPropertyChanged as an initialization
    #         self._onPropertyChanged("print_mode", "value")

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


