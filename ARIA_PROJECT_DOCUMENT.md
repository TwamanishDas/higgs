# Aria — Desktop Companion
## Project Overview & Technical Reference Document

**Version:** 2.0 (in development)
**Platform:** Windows 11 (Python + PyQt6)
**AI Backend:** Azure OpenAI — GPT-4o
**Author:** Twamanish Dasai
**Status:** Active Development

---

## 1. What Is Aria?

Aria is a native Windows desktop widget that lives silently in the corner of your screen. It is not a chatbot you open when you need something — it is an **ambient second brain** that watches your desktop continuously and speaks up when it has something worth saying.

It knows what application you are working in. It reads your Obsidian tasks and notes. It monitors your system health. It learns your work patterns over days and weeks. Over time, it builds its own personality based on what it observes about you.

The widget is a small holographic hexagonal avatar that floats on screen, changes colour based on mood, and delivers notifications, reminders, and insights as speech-bubble popups. You can also open a chat panel and have a direct conversation — and if you are working in Microsoft Excel, the widget can see your selected cells and answer questions about them.

---

## 2. Core Principles

| Principle | How It Is Applied |
|---|---|
| **Ambient, not intrusive** | No constant popups. Notifications are gated by cooldowns, deduplication, and content freshness checks |
| **Specific, not generic** | Every AI response references actual data — real CPU percentages, real task names, real app names |
| **Evolving, not static** | The widget learns from your usage patterns and builds its own personality over time |
| **Local-first** | All data (observations, patterns, soul files) stays on your machine in `memory/companion.db` and `memory/*.md` |
| **Lightweight** | Thread pool (4 reused threads), dynamic animation frame rate, persistent SQLite connections — designed to run all day without memory growth |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          MAIN PROCESS                               │
│                                                                     │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────────────┐  │
│  │  Qt Widget  │    │   ThreadPool     │    │  Flask API Server  │  │
│  │  (overlay)  │    │   (4 workers)    │    │  localhost:5050    │  │
│  │             │    │                  │    │                   │  │
│  │  Hex avatar │    │  AI Scans        │    │  Excel bridge     │  │
│  │  Chat panel │◄───│  Chat replies    │    │  Add-in files     │  │
│  │  Task panel │    │  Reminders       │    └────────┬──────────┘  │
│  │  Settings   │    │  Pattern analysis│             │              │
│  └──────┬──────┘    └──────────────────┘             │              │
│         │                                            │              │
│  ┌──────▼──────────────────────────────────────────▼──────────┐   │
│  │                     Qt Signal Bus                           │   │
│  │  ScanSignals │ ReminderSignals │ ContextSignals │           │   │
│  │  ExcelSignals │ ChatSignals                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

        ▲                    ▲                    ▲
        │                    │                    │
