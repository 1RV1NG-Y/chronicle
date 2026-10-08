# Digital Day Tracker — MVP Product & Implementation Spec

> **Redesign update (October 4, 2026):** See [current design direction](design-direction.md) for the user's latest-first day feed, expandable groups, and neutral dark visual preferences. Those decisions supersede conflicting presentation details below.

> **Working title:** Digital Day Tracker / Chronicle  
> **Status:** Initial implementation spec  
> **Primary platform for MVP:** Linux desktop (GNOME Wayland)  
> **Frontend stack:** Python + PySide6 + Qt Quick/QML  
> **Tracking/data substrate:** ActivityWatch-compatible data, with `aw-awatcher` on Linux Wayland

---

## 1. Product idea

Build a detailed, local-first activity tracker that reconstructs **what the user was doing throughout the day**, in chronological order.

The core idea is not conventional “screen time” such as:

- Browser: 3h 14m
- VS Code: 2h 03m
- Telegram: 47m

Instead, the app should make it easy to answer:

- What was I doing at 09:17?
- What happened between 13:00 and 15:00?
- What did I do before I started coding?
- Where did an hour disappear?
- How long did I stay on a specific site, window, file, or task?
- What does a normal day or routine look like over time?

The product should feel closer to a **digital activity ledger / personal timeline / calendar of computer use** than to a traditional screen-time dashboard.

---

## 2. Product principles

### 2.1 Time is the primary organizing axis

The central object is the **day**, not the app.

Applications, websites, window titles, files, and categories are context attached to time blocks.

The app should reconstruct:

```text
08:42–08:56  Firefox
             chatgpt.com
             ActivityWatch discussion

08:56–09:05  GitHub
             prime-agent README

09:05–09:42  VS Code
             luma/src/indexer.rs

09:42–09:48  Telegram

09:48–10:11  Screen off / idle
```

This is more important than aggregate totals.

### 2.2 Local-first and privacy-respecting

Activity data is sensitive.

For MVP:

- Data remains on the local machine.
- No cloud sync.
- No account system.
- No telemetry requirement.
- No AI dependency.
- No remote backend.

Multi-device synchronization may be considered later, but it is **not an MVP feature**.

### 2.3 Use existing tracking infrastructure where it is already good

Do not rebuild solved tracking infrastructure prematurely.

ActivityWatch already provides:

- local event storage,
- REST/query APIs,
- browser watcher support,
- window activity events,
- AFK/idle events,
- a useful event/bucket data model.

Use ActivityWatch source code as a reference for behavior and edge cases.

The new app should aggressively redesign the frontend while preserving or remaining compatible with the useful parts of the ActivityWatch data model/API.

### 2.4 Appearance and speed are both first-class requirements

The application should feel like a polished standalone desktop application, not a debug dashboard or a web page opened on localhost.

Priorities:

1. Appearance / visual quality
2. Perceived speed / responsiveness
3. Clear chronological information hierarchy
4. Maintainability

The app should be pinnable to the GNOME dock/panel and behave like a normal desktop app.

---

## 3. MVP scope

### Included

- Standalone desktop application
- Linux support first
- GNOME Wayland compatibility
- ActivityWatch local API integration
- `aw-awatcher` as the Linux activity collector
- ActivityWatch browser watcher integration
- Calendar view
- Timeline view
- Basic routines/statistics foundation
- Settings
- App/window/site context wherever data exists
- Local categories/rules support
- Smooth day navigation
- Search/filtering within recorded activity
- Display of active/idle periods

### Explicitly not required for MVP

- Multi-device synchronization
- Mobile app
- Cloud accounts
- AI assistant
- AI summaries
- AI categorization as a required feature
- Social features
- Teams/workspaces
- Full ActivityWatch feature parity
- A separate dedicated Apps section
- A separate dedicated Websites section
- A separate Devices section
- Stopwatch/time-entry workflow

AI-assisted categorization may be explored later, but the app should not depend on it.

---

## 4. Navigation structure

Use a **persistent left sidebar** as the primary application navigation.

Do not duplicate global navigation in a top tab bar.

Initial sidebar:

```text
[logo] Working Title

Calendar
Timeline
Routines

────────────

Settings
```

`Analytics` may be added later if it proves useful, but should not be included merely to fill the sidebar.

### Why no Apps / Websites sections?

Apps and websites are dimensions of activity, not separate primary objects.

They should appear as:

- filters,
- drill-downs,
- labels,
- detail panel fields,
- statistics within views.

