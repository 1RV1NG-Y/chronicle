# Digital Day Tracker — Design Journal / Conversation Summary

> **Historical context:** The [October 4, 2026 design direction](design-direction.md) records the user's updated preferences for the redesign.

> This is intentionally more narrative than the implementation spec.  
> Its purpose is to preserve the reasoning, preferences, discoveries, and product instincts that led to the current direction.

---

## Origin of the idea

The project started from dissatisfaction with normal screen-time tools.

Phone screen-time systems and desktop equivalents mostly answer:

- how long did I use an app?
- what was my total screen time?
- what were my most-used apps?

The desired product is much more detailed.

The core question is:

> **What exactly was I doing at each point in the day?**

The ideal history is chronological and reconstructable:

```text
10:42–10:48  Browser — GitHub
10:48–10:51  Telegram
10:51–10:53  launcher / idle
10:53–11:07  YouTube
11:07–11:21  Browser — ChatGPT
11:21–11:46  VS Code — specific project/file
```

The point is not merely productivity scoring.

It is closer to having a **personal digital history** that can reveal routines, transitions, and where time actually went.

---

## Early platform thinking

Linux initially seemed like the easier environment because desktop data can often be inspected more freely.

Android was expected to be more restrictive because applications are sandboxed.

The rough understanding that emerged:

- Android can reliably expose foreground app usage and timestamps.
- Accessibility can sometimes expose more context.
- Browser extensions or app-specific integrations can add detail.
- Root could expose much more but would be brittle and app-specific.
- Linux can provide much richer desktop activity context.

This led to the idea of a sensor-based architecture where different sources contribute pieces of context.

---

## ActivityWatch discovery

ActivityWatch turned out to be extremely close to the collection/storage part of the idea.

The most interesting ActivityWatch feature was the **Timeline** because it already stores chronological events rather than only aggregate totals.

However, both the desktop and Android interfaces felt rough.

The Android timeline especially felt like:

> a desktop web UI squeezed into the vertical space of a phone

rather than a genuinely mobile-first activity history.

That sparked the thought that a fork or replacement frontend could be enough.

---

## Important shift in project scope

After seeing ActivityWatch data working, the project stopped looking like:

> “build a screen-time tracker from scratch”

and started looking like:

> **“build a much better personal activity viewer on top of proven tracking infrastructure.”**

This is a major scope decision.

The collection layer is already good enough to prototype the actual product idea.

The strongest opportunity is presentation, normalization, and interaction.

---

## Wayland problems and what they taught us

The ActivityWatch AppImage initially failed because it could not find a system tray.

GNOME does not expose the legacy tray model ActivityWatch expects by default.

AppIndicator support solved the tray side.

A more important issue appeared afterward:

ActivityWatch’s default Linux watchers are built around assumptions that work better on X11 than GNOME Wayland.

This triggered a larger discussion about Wayland:

- X11 is old and permissive.
- Wayland is modern and more secure.
- The downside is that programs cannot freely inspect or control other programs.
- This breaks or complicates legitimate tools such as activity trackers, automation utilities, global hotkeys, remote control software, etc.
- GNOME is particularly conservative about exposing privileged desktop information.

There was no desire to move the whole machine to X11 just to make one app work.

The preferred philosophy became:

> stay on Wayland and solve the tracking problem the intended modern way.

---

## The middle ground: awatcher

The key practical discovery was `awatcher`.

It exists specifically to deal with Linux desktop-environment fragmentation and can replace ActivityWatch’s default active-window and AFK watchers.

For GNOME Wayland it uses the **Focused Window D-Bus** GNOME extension.

This means the working architecture is roughly:

```text
GNOME Wayland
     ↓
Focused Window D-Bus
     ↓
aw-awatcher
     ↓
ActivityWatch server/storage
```

Browser detail remains a separate source through ActivityWatch’s browser watcher.

This was a major validation:

> Wayland is not fatal to the project.  
> The ugly compatibility layer already exists.

---

## The actual install was messy

The ActivityWatch installation did not end up being a clean AUR install.

The AUR recipe tried to build an older web UI and ran into incompatible `pinia` / `vue-demi` dependencies.

The workaround that succeeded:

- ActivityWatch core/UI installed under `/opt/activitywatch`
- official `aw-awatcher` binary installed at `~/.local/bin/aw-awatcher`
- upstream SHA-256 verified
- ActivityWatch configured to use `aw-awatcher`
- `aw-qt` forced through XWayland because its Qt Wayland library was outdated
- corrected menu and autostart entries added
- live window events verified through the local API