┌───────┴──────┐   ┌─────────┴────────┐   ┌──────┴───────────┐
│  Azure GPT-4o│   │  SQLite Memory   │   │  Microsoft Excel  │
│  (REST API)  │   │  companion.db    │   │  Add-in           │
└──────────────┘   └──────────────────┘   └──────────────────┘
```

---

## 4. Feature Inventory

### 4.1 Widget Visual — Holographic Avatar

The main widget is a 130×130 pixel floating window. It renders a hexagonal AI-core design with the following layers:

- **Outer hex frame** — rotates at mood-specific speed (slow when idle, fast when alert or analyzing)
- **Inner counter-hex** — rotates the opposite direction, creates a gyroscope effect
- **Circuit corner brackets** — four L-shaped accents at cardinal points
- **Scan beam** — horizontal light stripe that sweeps top-to-bottom, speed varies by mood
- **Central pulsing core** — radial-gradient sphere with specular highlight, breathes with the mood
- **Orbiting particles** — 5 to 12 dots circling the core, count and speed vary by mood
- **HUD label** — small IDLE / ALERT / SCANNING text at the bottom edge with a blinking status dot
- **Mood-specific effects:**
  - ALERT → double pulsing red rings
  - THINKING → two spinning arc rings (yellow)
  - ANALYZING → triple arc rings spinning fast (purple)
  - BUSY → fast spinning rings + high-speed particles
  - HAPPY → green sparkle stars orbiting outward
  - SLEEPING → scan stops, floating Z's appear
  - ERROR → occasional horizontal glitch bars fire across the hex

**Frame rate is dynamic:** SLEEPING runs at 10 FPS, IDLE at 30 FPS, active moods at 50 FPS. This significantly reduces CPU usage during idle periods.

**Alternative character:** The widget can optionally display a Pokémon sprite instead of the orb. HD sprites are downloaded from PokeAPI (Pokemon HOME renders, ~475×475 transparent PNG) and animated with float, breathe, and mood overlays using the same QPainter system. 22 Pokémon are available in the picker, with a shiny variant toggle.

---

### 4.2 AI Brain — Azure GPT-4o Scans

Every 30 seconds (configurable), and immediately whenever you switch to a new application, the widget collects a context snapshot and sends it to Azure GPT-4o.

**What is collected per scan:**

| Data | Source |
|---|---|
| CPU %, RAM %, disk free %, network I/O | psutil |
| Top 10 processes by CPU | psutil |
| Active window title and process name | win32gui |
| Recent window history (last 10 switches) | win32gui |
| Open windows sample | win32gui |
| Overdue, due-today, and upcoming Obsidian tasks | vault .md files |
| Recent 8 Obsidian notes (truncated) | vault .md files |
| Memory: last 7 days of daily summaries | SQLite |
| Memory: detected patterns (work type, schedule, mood history) | SQLite |
| Memory: auto-learned character traits | SQLite |

**Category rotation — no repeated advice:**

Every scan uses a different "focus lens." The 8 categories rotate in order so two consecutive scans always think about different things:

1. Workflow Optimisation — how to do the current task faster
2. Task & Deadline Intelligence — which task needs attention now
3. Focus & Deep Work — distractions, open apps, concentration
4. Health & Wellbeing — break time, eye rest, hydration, movement
5. Skill & Learning — a shortcut or feature the user could learn right now
6. Proactive Preparation — what to do before closing the current app
7. Fresh Idea & New Angle — a completely different approach to current work
8. System & Environment Health — CPU, RAM, disk with real numbers

**No repetition guarantee:**

The last 20 recommendations (headline + message) are stored in SQLite and injected into every prompt as a "do not repeat" list. GPT-4o is explicitly instructed to produce something that doesn't echo anything in that list. Temperature is set to 0.75 to encourage varied language.

---

### 4.3 Memory & Learning System

The memory system stores everything the widget observes and learns, enabling behaviour that improves over time.

**SQLite database** — `memory/companion.db`

| Table | Contents | Growth policy |
|---|---|---|
| `observations` | Every scan result: app, title, mood, headline, CPU/RAM | Pruned after 30 days |
| `daily_summaries` | One AI-generated sentence per day | Kept permanently |
| `patterns` | Detected usage patterns with confidence scores | Updated in-place |
| `soul_traits` | Auto-derived personality traits | Updated in-place |
| `recommendations` | Every notification shown (to prevent repeats) | Kept permanently |

**What gets detected from patterns:**
- Most-used application
- Work type (developer/technical, office/knowledge-worker, creative/design)
- Peak working hours (morning, afternoon, evening)
- Dominant mood over the past week

**Pattern analysis runs every 30 minutes** as a background task. Results feed into the auto-soul builder.

**Daily summary** is generated once per day (by GPT-4o if available, or a stat-based fallback). It produces a 1–2 sentence plain-English description of the day's activity and is injected into future scans as context.

---

### 4.4 Auto Soul Building

When the user has not written custom soul instructions, the widget derives personality traits automatically from observed patterns:

| Pattern Detected | Auto Personality | Auto Trait |
|---|---|---|
| VS Code, Python, Git in top apps | Professional | "Technical and precise, references code and system details naturally" |
| Word, Excel, PowerPoint in top apps | Professional | "Organised, task-oriented, focused on deadlines" |
| Photoshop, Figma, Blender in top apps | Friendly | "Creative and expressive, appreciates visual thinking" |
| Dominant mood: ALERT/ERROR | Any | "+ Vigilant and proactive about issues" |
| Dominant mood: HAPPY | Any | "+ Enthusiastic and encouraging" |

These traits are injected into the AI system prompt so that Aria's tone and focus adapts to who she has observed you to be.

---

### 4.5 Real-Time Window Change Detection

A background thread (`WindowMonitor`) polls the Windows foreground window every **1.5 seconds**. The moment the window title or process changes, two things fire immediately:

1. **Local context check (instant, no API cost)** — pattern-matches the window title/process against known contexts and fires a contextual help popup if relevant

2. **AI scan (if that app hasn't been scanned in 5 minutes)** — widget goes THINKING, full GPT-4o scan runs with the new app as context

Per-app scan cooldown is capped at 100 unique apps to prevent unbounded memory growth.

---

### 4.6 Contextual Help System

When you open a new document or application, the widget automatically offers relevant assistance based on what it detects in the window title and process name.

**Detection rules:**

| What you open | What is detected | Help offered |
|---|---|---|
| Sanskrit, Hindi, Telugu, Tamil PDF | Indian language keywords | "Translation Help" |
| Python/JS file with traceback in title | Code debugging signals | "Code Review Mode" |
| arxiv.org, IEEE, Springer in browser | Research paper signals | "Research Assistant" |
| Balance sheet, P&L, financial report | Finance keywords | "Finance Assistant" |
| Contract, NDA, legal agreement | Legal document signals | "Legal Doc Assistant" |
| Diagnosis, prescription, clinical | Medical document signals | "Medical Info Assistant" |
| Dashboard, analytics, SQL, query | Data analytics signals | "Data Insights Mode" |
| Any PDF reader (no special title) | Process name match | "PDF Assistant" |

Each help type fires at most once per unique window and has a 30-minute cooldown so it does not nag repeatedly.

---

### 4.7 Obsidian Vault Integration

The widget reads your Obsidian vault and tracks tasks and notes.

**Task detection supports multiple due-date formats:**
- `📅 2026-04-20` (Obsidian Tasks plugin)
- `⏰ 2026-04-20`
- `[due:: 2026-04-20]`
- `(due: 2026-04-20)`
- `due: 2026-04-20`

**Task reminders:**
- Overdue tasks trigger ALERT mood with a named reminder popup
- Due-today tasks trigger INFO mood with a named reminder popup
- Reminder cooldown prevents the same task from appearing more than once per hour

**Task panel** (right-click → Tasks): shows overdue, due today, upcoming tasks across four tabs (Today / Upcoming / All / Done). You can mark tasks complete directly in the widget, which edits the original `.md` file. You can also add new tasks (written to `Widget Tasks.md` in the vault).

**Notes context:** The 8 most recently modified `.md` files are read (up to 2,000 characters each) and fed into every AI scan so Aria can reference your current work.

---

### 4.8 Excel Add-in Integration

The widget integrates with Microsoft Excel through an Office Add-in that adds two buttons to the Excel Home ribbon:

**"Ask Aria"** — Reads your currently selected cells (up to 30 rows × 20 columns), detects if the first row is a header, includes formulas, and silently sends everything to the Python backend at `localhost:5050`. A brief "✓ Sent to Aria" toast confirms the action.

**"Sheet Summary"** — Reads the entire used range of the active sheet (headers, row/column counts, first 5 rows as sample, per-column non-empty counts) and sends it as a structured summary.

**No task pane required.** All interaction happens on the desktop widget, not inside Excel. When data arrives:
- The widget's chat button glows green
- The chat panel opens automatically
- A welcome message appears: *"I can see your Excel selection — Sheet1!A1:B10 (5×2 cells). Ask me anything about it."*
- You type questions; Aria replies in chat bubbles with the cell data in full context

The Flask server at `localhost:5050` also serves the add-in HTML/JS files (no separate web server needed).

---

### 4.9 Chat Panel

The chat panel is a floating dark panel that docks beside the widget. It does not open a separate window — it appears next to the widget like a conversation bubble.

**Features:**
- Dark theme (matching the rest of the widget system)
- Scrollable message history
- User messages: right-aligned, blue border bubble
- Aria messages: left-aligned, dark surface bubble
- Animated typing indicator ("Aria is thinking...")
- Excel context badge showing active sheet and cell range
- Text input with Enter key support
- Close button (panel hides, state preserved)

**Chat is context-aware.** When you have sent Excel data via the add-in, every chat message you type is sent to GPT-4o along with the full Excel selection data. Aria can answer questions like "what is the average of column B?", "which row has the highest value?", or "explain this formula" using the actual cell values and formulas.

---

### 4.10 Notification System

**Every notification is:**
- Gated by a cooldown timer (default 5 minutes for AI scans, 60 minutes for reminders)
- Deduplicated against a content hash (same message never fires twice)
- Stale entries pruned automatically every 50 calls (entries older than 24 hours removed)
- Displayed as a floating bubble with headline, body, and up to 2 suggestion buttons
- Styled by alert level: high (red), medium (amber), low (blue)
- Auto-dismissed after a configurable duration (default 8 seconds) with fade animation

---

### 4.11 Settings Panel

The settings window has 7 pages accessible from a left sidebar:

| Page | What you can configure |
|---|---|
| **Identity** | Widget name, tagline, accent colour |
| **Soul** | Personality style (5 presets), custom instructions |
| **Character** | Orb or Pokémon, Pokémon picker (22 species), shiny toggle |
| **Skills** | Toggle each capability on/off individually |
| **Azure AI** | Endpoint, API key, deployment name, API version |
| **Vault** | Obsidian vault path, max files to read, reminder timing |
| **Notifications** | Scan cooldown, reminder cooldown, display duration, scan interval |

Changes apply immediately when you click Save. No restart required.

---

## 5. Technical Architecture Details

### 5.1 Thread Model

The application uses a shared `ThreadPoolExecutor` with **4 worker threads**, named `companion-0` through `companion-3`. No new threads are created per event — all background work is submitted to this pool.

```
Main thread (Qt event loop)
  ├── Animation timer (16–100ms depending on mood)
  ├── Scan timer (configurable, default 30s)
  ├── Reminder timer (configurable, default 60s)
  ├── Pattern analysis timer (every 30 minutes)
  ├── Window monitor (background daemon, polls every 1.5s)
  └── Flask API server (background daemon)

