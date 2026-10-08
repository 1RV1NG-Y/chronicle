import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    required property var theme
    required property var appController

    readonly property string connectionTitle: appController.status === "ready" ? "ActivityWatch connected"
        : appController.status === "loading" ? "Connecting to ActivityWatch"
        : appController.status === "empty" ? "Connected, no activity found"
        : "ActivityWatch connection error"

    Rectangle { anchors.fill: parent; color: theme.canvas }

    ScrollView {
        anchors.fill: parent
        clip: true

        ColumnLayout {
            width: Math.max(760, root.width)
            spacing: theme.space5

            Item { Layout.preferredHeight: theme.space5 }

            ColumnLayout {
                Layout.leftMargin: theme.space6
                Layout.rightMargin: theme.space6
                Layout.maximumWidth: 920
                spacing: theme.space2

                Label {
                    text: "Local by design"
                    color: theme.textPrimary
                    font.pixelSize: theme.typeDisplay
                    font.weight: Font.DemiBold
                }
                Label {
                    Layout.fillWidth: true
                    text: "Chronicle reads the ActivityWatch API on this computer. It has no account, cloud service, or AI processing path."
                    color: theme.textSecondary
                    font.pixelSize: theme.typeBody
                    wrapMode: Text.WordWrap
                    lineHeight: 1.3
                }
            }

            Rectangle {
                Layout.leftMargin: theme.space6
                Layout.rightMargin: theme.space6
                Layout.fillWidth: true
                Layout.maximumWidth: 920
                Layout.preferredHeight: connectionContent.implicitHeight + theme.space5 * 2
                radius: theme.radiusMedium
                color: theme.surface
                border.color: appController.status === "ready" ? theme.accentMuted : theme.rule

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 3
                    color: appController.status === "ready" ? theme.success
                         : appController.status === "error" ? theme.danger
                         : appController.status === "loading" ? theme.periwinkle
                         : theme.textMuted
                }

                ColumnLayout {
                    id: connectionContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: theme.space5
                    anchors.rightMargin: theme.space5
                    spacing: theme.space4

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: theme.space4
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: theme.space1
                            Label {
                                text: root.connectionTitle
                                color: theme.textPrimary
                                font.pixelSize: theme.typeHeading
                                font.weight: Font.DemiBold
                            }
                            Label {
                                Layout.fillWidth: true
                                text: appController.statusDetail.length ? appController.statusDetail
                                    : appController.status === "ready" ? "Current selected-day data is available."
                                    : appController.status === "loading" ? "Waiting for the local API response."
                                    : appController.status === "empty" ? "The API responded, but this day contains no consolidated sessions."
                                    : "Start ActivityWatch locally, then retry."
                                color: theme.textSecondary
                                font.pixelSize: theme.typeSmall
                                wrapMode: Text.WordWrap
                            }
                        }
                        Button {
                            id: retryButton
                            text: appController.isLoading ? "Connecting…" : "Retry"
                            enabled: !appController.isLoading
                            Accessible.name: "Retry ActivityWatch connection"
                            onClicked: appController.retry()
                            implicitHeight: theme.controlHeight
                            leftPadding: theme.space4
                            rightPadding: theme.space4
                            contentItem: Label {
                                text: retryButton.text
                                color: retryButton.enabled ? theme.textPrimary : theme.textDisabled
                                font.pixelSize: theme.typeSmall
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                radius: theme.radiusSmall
                                color: retryButton.hovered ? theme.surfaceHover : theme.surfaceRaised
                                border.color: retryButton.activeFocus ? theme.focus : theme.ruleStrong
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: theme.rule }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: theme.space5
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: theme.space1
                            Label { text: "ENDPOINT"; color: theme.textMuted; font.pixelSize: theme.typeCaption; font.weight: Font.DemiBold; font.letterSpacing: 0.6 }
                            Label {
                                Layout.fillWidth: true
                                text: appController.endpoint.length ? appController.endpoint : "Not configured"
                                color: theme.textPrimary
                                font.pixelSize: theme.typeSmall
                                font.family: theme.monoFamily
                                elide: Text.ElideRight
                            }
                        }
                        ColumnLayout {
                            Layout.preferredWidth: 240
                            spacing: theme.space1
                            Label { text: "LAST REFRESH"; color: theme.textMuted; font.pixelSize: theme.typeCaption; font.weight: Font.DemiBold; font.letterSpacing: 0.6 }
                            Label {
                                text: appController.lastRefreshLabel.length ? appController.lastRefreshLabel : "Not refreshed yet"
                                color: theme.textSecondary
                                font.pixelSize: theme.typeSmall
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.leftMargin: theme.space6
                Layout.rightMargin: theme.space6
                Layout.fillWidth: true
                Layout.maximumWidth: 920
                Layout.preferredHeight: websiteContent.implicitHeight + theme.space5 * 2
                radius: theme.radiusMedium
                color: theme.surface
                border.color: appController.websiteCaptureStatus === "capturing"
                    ? theme.success : theme.ruleStrong

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 3
                    color: appController.websiteCaptureStatus === "capturing"
                        ? theme.success
                        : appController.websiteCaptureStatus === "checking"
                            ? theme.periwinkle : theme.danger
                }

                ColumnLayout {
                    id: websiteContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: theme.space5
                    anchors.rightMargin: theme.space5
                    spacing: theme.space3

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: theme.space4
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: theme.space1
                            Label {
                                text: appController.websiteCaptureStatus === "capturing"
                                    ? "Website capture active"
                                    : appController.websiteCaptureStatus === "checking"
                                        ? "Checking website capture"
                                        : "Website capture needs attention"
                                color: theme.textPrimary
                                font.pixelSize: theme.typeHeading
                                font.weight: Font.DemiBold
                            }
                            Label {
                                Layout.fillWidth: true
                                text: appController.websiteCaptureDetail
                                color: theme.textSecondary
                                font.pixelSize: theme.typeSmall
                                wrapMode: Text.WordWrap
                            }
                        }
                        Label {
                            text: appController.websiteCaptureStatus.toUpperCase()
                            color: appController.websiteCaptureStatus === "capturing"
                                ? theme.success : theme.textMuted
                            font.pixelSize: theme.typeCaption
                            font.weight: Font.Bold
                            font.letterSpacing: 0.6
                        }
                    }

                    Label {
                        visible: appController.websiteCaptureStatus !== "capturing"
                        Layout.fillWidth: true
                        text: "Install ActivityWatch Web Watcher in every browser you use. In Thorium, set the extension’s Browser identity to “thorium” so its events cannot be confused with Chrome."
                        color: theme.textMuted
                        font.pixelSize: theme.typeSmall
                        wrapMode: Text.WordWrap
                        lineHeight: 1.25
                    }

                    RowLayout {
                        visible: appController.websiteCaptureStatus !== "capturing"
                        spacing: theme.space2
                        QuietButton {
                            theme: root.theme
                            emphasized: true
                            id: chromiumSetupButton
                            text: "Brave / Thorium extension"
                            onClicked: Qt.openUrlExternally("https://chromewebstore.google.com/detail/activitywatch-web-watcher/nglaklhklhcoonedhgnpgddginnjdadi")
                        }
                        QuietButton {
                            theme: root.theme
                            emphasized: true
                            text: "Firefox extension"
                            onClicked: Qt.openUrlExternally("https://addons.mozilla.org/firefox/addon/aw-watcher-web/")
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.leftMargin: theme.space6
                Layout.rightMargin: theme.space6
                Layout.fillWidth: true
                Layout.maximumWidth: 920
                spacing: theme.space3

                Label {
                    text: "Privacy boundary"
                    color: theme.textPrimary
                    font.pixelSize: theme.typeHeading
                    font.weight: Font.DemiBold
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: theme.rule }

                Repeater {
                    model: [
                        ["Network scope", "Loopback ActivityWatch API only"],
                        ["Cloud sync", "None"],
                        ["Account", "None"],
                        ["Chronicle telemetry", "None"],
                        ["AI processing", "None"]
                    ]
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 36
                        spacing: theme.space4
                        Label {
                            Layout.preferredWidth: 176
                            text: modelData[0]
                            color: theme.textSecondary
                            font.pixelSize: theme.typeSmall
                        }
                        Label {
                            Layout.fillWidth: true
                            text: modelData[1]
                            color: theme.textPrimary
                            font.pixelSize: theme.typeSmall
                            font.weight: Font.DemiBold
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: theme.rule }
                Label {
                    Layout.fillWidth: true
                    text: "Raw event provenance is displayed only in an activity’s collapsed technical details. Chronicle does not write to the ActivityWatch database."
                    color: theme.textMuted
                    font.pixelSize: theme.typeSmall
                    wrapMode: Text.WordWrap
                    lineHeight: 1.3
                }
            }

            Item { Layout.preferredHeight: theme.space6 }
        }
    }
}
