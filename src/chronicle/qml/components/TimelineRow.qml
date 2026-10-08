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
    required property string timeLabel
    required property string durationLabel
    required property real durationSeconds
    required property color accent
    required property bool isIdle
    required property bool isBrowser
    required property string rawJson
    required property int sourceCount
    property bool selected: false
    property bool showDetails: false

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
            "isBrowser": isBrowser,
            "rawJson": rawJson,
            "sourceCount": sourceCount
        }
    }

    height: 64
    radius: theme.radiusSmall
    color: selected ? theme.selection : (rowMouse.containsMouse ? theme.surfaceHover : "transparent")
    border.color: selected ? theme.accentMuted : "transparent"
    border.width: 1
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: timeLabel + ", " + primaryLabel + ", " + durationLabel
    Keys.onReturnPressed: eventSelected(eventSnapshot())
    Keys.onSpacePressed: eventSelected(eventSnapshot())

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 3
        color: root.isIdle ? theme.textMuted : root.accent
        opacity: root.isIdle ? 0.65 : 1
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: theme.space4
        anchors.rightMargin: theme.space3
        spacing: theme.space4

        ColumnLayout {
            Layout.preferredWidth: 144
            spacing: theme.space1
            Label {
                text: root.timeLabel
                color: theme.textPrimary
                font.pixelSize: theme.typeSmall
                font.family: theme.monoFamily
                font.weight: Font.DemiBold
            }
            Label {
                text: root.durationLabel
                color: theme.textMuted
                font.pixelSize: theme.typeCaption
                font.family: theme.monoFamily
            }
        }

        Rectangle {
            Layout.preferredWidth: 28
            Layout.preferredHeight: 28
            radius: theme.radiusSmall
            color: root.isIdle ? theme.idleFill : theme.surfaceRaised
            border.color: root.isIdle ? theme.rule : root.accent
            Label {
                anchors.centerIn: parent
                text: root.isIdle ? "ID" : root.primaryLabel.slice(0, 2).toUpperCase()
                color: root.isIdle ? theme.textMuted : theme.accentBright
                font.pixelSize: theme.typeCaption
                font.weight: Font.Bold
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            spacing: theme.space1
            RowLayout {
                Layout.fillWidth: true
                spacing: theme.space2
                Label {
                    text: root.isIdle ? "Idle / away" : root.primaryLabel
                    color: theme.textPrimary
                    font.pixelSize: theme.typeBody
                    font.weight: Font.DemiBold
                }
                Label {
                    visible: root.domain.length > 0
                    Layout.fillWidth: true
                    text: root.displayName
                    color: theme.textMuted
                    font.pixelSize: theme.typeCaption
                    elide: Text.ElideRight
                }
            }
            Label {
                visible: true
                Layout.fillWidth: true
                text: root.title.length ? root.title : (root.subtitle.length ? root.subtitle : (root.isIdle ? "No active input" : "No additional context"))
                color: theme.textSecondary
                font.pixelSize: theme.typeSmall
                elide: Text.ElideRight
            }
        }

        Label {
            Layout.preferredWidth: 80
            text: root.durationLabel
            color: theme.textPrimary
            font.pixelSize: theme.typeSmall
            font.family: theme.monoFamily
            horizontalAlignment: Text.AlignRight
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "transparent"
        border.color: root.activeFocus ? theme.focus : "transparent"
        border.width: 2
    }

    MouseArea {
        id: rowMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            root.forceActiveFocus()
            root.eventSelected(root.eventSnapshot())
        }
    }
}