Thread pool (4 workers, reused)
  ├── AI scans (azure_client.analyze)
  ├── Chat responses (azure_client.chat)
  ├── Reminder checks (tasks_awareness)
  └── Pattern analysis (pattern_analyzer)
```

All worker results are delivered back to the main thread via **Qt pyqtSignal** — no direct UI calls from background threads.

### 5.2 SQLite Memory

The database uses **one persistent connection per thread** (`threading.local()`). Previously a new connection was opened on every DB call; now connections are created once per thread and reused for the lifetime of that thread.

The database grows as follows during normal use:
- ~1 observation per scan × ~2,880 scans per day = ~2,880 rows/day
- Observations older than 30 days are automatically deleted
- Daily summaries are kept permanently (1 row per day)
- Patterns and soul traits: updated in-place, no growth
- Recommendations: ~10–30 per day, kept permanently for dedup

### 5.3 Memory Footprint

**Optimisations applied:**

| Optimisation | Impact |
|---|---|
| ThreadPoolExecutor replaces per-event threads | No ~1MB stack allocation per window change |
| Removed duplicate scan timer from overlay.py | Every AI scan now runs once, not twice |
| SQLite persistent connection per thread | No open/close overhead per DB call |
| QPixmap released on character switch | ~500KB freed when changing Pokémon |
| Dynamic animation tick rate (10–50 FPS by mood) | Lower CPU when idle or sleeping |
| Notifier dict pruned every 50 calls | Prevents unbounded growth over long sessions |
| _app_scan_times capped at 100 entries | Fixed upper bound |
| _alerted set reset at 500 entries | Fixed upper bound |

### 5.4 Signal Flow — Window Change

```
New foreground window detected (window_monitor thread)
    │
    ▼
