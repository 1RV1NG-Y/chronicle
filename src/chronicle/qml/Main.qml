pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"

ApplicationWindow {
    id: window
    objectName: "chronicleWindow"
    width: 1280
    height: 850
    minimumWidth: 900
    minimumHeight: 640
    visible: true
    title: "Chronicle"
    color: theme.canvas
    font.family: theme.uiFamily
    property int currentPage: 0
    property var selectedEvent: null
    readonly property bool compactSidebar: width < 1080
    readonly property bool dockInspector: width >= 1200
    readonly property bool inspectorVisible: selectedEvent !== null && currentPage < 2
    readonly property var calendarActivityModel: calendarModel
    readonly property var timelineActivityModel: timelineModel
    readonly property var applicationController: controller
    onCurrentPageChanged: selectedEvent = null
    Theme { id: theme }
    Connections { target: window.applicationController; function onSelectedDateChanged() { window.selectedEvent = null } }
    Shortcut { sequence: "Escape"; onActivated: window.selectedEvent = null }

    RowLayout {
        anchors.fill: parent
        spacing: 0
        Sidebar {
            Layout.preferredWidth: window.compactSidebar ? 70 : 190
            Layout.fillHeight: true
            theme: theme
            compact: window.compactSidebar
            currentIndex: window.currentPage
            status: window.applicationController.status
            onNavigate: index => window.currentPage = index
        }
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0
            Rectangle {
                visible: previewMode
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? 28 : 0
                color: theme.selection
                Label { anchors.centerIn: parent; text: "DESIGN PREVIEW  ·  Sample activity"; font.pixelSize: 10; font.letterSpacing: 0.6; color: theme.accentBright }
            }
            PageToolbar {
                Layout.fillWidth: true
                Layout.preferredHeight: 76
                theme: theme
                pageIndex: window.currentPage
                selectedDate: window.applicationController.selectedDate
                searchText: window.timelineActivityModel.filterText
                onPreviousDay: window.applicationController.previousDay()
                onNextDay: window.applicationController.nextDay()
                onTodayRequested: window.applicationController.goToday()
                onSearchRequested: text => window.timelineActivityModel.filterText = text
            }
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0
                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: window.currentPage
                    CalendarPage {
                        theme: theme
                        appController: window.applicationController
                        activityModel: window.calendarActivityModel
                        onEventSelected: eventData => window.selectedEvent = eventData
                    }
                    TimelinePage {
                        theme: theme
                        appController: window.applicationController
                        activityModel: window.timelineActivityModel
                        onEventSelected: eventData => window.selectedEvent = eventData
                    }
                    SettingsPage { theme: theme; appController: window.applicationController }
                }
                ActivityInspector {
                    visible: window.inspectorVisible && window.dockInspector
                    Layout.preferredWidth: visible ? 340 : 0
                    Layout.fillHeight: true
                    theme: theme
                    record: window.selectedEvent
                    onCloseRequested: window.selectedEvent = null
                }
            }
        }
    }
    Rectangle {
        visible: window.inspectorVisible && !window.dockInspector
        anchors.fill: parent
        color: theme.scrim
        z: 20
        MouseArea { anchors.fill: parent; onClicked: window.selectedEvent = null }
    }
    ActivityInspector {
        visible: window.inspectorVisible && !window.dockInspector
        width: 340
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        z: 21
        theme: theme
        record: window.selectedEvent
        onCloseRequested: window.selectedEvent = null
    }
}