### Why no Devices section?

MVP is local to one machine. Device synchronization is deferred.

---

## 5. Page-level toolbar behavior

The top area of the content pane is **contextual**, not global navigation.

Examples:

### Calendar

```text
Friday, Aug 8        [Day] [Week] [Month]    Today    ◀  ▶    Filter
```

### Timeline

```text
Timeline             Aug 8                   Search   Filter   Density
```

### Routines

```text
Routines             Last 30 days ▾          Weekdays ▾
```

The sidebar answers:

> Where am I in the application?

The page toolbar answers:

> How am I viewing this page?

---

## 6. Primary view: Calendar

Calendar should be the default/home experience.

The strongest expression of the product is a **calendar-like view of digital activity**.

### 6.1 Day view

Use a vertical time axis similar to a modern calendar.

Example:

```text
08:00  │
       │
08:30  │  ┌──────────────────────────────┐
       │  │ Firefox                      │
       │  │ ChatGPT — ActivityWatch      │
       │  │ 08:34–09:02                  │
       │  └──────────────────────────────┘
09:00  │
       │  ┌──────────────────┐
       │  │ Terminal         │
       │  │ ActivityWatch    │
       │  └──────────────────┘
09:30  │
       │  ┌──────────────────────────────┐
       │  │ Brave                        │
       │  │ GitHub / awatcher            │
       │  └──────────────────────────────┘
```

Important behavior:

- Vertical position = time of day
- Block height = duration
- App/context labels live inside blocks
- Idle/screen-off time should be visible
- Short events must remain inspectable without overwhelming the view
- Zoom should expose increasing detail
- Clicking a block opens detailed context

### 6.2 Week view

Week view should emphasize broad patterns.

Possible layout:

```text
        MON       TUE       WED       THU       FRI

08:00   Firefox   Firefox   Away      Firefox   Firefox
09:00   Code      Code      Firefox   Code      Terminal
10:00   Code      Code      Code      Code      Code
```

At this scale:

- show app/category/session blocks,
- avoid verbose page titles,
- preserve time/duration,
- allow clicking into a day.

### 6.3 Month view

Month should be intentionally abstract.

Possible data:

- total active time per day,
- dominant category/app,
- unusually high/low activity,
- compact visual indication of routines.

Do not attempt to render every event at month scale.

---

## 7. Secondary view: Timeline

Timeline is the precise chronological ledger.

It should answer:

> Exactly what happened, and in what order?

Example:

```text
09:17:03  Brave       chatgpt.com         4m 28s
09:21:31  Terminal    ~/Downloads         1m 04s
09:22:35  Brave       github.com          7m 11s
09:29:46  Files       Downloads           42s
```

Requirements:

- Vertical scrolling
- Time moves downward
- Exact timestamps available
- Duration always visible
- App icon + normalized display name
- Window title
- URL/domain when available
- File/editor context when available
- AFK/idle periods
- Expandable entries
- Detail panel or expandable card
- Search
- Filtering
- Optional density controls

Avoid ActivityWatch’s current horizontal “debug graph” as the main interface.

That visualization may exist later as an optional diagnostic/overview view.

---

## 8. Routines view

Routines is not required for the first implementation milestone, but the data model should support it.

The initial routines feature should be **statistical**, not AI-driven.

Examples:

- typical active hours,
- usual first app of the day,
- repeated coding windows,
- frequent app/site sequences,
- weekday/weekend differences,
- average idle periods,
- average time spent by category in specific time windows.

Example:

```text
Typical 08:00–10:00
████████████ Firefox
██████       Terminal
████         VS Code

Typical 14:00–17:00
████████████████ VS Code
██               Firefox
```

AI categorization or routine naming may be considered later.

---

## 9. Visual design direction

### 9.1 General aesthetic

- Modern desktop productivity app
- Dark theme first is acceptable
- Clean, restrained color palette
- Strong typography
- Subtle borders
- Good spacing
- Rounded cards where useful
- Avoid excessive glassmorphism
- Avoid “gaming UI”
- Avoid dashboard clutter
- Avoid bootstrap/debug-tool appearance

The reference direction discussed includes:

- modern left sidebar,
- clear separation between applications,
- compact contextual top toolbar,
- calendar/timeline emphasis,
- restrained app/category colors.

### 9.2 Color usage

Do not make every block a fully saturated color.

Preferred approach:

- mostly neutral surface colors,
- thin app/category accent stripe,
- subtle icon-derived or user-configurable accent colors,
- muted category colors,
- neutral gray for AFK/unknown.