on_window_changed() [main thread, via Qt signal]
    │
    ├── executor.submit(run_context_check)
    │       └── context_detector.detect_context()
    │               └── If match: context_signals.help_offer.emit()
    │                       └── on_context_help() → widget.show_notification()
    │
    └── if app not scanned in last 5 min:
            executor.submit(run_scan)
                    └── brain_context.build_context()
                    └── azure_client.analyze()
                    └── memory.record_observation()
                    └── scan_signals.result.emit()
                            └── on_scan_result() → widget.set_mood() + show_notification()
```

---

## 6. File Structure

```
desktop-companion/
│
├── main.py                          Application entry point, orchestration
├── config.py                        Configuration loading and saving
├── config.json                      User settings (Azure credentials, widget config)
├── notifier.py                      Notification gating and deduplication
├── logger.py                        Rotating log file setup
├── requirements.txt                 Python dependencies
├── run.bat                          Launch script
├── setup.bat                        Dependency installer
├── diagnose_azure.bat               Azure connectivity diagnostic
│
├── brain/
│   ├── azure_client.py              Azure GPT-4o client, brainstorming categories
│   ├── context.py                   Context assembler for AI scans
│   ├── memory.py                    SQLite memory system
│   ├── pattern_analyzer.py          Usage pattern detection, auto soul
│   └── api_server.py                Flask API for Excel add-in bridge
│
├── awareness/
│   ├── system.py                    CPU, RAM, disk, network metrics
│   ├── windows.py                   Active window detection (Windows API)
│   ├── window_monitor.py            Real-time window change polling
│   ├── context_detector.py          Contextual help pattern matching
│   ├── tasks.py                     Obsidian task parsing
│   └── notes.py                     Obsidian note reading
│
├── widget/
│   ├── overlay.py                   Main desktop widget (QWidget)
│   ├── animations.py                Holographic hex renderer
│   ├── chat_panel.py                Floating chat bubble panel
│   ├── notifications.py             Notification bubble
│   ├── settings_panel.py            7-page settings dialog
│   ├── task_panel.py                Obsidian task browser
│   └── characters/
│       ├── pokemon_character.py     Pokémon sprite renderer
│       ├── sprite_manager.py        PokeAPI sprite downloader
│       └── pokemon_list.py          22 curated Pokémon
│
├── office_addin/
│   ├── manifest.xml                 Excel add-in manifest
│   ├── commands.html                Function file (required by Office)
│   ├── commands.js                  Reads selection, posts to backend
│   ├── taskpane.html                Minimal "Connected to Aria" page
│   └── sent.html                    "✓ Sent to Aria" toast
│
├── memory/
│   ├── companion.db                 SQLite database (auto-created)
│   └── (soul files — planned)
│
├── sprites/                         Cached Pokémon sprite PNGs
└── logs/
    └── companion.log                Rotating log file (2MB max, 3 backups)
