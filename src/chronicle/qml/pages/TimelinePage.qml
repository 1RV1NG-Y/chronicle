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

    signal eventSelected(var eventData)

    function selectEvent(eventData) {
        selectedKey = eventData.eventId
        eventSelected(eventData)
    }

    Connections {
        target: root.appController
        function onSelectedDateChanged() { root.selectedKey = "" }
    }

    Rectangle { anchors.fill: parent; color: theme.canvas }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            visible: root.appController.status !== "ready"
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 44 : 0
            color: theme.surface
            border.color: theme.rule

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: theme.space4
                anchors.rightMargin: theme.space4
                spacing: theme.space3
                Rectangle {
                    Layout.preferredWidth: 8
                    Layout.preferredHeight: 8
                    radius: 4
                    color: root.appController.status === "error" ? theme.danger
                         : root.appController.status === "loading" ? theme.periwinkle
                         : theme.textMuted
                }
                Label {
                    Layout.fillWidth: true
                    text: root.appController.status === "loading" ? "Loading the consolidated ledger…"
                        : root.appController.status === "empty" ? "No activity was recorded for this day."
                        : "ActivityWatch could not be reached. " + root.appController.statusDetail
                    color: theme.textSecondary
                    font.pixelSize: theme.typeSmall
                    elide: Text.ElideRight
                }
                Button {
                    id: retryButton
                    visible: root.appController.status === "error"
                    text: "Retry"
                    onClicked: root.appController.retry()
                    contentItem: Label {
                        text: retryButton.text
                        color: theme.textPrimary
                        font.pixelSize: theme.typeSmall
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: theme.radiusSmall
                        color: retryButton.hovered ? theme.surfaceHover : theme.surfaceRaised
                        border.color: retryButton.activeFocus ? theme.focus : theme.rule
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            Layout.leftMargin: theme.space5
            Layout.rightMargin: theme.space5
            spacing: theme.space4

            Label {
                text: "Exact activity · earliest first"
                color: theme.textSecondary
                font.pixelSize: theme.typeSmall
                font.weight: Font.DemiBold
            }
            Item { Layout.fillWidth: true }
            Label {
                text: root.activityModel.filterText.length
                    ? root.activityModel.resultCount + " of " + root.activityModel.totalCount + " results"
                    : root.activityModel.totalCount + (root.activityModel.totalCount === 1 ? " session" : " sessions")
                color: theme.textMuted
                font.pixelSize: theme.typeCaption
                font.family: theme.monoFamily
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            Layout.leftMargin: theme.space5 + theme.space4
            Layout.rightMargin: theme.space5 + theme.space3
            spacing: theme.space4
            Label {
                Layout.preferredWidth: 144
                text: "TIME RANGE"
                color: theme.textMuted
                font.pixelSize: theme.typeCaption
                font.weight: Font.DemiBold
                font.letterSpacing: 0.7
            }
            Item { Layout.preferredWidth: 28 }
            Label {
                Layout.fillWidth: true
                text: "ACTIVITY AND CONTEXT"
                color: theme.textMuted
                font.pixelSize: theme.typeCaption
                font.weight: Font.DemiBold
                font.letterSpacing: 0.7
            }
            Label {
                Layout.preferredWidth: 80
                text: "DURATION"
                color: theme.textMuted
                font.pixelSize: theme.typeCaption
                font.weight: Font.DemiBold
                font.letterSpacing: 0.7
                horizontalAlignment: Text.AlignRight
            }
        }

        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: theme.rule }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: ledger
                anchors.fill: parent
                anchors.leftMargin: theme.space5
                anchors.rightMargin: theme.space5
                anchors.topMargin: theme.space2
                anchors.bottomMargin: theme.space3
                clip: true
                spacing: theme.space1
                model: root.activityModel
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                delegate: TimelineRow {
                    required property int index
                    width: ledger.width - theme.space2
                    theme: root.theme
                    selected: root.selectedKey === eventId
                    showDetails: root.activityModel.hasActiveFilters
                    onEventSelected: eventData => root.selectEvent(eventData)
                }
            }

            ColumnLayout {
                visible: root.appController.status !== "loading" && root.activityModel.resultCount === 0
                anchors.centerIn: parent
                width: Math.min(520, parent.width - theme.space6 * 2)
                spacing: theme.space2

                Label {
                    Layout.fillWidth: true
                    text: root.activityModel.filterText.length ? "No matching sessions"
                        : root.appController.status === "error" ? "Timeline unavailable"
                        : "No sessions for this day"
                    color: theme.textPrimary
                    font.pixelSize: theme.typeHeading
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                }
                Label {
                    Layout.fillWidth: true
                    text: root.activityModel.filterText.length
                        ? "Try a broader app, title, or domain search."
                        : root.appController.status === "error"
                            ? "Retry the local connection above or from Settings."
                            : "Choose another date, or keep ActivityWatch running to record activity."
                    color: theme.textSecondary
                    font.pixelSize: theme.typeSmall
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }
}
