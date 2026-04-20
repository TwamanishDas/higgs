# Higgs — Ambient AI Desktop Companion

> *An always-on, always-learning AI that lives on your desktop.*

Higgs is a lightweight desktop widget powered by **Azure OpenAI (GPT-4o)** that watches your screen activity in real time, proactively surfaces insights, schedules events through natural conversation, and evolves its personality as it learns how you work.

It does not open a browser tab. It does not require a keyboard shortcut. It sits silently at the edge of your screen and speaks up only when it matters.

---

## ✨ Key Features

### 🧠 Proactive AI Brain
- Performs live scans of your system every 30 seconds (CPU, RAM, active window, open apps)
- Rotates across **8 distinct assistance categories** per scan (workflow optimisation, focus, health, skill learning, proactive prep, system health, creative ideas, task intelligence) — so every notification brings a fresh angle
- Injects your last 20 recommendations into each prompt so the AI **never repeats itself**

### 🗓 NLP Calendar Scheduling
Type naturally in the chat — no forms, no clicks:
```
You:   schedule a call for Monday to brainstorm the app
Higgs: What's the main outcome you want, and how long should we block out?
You:   map out v3 features, about 1 hour, just me
Higgs: Done! I've scheduled "App Feature Brainstorm" for Monday 28 Apr at 10:00 AM.
       I'll remind you 15 minutes before with your agenda.

[At 9:45 AM] → 15-minute desktop warning notification
[At 10:00 AM] → Chat panel opens automatically with AI-generated agenda + prep checklist
```

### 🧬 Evolving Soul (OpenClaw Architecture)
Higgs builds and maintains **5 living markdown files** that define its identity:

| File | Purpose |
|------|---------|
| `memory/soul.md` | First-person personality — rewritten daily by GPT-4o |
| `memory/identity.md` | Immutable anchor — name, role, core constraints |
| `memory/procedures.md` | Learned "if X → do Y" behaviour rules |
| `memory/salience.md` | High-importance facts about you |
| `memory/memory.md` | Append-only dated narrative log |

Every AI prompt is prefixed with this soul context so Higgs always knows who it is and who you are — becoming more specific and useful over time without any manual configuration.

### 💬 Floating Chat Panel
- Click the **💬** button on the widget to open a sleek floating chat panel
- Ask anything: questions, analysis, ideas, scheduling
- Excel context-aware — when you send a selection from Excel, Higgs can analyse your data directly in the chat

### 📊 Excel Add-in Bridge
- Ribbon button in Excel sends your current selection or sheet summary to Higgs
- All interaction stays on your desktop — no task pane, no browser tab
- Higgs can analyse formulas, explain data patterns, and suggest next steps

### 💡 Contextual Help Engine
Detects what you are working on and offers targeted help:
- **Code files / tracebacks** → offer to explain the error
- **PDF research** → research assistance
- **Financial documents** → formula and analysis suggestions
- **Indian language documents** → translation support
- **Medical / legal documents** → summary and clarification

### 🧠 Memory & Pattern Learning
- Stores every observation in SQLite (`memory/companion.db`)
- Detects your work patterns: peak hours, primary tools, dominant moods
- Generates a natural-language daily summary
- Auto-builds personality traits from observed behaviour

### 🎮 Character System
- Default animated **holographic orb** with mood-reactive visual states
- Optional **Pokémon sprite** mode — choose any Gen 1–4 Pokémon, normal or shiny

---

## 🖥 Mood States

| Mood | Visual | Meaning |
|------|--------|---------|
| `IDLE` | Calm blue glow | Normal monitoring |
| `THINKING` | Rotating scan ring | AI call in progress |
| `ANALYZING` | Dual spinner | Deep analysis |
| `ALERT` | Red pulse | Overdue task / high CPU |
| `WARNING` | Orange ring | Something needs attention |
| `HAPPY` | Green sparks | Positive event |
| `INFO` | Cyan pulse | Non-urgent information |
| `BUSY` | Spinner overlay | Background task running |
| `SLEEPING` | Dimmed / slow | Sleep mode |
| `ERROR` | Glitch bars | Connection or config issue |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | PyQt6 (frameless, translucent, always-on-top) |
| AI | Azure OpenAI GPT-4o (REST API) |
| Memory | SQLite via `threading.local()` persistent connections |
| Threading | `concurrent.futures.ThreadPoolExecutor` (4 workers) |
| Excel bridge | Flask REST API (`localhost:5050`) + Office.js add-in |
| Soul system | Markdown files + GPT-4o reflection (OpenClaw pattern) |
| Scheduling | NLP two-turn conversation → SQLite calendar events |
| Window monitoring | Win32 API polling thread → Qt signals |

---

## 📁 Project Structure

