# Copyright (C) 2026 Fraser Boyd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Flag Viewer – a live, collapsible panel that shows every flag-type
parameter from the loaded blackbox log.

Active flags are rendered in bright green; inactive ones are dimmed.
Collapse / expand state for each section is persisted between app restarts
via a dict stored in defaults_inav.cfg.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QScrollArea, QWidget, QLabel,
    QGridLayout, QFrame, QPushButton, QHBoxLayout, QSizePolicy,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QMimeData, QPoint
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QPolygonF, QDrag
from PyQt6 import sip

# ── Canonical flag definitions sourced from the INAV firmware ──────────
# Box IDs generated as text strings by blackbox_decode for flightModeFlags
BLACKBOX_BOX_NAMES = [
    "AIRMODE", "ANGLE", "ANGLEHOLD", "ARM", "AUTOLEVEL", "AUTOTRIM", 
    "AUTOTUNE", "BEEPERON", "BLACKBOX", "FAILSAFE", "FLAPERON", 
    "HEADFREE", "HORIZON", "MAG", "NAVALTHOLD", "NAVCOURSEHOLD", 
    "NAVCRUISE", "NAVFWAUTOLAND", "NAVLAUNCH", "NAVPOSHOLD", 
    "NAVRTH", "NAVSENDTO", "NAVWP", "OSD", "SERVO1", "SERVO2", 
    "SERVO3", "SOARING", "TELEMETRY", "TURNASSISTANT", "TURTLE", 
    "VTXPITMODE"
]

# activeFlightModeFlags bitmask
ACTIVE_FLIGHT_MODE_BITS_ALL = {
    0:  "ANGLE",            1:  "HORIZON",         2:  "HEADING",
    3:  "NAV_ALTHOLD",      4:  "NAV_RTH",         5:  "NAV_POSHOLD",
    6:  "HEADFREE",         7:  "NAV_LAUNCH",      8:  "MANUAL",
    9:  "FAILSAFE",         10: "AUTO_TUNE",       11: "NAV_WP",
    12: "NAV_COURSE_HOLD",  13: "FLAPERON",        14: "TURN_ASSISTANT",
    15: "TURTLE",           16: "SOARING",         17: "ANGLEHOLD",
    18: "NAV_FW_AUTOLAND",  19: "NAV_SEND_TO",     20: "NAV_TAKEOFF",
    21: "NAV_LAND",
}

# runtime_config.h  stateFlags_t
STATE_FLAGS = [
    "GPS_FIX_HOME", "GPS_FIX", "CALIBRATE_MAG", "SMALL_ANGLE",
    "FIXED_WING_LEGACY", "ANTI_WINDUP", "FLAPERON_AVAILABLE",
    "NAV_MOTOR_STOP_OR_IDLE", "COMPASS_CALIBRATED",
    "ACCELEROMETER_CALIBRATED", "GPS_ESTIMATED_FIX",
    "NAV_CRUISE_BRAKING", "NAV_CRUISE_BRAKING_BOOST",
    "NAV_CRUISE_BRAKING_LOCKED", "NAV_EXTRA_ARMING_SAFETY_BYPASSED",
    "AIRMODE_ACTIVE", "ESC_SENSOR_ENABLED",
    "AIRPLANE", "MULTIROTOR", "ROVER", "BOAT",
    "ALTITUDE_CONTROL", "MOVE_FORWARD_ONLY",
    "SET_REVERSIBLE_MOTORS_FORWARD", "FW_HEADING_USE_YAW",
    "ANTI_WINDUP_DEACTIVATED", "LANDING_DETECTED",
    "IN_FLIGHT_EMERG_REARM", "TAILSITTER",
]

# failsafePhase
FAILSAFE_FLAGS_ALL = [
    "IDLE", "RX_LOSS_DETECTED", "RX_LOSS_RECOVERY", "RX_LOSS_RECOVERED",
    "RX_LOSS_MONITORING", "GPS_RESCUE", "RETURN_TO_HOME", "LANDING", "LANDED",
    "SETTLED", "BEEP_PULSE", "COMPLETE"
]

