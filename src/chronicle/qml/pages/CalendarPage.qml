import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    required property var theme
    required property var appController
    required property var activityModel
    property string selectedKey: ""
    property real savedPosition: 0
    signal eventSelected(var eventData)

    Connections {
        target: root.appController
        function onSelectedDateChanged() { root.selectedKey = ""; root.savedPosition = 0; feed.positionViewAtBeginning() }
    }
    Connections {
        target: root.activityModel
        function onSummaryChanged() { overview.requestPaint() }
        function onModelAboutToBeReset() { root.savedPosition = Math.max(0, feed.contentY) }
        function onModelReset() { Qt.callLater(function() { feed.contentY = Math.min(root.savedPosition, Math.max(0, feed.contentHeight - feed.height)) }) }
    }
    onVisibleChanged: { if (!visible) appController.setInteractionActive(false) }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 28
        anchors.rightMargin: 28
        spacing: 0
        Item { Layout.preferredHeight: 24 }
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Label { text: "The shape of your day"; color: root.theme.textSecondary; font.pixelSize: 12 }
            Item { Layout.fillWidth: true }
            Label {
                text: root.activityModel.activeLabel + " active"
                color: root.theme.textPrimary
                font.pixelSize: 12
            }
            Label { text: "·"; color: root.theme.textMuted; font.pixelSize: 12 }
            Label { text: root.activityModel.idleLabel + " away"; color: root.theme.textMuted; font.pixelSize: 12 }
        }
        Item { Layout.preferredHeight: 14 }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 24
            radius: 4
            color: root.theme.surfaceRaised
            Canvas {
                id: overview
                anchors.fill: parent
                onWidthChanged: requestPaint()
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    var segments = root.activityModel.overview
                    for (var i = 0; i < segments.length; i++) {
                        var s = segments[i]
                        ctx.fillStyle = s.color
                        ctx.globalAlpha = 0.65
                        ctx.fillRect(s.start * width, 3, Math.max(1, (s.end - s.start) * width), height - 6)
                    }
                }
            }
            MouseArea {
                id: dayMapMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: mouse => {
                    var row = root.activityModel.rowAtMinute(mouse.x / width * 1440)
                    if (row >= 0) {
                        feed.positionViewAtIndex(row, ListView.Center)
                        root.selectedKey = root.activityModel.recordAt(row).eventId
                        root.eventSelected(root.activityModel.recordAt(row))
                    }
                }
                ToolTip.visible: containsMouse
                ToolTip.text: {
                    var minutes = Math.min(1439, Math.floor(mouseX / Math.max(1, width) * 1440))
                    return String(Math.floor(minutes / 60)).padStart(2, "0") + ":" + String(minutes % 60).padStart(2, "0") + " · click to inspect"
                }
            }
            Accessible.name: "Day overview. Use the activity list below to inspect recordings."
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 6
            spacing: 0
            Repeater {
                model: ["00:00", "06:00", "12:00", "18:00", "24:00"]
                Label {
                    required property string modelData
                    required property int index
                    Layout.fillWidth: index < 4
                    text: modelData
                    color: root.theme.textMuted
                    font.pixelSize: 10
                    font.family: root.theme.monoFamily
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 26
            Layout.bottomMargin: 14
            Label { text: "Activity"; color: root.theme.textPrimary; font.pixelSize: 15; font.weight: Font.DemiBold }
            Label { text: root.activityModel.activityCount; color: root.theme.textMuted; font.pixelSize: 11 }
            Item { Layout.fillWidth: true }
            Label { text: "Latest first"; color: root.theme.textMuted; font.pixelSize: 11 }
            QuietButton {
                visible: feed.contentY > 100
                theme: root.theme
                text: "Back to latest"
                onClicked: feed.positionViewAtBeginning()
            }
        }

        ListView {
            id: feed
            objectName: "dayFeed"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.bottomMargin: 16
            clip: true
            spacing: 8
            model: root.activityModel
            boundsBehavior: Flickable.StopAtBounds
            reuseItems: true
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            onMovementStarted: root.appController.setInteractionActive(true)
            onMovementEnded: root.appController.setInteractionActive(false)

            delegate: Item {
                id: activity
                required property int index
                required property string eventId
                required property string primaryLabel
                required property string displayName
                required property string title
                required property string domain
                required property var startTime
                required property var endTime
                required property string durationLabel
                required property color accent
                required property bool isIdle
                required property int activityCount
                width: feed.width - 10
                height: isIdle ? 52 : activityCount > 1 ? 86 : 74

                Column {
                    x: 0; y: 14; spacing: 5
                    Label { text: Qt.formatTime(activity.endTime, "HH:mm"); color: root.theme.textSecondary; font.pixelSize: 12; font.family: root.theme.monoFamily }
                    Label { text: Qt.formatTime(activity.startTime, "HH:mm"); color: root.theme.textMuted; font.pixelSize: 10; font.family: root.theme.monoFamily }
                }
                Rectangle {
                    x: 69; y: 0; width: 1; height: parent.height + 8
                    color: root.theme.rule
                }
                Rectangle {
                    x: 66; y: 22; width: 7; height: 7; radius: 4
                    color: activity.isIdle ? root.theme.textDisabled : activity.accent
                    border.color: root.theme.canvas
                    border.width: 1
                }
                Button {
                    id: card
                    objectName: "dayCard" + activity.index
                    x: 86; width: parent.width - 86; height: parent.height
                    padding: 14
                    Accessible.name: activity.primaryLabel + ", " + activity.durationLabel + (activity.activityCount > 1 ? ", " + activity.activityCount + " activities. Expand to inspect." : ". Inspect activity.")
                    onClicked: {
                        root.selectedKey = activity.eventId
                        root.eventSelected(root.activityModel.recordAt(activity.index))
                    }
                    background: Rectangle {
                        radius: 8
                        color: root.selectedKey === activity.eventId ? root.theme.selection : card.hovered ? root.theme.surfaceHover : activity.isIdle ? root.theme.idleFill : root.theme.surface
                        border.color: card.activeFocus ? root.theme.focus : root.selectedKey === activity.eventId ? root.theme.accentMuted : root.theme.rule
                        Rectangle { x: 0; y: 14; width: 2; height: parent.height - 28; radius: 1; color: activity.isIdle ? root.theme.textDisabled : activity.accent }
                    }
                    contentItem: RowLayout {
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 5
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Label {
                                    text: activity.isIdle ? "Away from your computer" : activity.primaryLabel
                                    color: activity.isIdle ? root.theme.textMuted : root.theme.textPrimary
                                    font.pixelSize: 13
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                    Layout.maximumWidth: card.width * 0.55
                                }
                                Label { visible: activity.domain.length > 0; text: activity.displayName; color: root.theme.textMuted; font.pixelSize: 10 }
                                Item { Layout.fillWidth: true }
                            }
                            Label {
                                visible: !activity.isIdle
                                Layout.fillWidth: true
                                text: activity.title
                                color: root.theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                            Label {
                                visible: activity.activityCount > 1
                                text: activity.activityCount + " activities · expand"
                                color: root.theme.textMuted
                                font.pixelSize: 10
                            }
                        }
                        Label { text: activity.durationLabel; color: root.theme.textSecondary; font.pixelSize: 11 }
                        Glyph { name: "right"; ink: root.theme.textMuted; width: 14; height: 14 }
                    }
                }
            }

            ColumnLayout {
                visible: feed.count === 0
                anchors.centerIn: parent
                width: Math.min(400, parent.width - 32)
                spacing: 12
                Glyph { Layout.alignment: Qt.AlignHCenter; name: "day"; ink: root.theme.textMuted; width: 28; height: 28 }
                Label {
                    Layout.fillWidth: true
                    text: root.appController.status === "loading" ? "Gathering your day…" : root.appController.status === "error" ? "Connect your activity history" : "A quiet page, for now"
                    color: root.theme.textPrimary
                    font.pixelSize: 18
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    Layout.fillWidth: true
                    text: root.appController.status === "error" ? "Start ActivityWatch on this computer, then retry." : root.appController.status === "loading" ? "Reading activity saved on this device." : "There’s no recorded activity for this date. Try another day."
                    color: root.theme.textMuted
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }
                QuietButton {
                    Layout.alignment: Qt.AlignHCenter
                    visible: root.appController.status === "error"
                    theme: root.theme
                    text: "Retry connection"
                    emphasized: true
                    onClicked: root.appController.retry()
                }
            }
        }
        Label {
            Layout.bottomMargin: 14
            text: "Gaps in the overview mean no recording. Grouped activities keep every detail."
            color: root.theme.textMuted
            font.pixelSize: 10
            Layout.fillWidth: true
            elide: Text.ElideRight
        }
    }
}
