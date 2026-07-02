#!/usr/bin/env python3
import ctypes
import ctypes.util
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import QPoint, QRect, QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizeGrip,
    QSystemTrayIcon,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


CONFIG_DIR = Path.home() / ".config" / "window-labels"
CONFIG_PATH = CONFIG_DIR / "labels.json"


class XButtonEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
        ("root", ctypes.c_ulong),
        ("subwindow", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("x_root", ctypes.c_int),
        ("y_root", ctypes.c_int),
        ("state", ctypes.c_uint),
        ("button", ctypes.c_uint),
        ("same_screen", ctypes.c_int),
    ]


class XEvent(ctypes.Union):
    _fields_ = [
        ("type", ctypes.c_int),
        ("xbutton", XButtonEvent),
        ("pad", ctypes.c_long * 24),
    ]


class WindowAttributes(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("border_width", ctypes.c_int),
        ("depth", ctypes.c_int),
        ("visual", ctypes.c_void_p),
        ("root", ctypes.c_ulong),
        ("class", ctypes.c_int),
        ("bit_gravity", ctypes.c_int),
        ("win_gravity", ctypes.c_int),
        ("backing_store", ctypes.c_int),
        ("backing_planes", ctypes.c_ulong),
        ("backing_pixel", ctypes.c_ulong),
        ("save_under", ctypes.c_int),
        ("colormap", ctypes.c_ulong),
        ("map_installed", ctypes.c_int),
        ("map_state", ctypes.c_int),
        ("all_event_masks", ctypes.c_long),
        ("your_event_mask", ctypes.c_long),
        ("do_not_propagate_mask", ctypes.c_long),
        ("override_redirect", ctypes.c_int),
        ("screen", ctypes.c_void_p),
    ]