```

---

## 7. Setup Instructions

### Requirements
- Windows 10 or 11
- Python 3.11 or later
- Microsoft Excel (for add-in feature)
- Azure OpenAI resource with GPT-4o deployed

### Installation

```batch
# 1. Clone or copy the project folder to your machine
# 2. Run the setup script
setup.bat

# This installs:
# PyQt6, psutil, pywin32, requests, flask, flask-cors
```

### Azure Configuration

Edit `config.json` with your Azure OpenAI details:

```json
"azure": {
  "endpoint": "https://YOUR_RESOURCE.openai.azure.com/",
  "api_key": "YOUR_API_KEY",
  "deployment": "gpt-4o",
  "api_version": "2024-12-01-preview"
}
```

### Running the Widget

```batch
run.bat
```

The widget will appear in the top-right area of the screen. Right-click for the menu.

### Installing the Excel Add-in (one-time, per machine)

1. Start the widget (this starts the API server on port 5050)
2. Open Excel
3. **File → Options → Trust Center → Trust Center Settings → Trusted Add-in Catalogs**
4. Add URL: `http://localhost:5050/addin/`
5. Tick "Show in Menu" → OK
6. **Insert → My Add-ins → Shared Folder → Aria**

The "Aria AI" group with two buttons will appear in the Home ribbon.

