# Graph Report - .  (2026-04-20)

## Corpus Check
- Corpus is ~29,515 words - fits in a single context window. You may not need a graph.

## Summary
- 468 nodes · 898 edges · 25 communities detected
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 154 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Widget Animation & Window Tracking|Widget Animation & Window Tracking]]
- [[_COMMUNITY_Office Add-in & API Bridge|Office Add-in & API Bridge]]
- [[_COMMUNITY_Qt UI Components|Qt UI Components]]
- [[_COMMUNITY_AI Chat & Analysis Engine|AI Chat & Analysis Engine]]
- [[_COMMUNITY_Widget Rendering & Drawing|Widget Rendering & Drawing]]
- [[_COMMUNITY_Calendar Scheduling|Calendar Scheduling]]
- [[_COMMUNITY_Soul Evolution System|Soul Evolution System]]
- [[_COMMUNITY_Chat Panel UI|Chat Panel UI]]
- [[_COMMUNITY_Context Awareness Layer|Context Awareness Layer]]
- [[_COMMUNITY_Browser Context Reading|Browser Context Reading]]
- [[_COMMUNITY_Obsidian Task Integration|Obsidian Task Integration]]
- [[_COMMUNITY_Pokemon Sprite Loading|Pokemon Sprite Loading]]
- [[_COMMUNITY_Azure Diagnostics Tool|Azure Diagnostics Tool]]
- [[_COMMUNITY_Office COM Reader|Office COM Reader]]
- [[_COMMUNITY_Flask API Server Setup|Flask API Server Setup]]
- [[_COMMUNITY_Notification System|Notification System]]
- [[_COMMUNITY_Project Documentation|Project Documentation]]
- [[_COMMUNITY_Context Detection|Context Detection]]
- [[_COMMUNITY_Excel Add-in JS Functions|Excel Add-in JS Functions]]
- [[_COMMUNITY_Package Init Files|Package Init Files]]
- [[_COMMUNITY_Package Init Files|Package Init Files]]
- [[_COMMUNITY_Build Scripts|Build Scripts]]
- [[_COMMUNITY_Package Init Files|Package Init Files]]
- [[_COMMUNITY_Pokemon Data|Pokemon Data]]
- [[_COMMUNITY_Package Init Files|Package Init Files]]

