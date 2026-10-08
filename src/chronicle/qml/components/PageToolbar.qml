import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property var theme
    property int pageIndex: 0
    property var selectedDate
    property string searchText: ""
    signal previousDay()
    signal nextDay()
    signal todayRequested()
    signal searchRequested(string text)

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 28
        anchors.rightMargin: 28
        spacing: 8
        Label {
            Layout.fillWidth: true
            text: root.pageIndex === 2 ? "Settings" : Qt.formatDate(root.selectedDate, "dddd, MMMM d")
            color: root.theme.textPrimary
            font.pixelSize: 20
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }
        RowLayout {
            visible: root.pageIndex < 2
            spacing: 2
            QuietButton { theme: root.theme; glyph: "left"; Accessible.name: "Previous day"; onClicked: root.previousDay() }
            QuietButton { theme: root.theme; text: "Today"; emphasized: true; onClicked: root.todayRequested() }
            QuietButton { theme: root.theme; glyph: "right"; Accessible.name: "Next day"; onClicked: root.nextDay() }
        }
        Rectangle {
            visible: root.pageIndex === 1
            Layout.leftMargin: 12
            Layout.preferredWidth: 210
            Layout.preferredHeight: 32
            radius: 6
            color: root.theme.surface
            border.color: search.activeFocus ? root.theme.focus : root.theme.rule
            Glyph { anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; name: "search"; ink: root.theme.textMuted; width: 15; height: 15 }
            TextField {
                id: search
                anchors.fill: parent
                leftPadding: 34
                rightPadding: 8
                text: root.searchText
                placeholderText: "Search your activity"
                color: root.theme.textPrimary
                placeholderTextColor: root.theme.textMuted
                font.pixelSize: 12
                selectByMouse: true
                Accessible.name: "Search timeline"
                onTextEdited: root.searchRequested(text)
                background: Item {}
            }
        }
    }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: root.theme.rule }
}
