import QtQuick 2.11
import QtQuick.Controls 2.11
import QtQuick.Layouts 1.11
import UM 1.2 as UM
import Cura 1.3 as Cura

UM.Dialog {
    id: dialog
    title: qsTr("Pressure Advance Tower")
    minimumWidth: screenScaleFactor * 445
    minimumHeight: (screenScaleFactor * contents.childrenRect.height) + (2 * UM.Theme.getSize('default_margin').height) + UM.Theme.getSize('button').height
    maximumHeight: minimumHeight
    width: minimumWidth
    height: minimumHeight
    property int numberInputWidth: UM.Theme.getSize('button').width

    ColumnLayout {
        id: contents
        width: dialog.width - 2 * UM.Theme.getSize('default_margin').width
        spacing: UM.Theme.getSize('default_margin').width

        // Sub-heading for instructions
        UM.Label {
            text: qsTr("How to calculate Pressure Advance:
Measure the part height at the desired K value.
pressure_advance = <Starting Factor> + <measured_height> X <Factor Step> ")
            wrapMode: Text.WordWrap
            font.bold: true
            font.pixelSize: UM.Theme.getSize('default_font_size').height * 1.05
            Layout.fillWidth: true
            Layout.bottomMargin: UM.Theme.getSize('default_margin').height / 2
        }

        GridLayout {
            columns: 2
            rowSpacing: UM.Theme.getSize('default_lining').height
            columnSpacing: UM.Theme.getSize('default_margin').width
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop

            UM.Label {
                text: qsTr("Starting Pressure Advance Factor (K)")
            }
            Cura.TextField {
                Layout.preferredWidth: numberInputWidth
                validator: RegExpValidator { regExp: /[0-9]*(\.[0-9]+)?/ }
                text: dataModel.startKStr
                onTextChanged: if (dataModel.startKStr != text) dataModel.startKStr = text
            }
            UM.Label {
                text: qsTr("Pressure Advance Factor Step (K per mm)")
            }
            Cura.TextField {
                Layout.preferredWidth: numberInputWidth
                validator: RegExpValidator { regExp: /[0-9]*(\.[0-9]+)?/ }
                text: dataModel.kChangeStr
                onTextChanged: if (dataModel.kChangeStr != text) dataModel.kChangeStr = text
            }
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
