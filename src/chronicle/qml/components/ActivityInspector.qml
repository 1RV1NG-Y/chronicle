import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    required property var theme
    property var record: null
    property int expandedIndex: -1
    property bool showRaw: false
    readonly property var entries: !record ? [] : record.activities && record.activities.length ? record.activities.slice().reverse() : [record]
    signal closeRequested()
    onRecordChanged: { expandedIndex = entries.length === 1 ? 0 : -1; showRaw = false; records.positionViewAtBeginning() }
    color: theme.sidebar
    Rectangle { width: 1; height: parent.height; color: root.theme.rule }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16
        RowLayout {
            Layout.fillWidth: true
            Label { Layout.fillWidth: true; text: "Activity details"; color: root.theme.textSecondary; font.pixelSize: 12 }
            QuietButton { theme: root.theme; glyph: "close"; Accessible.name: "Close activity details"; onClicked: root.closeRequested() }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
            Label {
                Layout.fillWidth: true
                text: root.record ? root.record.primaryLabel : ""
                color: root.theme.textPrimary
                font.pixelSize: 21
                font.weight: Font.DemiBold
                wrapMode: Text.WrapAnywhere
            }
            Label { text: root.record ? root.record.timeLabel + "  ·  " + root.record.durationLabel : ""; color: root.theme.textSecondary; font.pixelSize: 12 }
            Label { visible: root.entries.length > 1; text: root.entries.length + " activities · latest first"; color: root.theme.textMuted; font.pixelSize: 11 }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: root.theme.rule }
        ListView {
            id: records
            objectName: "inspectorRecords"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: root.entries
            spacing: 8
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                id: entry
                required property var modelData
                required property int index
                readonly property bool expanded: root.expandedIndex === index
                width: records.width - 8
                height: detail.implicitHeight + 24
                radius: 7
                color: expanded ? root.theme.surface : "transparent"
                border.color: expanded ? root.theme.rule : "transparent"
                ColumnLayout {
                    id: detail
                    x: 12; y: 12; width: parent.width - 24
                    spacing: 10
                    Button {
                        id: expand
                        objectName: "inspectorEntry" + entry.index
                        Layout.fillWidth: true
                        implicitHeight: headline.implicitHeight
                        padding: 0
                        Accessible.name: entry.modelData.primaryLabel + ", " + entry.modelData.timeLabel + ". " + (entry.expanded ? "Collapse" : "Expand")
                        onClicked: { root.expandedIndex = entry.expanded ? -1 : entry.index; root.showRaw = false }
                        background: Item {}
                        contentItem: ColumnLayout {
                            id: headline
                            spacing: 5
                            RowLayout {
                                Layout.fillWidth: true
                                Rectangle { width: 5; height: 5; radius: 3; color: entry.modelData.accent }
                                Label {
                                    Layout.fillWidth: true
                                    text: entry.modelData.primaryLabel
                                    color: root.theme.textPrimary
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }
                                Label {
                                    text: entry.modelData.durationSeconds < 60 ? Math.round(entry.modelData.durationSeconds) + " sec" : entry.modelData.durationLabel
                                    color: root.theme.textMuted
                                    font.pixelSize: 10
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: entry.modelData.title || entry.modelData.subtitle
                                color: root.theme.textSecondary
                                font.pixelSize: 11
                                elide: entry.expanded ? Text.ElideNone : Text.ElideRight
                                wrapMode: entry.expanded ? Text.WrapAnywhere : Text.NoWrap
                            }
                            Label {
                                text: Qt.formatTime(entry.modelData.startTime, "HH:mm:ss") + " – " + Qt.formatTime(entry.modelData.endTime, "HH:mm:ss")
                                color: root.theme.textMuted
                                font.pixelSize: 10
                                font.family: root.theme.monoFamily
                            }
                        }
                    }
                    ColumnLayout {
                        visible: entry.expanded
                        Layout.fillWidth: true
                        spacing: 10
                        Label { text: entry.modelData.displayName; color: root.theme.textSecondary; font.pixelSize: 11 }
                        TextEdit {
                            visible: !!entry.modelData.url
                            Layout.fillWidth: true
                            text: entry.modelData.url || ""
                            color: root.theme.accentBright
                            font.pixelSize: 11
                            wrapMode: TextEdit.WrapAnywhere
                            readOnly: true
                            selectByMouse: true
                        }
                        QuietButton {
                            theme: root.theme
                            text: root.showRaw ? "Hide source data" : "Source data"
                            onClicked: root.showRaw = !root.showRaw
                        }
                        TextArea {
                            visible: root.showRaw
                            Layout.fillWidth: true
                            text: entry.modelData.rawJson || ""
                            color: root.theme.textSecondary
                            font.pixelSize: 10
                            font.family: root.theme.monoFamily
                            wrapMode: TextEdit.WrapAnywhere
                            readOnly: true
                            selectByMouse: true
                            background: Rectangle { color: root.theme.canvas; radius: 4 }
                        }
                    }
                }
            }
        }
    }
}