Potentially:

```text
┃ Firefox
┃ ChatGPT — ActivityWatch discussion
┃ 28m
```

where the thin left stripe communicates application identity.

### 9.3 App colors

Stable colors per application are useful.

Examples:

- Firefox → stable accent
- VS Code → stable accent
- Terminal → stable accent
- Telegram → stable accent
- AFK → neutral

Colors may eventually be:

- manually configurable,
- derived from icons,
- generated from stable app IDs.

---

## 10. Interaction model

### 10.1 Zoom and detail

Calendar should progressively reveal detail.

Normal zoom:

```text
09:00  Firefox — 31 min
```

Closer zoom:

```text
09:00  Firefox — ChatGPT
09:12  Firefox — GitHub
09:18  Firefox — ActivityWatch docs
```

Detailed inspection:

```text
09:12:04  GitHub
          ActivityWatch/awatcher

09:14:37  GitHub
          issue #...

09:17:52  ActivityWatch docs
          REST API
```

### 10.2 Clicking activity

Opening an event/block should expose available metadata:

- exact start time,
- exact end time,
- duration,
- application,
- raw app ID,
- window title,
- URL,
- domain,
- source bucket/watcher,
- category,
- raw event payload if useful.

### 10.3 Filtering

Filters should be contextual, not separate navigation pages.

Potential filters:

- application,
- category,
- domain,
- title text,
- active/idle,
- time range,
- source/watcher.

---

## 11. Categorization

ActivityWatch currently supports rule-based categorization over event context.

Preserve the useful principle:

> Raw events remain raw; categories are applied dynamically and can reorganize historical data.

Initial categorization can be rule-based.

Potential category tree:

```text
Work
└── Programming
    └── Digital Day Tracker

Media
└── Video

Comms
└── IM
```

The new implementation should eventually allow categorization rules to operate on more context than ActivityWatch’s typical app/title matching, including:

- app,
- window title,
- URL,
- domain,
- file path,
- source,
- device (future),
- category ancestry.

AI-assisted categorization is a possible future enhancement, not an MVP dependency.

---

## 12. Frontend technology

Chosen stack:

```text
Python 3
PySide6
Qt Quick / QML
```

### Why

The application needs:

- native standalone behavior,
- good desktop integration,
- dock/panel pinning,
- high visual quality,
- smooth scrolling,
- animations,
- custom calendar/timeline drawing,
- cross-platform potential,
- fast iteration.

QML should handle presentation.

Python should handle:

- API client,
- event normalization,
- caching,
- models,
- filtering,
- data transformation.

Do not implement the UI as traditional Tkinter or default Qt Widgets.

Do not use Electron.

---

## 13. Suggested frontend architecture

```text
ActivityWatch / aw-server
          ↓
    ActivityWatchClient
          ↓
  Event normalization layer
          ↓
     Timeline store/cache
          ↓
  QAbstractListModel / models
          ↓
         QML UI
```

Suggested internal modules:

```text
src/
├── main.py
├── api/
│   └── activitywatch_client.py
├── models/
│   ├── activity_event.py
│   ├── activity_block.py
│   └── category.py
├── services/
│   ├── event_normalizer.py
│   ├── timeline_builder.py
│   ├── categorizer.py
│   └── cache.py
├── qtmodels/
│   ├── timeline_model.py
│   └── calendar_model.py
└── qml/
    ├── Main.qml
    ├── components/
    │   ├── Sidebar.qml
    │   ├── ActivityBlock.qml
    │   ├── AppIcon.qml
    │   ├── TimelineRow.qml
    │   └── PageToolbar.qml
    └── pages/
        ├── CalendarPage.qml
        ├── TimelinePage.qml
        ├── RoutinesPage.qml
        └── SettingsPage.qml
```

This is only a suggested shape; adapt as implementation reveals better boundaries.

---

## 14. Performance requirements

The app should feel immediate.

Avoid this pattern:

```text
user scrolls
   ↓
fetch huge API range
   ↓
normalize everything
   ↓
block UI thread
```

Preferred behavior:

- preload current day,
- cache normalized activity blocks,
- lazy-load neighboring days,
- perform expensive transforms away from UI thread,
- only instantiate visible QML delegates,
- keep raw events separate from rendered activity blocks.

The Python layer should not be responsible for drawing.

Qt Quick/QML should handle visual rendering.

---

## 15. ActivityWatch integration

### Local API

ActivityWatch exposes its local API through:

```text
http://localhost:5600
```

The frontend should initially consume the existing API instead of reading the database directly.

Useful concepts:

- buckets,
- events,
- queries,
- browser watcher buckets,
- AFK buckets,
- active-window buckets.

Do not couple the first frontend implementation directly to ActivityWatch’s SQLite storage.

Keep the API boundary.

### Source code usage

ActivityWatch source should be available locally as implementation reference.

Study upstream behavior for:

- bucket discovery,
- query behavior,
- AFK filtering,
- browser/window merging,
- category handling,
- overlapping events,
- heartbeat semantics,
- duration calculations,
- edge cases.

The goal is not to preserve the old frontend.

The goal is to avoid rediscovering already-solved domain problems.

---

## 16. Linux / GNOME Wayland collector setup

The currently working Linux setup uses:

- ActivityWatch core/UI under `/opt/activitywatch`
- `aw-awatcher` at `~/.local/bin/aw-awatcher`
- GNOME AppIndicator extension
- GNOME Focused Window D-Bus extension
- ActivityWatch data under `~/.local/share/activitywatch`

The standard ActivityWatch watchers were not sufficient under GNOME Wayland.

`aw-awatcher` replaces:

- `aw-watcher-window`
- `aw-watcher-afk`

Current launcher configuration concept:

```toml
[aw-qt]
autostart_modules = ["aw-server", "aw-awatcher"]
```

The current `aw-qt` launcher had to be forced through XWayland because of its outdated Qt Wayland library.

This is a useful signal for the new app:

> Do not inherit `aw-qt` as a long-term architectural dependency.

The new application should eventually launch cleanly on Wayland itself.

---

## 17. Packaging direction

Not required in the first coding milestone, but the final app should behave as a normal desktop application.

Desired:

- `.desktop` launcher on Linux,
- proper icon,
- GNOME dock pinning,
- normal window behavior,
- no requirement to manually open localhost,
- clean install/uninstall path,
- package format to be decided later.

The collection services may eventually run as user-level systemd services.

Example future architecture:

```text
systemd --user
├── activity server
└── activity watcher

Desktop app
└── frontend only
```

---

## 18. Cross-platform direction

ActivityWatch itself supports Windows and macOS.

The frontend should avoid Linux-specific assumptions where practical.

Potential future collector structure:

```text
Windows ───── ActivityWatch watcher ─┐
macOS ─────── ActivityWatch watcher ─┤
Linux ─────── aw-awatcher ───────────┤
                                     ↓
                            ActivityWatch-compatible events
                                     ↓
                               same frontend
```

Cross-platform support is desirable later, but Linux is the MVP target.

---

## 19. Licensing notes

ActivityWatch is licensed under the **Mozilla Public License 2.0 (MPL-2.0)**.

Important implementation implication:

- ActivityWatch code can be studied and modified.
- Modified MPL-covered source files remain under MPL when distributed.
- New, separate files/modules can generally use another license.
- A ground-up frontend can be separately licensed if it does not copy MPL-covered files into those new files.
- Preserve required notices for any reused/modified ActivityWatch code.
- Do not assume ActivityWatch branding/logo rights are granted by the source license.

For the cleanest separation, keep upstream ActivityWatch code as a reference tree and implement the new frontend in a fresh project/repository.

---

## 20. First implementation milestone

Build the smallest useful standalone prototype.

### Milestone 1

- Launchable PySide6/QML desktop app
- Sidebar
- Calendar page
- Timeline page
- Settings page
- Connect to local ActivityWatch API
- Load current-day events
- Normalize:
  - window events,
  - browser events,
  - AFK events
- Render:
  - application,
  - title,
  - domain where available,
  - timestamps,
  - duration
- Smooth scrolling
- Click activity to inspect raw details

### Milestone 2

- Calendar day layout with duration-proportional blocks
- App colors/icons
- Filtering
- Search
- Day navigation
- Idle/screen-off visualization
- Better event merging/normalization

### Milestone 3

- Week view
- Categorization UI
- Routines/statistics
- Packaging polish

---

## 21. Non-goals for early implementation

Do not spend early time on:

- AI features,
- multi-device sync,
- Android,
- cloud services,
- user accounts,
- complex dashboard charts,
- rebuilding ActivityWatch server,
- replacing ActivityWatch event storage,
- full categorization automation,
- perfect cross-platform packaging.

The first question to answer is:

> Can the app turn real ActivityWatch data into an excellent calendar/timeline of the user’s day?

If yes, continue outward from there.