Current data lives under:

```text
~/.local/share/activitywatch
```

This messy setup matters for product direction.

It suggests the future app should **not inherit the old `aw-qt` launcher architecture** if avoidable.

The frontend should be a clean Wayland-native standalone application.

---

## Seeing the real data

Once tracking worked, the ActivityWatch timeline showed surprisingly good raw data.

There were many fine-grained events over only a few minutes.

Examples included:

- browser application IDs,
- GNOME Terminal,
- Files/Nautilus,
- rapid context switches,
- active vs AFK state.

The conclusion was:

> the problem is no longer “can we collect enough data?”  
> the problem is “how do we present noisy telemetry as a comprehensible day?”

That is exactly the kind of problem the project should solve.

---

## Why the current ActivityWatch timeline is not enough

ActivityWatch’s existing timeline feels more like a debugging / inspection tool:

- horizontal tracks,
- bucket names,
- pan and zoom,
- event counts,
- truncated labels.

It is useful for verifying data collection.

It is not ideal for answering:

> “what was I doing at 9:17?”

The desired interface should read naturally in chronological order.

Time should move vertically.

---

## Calendar view became the central idea

A major design decision was that the strongest view is probably not merely a list.

It should have a **calendar-like day view**.

The height of an activity block should literally represent duration.

Example:

```text
08:00  │
       │
08:30  │  Firefox
       │  ChatGPT — ActivityWatch discussion
       │
09:00  ├────────────────────
       │  Terminal
       │  ActivityWatch setup
09:30  ├────────────────────
       │  Brave
       │  GitHub / awatcher
```

This gives an intuitive visual picture of the day:

- long uninterrupted coding block,
- short distraction,
- half hour away,
- browser research,
- terminal setup.

The product can then support several views over the same underlying data.

---

## Multiple views, not one overloaded screen

The expected app should have several ways of looking at the same history.

### Calendar

The main/default experience.

Purpose:

> reconstruct the day visually.

Possible modes:

- Day
- Week
- Month

### Timeline

The precise event ledger.

Purpose:

> exactly what happened, in what order?

Example:

```text
09:17:03  Brave       chatgpt.com       4m 28s
09:21:31  Terminal    ~/Downloads       1m 04s
09:22:35  Brave       github.com        7m 11s
```

### Routines

Later feature.

Purpose:

> identify repeated patterns across days/weeks.

Initially this should be statistical, not AI-generated.

---

## Reddit redesign reference

A Reddit user posted a redesign of ActivityWatch.

The exact code was not shared, but the screenshot was useful enough as a visual reference.

What was appealing:

- modern sidebar,
- clearer separation of activity between applications,
- more polished visual hierarchy,
- generally more contemporary feel.

What should *not* be copied:

- its exact color scheme,
- AI features,
- any unnecessary complexity.

The useful design lesson was:

> separating applications visually is good, but the main organizing principle should still be time.

---

## Sidebar decision

A modern persistent sidebar felt like the most natural primary navigation.

There was an early mockup that accidentally had both a top navigation row and a sidebar.

That was rejected as redundant.

The agreed structure is:

```text
[logo / app name]

Calendar
Timeline
Routines

────────

Settings
```

Possible later addition:

```text
Analytics
```

but only if it earns its place.

The top of each page is not global navigation.

It is a contextual toolbar.

Examples:

```text
Calendar:
Friday, Aug 8   Day / Week / Month   Today   ◀ ▶   Filter
```

```text
Timeline:
Timeline        Aug 8                Search  Filter
```

---

## Why there are no Apps / Websites sidebar items

At one point Apps and Websites were considered as sidebar destinations.

They were removed from the MVP concept.

Reason:

There probably is not enough distinct product value in treating them as top-level destinations.

Apps and websites are better understood as **attributes or filters of activity**.

They should appear through:

- filters,
- detail views,
- drill-downs,
- statistics.

The product should not grow a bloated sidebar just because those dimensions exist.

---

## Why there is no Devices section

Multi-device synchronization is not planned for MVP.

It may become valuable later.

But designing a Devices section before synchronization exists would be speculative UI.

The MVP stays local to one machine.

---

## Categorization discovery

ActivityWatch has a surprisingly interesting categorization system.

It can classify activity into hierarchies such as:

```text
Work
└── Programming
    └── ActivityWatch
```

The system is rule-based rather than AI-based.

This revealed an important principle:

> categories should not permanently overwrite raw events.

Raw history remains raw.

Categorization is a dynamic interpretation layer.