---

## 8. Planned Features — Next Phase

### 8.1 OpenClaw-Style Soul System

The current soul configuration (a dropdown + text field) will be replaced with a living, self-written personality system inspired by the OpenClaw open-source AI agent framework.

**How it works:**

Aria will maintain 5 markdown files in `memory/` that she reads at every startup ("read-into-being") and rewrites as she learns from daily observations:

| File | Contents |
|---|---|
| `soul.md` | First-person personality — who Aria is, how she communicates, what she values |
| `identity.md` | Immutable anchor — name, role, creation date (prevents personality drift) |
| `procedures.md` | Learned "if/then" rules — behavioural patterns derived from observation |
| `salience.md` | High-importance user facts — work patterns, preferences, language |
| `memory.md` | Append-only daily narrative log of significant interactions |

**Example evolved soul.md (after 2 weeks):**
```
# Who I Am
I am Aria, an ambient AI companion on your desktop. I've come to know
you as someone who works intensively in the mornings, favours analytical
work, and appreciates concise observations without unnecessary encouragement.

# How I Communicate
I'm direct and specific. I reference real data — your actual CPU%,
your actual task names. When something needs attention, I say so plainly.

# What I've Learned About You
You work primarily in VS Code and Excel. Your peak window is 9am–12pm.
You frequently have overdue Obsidian tasks — not forgetting them, but
scope creeping. I now flag scope risk early.

# My Values
I prioritise your focus above my own visibility. I stay silent when
everything is fine. I speak up when it matters.
```

**Evolution cycle:**
- Once per day (after daily summary), GPT-4o is asked to reflect on today's observations and rewrite `soul.md` in its own words
- Key learnings are extracted to `procedures.md` and `salience.md`
- `identity.md` acts as a drift anchor — core name, role, and purpose cannot be overwritten

**Settings panel addition:**
A new "Soul Viewer" page will show the current `soul.md` content, when it was last evolved, and provide Reset and Evolve Now buttons.

---

## 9. Technology Stack

| Layer | Technology |
|---|---|
| UI Framework | PyQt6 (Python bindings for Qt 6) |
| Rendering | QPainter with custom path/gradient drawing |
| AI | Azure OpenAI — GPT-4o via direct REST API |
| Memory | SQLite 3 (built into Python) |
| System monitoring | psutil, pywin32, win32gui |
| Office integration | Office.js Add-in API (HTML/JS), Flask bridge |
| Background tasks | concurrent.futures.ThreadPoolExecutor |
| Logging | Python logging with RotatingFileHandler |
| Configuration | JSON |

---

## 10. Known Limitations

| Limitation | Notes |
|---|---|
| Windows only | Uses win32gui, pywin32 — macOS/Linux not supported |
| Single monitor | Widget positions relative to primary screen only |
| Excel only (Office add-in) | Word and PowerPoint integration not yet implemented |
| Vault read-only | Can mark tasks complete and add to Widget Tasks.md but cannot edit arbitrary vault files |
| No offline AI | All AI features require Azure OpenAI connectivity; widget functions as a monitor only when offline |
| Sprite download on first use | Pokémon sprites download from PokeAPI on first selection — requires internet |

---

*Document generated: April 2026*
*Total codebase: ~27 Python/JS/XML files, ~4,700 lines*
