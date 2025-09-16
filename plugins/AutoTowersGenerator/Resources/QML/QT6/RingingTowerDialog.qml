import QtQuick 6.0
import QtQuick.Controls 6.0
import QtQuick.Layouts 6.0
import UM 1.6 as UM
import Cura 1.7 as Cura

UM.Dialog {
    id: dialog
    title: qsTr("Ringing Tower")
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

        UM.Label {
            text: qsTr("How to use the Ringing Tower:\nThe frequency will sweep from the start to end value. Inspect the print to determine the optimal input shaping frequency.")
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
                text: qsTr("Start Frequency (Hz)")
            }
            Cura.TextField {
                Layout.preferredWidth: numberInputWidth
                validator: RegularExpressionValidator { regularExpression: /[0-9]*(\.[0-9]+)?/ }
                text: dataModel.startFStr
                onTextChanged: {
                    if (dataModel.startFStr !== text) dataModel.startFStr = text
                }
            }
            UM.Label {
                text: qsTr("End Frequency (Hz)")
            }
            Cura.TextField {
                Layout.preferredWidth: numberInputWidth
                validator: RegularExpressionValidator { regularExpression: /[0-9]*(\.[0-9]+)?/ }
                text: dataModel.endFStr
                onTextChanged: {
                    if (dataModel.endFStr !== text) dataModel.endFStr = text
                }
            }
            UM.Label {
                text: qsTr("G-code Type")
            }
            UM.Label {
                text: qsTr("M593 (ZV Input Shaping)")
                color: "#888"
            }
        }
    }

    rightButtons: [
        Cura.SecondaryButton {
            text: qsTr("Cancel")
            onClicked: dialog.reject()
        },
        Cura.PrimaryButton {
            text: qsTr("OK")
            onClicked: dialog.accept()
        }
    ]

    onAccepted: {
        controller.dialogAccepted()
    }
}