# navigation.h  navFlags (numeric bitmask logged as integer)
NAV_FLAGS_BITS = {
    0: "NAV_CTL_ALT",
    1: "NAV_CTL_POS",
    2: "NAV_CTL_YAW",
    3: "NAV_CTL_HEADING",
    4: "NAV_REQUIRE_ANGLE",
    5: "NAV_REQUIRE_ANGLE_FW",
    6: "NAV_REQUIRE_THROT",
    7: "NAV_REQUIRE_TURN_ASSIST",
    8: "NAV_RC_ALT",
    9: "NAV_RC_POS",
    10: "NAV_RC_YAW",
}

# hwHealthStatus (numeric bitmask – sensor health bits)
HW_HEALTH_BITS = {
    0: "GYRO",
    2: "ACCEL",
    4: "MAG",
    6: "BARO",
    8: "GPS",
    10: "RANGEFINDER",
    12: "PITOT",
    14: "OPTICAL_FLOW",
}

# navState enum
NAV_STATES_ALL = {
    0:  "IDLE",             1:  "RTH_START",       2:  "RTH_ENROUTE",
    3:  "RTH_APPROACH",     4:  "RTH_LANDING",     5:  "RTH_FINISH",
    6:  "RTH_DONE",         7:  "POSHOLD",         8:  "CRUISE",
    9:  "WP_ENROUTE",       10: "WP_DONE",         11: "LAUNCH",
    12: "LANDING",          13: "EMERG_LANDING",   14: "COURSE_HOLD",
    15: "CRUISE_2D",        16: "WP_RECOVERY",     17: "AUTO_TAKEOFF",
    26: "LAUNCH_IDLE",      27: "LAUNCH_MOTOR_WAIT", 28: "LAUNCH_IN_PROGRESS",
}

# rxSignalReceived / rxFlightChannelsValid
RX_SIGNAL_MAP = {0: "DISCONNECTED", 1: "RECEIVED"}
RX_VALID_MAP = {0: "INVALID", 1: "VALID"}

# States that should not count as "active" in the header summary
NEUTRAL_STATES = {"IDLE", "DISCONNECTED", "INVALID", "NONE", "UNKNOWN", "STATE_0"}

# Versioned Parameter Overrides
VERSION_CONFIG = {
    "INAV 7": {
        "activeFlightModeFlags": {k: v for k, v in ACTIVE_FLIGHT_MODE_BITS_ALL.items() if k <= 19},
        "navState": {k: v for k, v in NAV_STATES_ALL.items() if k < 16 or k >= 26},
        "failsafePhase (flags)": ["IDLE", "RX_LOSS_DETECTED", "RX_LOSS_RECOVERY", "RX_LOSS_RECOVERED", "RX_LOSS_MONITORING", "GPS_RESCUE", "RETURN_TO_HOME", "LANDING", "LANDED"]
    },
    "INAV 8": {
        "activeFlightModeFlags": {k: v for k, v in ACTIVE_FLIGHT_MODE_BITS_ALL.items() if k <= 21},
        "navState": {k: v for k, v in NAV_STATES_ALL.items() if k != 17},
        "failsafePhase (flags)": FAILSAFE_FLAGS_ALL
    },
    "INAV 9": {
        "activeFlightModeFlags": ACTIVE_FLIGHT_MODE_BITS_ALL,
        "navState": NAV_STATES_ALL,
        "failsafePhase (flags)": FAILSAFE_FLAGS_ALL
    },
    "All": {
        "activeFlightModeFlags": ACTIVE_FLIGHT_MODE_BITS_ALL,
        "navState": NAV_STATES_ALL,
        "failsafePhase (flags)": FAILSAFE_FLAGS_ALL
    }
}

def get_flag_params(version="All"):
    """Returns the FLAG_PARAMS dictionary filtered by INAV version,
    or delegates to ardupilot_flags for ArduPilot versions."""
    # Route ArduPilot versions to the dedicated module
    if version.startswith("Ardu"):
        from ardupilot_flags import get_ardupilot_flag_params
        return get_ardupilot_flag_params(version)

    v_cfg = VERSION_CONFIG.get(version, VERSION_CONFIG["All"])
    
    return {
        "flightModeFlags (flags)": ("text",   BLACKBOX_BOX_NAMES),
        "activeFlightModeFlags":   ("bits",   v_cfg["activeFlightModeFlags"]),
        "stateFlags (flags)":      ("text",   STATE_FLAGS),
        "failsafePhase (flags)":   ("text",   v_cfg["failsafePhase (flags)"]),
        "navFlags":                ("bits",   NAV_FLAGS_BITS),
        "navState":                ("enum",   v_cfg["navState"]),
        "hwHealthStatus":          ("bits",   HW_HEALTH_BITS),
        "rxSignalReceived":        ("enum",   RX_SIGNAL_MAP),
        "rxFlightChannelsValid":   ("enum",   RX_VALID_MAP),
        "activeWpNumber":          ("scalar", "Waypoint"),
    }