This is useful because the user can change a rule later and historical data can be reorganized.

The project should preserve that idea.

A possible future improvement is to allow rules to inspect richer context:

- app,
- title,
- URL,
- domain,
- file path,
- source.

There was also a thought that categorization is one area where AI **might actually be useful later**, because classification is a relatively constrained problem.

However:

> AI is not part of the MVP.

---

## Frontend technology discussion

The original instinct was Python.

After seeing ActivityWatch running through localhost, a web UI seemed like the obvious implementation path.

But there was a strong concern that a normal web frontend would feel cheap or less like a real desktop application.

Important requirements:

- looks polished,
- feels fast,
- behaves like a normal desktop app,
- can be pinned in the dock/panel,
- does not feel like “open localhost in browser.”

Several options were considered:

- web frontend,
- Electron,
- Tauri,
- Flutter,
- GTK/libadwaita,
- Qt Widgets,
- PySide6 + QML.

The chosen stack is:

```text
Python + PySide6 + Qt Quick/QML
```

Why this fit:

- standalone desktop app,
- good visual ceiling,
- GPU-accelerated Qt Quick rendering,
- custom calendar/timeline layouts,
- smooth scrolling/animation,
- Python remains available for data handling,
- reasonable cross-platform path.

Traditional Qt Widgets were considered less appropriate because the interface is highly custom and visual.

Electron was rejected.

Tauri was acknowledged as capable, but the preference remained for a non-web UI.

---

## Performance philosophy

The app should feel immediate.

The UI should not fetch/process huge raw event ranges synchronously while scrolling.

The preferred data flow is:

```text
ActivityWatch API
      ↓
event ingestion
      ↓
normalization
      ↓
cached timeline model
      ↓
QML rendering
```

The Python layer should provide models and transformed data.

QML should render.

The frontend should not directly draw everything through Python.

---

## ActivityWatch source as reference

There was some ambiguity around the word “fork.”

The intent is not necessarily to keep modifying ActivityWatch’s frontend in place.

The actual goal is:

> have the source available as reference and potentially remake the frontend entirely.

This is useful because ActivityWatch has already solved domain-specific edge cases:

- AFK handling,
- window/browser merging,
- bucket discovery,
- event overlap,
- heartbeat semantics,
- categories,
- query behavior.

The best approach is probably:

- keep ActivityWatch source locally as a reference tree,
- build a clean new frontend project,
- consume the local API,
- study upstream code whenever behavior is unclear.

---

## ActivityWatch license

ActivityWatch uses **MPL-2.0**.

This is useful because it allows studying and modifying the code while keeping obligations mostly at the file level.

The cleanest path for a truly new frontend is still to implement it in new files/repository rather than copying the old frontend wholesale.

---

## Cross-platform thought

ActivityWatch also supports Windows and macOS.

That means the new frontend could eventually become cross-platform without rethinking the whole product.

Potential later picture:

```text
Windows watcher ─┐
macOS watcher ───┤
Linux awatcher ──┤
                 ↓
      ActivityWatch-compatible events
                 ↓
          same frontend
```

But Linux is the first target.

---

## Product identity in one sentence

The strongest distinction that emerged is:

> **ActivityWatch asks “how did you spend your computer time?”  
> This app should ask “what happened during your day?”**

That difference should guide the design.

---

## MVP mindset

The MVP should stay narrow.

The first real milestone only needs to prove:

- ActivityWatch data can be read,
- it can be normalized,
- it can be shown beautifully,
- a calendar/day view feels useful,
- a detailed timeline feels useful,
- the app feels fast and standalone.

Do not get distracted early by:

- AI,
- cloud sync,
- multi-device merging,
- Android,
- complex dashboards,
- full ActivityWatch replacement,
- elaborate analytics.

If Calendar + Timeline already feel excellent, the project has succeeded at its core idea.

---

## Current practical setup at the time this journal was written

Linux environment:

- GNOME Wayland
- ActivityWatch core/UI at `/opt/activitywatch`
- `aw-awatcher` at `~/.local/bin/aw-awatcher`
- GNOME AppIndicator extension installed
- GNOME Focused Window D-Bus extension installed
- ActivityWatch data at `~/.local/share/activitywatch`
- ActivityWatch API live and receiving window events
- browser watcher intended/available for richer web context
- `aw-qt` currently forced through XWayland due to outdated Qt Wayland support

This setup is useful as a working backend prototype.

The new frontend should eventually remove the need to interact with the current ActivityWatch UI for everyday use.
