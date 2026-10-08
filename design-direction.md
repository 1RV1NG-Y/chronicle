# Chronicle — current design direction

Updated October 4, 2026. This records the user's choices for the redesign and takes precedence over conflicting presentation requirements in the original spec and journal.

## Confirmed preferences

- The main day view opens with **latest activity first**.
- Short switches are **grouped visually**, with every activity available on expansion.
- Use **neutral dark surfaces, restrained colors, and compact spacing**.

## First redesign pass

The Day page combines a duration-proportional overview of the full day with a readable, latest-first activity feed. Feed cards have readable heights; their heights do not encode duration. The overview does encode time, and clicking a recorded interval opens the corresponding group.

Groups open an inspector that lists exact activities, latest first. Each entry preserves its app, title, website, timestamp, duration, and source data. Same-app/site activity can form a session; brief mixed-app switches have an explicit “Quick switches” label. Grouping never assigns one application's activity to another.

The Timeline page remains an exact, searchable ledger in chronological order. Browser titles are visible without requiring a search. Day, Timeline, and Settings are the working navigation; Routines is deferred until it can provide real value.

## Data guarantees

- Preserve window-title and URL changes in the precise ledger.
- Preserve even brief app switches; simplification happens only in the day projection.
- Coalesce only matching, contiguous context. Missing recordings remain gaps.
- Keep idle boundaries intact.
- Every grouped record retains its original records for inspection.
- Live data comes from ActivityWatch. Sample data is available only through the explicit `--demo` option and is visibly labeled.

## Implementation and validation

The existing local API client, asynchronous controller, and Qt model architecture are retained. Day feed and inspector lists instantiate visible delegates. The day overview is drawn on a single canvas. A runtime import issue in the controller's default-client/error paths is also fixed.

Unit tests cover title and URL preservation, short switches, grouping, gaps, midnight boundaries, latest-first presentation, and recoverable connection failures. `scripts/preview.py` renders the real QML with sample data and exercises group selection, expansion, narrow windows, keyboard dismissal, search, date navigation, and empty/error states.

## Still outside this pass

Week/month views, routines, categorization controls, cross-day caching, native application icons, and packaging polish. These should build on the revised day experience after visual feedback.