```
higgs/
├── main.py                     # Entry point — wires everything together
├── config.py                   # Config loading with defaults
├── config.example.json         # Copy this to config.json and fill in your keys
├── requirements.txt
│
├── brain/
│   ├── azure_client.py         # GPT-4o integration (scan + chat + scheduling)
│   ├── context.py              # System context builder (CPU, RAM, windows, notes)
│   ├── memory.py               # SQLite observation store
│   ├── pattern_analyzer.py     # Usage pattern detection + daily summaries
│   ├── soul_builder.py         # OpenClaw soul system (seed, load, evolve, reset)
│   ├── scheduler.py            # NLP calendar — event DB + notification builders
│   └── api_server.py           # Flask bridge for Excel add-in
│
├── awareness/
│   ├── windows.py              # Active window detection (Win32)
│   ├── window_monitor.py       # Background window change monitor
│   ├── system.py               # CPU, RAM, disk, process monitoring
│   ├── notes.py                # Obsidian vault reader
│   ├── apps.py                 # Installed app awareness
│   └── context_detector.py     # Rule-based contextual help detection
│
├── widget/
│   ├── overlay.py              # Main QWidget — draggable, always-on-top
│   ├── animations.py           # Holographic orb renderer (QPainter)
│   ├── chat_panel.py           # Floating chat panel with bubble UI
│   ├── notifications.py        # Notification bubble widget
│   ├── settings_panel.py       # Multi-page settings UI
│   └── characters/             # Pokémon sprite character system
│
├── office_addin/
│   ├── manifest.xml            # Office Add-in manifest
│   ├── commands.js             # Excel ribbon button handlers (Office.js)
│   └── commands.html           # Function file for ExecuteFunction actions
│
└── memory/                     # Auto-created at runtime
    ├── companion.db            # SQLite — observations, patterns, recommendations, calendar
    ├── soul.md                 # Living personality document (auto-evolved daily)
    ├── identity.md             # Immutable identity anchor
    ├── procedures.md           # Learned behavioural rules
    ├── salience.md             # Key user facts
    └── memory.md               # Narrative activity log
```

---

## ⚡ Quick Start

### Prerequisites
- Windows 10 / 11
- Python 3.11+
- Azure OpenAI resource with a GPT-4o deployment

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/higgs.git
cd higgs
pip install -r requirements.txt
```

### 2. Configure

```bash
copy config.example.json config.json
```

Open `config.json` and fill in:
```json
{
  "azure": {
    "endpoint": "https://YOUR-RESOURCE.openai.azure.com/",
    "api_key":  "YOUR_AZURE_OPENAI_API_KEY",
    "deployment": "gpt-4o"
  },
  "identity": {
    "name": "Higgs"
  }
}
```

### 3. Run

```bash
python main.py
```

Or double-click `run.bat`.

Higgs appears at the top-right of your screen. Right-click for options. Double-click to trigger an immediate AI scan.

### 4. Optional — Excel Add-in

1. Open Excel → **Insert** → **Add-ins** → **Upload My Add-in**
2. Select `office_addin/manifest.xml`
3. A **Higgs** tab appears in the ribbon with two buttons:
   - **Send Selection** — sends your selected cells to Higgs
   - **Send Sheet Summary** — sends headers + sample rows

> **Note:** Higgs must be running before you use the add-in (it hosts a local server on port 5050).

---

## 💬 Chat Examples

| What you type | What Higgs does |
|---------------|-----------------|
| `schedule a meeting Friday at 2pm to review the budget` | Asks 2 probe questions, books it, delivers AI agenda at start time |
| `what's in my Excel selection?` | Analyses the data you sent from Excel |
| `explain this traceback` + paste error | Explains the Python/JS error in context |
| `what should I focus on right now?` | Reviews your system state and suggests the highest-leverage action |
| `remind me to take a break every 90 minutes` | Stored as a preference, injected into future prompts |

---

## ⚙ Settings

Right-click the widget → **Settings** to open the settings panel:

| Page | What you configure |
|------|--------------------|
| **Identity** | Widget name, tagline, accent colour |
| **Soul** | Personality style, custom instructions, soul viewer (evolve / reset) |
| **Character** | Orb or Pokémon sprite, Pokémon chooser |
| **Skills** | Toggle each capability on/off |
| **Azure AI** | Endpoint, API key, deployment, API version |
| **Vault** | Obsidian vault path for notes context |
| **Notifications** | Cooldowns, scan interval, display duration |

---

## 🔒 Security Notes

- `config.json` is listed in `.gitignore` and **must never be committed** — it contains your Azure API key.
- All AI calls go directly from your machine to Azure OpenAI. No data passes through any third-party server.
- The local Flask server (port 5050) binds to `127.0.0.1` only and is not accessible from the network.
- The `memory/` folder contains your personal activity data. It is also excluded from git.

---

## 🗺 Roadmap

- [ ] Voice input / output (Whisper + TTS)
- [ ] Google Calendar / Outlook sync for NLP-scheduled events
- [ ] Multi-monitor awareness
- [ ] Word and PowerPoint add-ins
- [ ] Mobile companion app (companion.db sync)
- [ ] Plugin system for custom skills

---

## 📄 License

MIT License — see `LICENSE` for details.

---

*Built with Python, PyQt6, and Azure OpenAI.*
*The soul system is inspired by the [OpenClaw](https://github.com/openclaw) read-into-being architecture.*
