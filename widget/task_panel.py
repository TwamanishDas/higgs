from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QDateEdit, QDialog,
    QCheckBox, QTabBar, QApplication, QSizeGrip
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QPen

from awareness.tasks import Task, scan_vault_tasks, mark_complete_in_file, append_task_to_vault

_DARK = "#0d1117"
_SURFACE = "#161b22"
_BORDER = "#30363d"
_ACCENT = "#4a9eff"
_TEXT = "#e6edf3"
_MUTED = "#8b949e"
_RED = "#ff4444"
_ORANGE = "#ff9a00"
_GREEN = "#3fb950"
_BLUE = "#4a9eff"

_BASE_STYLE = f"""
    QWidget {{ background: {_DARK}; color: {_TEXT}; font-family: Segoe UI; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: {_SURFACE}; width: 6px; border-radius: 3px; }}
    QScrollBar::handle:vertical {{ background: {_BORDER}; border-radius: 3px; min-height: 20px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QLineEdit {{
        background: {_SURFACE}; color: {_TEXT}; border: 1px solid {_BORDER};
        border-radius: 6px; padding: 6px 10px; font-size: 12px;
    }}
    QLineEdit:focus {{ border-color: {_ACCENT}; }}
    QPushButton {{
        background: {_ACCENT}; color: white; border: none;
        border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: bold;
    }}
    QPushButton:hover {{ background: #6ab0ff; }}
    QPushButton:pressed {{ background: #3a8eef; }}
    QPushButton#secondary {{
        background: {_SURFACE}; color: {_TEXT}; border: 1px solid {_BORDER};
    }}
    QPushButton#secondary:hover {{ border-color: {_ACCENT}; color: {_ACCENT}; }}
    QDateEdit {{
        background: {_SURFACE}; color: {_TEXT}; border: 1px solid {_BORDER};
        border-radius: 6px; padding: 5px 8px; font-size: 12px;
    }}
    QCheckBox {{ spacing: 8px; font-size: 12px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px; border-radius: 4px;
        border: 1px solid {_BORDER}; background: {_SURFACE};
    }}
    QCheckBox::indicator:checked {{
        background: {_GREEN}; border-color: {_GREEN};
    }}
"""


class TaskItem(QFrame):
    completed_toggled = pyqtSignal(object)  # Task

    def __init__(self, task: Task, parent=None):
        super().__init__(parent)
        self.task = task
        self.setStyleSheet(f"QFrame {{ background: {_SURFACE}; border-radius: 8px; border: 1px solid {_BORDER}; }}")
        self.setFixedHeight(62)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(10)

        cb = QCheckBox()
        cb.setChecked(task.completed)
        cb.stateChanged.connect(lambda _: self.completed_toggled.emit(task))
        row.addWidget(cb)

        info = QVBoxLayout()
        info.setSpacing(2)

        title = QLabel(task.title)
        title.setFont(QFont("Segoe UI", 11))
        if task.completed:
            title.setStyleSheet(f"color: {_MUTED}; text-decoration: line-through;")
        row.addLayout(info)
        info.addWidget(title)

        meta = QLabel(f"{task.source_name}")
        meta.setStyleSheet(f"color: {_MUTED}; font-size: 10px;")
        info.addWidget(meta)

        row.addStretch()

        if not task.completed and task.due:
            badge = QLabel(task.due_label)
            badge.setFixedHeight(22)
            badge.setContentsMargins(8, 2, 8, 2)
            if task.is_overdue:
                badge.setStyleSheet(f"background: #2a0a0a; color: {_RED}; border-radius: 4px; font-size: 10px; font-weight: bold;")
            elif task.is_today:
                badge.setStyleSheet(f"background: #1a2a0a; color: {_GREEN}; border-radius: 4px; font-size: 10px; font-weight: bold;")
            else:
                badge.setStyleSheet(f"background: #0a1a2a; color: {_BLUE}; border-radius: 4px; font-size: 10px;")
            row.addWidget(badge)


class AddTaskDialog(QDialog):
    def __init__(self, vault_path: str, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint)
        self.vault_path = vault_path
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(380)
        self.setStyleSheet(_BASE_STYLE)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {_SURFACE}; border-radius: 12px; border: 1px solid {_BORDER}; }}")
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title_label = QLabel("Add Task to Obsidian Vault")
        title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        layout.addWidget(title_label)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Task title...")
        layout.addWidget(self.title_input)

        due_row = QHBoxLayout()
        due_label = QLabel("Due date:")
        due_label.setStyleSheet(f"color: {_MUTED}; font-size: 11px;")
        due_row.addWidget(due_label)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        due_row.addWidget(self.date_edit)
        self.no_date_cb = QCheckBox("No due date")
        self.no_date_cb.setStyleSheet(f"color: {_MUTED}; font-size: 11px;")
        self.no_date_cb.toggled.connect(lambda c: self.date_edit.setEnabled(not c))
        due_row.addWidget(self.no_date_cb)
        layout.addLayout(due_row)

        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondary")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Add to Vault")
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _save(self):
        title = self.title_input.text().strip()
        if not title:
            return
        due = None
        if not self.no_date_cb.isChecked():
            qd = self.date_edit.date()
            due = date(qd.year(), qd.month(), qd.day())
        append_task_to_vault(self.vault_path, title, due)
        self.accept()


