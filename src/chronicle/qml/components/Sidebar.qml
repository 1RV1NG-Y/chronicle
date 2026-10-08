import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    required property var theme
    property bool compact: false
    property int currentIndex: 0
    property string status: "loading"
    signal navigate(int index)
    color: theme.sidebar

    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: root.theme.rule }

    component NavItem: Button {
        id: nav
        required property int page
        required property string glyph
        Layout.fillWidth: true
        implicitHeight: 38
        leftPadding: 12
        rightPadding: 12
        Accessible.name: text
        onClicked: root.navigate(page)
        contentItem: RowLayout {
            spacing: 12
            Glyph { name: nav.glyph; ink: nav.page === root.currentIndex ? root.theme.accentBright : root.theme.textMuted }
            Label {
                visible: !root.compact
                Layout.fillWidth: true
                text: nav.text
                color: nav.page === root.currentIndex ? root.theme.textPrimary : root.theme.textSecondary
                font.pixelSize: 13
                font.weight: nav.page === root.currentIndex ? Font.DemiBold : Font.Normal
            }
        }
        background: Rectangle {
            radius: 7
            color: nav.page === root.currentIndex ? root.theme.surfaceRaised : nav.hovered ? root.theme.surface : "transparent"
            border.color: nav.activeFocus ? root.theme.focus : "transparent"
        }
        ToolTip.visible: hovered && root.compact
        ToolTip.text: text
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 5
        RowLayout {
            Layout.preferredHeight: 64
            Layout.leftMargin: 10
            spacing: 10
            Rectangle {
                width: 25; height: 25; radius: 7
                color: root.theme.accent
                Glyph { anchors.centerIn: parent; name: "clock"; ink: root.theme.textOnAccent; width: 20; height: 20 }
            }
            Label {
                visible: !root.compact
                text: "chronicle"
                color: root.theme.textPrimary
                font.pixelSize: 17
                font.weight: Font.DemiBold
                font.letterSpacing: -0.5
            }
        }
        Item { Layout.preferredHeight: 20 }
        Label {
            visible: !root.compact
            Layout.leftMargin: 12
            Layout.bottomMargin: 8
            text: "YOUR ACTIVITY"
            color: root.theme.textMuted
            font.pixelSize: 10
            font.letterSpacing: 1.2
        }
        NavItem { page: 0; text: "Day"; glyph: "day" }
        NavItem { page: 1; text: "Timeline"; glyph: "list" }
        Item { Layout.fillHeight: true }
        NavItem { page: 2; text: "Settings"; glyph: "settings" }
        Rectangle { Layout.fillWidth: true; Layout.topMargin: 10; Layout.bottomMargin: 10; height: 1; color: root.theme.rule }
        RowLayout {
            Layout.leftMargin: 12
            Layout.bottomMargin: 8
            spacing: 8
            Rectangle { width: 5; height: 5; radius: 3; color: root.status === "error" ? root.theme.danger : root.theme.textMuted }
            Label {
                visible: !root.compact
                text: "Stored on this device"
                color: root.theme.textMuted
                font.pixelSize: 11
            }
        }
    }
}