## God Nodes (most connected - your core abstractions)
1. `DesktopWidget` - 42 edges
2. `SettingsPanel` - 29 edges
3. `ChatPanel` - 20 edges
4. `WindowMonitor` - 19 edges
5. `main()` - 14 edges
6. `_conn()` - 14 edges
7. `_col()` - 14 edges
8. `TaskPanel` - 14 edges
9. `build_context()` - 13 edges
10. `azure_client.py â€” GPT-4o Scan/Chat/Schedule` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Call from main thread after sprites are downloaded.` --uses--> `Mood`  [INFERRED]
  widget\characters\pokemon_character.py → widget\animations.py
- `main()` --calls--> `setup()`  [INFERRED]
  main.py → logger.py
- `run_scan()` --calls--> `analyze()`  [INFERRED]
  main.py → brain\azure_client.py
- `run_scan()` --calls--> `record_observation()`  [INFERRED]
  main.py → brain\memory.py
- `run_context_check()` --calls--> `detect_context()`  [INFERRED]
  main.py → awareness\context_detector.py

## Hyperedges (group relationships)
- **AI Scan Cycle Pipeline** — concept_awareness_layer, concept_context_py, concept_soul_builder_py, concept_azure_client_py, concept_gpt4o, concept_memory_py, concept_qt_signals, concept_overlay_py [EXTRACTED 1.00]
- **Widget UI Components** — concept_overlay_py, concept_chat_panel_py, concept_settings_panel_py, concept_notifications_py, concept_pokemon_character_py [EXTRACTED 1.00]
- **Excel Add-in File Components** — addin_commands_html, addin_sent_html, addin_taskpane_html, addin_commands_js, concept_manifest_xml [EXTRACTED 1.00]
- **Soul Evolution Daily Cycle** — concept_companion_db, concept_pattern_analyzer_py, concept_soul_builder_py, concept_gpt4o, concept_soul_files [EXTRACTED 1.00]
- **ThreadPoolExecutor Background Tasks** — concept_thread_pool, concept_azure_client_py, concept_context_detector_py, concept_tasks_py, concept_pattern_analyzer_py [EXTRACTED 1.00]
- **Python Dependency Stack** — requirements_txt, concept_pyqt6, concept_psutil, concept_pywin32, concept_requests, concept_flask, concept_flask_cors, concept_websocket_client [EXTRACTED 1.00]

## Communities

### Community 0 - "Widget Animation & Window Tracking"
Cohesion: 0.05
Nodes (32): AnimationState, Position the panel beside the main widget and show it., setup(), ChatSignals, ContextSignals, ExcelSignals, _init_azure(), main() (+24 more)

### Community 1 - "Office Add-in & API Bridge"
Cohesion: 0.05
Nodes (63): Office Add-in Commands HTML (Function File), commands.js â€” Excel Ribbon Button Handlers (Office.js), Office Add-in Sent Confirmation Page, Office Add-in Task Pane Page, Higgs Architecture Diagram, api_server.py â€” Flask REST Bridge (localhost:5050), apps.py â€” Installed App List, Awareness Layer (awareness/) (+55 more)

### Community 2 - "Qt UI Components"
Cohesion: 0.12
Nodes (14): QDialog, QFrame, QLabel, QPushButton, QWidget, _divider(), _field_row(), _hint() (+6 more)

### Community 3 - "AI Chat & Analysis Engine"
Cohesion: 0.08
Nodes (42): analyze(), _build_system_prompt(), chat(), _fallback(), finalize_schedule_chat(), _next_category(), Azure OpenAI client with brainstorming prompt engine. - Rotates through 8 assist, Conversational chat — returns plain text (not JSON).     Incorporates Excel sele (+34 more)

### Community 4 - "Widget Rendering & Drawing"
Cohesion: 0.11
Nodes (27): _col(), _draw_alert_pulse(), _draw_circuit_corners(), _draw_core(), _draw_data_particles(), _draw_error_glitch(), _draw_happy_sparks(), _draw_hex_frame() (+19 more)

### Community 5 - "Calendar Scheduling"
Cohesion: 0.12
Nodes (24): run_scheduler_check(), build_15min_notification(), build_start_chat_message(), build_start_notification(), _conn(), delete_event(), _fmt_dt(), get_all_events() (+16 more)

### Community 6 - "Soul Evolution System"
Cohesion: 0.13
Nodes (21): Load current soul data into the viewer labels., Wipe soul files and refresh the viewer., append_memory(), evolve(), get_soul_summary(), is_seeded(), load_all(), OpenClaw-style soul system — Aria's evolving identity.  Five anchor files live i (+13 more)

### Community 7 - "Chat Panel UI"
Cohesion: 0.15
Nodes (5): _Bubble, ChatPanel, Floating chat panel — docks beside the widget. Shows conversation bubbles, Excel, Floating frameless panel that docks next to the main widget.     Emits `message_, _TypingIndicator

### Community 8 - "Context Awareness Layer"
Cohesion: 0.18
Nodes (13): get_installed_apps(), build_context(), run_scan(), build_notes_context(), get_daily_note(), get_recent_files(), _parse_frontmatter(), VaultFile (+5 more)