class X11:
    ButtonPress = 4
    GrabModeAsync = 1
    ButtonPressMask = 1 << 2
    Success = 0
    AnyButton = 0
    AnyModifier = 1 << 15
    XA_ATOM = 4
    XA_WINDOW = 33
    XA_CARDINAL = 6
    XA_STRING = 31

    def __init__(self) -> None:
        lib_name = ctypes.util.find_library("X11")
        if not lib_name:
            raise RuntimeError("libX11 was not found")
        self.x = ctypes.cdll.LoadLibrary(lib_name)
        self.x.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.x.XOpenDisplay.restype = ctypes.c_void_p
        self.display = self.x.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("Cannot open X display. This app requires an X11 session.")

        self.x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self.x.XDefaultRootWindow.restype = ctypes.c_ulong
        self.root = self.x.XDefaultRootWindow(self.display)

        self.x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self.x.XInternAtom.restype = ctypes.c_ulong
        self.x.XGetWindowProperty.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_long,
            ctypes.c_long,
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
        ]
        self.x.XGetWindowProperty.restype = ctypes.c_int
        self.x.XFree.argtypes = [ctypes.c_void_p]
        self.x.XFree.restype = ctypes.c_int
        self.x.XFetchName.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_char_p),
        ]
        self.x.XFetchName.restype = ctypes.c_int
        self.x.XQueryTree.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)),
            ctypes.POINTER(ctypes.c_uint),
        ]
        self.x.XQueryTree.restype = ctypes.c_int
        self.x.XGetWindowAttributes.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(WindowAttributes),
        ]
        self.x.XGetWindowAttributes.restype = ctypes.c_int
        self.x.XTranslateCoordinates.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_ulong),
        ]
        self.x.XTranslateCoordinates.restype = ctypes.c_int
        self.x.XGrabPointer.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        self.x.XGrabPointer.restype = ctypes.c_int
        self.x.XUngrabPointer.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.x.XUngrabPointer.restype = ctypes.c_int
        self.x.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.POINTER(XEvent)]
        self.x.XNextEvent.restype = ctypes.c_int
        self.x.XFlush.argtypes = [ctypes.c_void_p]
        self.x.XFlush.restype = ctypes.c_int
        self.x.XCloseDisplay.argtypes = [ctypes.c_void_p]
        self.x.XCloseDisplay.restype = ctypes.c_int
        self.x.XChangeProperty.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.c_int,
        ]
        self.x.XChangeProperty.restype = ctypes.c_int
        self.x.XSetTransientForHint.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        self.x.XSetTransientForHint.restype = ctypes.c_int

        self.atom_client_list = self.atom("_NET_CLIENT_LIST")
        self.atom_wm_name = self.atom("_NET_WM_NAME")
        self.atom_utf8 = self.atom("UTF8_STRING")
        self.atom_pid = self.atom("_NET_WM_PID")
        self.atom_wm_state = self.atom("_NET_WM_STATE")
        self.atom_state_skip_taskbar = self.atom("_NET_WM_STATE_SKIP_TASKBAR")
        self.atom_window_type = self.atom("_NET_WM_WINDOW_TYPE")
        self.atom_window_type_utility = self.atom("_NET_WM_WINDOW_TYPE_UTILITY")

    def atom(self, name: str) -> int:
        return int(self.x.XInternAtom(self.display, name.encode("ascii"), False))

    def close(self) -> None:
        if self.display:
            self.x.XCloseDisplay(self.display)
            self.display = None

    def property_words(self, window: int, atom: int, expected_type: int) -> List[int]:
        actual_type = ctypes.c_ulong()
        actual_format = ctypes.c_int()
        nitems = ctypes.c_ulong()
        bytes_after = ctypes.c_ulong()
        prop = ctypes.POINTER(ctypes.c_ubyte)()
        status = self.x.XGetWindowProperty(
            self.display,
            window,
            atom,
            0,
            4096,
            False,
            expected_type,
            ctypes.byref(actual_type),
            ctypes.byref(actual_format),
            ctypes.byref(nitems),
            ctypes.byref(bytes_after),
            ctypes.byref(prop),
        )
        if status != self.Success or not prop:
            return []
        try:
            if actual_format.value == 32:
                array_type = ctypes.c_ulong * nitems.value
                return [int(v) for v in ctypes.cast(prop, ctypes.POINTER(array_type)).contents]
            if actual_format.value == 8:
                array_type = ctypes.c_ubyte * nitems.value
                return [int(v) for v in ctypes.cast(prop, ctypes.POINTER(array_type)).contents]
            return []
        finally:
            self.x.XFree(prop)

    def property_text(self, window: int, atom: Optional[int] = None) -> str:
        if atom is None:
            atom = self.atom_wm_name
        actual_type = ctypes.c_ulong()
        actual_format = ctypes.c_int()
        nitems = ctypes.c_ulong()
        bytes_after = ctypes.c_ulong()
        prop = ctypes.POINTER(ctypes.c_ubyte)()
        status = self.x.XGetWindowProperty(
            self.display,
            window,
            atom,
            0,
            4096,
            False,
            self.atom_utf8,
            ctypes.byref(actual_type),
            ctypes.byref(actual_format),
            ctypes.byref(nitems),
            ctypes.byref(bytes_after),
            ctypes.byref(prop),
        )
        if status == self.Success and prop:
            try:
                if actual_format.value == 8:
                    data = ctypes.string_at(prop, nitems.value)
                    return data.decode("utf-8", errors="replace")
            finally:
                self.x.XFree(prop)

        name = ctypes.c_char_p()
        if self.x.XFetchName(self.display, window, ctypes.byref(name)) and name:
            try:
                return name.value.decode("utf-8", errors="replace")
            finally:
                self.x.XFree(name)
        return f"0x{window:x}"

    def window_pid(self, window: int) -> Optional[int]:
        words = self.property_words(window, self.atom_pid, self.XA_CARDINAL)
        return int(words[0]) if words else None

    def client_windows(self) -> List[int]:
        return self.property_words(self.root, self.atom_client_list, self.XA_WINDOW)

    def parent_of(self, window: int) -> Optional[int]:
        root = ctypes.c_ulong()
        parent = ctypes.c_ulong()
        children = ctypes.POINTER(ctypes.c_ulong)()
        nchildren = ctypes.c_uint()
        ok = self.x.XQueryTree(
            self.display,
            window,
            ctypes.byref(root),
            ctypes.byref(parent),
            ctypes.byref(children),
            ctypes.byref(nchildren),
        )
        if children:
            self.x.XFree(children)
        if not ok or parent.value == 0:
            return None
        return int(parent.value)

    def nearest_client(self, window: int) -> Optional[int]:
        clients = set(self.client_windows())
        current = window
        seen = set()
        while current and current not in seen:
            if current in clients:
                return current
            seen.add(current)
            if current == self.root:
                break
            current = self.parent_of(current) or 0
        return None

    def geometry(self, window: int) -> Optional[QRect]:
        attrs = WindowAttributes()
        if not self.x.XGetWindowAttributes(self.display, window, ctypes.byref(attrs)):
            return None
        if attrs.map_state == 0 or attrs.width <= 0 or attrs.height <= 0:
            return None
        dest_x = ctypes.c_int()
        dest_y = ctypes.c_int()
        child = ctypes.c_ulong()
        if not self.x.XTranslateCoordinates(
            self.display,
            window,
            self.root,
            0,
            0,
            ctypes.byref(dest_x),
            ctypes.byref(dest_y),
            ctypes.byref(child),
        ):
            return None
        return QRect(dest_x.value, dest_y.value, attrs.width, attrs.height)

    def mark_label_window(self, window: int, target_window: int) -> None:
        states = (ctypes.c_ulong * 1)(self.atom_state_skip_taskbar)
        self.x.XChangeProperty(
            self.display,
            window,
            self.atom_wm_state,
            self.XA_ATOM,
            32,
            0,
            states,
            1,
        )
        window_type = (ctypes.c_ulong * 1)(self.atom_window_type_utility)
        self.x.XChangeProperty(
            self.display,
            window,
            self.atom_window_type,
            self.XA_ATOM,
            32,
            0,
            window_type,
            1,
        )
        self.x.XSetTransientForHint(self.display, window, target_window)
        self.x.XFlush(self.display)

    def pick_window(self) -> Optional[int]:
        status = self.x.XGrabPointer(
            self.display,
            self.root,
            False,
            self.ButtonPressMask,
            self.GrabModeAsync,
            self.GrabModeAsync,
            0,
            0,
            0,
        )
        if status != self.Success:
            return None
        self.x.XFlush(self.display)
        event = XEvent()
        while True:
            self.x.XNextEvent(self.display, ctypes.byref(event))
            if event.type == self.ButtonPress:
                self.x.XUngrabPointer(self.display, 0)
                self.x.XFlush(self.display)
                target = int(event.xbutton.subwindow or event.xbutton.window)
                return self.nearest_client(target) or target


