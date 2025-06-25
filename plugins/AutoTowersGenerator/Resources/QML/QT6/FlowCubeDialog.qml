import QtQuick 6.0
import QtQuick.Controls 6.0
import QtQuick.Layouts 6.0
import UM 1.6 as UM
import Cura 1.7 as Cura

UM.Dialog {
    id: dialog
    title: qsTr("Flow Cube")
    minimumWidth: screenScaleFactor * 445
    minimumHeight: (screenScaleFactor * contents.childrenRect.height) + (2 * UM.Theme.getSize('default_margin').height) + UM.Theme.getSize('button').height
    maximumHeight: minimumHeight
    width: minimumWidth
    height: minimumHeight

    ColumnLayout {
        id: contents
        width: dialog.width - 2 * UM.Theme.getSize('default_margin').width
        spacing: UM.Theme.getSize('default_margin').width

        UM.Label {
            text: qsTr("How to use the Flow Cube:\n\n1. Print the Flow Cube.\n2. Measure the wall thickness of the printed cube with calipers.\n3. Calculate the correct line width using the formula:\n\n    New Line Width = (Measured Wall Thickness / Expected Wall Thickness) * Current Line Width\n\n4. Update your slicer settings with the new line width if needed.")
            wrapMode: Text.WordWrap
            font.bold: true
            font.pixelSize: UM.Theme.getSize('default_font_size').height * 1.05
            Layout.fillWidth: true
            Layout.bottomMargin: UM.Theme.getSize('default_margin').height / 2
        }
    }

    rightButtons: Button {
        text: qsTr("OK")
        onClicked: dialog.accept()
    }
    leftButtons: Button {
        text: qsTr("Cancel")
        onClicked: dialog.reject()
    }

    onAccepted: {
        controller.dialogAccepted()
    }
}
