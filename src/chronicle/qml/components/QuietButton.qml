import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
    id: root
    required property var theme
    property string glyph: ""
    property bool emphasized: false
    implicitHeight: 32
    implicitWidth: glyph.length && !text.length ? 32 : contentItem.implicitWidth + 24
    padding: 8
    hoverEnabled: true
    contentItem: RowLayout {
        spacing: 7
        Glyph {
            visible: root.glyph.length > 0
            name: root.glyph
            ink: root.enabled ? root.theme.textSecondary : root.theme.textDisabled
            Layout.preferredWidth: 16
            Layout.preferredHeight: 16
        }
        Label {
            visible: root.text.length > 0
            text: root.text
            color: root.enabled ? root.theme.textPrimary : root.theme.textDisabled
            font.pixelSize: root.theme.typeSmall
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
        }
    }
    background: Rectangle {
        radius: 6
        color: root.down ? root.theme.selection : root.hovered ? root.theme.surfaceHover : root.emphasized ? root.theme.surfaceRaised : "transparent"
        border.color: root.activeFocus ? root.theme.focus : root.emphasized ? root.theme.rule : "transparent"
    }
    ToolTip.visible: hovered && !text.length
    ToolTip.text: Accessible.name
    ToolTip.delay: 600
}