# Human-friendly section titles
SECTION_TITLES = {
    "flightModeFlags (flags)": "Flight Mode Flags - [Legacy]",
    "activeFlightModeFlags":   "Active Flight Modes",
    "stateFlags (flags)":      "State Flags",
    "failsafePhase (flags)":   "Failsafe Phase",
    "navFlags":                "Navigation Flags",
    "navState":                "Navigation State",
    "hwHealthStatus":          "HW Health Status",
    "rxSignalReceived":        "Receiver Connection",
    "rxFlightChannelsValid":   "Receiver Link",
    "activeWpNumber":          "Mission Progress",
    "GPS_fixType":             "GPS Fix Type",
    "EventId":                 "ArduPilot Events",
    "GPS Vertical Velocity Valid": "GPS Vertical Velocity",
    "Attitude EKF Active":     "Attitude EKF Active",
}
def decode_flag_value(col_name, raw, params=None):
    active = set()
    errors = set()
    if params is None:
        params = get_flag_params("All")
        
    if col_name not in params:
        return active, errors
    
    kind, definition = params[col_name]
    
    if kind == "text":
        if isinstance(raw, str):
            active = {f.strip() for f in raw.split("|") if f.strip()}
        else:
            # Fallback for numeric value if definition is a list/indexable
            try:
                val = int(raw)
                if isinstance(definition, list) and 0 <= val < len(definition):
                    active.add(definition[val])
                elif isinstance(definition, dict) and val in definition:
                    active.add(definition[val])
            except (ValueError, TypeError):
                pass
    elif kind == "bits":
        try:
            val = int(raw)
            if col_name.startswith("hwHealthStatus"):
                for bit_pos, name in HW_HEALTH_BITS.items():
                    status = (val >> bit_pos) & 0x03
                    if status == 1:
                        active.add(name)
                    elif status == 2:
                        errors.add(name)
            else:
                for bit, name in definition.items():
                    if val & (1 << bit):
                        active.add(name)
        except (ValueError, TypeError):
            pass
    elif kind == "enum":
        try:
            # Handle both integer and string (if already decoded by blackbox-tools)
            if isinstance(raw, str):
                # If it's already a name, check if it's in our definition values
                if raw in definition.values():
                    active.add(raw)
                else:
                    # Try splitting if it's a pipe-delimited string erroneously marked as enum
                    active.update({f.strip() for f in raw.split("|") if f.strip()})
            else:
                val = int(raw)
                state_name = definition.get(val, f"STATE_{val}")
                active.add(state_name)
        except (ValueError, TypeError):
            pass
    elif kind == "scalar":
        try:
            val = int(raw)
            if val > 0:
                active.add(f"{definition}: {val}")
        except (ValueError, TypeError):
            pass
            
    return active, errors

