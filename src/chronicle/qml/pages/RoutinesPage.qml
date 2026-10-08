import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property var theme

    Rectangle { anchors.fill: parent; color: theme.canvas }

    ScrollView {
        anchors.fill: parent
        clip: true

        ColumnLayout {
            width: Math.max(720, root.width)
            spacing: 0

            Item { Layout.preferredHeight: theme.space6 * 2 }

            ColumnLayout {
                Layout.leftMargin: theme.space6 * 2
                Layout.rightMargin: theme.space6 * 2
                Layout.maximumWidth: 760
                spacing: theme.space4

                Rectangle {
                    Layout.preferredWidth: 64
                    Layout.preferredHeight: 4
                    color: theme.periwinkle
                }

                Label {
                    text: "Routines need history"
                    color: theme.textPrimary
                    font.pixelSize: theme.typeDisplay
                    font.weight: Font.DemiBold
                }

                Label {
                    Layout.fillWidth: true
                    text: "Chronicle currently loads one selected day at a time. Repeated patterns cannot be measured honestly until multiple days of consolidated history are available."
                    color: theme.textSecondary
                    font.pixelSize: theme.typeBody
                    wrapMode: Text.WordWrap
                    lineHeight: 1.35
                }

                Item { Layout.preferredHeight: theme.space3 }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: theme.rule }
                Item { Layout.preferredHeight: theme.space2 }

                Label {
                    text: "Unavailable in the current data scope"
                    color: theme.textPrimary
                    font.pixelSize: theme.typeTitle
                    font.weight: Font.DemiBold
                }

                Repeater {
                    model: [
                        ["Typical active window", "Requires comparable start and end times across days."],
                        ["Repeated app sequences", "Requires ordered sessions from multiple days."],
                        ["Weekday and weekend differences", "Requires enough history to compare both groups."]
                    ]
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: theme.space4

                        Rectangle {
                            Layout.preferredWidth: 3
                            Layout.preferredHeight: 44
                            color: theme.accentMuted
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: theme.space1
                            Label {
                                text: modelData[0]
                                color: theme.textSecondary
                                font.pixelSize: theme.typeBody
                                font.weight: Font.DemiBold
                            }
                            Label {
                                Layout.fillWidth: true
                                text: modelData[1]
                                color: theme.textMuted
                                font.pixelSize: theme.typeSmall
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }

                Item { Layout.preferredHeight: theme.space3 }
                Label {
                    Layout.fillWidth: true
                    text: "No estimates, synthetic charts, or inferred labels are shown from a single day. All future routine calculations will remain local to this computer."
                    color: theme.textMuted
                    font.pixelSize: theme.typeSmall
                    wrapMode: Text.WordWrap
                    lineHeight: 1.3
                }
            }

            Item { Layout.preferredHeight: theme.space6 * 2 }
        }
    }
}