### Community 9 - "Browser Context Reading"
Cohesion: 0.16
Nodes (16): get_active_tab(), _get_cached(), get_chrome_launch_command(), get_edge_launch_command(), get_page_text(), _is_cached(), is_debug_port_open(), awareness/browser_reader.py Reads the active browser tab (URL, title, and option (+8 more)

### Community 10 - "Obsidian Task Integration"
Cohesion: 0.18
Nodes (10): append_task_to_vault(), build_tasks_context(), _clean_title(), get_due_today(), get_overdue(), get_upcoming(), mark_complete_in_file(), _parse_due() (+2 more)

### Community 11 - "Pokemon Sprite Loading"
Cohesion: 0.18
Nodes (10): Call from main thread after sprites are downloaded., download(), ensure_pokemon(), is_cached(), Downloads and caches Pokemon HOME HD sprites from PokeAPI's GitHub sprite repo., Download front and shiny variants. Returns dict of variant -> local path., sprite_path(), load_config() (+2 more)

### Community 12 - "Azure Diagnostics Tool"
Cohesion: 0.45
Nodes (12): check_requests(), _header(), _log(), main(), Azure AI Foundry — Standalone Diagnostic Tool Run this independently to test con, _save_log(), test_api_versions(), test_chat_completion() (+4 more)

### Community 13 - "Office COM Reader"
Cohesion: 0.27
Nodes (12): _get_cached(), _is_cached(), awareness/office_reader.py Reads content from open Office applications (Excel, W, Attaches to a running Word instance via COM and reads the active document text., Attaches to a running PowerPoint instance via COM and reads the active slide tex, Routes to the correct reader based on the active process name.     Returns None, Attaches to a running Excel instance via COM and reads the active selection., read_active_office() (+4 more)

### Community 14 - "Flask API Server Setup"
Cohesion: 0.31
Nodes (7): _build_app(), _ensure_icons(), _make_png(), Local REST API server — bridges the Excel Office Add-in with the Python backend., Generate a solid-colour PNG of given size., Create placeholder icon PNGs in office_addin/ if they don't exist., start()

### Community 15 - "Notification System"
Cohesion: 0.29
Nodes (6): force_notify(), _prune(), Notification gate — prevents spam and deduplication. Prunes stale entries older, Remove entries not touched in the last 24 hours., Mark as notified without checking cooldown — for high-priority alerts., should_notify()

### Community 16 - "Project Documentation"
Cohesion: 0.4
Nodes (6): Aria Desktop Companion Project Document, Rationale: Ambient Not Intrusive Design Principle, Aria Desktop Widget (v2.0), Azure OpenAI GPT-4o Backend, Higgs Desktop Widget, Higgs â€” Ambient AI Desktop Companion

### Community 17 - "Context Detection"
Cohesion: 0.5
Nodes (3): detect_context(), Detects what the user is working on from the active window and generates context, Analyse the active window and return a contextual help offer if relevant.     Re

### Community 18 - "Excel Add-in JS Functions"
Cohesion: 0.5
Nodes (0): 

### Community 19 - "Package Init Files"
Cohesion: 1.0
Nodes (0): 

### Community 20 - "Package Init Files"
Cohesion: 1.0
Nodes (0): 

### Community 21 - "Build Scripts"
Cohesion: 1.0
Nodes (0): 

### Community 22 - "Package Init Files"
Cohesion: 1.0
Nodes (0): 

### Community 23 - "Pokemon Data"
Cohesion: 1.0
Nodes (0): 

### Community 24 - "Package Init Files"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **85 isolated node(s):** `Azure AI Foundry — Standalone Diagnostic Tool Run this independently to test con`, `Notification gate — prevents spam and deduplication. Prunes stale entries older`, `Remove entries not touched in the last 24 hours.`, `Mark as notified without checking cooldown — for high-priority alerts.`, `awareness/browser_reader.py Reads the active browser tab (URL, title, and option` (+80 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Package Init Files`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Package Init Files`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Build Scripts`** (1 nodes): `build_xlam.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Package Init Files`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Pokemon Data`** (1 nodes): `pokemon_list.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Package Init Files`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DesktopWidget` connect `Widget Animation & Window Tracking` to `Qt UI Components`, `Pokemon Sprite Loading`, `Widget Rendering & Drawing`, `Chat Panel UI`?**
  _High betweenness centrality (0.255) - this node is a cross-community bridge._
- **Why does `build_context()` connect `Context Awareness Layer` to `Browser Context Reading`, `Obsidian Task Integration`, `AI Chat & Analysis Engine`, `Office COM Reader`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `run_scan()` connect `Context Awareness Layer` to `Widget Animation & Window Tracking`, `AI Chat & Analysis Engine`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `DesktopWidget` (e.g. with `ScanSignals` and `ContextSignals`) actually correct?**
  _`DesktopWidget` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `SettingsPanel` (e.g. with `DesktopWidget` and `Called from main.py when Excel sends a selection.`) actually correct?**
  _`SettingsPanel` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ChatPanel` (e.g. with `DesktopWidget` and `Called from main.py when Excel sends a selection.`) actually correct?**
  _`ChatPanel` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `WindowMonitor` (e.g. with `ScanSignals` and `ContextSignals`) actually correct?**
  _`WindowMonitor` has 13 INFERRED edges - model-reasoned connections that need verification._