class TaskPanel(QWidget):
    def __init__(self, vault_path: str, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.vault_path = vault_path
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(420)
        self.setMinimumHeight(500)
        self.setStyleSheet(_BASE_STYLE)
        self._drag_pos: QPoint | None = None
        self._active_tab = 0  # 0=Today, 1=Upcoming, 2=All, 3=Done

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._card = QFrame()
        self._card.setStyleSheet(f"""
            QFrame#card {{
                background: {_DARK};
                border-radius: 14px;
                border: 1px solid {_BORDER};
            }}
        """)
        self._card.setObjectName("card")
        outer.addWidget(self._card)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        title_bar = QFrame()
        title_bar.setFixedHeight(48)
        title_bar.setStyleSheet(f"background: {_SURFACE}; border-radius: 14px 14px 0 0; border-bottom: 1px solid {_BORDER};")
        tb_row = QHBoxLayout(title_bar)
        tb_row.setContentsMargins(16, 0, 12, 0)

        icon = QLabel("◆")
        icon.setStyleSheet(f"color: {_ACCENT}; font-size: 14px;")
        tb_row.addWidget(icon)

        lbl = QLabel("Tasks & Reminders")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {_TEXT};")
        tb_row.addWidget(lbl)
        tb_row.addStretch()

        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setStyleSheet(f"background: transparent; color: {_MUTED}; font-size: 16px; border: none;")
        refresh_btn.clicked.connect(self.refresh)
        tb_row.addWidget(refresh_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"background: transparent; color: {_MUTED}; font-size: 12px; border: none;")
        close_btn.clicked.connect(self.hide)
        tb_row.addWidget(close_btn)

        layout.addWidget(title_bar)

        # Tab bar
        tab_frame = QFrame()
        tab_frame.setFixedHeight(38)
        tab_frame.setStyleSheet(f"background: {_SURFACE}; border-bottom: 1px solid {_BORDER};")
        tab_row = QHBoxLayout(tab_frame)
        tab_row.setContentsMargins(12, 0, 12, 0)
        tab_row.setSpacing(4)

        self._tab_btns = []
        for i, label in enumerate(["Today", "Upcoming", "All", "Done"]):
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setStyleSheet(self._tab_style(i == 0))
            idx = i
            btn.clicked.connect(lambda _, x=idx: self._switch_tab(x))
            tab_row.addWidget(btn)
            self._tab_btns.append(btn)
        tab_row.addStretch()
        layout.addWidget(tab_frame)

        # Summary bar
        self._summary = QLabel("")
        self._summary.setContentsMargins(16, 8, 16, 4)
        self._summary.setStyleSheet(f"color: {_MUTED}; font-size: 10px;")
        layout.addWidget(self._summary)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._task_container = QWidget()
        self._task_layout = QVBoxLayout(self._task_container)
        self._task_layout.setContentsMargins(12, 4, 12, 12)
        self._task_layout.setSpacing(6)
        self._task_layout.addStretch()
        scroll.setWidget(self._task_container)
        layout.addWidget(scroll)

        # Add task button
        add_frame = QFrame()
        add_frame.setFixedHeight(54)
        add_frame.setStyleSheet(f"background: {_SURFACE}; border-radius: 0 0 14px 14px; border-top: 1px solid {_BORDER};")
        add_row = QHBoxLayout(add_frame)
        add_row.setContentsMargins(16, 8, 16, 8)
        add_btn = QPushButton("+ Add Task to Vault")
        add_btn.clicked.connect(self._add_task)
        add_row.addWidget(add_btn)
        layout.addWidget(add_frame)

    def _tab_style(self, active: bool) -> str:
        if active:
            return f"QPushButton {{ background: {_ACCENT}; color: white; border-radius: 5px; font-size: 11px; font-weight: bold; padding: 2px 10px; border: none; }}"
        return f"QPushButton {{ background: transparent; color: {_MUTED}; border-radius: 5px; font-size: 11px; padding: 2px 10px; border: none; }} QPushButton:hover {{ color: {_TEXT}; }}"

    def _switch_tab(self, idx: int):
        self._active_tab = idx
        for i, btn in enumerate(self._tab_btns):
            btn.setChecked(i == idx)
            btn.setStyleSheet(self._tab_style(i == idx))
        self._populate(self._all_tasks)

    def refresh(self):
        self._all_tasks = scan_vault_tasks(self.vault_path)
        overdue = sum(1 for t in self._all_tasks if t.is_overdue)
        today = sum(1 for t in self._all_tasks if t.is_today)
        pending = sum(1 for t in self._all_tasks if not t.completed)
        self._summary.setText(
            f"{pending} pending  •  {today} due today  •  {overdue} overdue  •  vault: {self.vault_path}"
        )
        self._populate(self._all_tasks)

    def _populate(self, tasks: list):
        layout = self._task_layout
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._active_tab == 0:
            filtered = [t for t in tasks if (t.is_today or t.is_overdue) and not t.completed]
            empty_msg = "No tasks due today."
        elif self._active_tab == 1:
            filtered = [t for t in tasks if t.is_upcoming]
            empty_msg = "No upcoming tasks in the next 7 days."
        elif self._active_tab == 2:
            filtered = [t for t in tasks if not t.completed]
            empty_msg = "No pending tasks."
        else:
            filtered = [t for t in tasks if t.completed]
            empty_msg = "No completed tasks."

        if not filtered:
            lbl = QLabel(empty_msg)
            lbl.setStyleSheet(f"color: {_MUTED}; font-size: 12px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setContentsMargins(0, 30, 0, 0)
            layout.insertWidget(0, lbl)
            return

        for i, task in enumerate(filtered):
            item = TaskItem(task)
            item.completed_toggled.connect(self._on_complete)
            layout.insertWidget(i, item)

    def _on_complete(self, task: Task):
        mark_complete_in_file(task)
        self.refresh()

    def _add_task(self):
        dlg = AddTaskDialog(self.vault_path, self)
        dlg.move(self.geometry().center() - dlg.rect().center())
        if dlg.exec():
            self.refresh()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
