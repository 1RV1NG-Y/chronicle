import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    required property var theme
    required property string eventId
    required property string displayName
    required property string primaryLabel
    required property string appId
    required property string title
    required property string subtitle
    required property string domain
    required property string url
    required property var startTime
    required property var endTime
    required property real startMinute
    required property real endMinute
    required property string timeLabel
    required property string durationLabel
    required property real durationSeconds
    required property color accent
    required property bool isIdle
    required property bool isBrowser
    required property string rawJson
    required property int sourceCount
    property bool selected: false

    signal eventSelected(var eventData)

    function eventSnapshot() {
        return {
            "eventId": eventId,
            "displayName": displayName,
            "primaryLabel": primaryLabel,
            "appId": appId,
            "title": title,
            "subtitle": subtitle,
            "domain": domain,
            "url": url,
            "startTime": startTime,
            "endTime": endTime,
            "timeLabel": timeLabel,
            "durationLabel": durationLabel,
            "durationSeconds": durationSeconds,
            "accent": accent,
            "isIdle": isIdle,
            "rawJson": rawJson,
            "isBrowser": isBrowser,
            "sourceCount": sourceCount
        }
    }

    radius: height >= 10 ? theme.radiusSmall : 0
    color: height < 4 ? "transparent"
        : selected ? theme.selection
        : isIdle ? theme.idleFill
        : theme.activeFill
    border.color: selected ? theme.accentBright
        : blockMouse.containsMouse && height >= 8 ? theme.ruleStrong
        : theme.rule
    border.width: height >= 8 ? 1 : 0
    opacity: 1
    clip: true
    activeFocusOnTab: height >= 8
    Accessible.role: Accessible.Button
    Accessible.name: primaryLabel + ", " + timeLabel + ", " + durationLabel
    Keys.onReturnPressed: eventSelected(eventSnapshot())
    Keys.onSpacePressed: eventSelected(eventSnapshot())

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.accent
        opacity: root.isIdle ? 0 : (root.selected ? 0.16 : 0.10)
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: root.height < 4 ? parent.width : Math.min(3, parent.width)
        color: root.isIdle ? root.theme.textMuted : root.accent
        opacity: root.height < 4 ? 0.8 : 1
    }

    ColumnLayout {
        visible: root.height >= 20
        anchors.fill: parent
        anchors.leftMargin: theme.space3
        anchors.rightMargin: theme.space2
        anchors.topMargin: 2
        anchors.bottomMargin: 2
        spacing: theme.space1

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 16
            spacing: theme.space2

            Label {
                Layout.fillWidth: true
                text: root.isIdle ? "Idle / away" : root.primaryLabel
                color: theme.textPrimary
                font.pixelSize: theme.typeCaption
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }
            Label {
                visible: root.height >= 26
                text: root.durationLabel
                color: theme.textMuted
                font.pixelSize: theme.typeCaption
                font.family: theme.monoFamily
            }
        }

        Label {
            visible: root.height >= 42
            Layout.fillWidth: true
            text: root.isBrowser
                ? (root.domain.length ? root.displayName : "Website unavailable")
                : (root.title.length ? root.title : root.subtitle)
            color: theme.textSecondary
            font.pixelSize: theme.typeCaption
            elide: Text.ElideRight
        }

        Label {
            visible: root.height >= 66
            Layout.fillWidth: true
            text: root.timeLabel
            color: theme.textMuted
            font.pixelSize: theme.typeCaption
            elide: Text.ElideRight
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: root.activeFocus ? theme.focus : "transparent"
        border.width: 2
        radius: root.radius
    }

    MouseArea {
        id: blockMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            root.forceActiveFocus()
            root.eventSelected(root.eventSnapshot())
        }
    }
}