@dataclass
class LabelRecord:
    window_id: int
    window_title: str
    text: str = "Label"
    offset_x: int = 8
    offset_y: int = 8
    width: int = 220
    height: int = 72
    color: str = "#fff3a3"


class PickerThread(QThread):
    picked = pyqtSignal(int)
    failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            x11 = X11()
            window = x11.pick_window()
            x11.close()
            if window:
                self.picked.emit(window)
            else:
                self.failed.emit("Could not grab the pointer for window picking.")
        except Exception as exc:
            self.failed.emit(str(exc))


class LabelWindow(QWidget):
    changed = pyqtSignal()
    delete_requested = pyqtSignal(object)

    def __init__(self, record: LabelRecord, x11: X11) -> None:
        super().__init__()
        self.record = record
        self.x11 = x11
        self._drag_start: Optional[QPoint] = None
        self._drag_geometry: Optional[QRect] = None
        self._target_geometry: Optional[QRect] = None

        self.setWindowTitle("Window Label")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)
        self.setAutoFillBackground(True)

        self.header = QLabel(self.record.window_title)
        self.header.setObjectName("header")
        self.header.setTextInteractionFlags(Qt.NoTextInteraction)
        self.header.setFixedHeight(22)

        self.delete_button = QToolButton()
        self.delete_button.setText("x")
        self.delete_button.setFixedSize(22, 22)
        self.delete_button.clicked.connect(lambda: self.delete_requested.emit(self))

        header_row = QHBoxLayout()
        header_row.setContentsMargins(6, 4, 4, 0)
        header_row.setSpacing(4)
        header_row.addWidget(self.header, 1)
        header_row.addWidget(self.delete_button)

        self.editor = QTextEdit()
        self.editor.setPlainText(self.record.text)
        self.editor.textChanged.connect(self._text_changed)

        self.grip = QSizeGrip(self)
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 3, 3)
        grip_row.addStretch(1)
        grip_row.addWidget(self.grip)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header_row)
        layout.addWidget(self.editor)
        layout.addLayout(grip_row)
        self.setLayout(layout)
        self.setMinimumSize(140, 62)
        self.resize(self.record.width, self.record.height)
        self.apply_style()
        self.x11.mark_label_window(int(self.winId()), self.record.window_id)

    def apply_style(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget {{
                background: {self.record.color};
                border: 1px solid rgba(0, 0, 0, 95);
                border-radius: 5px;
            }}
            QLabel#header {{
                color: #202020;
                border: none;
                font-size: 11px;
                font-weight: 600;
            }}
            QTextEdit {{
                background: rgba(255, 255, 255, 70);
                border: none;
                color: #111111;
                padding: 5px;
                selection-background-color: #3867d6;
            }}
            QToolButton {{
                background: rgba(0, 0, 0, 35);
                border: none;
                border-radius: 3px;
                color: #111111;
                font-weight: 700;
            }}
            QToolButton:hover {{
                background: rgba(0, 0, 0, 60);
            }}
            """
        )

    def _text_changed(self) -> None:
        self.record.text = self.editor.toPlainText()
        self.changed.emit()

    def update_from_target(self) -> bool:
        geometry = self.x11.geometry(self.record.window_id)
        if geometry is None:
            self.hide()
            return False
        self._target_geometry = geometry
        self.header.setText(self.x11.property_text(self.record.window_id))
        self.record.window_title = self.header.text()
        self.move(geometry.x() + self.record.offset_x, geometry.y() + self.record.offset_y)
        if not self.isVisible():
            self.show()
        return True

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and event.pos().y() <= 28:
            self._drag_start = event.globalPos()
            self._drag_geometry = self.geometry()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is not None and self._drag_geometry is not None:
            delta = event.globalPos() - self._drag_start
            self.move(self._drag_geometry.topLeft() + delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_start is not None:
            if self._target_geometry is None:
                self._target_geometry = self.x11.geometry(self.record.window_id)
            if self._target_geometry is not None:
                self.record.offset_x = self.x() - self._target_geometry.x()
                self.record.offset_y = self.y() - self._target_geometry.y()
                self.changed.emit()
            self._drag_start = None
            self._drag_geometry = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event) -> None:
        self.record.width = self.width()
        self.record.height = self.height()
        self.changed.emit()
        super().resizeEvent(event)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        for name, color in [
            ("Yellow", "#fff3a3"),
            ("Green", "#b9f6ca"),
            ("Blue", "#b3e5fc"),
            ("Pink", "#ffcdd2"),
            ("White", "#fafafa"),
        ]:
            action = QAction(name, self)
            action.triggered.connect(lambda checked=False, value=color: self.set_color(value))
            menu.addAction(action)
        menu.addSeparator()
        delete_action = QAction("Delete label", self)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self))
        menu.addAction(delete_action)
        menu.exec_(event.globalPos())

    def set_color(self, color: str) -> None:
        self.record.color = color
        self.apply_style()
        self.changed.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Window Labels")
        self.x11 = X11()
        self.labels: List[LabelWindow] = []
        self.picker: Optional[PickerThread] = None
        self.save_timer = QTimer(self)
        self.save_timer.setInterval(350)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save)

        self.status = QLabel("Attach editable labels to running X11 windows.")
        self.status.setWordWrap(True)

        self.add_button = QPushButton("Pick Window")
        self.add_button.clicked.connect(self.start_pick)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.tick)

        self.position = QComboBox()
        self.position.addItem("Inside top-left", (8, 8))
        self.position.addItem("Outside right", (20, 8))
        self.position.addItem("Above", (8, -84))
        self.position.addItem("Below", (8, 20))

        controls = QHBoxLayout()
        controls.addWidget(self.add_button)
        controls.addWidget(self.position)
        controls.addWidget(self.refresh_button)

        self.list_label = QLabel("")
        self.list_label.setWordWrap(True)

        root = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.status)
        layout.addLayout(controls)
        layout.addWidget(self.list_label, 1)
        root.setLayout(layout)
        self.setCentralWidget(root)
        self.resize(420, 220)

        self.timer = QTimer(self)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(self.style().SP_FileDialogDetailedView))
        self.tray.setToolTip("Window Labels")
        tray_menu = QMenu()
        show_action = QAction("Show controls", self)
        show_action.triggered.connect(self.show)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()

        self.load()
        self.tick()

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
        self.tray.showMessage("Window Labels", "Still running in the tray.", QSystemTrayIcon.Information, 1600)

    def tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.setVisible(not self.isVisible())

    def start_pick(self) -> None:
        self.add_button.setEnabled(False)
        self.status.setText("Click the terminal or other window you want to label.")
        self.hide()
        self.picker = PickerThread()
        self.picker.picked.connect(self.add_label_for_window)
        self.picker.failed.connect(self.pick_failed)
        self.picker.finished.connect(lambda: self.add_button.setEnabled(True))
        self.picker.start()

    def pick_failed(self, message: str) -> None:
        self.show()
        self.status.setText(message)

    def add_label_for_window(self, window_id: int) -> None:
        self.show()
        geometry = self.x11.geometry(window_id)
        if geometry is None:
            self.status.setText("The selected window is not visible anymore.")
            return
        offset_x, offset_y = self.position.currentData()
        if self.position.currentText() == "Outside right":
            offset_x = geometry.width() + 12
        elif self.position.currentText() == "Below":
            offset_y = geometry.height() + 12
        title = self.x11.property_text(window_id)
        record = LabelRecord(
            window_id=window_id,
            window_title=title,
            text=title if title else "Label",
            offset_x=offset_x,
            offset_y=offset_y,
        )
        label = LabelWindow(record, self.x11)
        label.changed.connect(self.schedule_save)
        label.delete_requested.connect(self.delete_label)
        self.labels.append(label)
        label.update_from_target()
        self.status.setText(f"Attached label to {title}.")
        self.schedule_save()
        self.update_list()

    def delete_label(self, label: LabelWindow) -> None:
        if label in self.labels:
            self.labels.remove(label)
            label.hide()
            label.deleteLater()
            self.schedule_save()
            self.update_list()

    def tick(self) -> None:
        live = 0
        for label in list(self.labels):
            if label.update_from_target():
                live += 1
        self.update_list(live)

    def update_list(self, live: Optional[int] = None) -> None:
        if live is None:
            live = sum(1 for label in self.labels if label.isVisible())
        if not self.labels:
            self.list_label.setText("No labels yet. Use Pick Window, then click a terminal.")
            return
        lines = [f"{live}/{len(self.labels)} labels visible:"]
        for label in self.labels:
            title = label.record.window_title or f"0x{label.record.window_id:x}"
            lines.append(f"- {title}")
        self.list_label.setText("\n".join(lines))

    def schedule_save(self) -> None:
        self.save_timer.start()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = [asdict(label.record) for label in self.labels]
        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self) -> None:
        if not CONFIG_PATH.exists():
            return
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            for item in raw:
                record = LabelRecord(**item)
                label = LabelWindow(record, self.x11)
                label.changed.connect(self.schedule_save)
                label.delete_requested.connect(self.delete_label)
                self.labels.append(label)
        except Exception as exc:
            self.status.setText(f"Could not load saved labels: {exc}")


def main() -> int:
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        print("Window Labels requires an X11 session. Log into Plasma (X11) to use it.", file=sys.stderr)
        return 2
    app = QApplication(sys.argv)
    app.setApplicationName("Window Labels")
    palette = app.palette()
    palette.setColor(QPalette.Highlight, QColor("#3867d6"))
    app.setPalette(palette)
    try:
        window = MainWindow()
    except Exception as exc:
        QMessageBox.critical(None, "Window Labels", str(exc))
        return 1
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