class TimelineWidget(QWidget):
    timeClicked = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self._time_s = None
        self._change_times = None
        self._current_time_s = 0.0

    def set_data(self, time_s, change_times):
        self._time_s = time_s
        self._change_times = change_times
        self.update()

    def set_cursor(self, time_s):
        self._current_time_s = time_s
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._time_s is not None:
            # Map pixel X to time
            x = event.pos().x()
            w = self.width()
            if w > 0:
                t_min = self._time_s.min()
                t_max = self._time_s.max()
                t_clicked = t_min + (x / w) * (t_max - t_min)
                self.timeClicked.emit(float(t_clicked))
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        w = rect.width()
        h = rect.height()
        
        painter.fillRect(rect, QColor("#1e1e1e"))
        
        if self._time_s is None or len(self._time_s) == 0:
            return
            
        t_min = self._time_s.min()
        t_max = self._time_s.max()
        t_range = max(1e-6, t_max - t_min)
        
        painter.setPen(QPen(QColor("#444444"), 1))
        y_center = 12
        painter.drawLine(0, y_center, w, y_center)
        
        if self._change_times is not None:
            painter.setBrush(QBrush(QColor("#00aaff"))) # Blue diamonds
            painter.setPen(Qt.PenStyle.NoPen)
            for t in self._change_times:
                x = int((t - t_min) / t_range * w)
                
                poly = QPolygonF()
                d_size = 4
                poly.append(QPointF(x, y_center - d_size))
                poly.append(QPointF(x + d_size, y_center))
                poly.append(QPointF(x, y_center + d_size))
                poly.append(QPointF(x - d_size, y_center))
                painter.drawPolygon(poly)
                
        cursor_x = int((self._current_time_s - t_min) / t_range * w)
        painter.setPen(QPen(QColor("#ffff00"), 1)) # Yellow time marker
        painter.drawLine(cursor_x, 0, cursor_x, h)
        
        # Draw time axis ticks and labels
        painter.setPen(QPen(QColor("#888888"), 1))
        font = painter.font()
        font.setPointSize(7)
        painter.setFont(font)
        
        # Calculate tick times: start, end, and every minute
        tick_times = [t_min, t_max]
        
        first_minute = int(t_min / 60) * 60
        if first_minute < t_min:
            first_minute += 60
            
        current_minute = first_minute
        while current_minute < t_max:
            if (current_minute - t_min) > 5 and (t_max - current_minute) > 5:
                tick_times.append(current_minute)
            current_minute += 60
            
        tick_times = sorted(list(set(tick_times)))
        
        for t_tick in tick_times:
            if t_range > 0:
                frac = (t_tick - t_min) / t_range
            else:
                frac = 0
            x = int(frac * w)
            if x < 2: x = 2
            elif x > w - 2: x = w - 2
            
            painter.drawLine(x, y_center, x, y_center + 4)
            
            tm, ts = divmod(t_tick, 60)
            th, tm = divmod(tm, 60)
            if th >= 1:
                t_str = f"{int(th)}:{int(tm):02}:{int(ts):02}"
            else:
                t_str = f"{int(tm)}:{int(ts):02}"
                
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(t_str)
            if t_tick == t_min:
                painter.drawText(x, y_center + 18, t_str)
            elif t_tick == t_max:
                painter.drawText(x - tw, y_center + 18, t_str)
            else:
                painter.drawText(x - tw//2, y_center + 18, t_str)


class _CollapsibleSection(QWidget):
    """A header button + a grid of flag labels that can be collapsed."""
    toggled = pyqtSignal()
    timeClicked = pyqtSignal(float)

    def __init__(self, col_name: str, title: str, flag_names: list[str], collapsed: bool = False, parent=None):
        super().__init__(parent)
        self.col_name = col_name
        self._collapsed = collapsed
        self._flag_labels: dict[str, QLabel] = {}
        self._drag_start_pos = QPoint()
        self._last_active = None
        self._last_errors = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────────
        self.header = QPushButton()
        self.header.setCheckable(True)
        self.header.setChecked(not collapsed)
        self.header.clicked.connect(self._toggle)
        self._update_header_text(title)
        self.header.setStyleSheet("""
            QPushButton {
                background: #2a2a2a;
                color: #e0e0e0;
                border: none;
                border-bottom: 1px solid #444;
                text-align: left;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 9pt;
            }
            QPushButton:hover { background: #333; }
        """)
        # Forward mouse events for drag and drop
        self.header.mousePressEvent = self._header_mouse_press
        self.header.mouseMoveEvent = self._header_mouse_move
        layout.addWidget(self.header)
        
        # ── Timeline ──────────────────────────────────────────────────
        self.timeline = TimelineWidget()
        self.timeline.timeClicked.connect(self.timeClicked.emit)
        layout.addWidget(self.timeline)
        self.timeline.setVisible(not collapsed)

        # ── Flag grid ─────────────────────────────────────────────────
        self.grid_container = QWidget()
        grid = QGridLayout(self.grid_container)
        grid.setContentsMargins(12, 6, 12, 8)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(3)

        cols = 4  # flags per row
        for idx, name in enumerate(flag_names):
            lbl = QLabel(name)
            lbl.setFont(QFont("Consolas", 8))
            lbl.setStyleSheet("color: #555555;")  # default: inactive
            lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            grid.addWidget(lbl, idx // cols, idx % cols)
            self._flag_labels[name] = lbl

        layout.addWidget(self.grid_container)
        self.grid_container.setVisible(not collapsed)
        self._title = title

    # ── Public API ────────────────────────────────────────────────────
    def set_active_flags(self, active: set[str], errors: set[str] | None = None):
        """Highlight *active* flags green, *errors* red, and grey out the rest."""
        active_count = 0
        error_count = 0
        for name, lbl in self._flag_labels.items():
            # Check for exact match or scalar match (e.g. "Waypoint: 5")
            match = name if name in active else None
            if not match:
                for a in active:
                    if a.startswith(f"{name}: "):
                        match = a
                        break

            if errors and name in errors:
                lbl.setText(name)
                lbl.setStyleSheet("color: #ff4444; font-weight: bold;")
                error_count += 1
            elif match:
                lbl.setText(match)
                lbl.setStyleSheet("color: #00ee66; font-weight: bold;")
                active_count += 1
            else:
                lbl.setText(name)
                lbl.setStyleSheet("color: #444444;")
        
        self._last_active = active_count
        self._last_errors = error_count
        self._update_header_text(self._title, active_count, error_count)

    def is_collapsed(self) -> bool:
        return self._collapsed

    # ── Private ───────────────────────────────────────────────────────
    def _toggle(self):
        self._collapsed = not self._collapsed
        self.grid_container.setVisible(not self._collapsed)
        self.timeline.setVisible(not self._collapsed)
        self._update_header_text(self._title, self._last_active, self._last_errors)
        self.toggled.emit()

    def _update_header_text(self, title: str, active: int | None = None, errors: int = 0):
        arrow = "▶" if self._collapsed else "▼"
        status_parts = []
        if active is not None:
            status_parts.append(f"{active} active")
        if errors > 0:
            status_parts.append(f"{errors} error")
            
        suffix = f"  ({', '.join(status_parts)})" if status_parts else ""
        self.header.setText(f" {arrow}  {title}{suffix}")

    def _header_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        # Call original implementation for clicking
        QPushButton.mousePressEvent(self.header, event)

    def _header_mouse_move(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.col_name)
        drag.setMimeData(mime)
        
        # Grab a preview image
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        drag.exec(Qt.DropAction.MoveAction)


class _ReorderableContainer(QWidget):
    """A container that allows reordering its children via drag and drop."""
    orderChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        col_name = event.mimeData().text()
        
        # Find the widget being moved
        source_widget = None
        for i in range(self._layout.count()):
            w = self._layout.itemAt(i).widget()
            if isinstance(w, _CollapsibleSection) and w.col_name == col_name:
                source_widget = w
                break
        
        if not source_widget:
            return

        # Find the drop index
        drop_pos = event.position().toPoint()
        index = 0
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if item.widget() == source_widget:
                continue
            if item.widget() and drop_pos.y() > item.widget().geometry().center().y():
                index = i + 1
            elif not item.widget(): # Stretch
                break
        
        # Move the widget
        self._layout.removeWidget(source_widget)
        self._layout.insertWidget(index, source_widget)
        self.orderChanged.emit()
        event.acceptProposedAction()


class FlagViewer(QDialog):
    """Non-modal dialog that displays all flag parameters with live updates."""
    stateChanged = pyqtSignal()
    timeClicked = pyqtSignal(float)

    def __init__(self, parent=None, collapse_state: dict | None = None, order: list[str] | None = None, version: str = "All"):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
        self.setWindowTitle("Flag and State Viewer")
        self.resize(600, 700)
        self.setMinimumWidth(420)

        self._collapse_state = collapse_state or {}
        self._version = version
        self._params = get_flag_params(version)
        self._order = order or list(self._params.keys())
        self._sections: dict[str, _CollapsibleSection] = {}
        self._df = None
        self._last_row = None

        self._build_ui()
        self._apply_theme()

    def _build_ui(self):
        # Clear existing layout if any
        if hasattr(self, 'container'):
            # Safely check if the C++ object still exists before accessing it
            if not sip.isdeleted(self.container):
                try:
                    # Save current collapse state and order before clearing
                    self._collapse_state = self.get_collapse_state()
                    self._order = self.get_section_order()
                except RuntimeError:
                    pass
            
            # Properly clear the layout
            layout = self.layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            
            self._sections.clear()

        outer = self.layout()
        if outer is None:
            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.container = _ReorderableContainer()
        self.container.orderChanged.connect(self.stateChanged.emit)
        self._layout = self.container._layout

        # Create one collapsible section per flag parameter in the requested order
        # First, include all params from the saved order that still exist in the CURRENT version
        ordered_params = [p for p in self._order if p in self._params]
        # Then, append any new params in this version not in the saved order
        for p in self._params:
            if p not in ordered_params:
                ordered_params.append(p)

        for col_name in ordered_params:
            kind, definition = self._params[col_name]
            title = SECTION_TITLES.get(col_name, col_name)
            
            # ArduPilot specific title overrides
            if self._version.startswith("Ardu") and col_name == "flightModeFlags (flags)":
                title = "Flight Mode"
            
            if kind == "text":
                flag_names = definition
            elif kind == "scalar":
                flag_names = [definition]
            else:
                # bits or enum (dictionary)
                flag_names = [definition[b] for b in sorted(definition.keys())]
            
            collapsed = self._collapse_state.get(col_name, False)
            section = _CollapsibleSection(col_name, title, flag_names, collapsed)
            section.toggled.connect(self.stateChanged.emit)
            section.timeClicked.connect(self.timeClicked.emit)
            self._sections[col_name] = section
            self._layout.addWidget(section)

        self._layout.addStretch()
        scroll.setWidget(self.container)
        outer.addWidget(scroll)

    # ── Public API ────────────────────────────────────────────────────
    def set_version(self, version: str):
        if self._version == version:
            return
        self._version = version
        self._params = get_flag_params(version)
        self._build_ui()
        
        # Re-apply data if we have it
        if self._df is not None:
            self.set_data(self._df)
        if self._last_row is not None:
            self.update_flags(self._last_row)

    def set_data(self, df):
        self._df = df
        if df is None or 'time (us)' not in df.columns:
            return
            
        time_s = (df['time (us)'] - df['time (us)'].iloc[0]) / 1e6
        
        for col_name, section in self._sections.items():
            # Try exact match, then try without " (flags)" suffix
            actual_col = col_name
            if actual_col not in df.columns:
                clean = col_name.split(" (")[0]
                if clean in df.columns:
                    actual_col = clean
                else:
                    continue
            
            raw_data = df[actual_col].ffill().bfill()
            
            # Robust change detection by decoding unique values
            unique_vals = raw_data.unique()
            mapping = {}
            for uv in unique_vals:
                active, errors = decode_flag_value(col_name, uv, self._params)
                mapping[uv] = tuple(sorted(list(active))) + tuple(sorted(list(errors)))
                
            canonical_state = raw_data.map(mapping)
            changes = canonical_state != canonical_state.shift(1)
            # First row always triggers vs NaN; skip it
            changes.iloc[0] = False
            
            change_times = time_s[changes]
            section.timeline.set_data(time_s, change_times.values)

    def update_flags(self, row):
        """Call with a pandas Series (one row of the dataframe) to refresh
        all sections with the current flag state."""
        self._last_row = row
        if self._df is not None and 'time (us)' in row.index:
            current_time_s = (row['time (us)'] - self._df['time (us)'].iloc[0]) / 1e6
            for section in self._sections.values():
                section.timeline.set_cursor(current_time_s)
                
        for col_name, (kind, definition) in self._params.items():
            section = self._sections.get(col_name)
            if section is None:
                continue

            # Try exact match, then try without suffix
            actual_col = col_name
            if actual_col not in row.index:
                clean = col_name.split(" (")[0]
                if clean in row.index:
                    actual_col = clean
                else:
                    continue

            raw = row[actual_col]
            active, errors = decode_flag_value(col_name, raw, self._params)
            section.set_active_flags(active, errors)

    def get_collapse_state(self) -> dict:
        """Return the current collapse state so the caller can persist it."""
        return {col: sec.is_collapsed() for col, sec in self._sections.items()}

    def get_section_order(self) -> list[str]:
        """Return the current order of sections as a list of col_names."""
        order = []
        for i in range(self._layout.count()):
            w = self._layout.itemAt(i).widget()
            if isinstance(w, _CollapsibleSection):
                order.append(w.col_name)
        return order

    # ── Theme ─────────────────────────────────────────────────────────
    def _apply_theme(self):
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QScrollArea { background: #1e1e1e; }
            QWidget { background: #1e1e1e; }
        """)
