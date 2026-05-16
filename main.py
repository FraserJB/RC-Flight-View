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

import sys
import os
import re
import html

if __name__ == "__main__":
    # PyInstaller windowed mode fix: redirect stdout/stderr if they are None
    # This MUST happen before faulthandler.enable() or it will crash on some systems
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')

    import faulthandler, traceback
    faulthandler.enable()
    
    def exception_hook(exc_type, exc_value, exc_tb):
        if sys.stderr is not None:
            try:
                print("=== UNCAUGHT EXCEPTION ===")
                traceback.print_exception(exc_type, exc_value, exc_tb)
            except:
                pass
        sys.exit(1)
    sys.excepthook = exception_hook

    from PyQt6.QtWidgets import QApplication, QSplashScreen
    from PyQt6.QtGui import QPixmap, QColor
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    
    splash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "splash.png")
    pixmap = QPixmap(splash_path)
    if pixmap.isNull():
        # fallback if splash.png is missing
        pixmap = QPixmap(640, 360)
        pixmap.fill(QColor("#111111"))

    splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()
    
    # Force a global font and size to prevent "Point size <= 0 (-1)" warnings
    app.setStyleSheet("QWidget { font-family: 'Segoe UI'; font-size: 8.5pt; }")

# Now perform heavy imports after the splash screen is visible
import json
import pandas as pd
import numpy as np

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QApplication,
                             QHBoxLayout, QPushButton, QSlider, QLabel, QFileDialog, QSplitter, QComboBox, QCheckBox, QSizePolicy, QGridLayout, QMessageBox, QDialog, QProgressDialog, QLineEdit)
from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtCore import QTimer, QRect, QPoint, QElapsedTimer, QThread, pyqtSignal, QEvent, QUrl, Qt
from PyQt6.QtGui import QPalette, QColor, QPainter, QPen, QFont, QDesktopServices, QImage, QPixmap

from data_parser import DataParser, BlackboxDecodeMissingError, detect_and_parse
from viewer_3d import Viewer3D
from plots import PlotWidget
from map_provider import MapProvider
from param_selector import ParameterSelector
from rc_overlay import RCSticksWidget
from flag_viewer import FlagViewer
from custom_url_dialog import CustomUrlDialog
from units_dialog import UnitsDialog
from unit_utils import apply_units_to_df, DEFAULT_UNITS

from parameters_config import INAV_PARAMS, ARDUPILOT_PARAMS, ENCODED_PARAMS, ARDUPILOT_ENCODED_PARAMS

import matplotlib
matplotlib.rcParams['font.size'] = 8
matplotlib.rcParams['font.family'] = 'Segoe UI'

class TimeSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.duration_s = 0
        self.start_time_us = 0
        self.df = None
        self.setMinimumHeight(40) # Extra space for labels

    def set_data(self, df):
        self.df = df
        if df is not None and len(df) > 0:
            self.start_time_us = df['time (us)'].iloc[0]
            self.duration_s = (df['time (us)'].iloc[-1] - self.start_time_us) / 1e6
        else:
            self.duration_s = 0
        self.update()

    def paintEvent(self, event):
        # Draw base slider first (it uses its own internal QPainter)
        super().paintEvent(event)
        
        if self.duration_s <= 0:
            return

        # Now draw our custom tick marks on top
        painter = QPainter(self)
        painter.setPen(QPen(QColor("#555555"), 1))
        f = self.font()
        f.setPointSize(8)
        painter.setFont(f)
        
        # The usable width for the handle is slightly less than widget width
        # QSlider internal geometry is a bit opaque, but we can approximate
        w = self.width() - 20 
        offset = 10
        
        for s in range(0, int(self.duration_s) + 1, 15):
            # Simple linear approximation is usually enough for ticks
            ratio = s / self.duration_s
            x = int(offset + ratio * w)
            
            if s % 60 == 0:
                # 1 minute major marker
                painter.setPen(QColor("#888888"))
                painter.drawLine(x, 28, x, 36)
                if s > 0:
                    m = s // 60
                    painter.drawText(x - 10, 39, f"{m}m")
            else:
                # 15 second minor marker
                painter.setPen(QColor("#555555"))
                painter.drawLine(x, 32, x, 36)
        painter.end()


# (DEFAULT_PARAMS has been moved to parameters_config.py)



def get_viewer_params_dict(config):
    """Helper to build the name->param mapping for the 3D viewer dropdown."""
    return {p['name']: p['param'] for p in config if p.get('trail', False)}

# Mapping of parameter values to human-readable labels


class MapWorker(QThread):
    finished = pyqtSignal(str, tuple) # map_path, map_bounds
    progress = pyqtSignal(int, int)    # current, total
    error = pyqtSignal(str)

    def __init__(self, map_provider, bounds):
        super().__init__()
        self.map_provider = map_provider
        self.bounds = bounds # (min_lat, max_lat, min_lon, max_lon)

    def run(self):
        try:
            def callback(curr, total):
                self.progress.emit(curr, total)
                
            map_path, map_bounds = self.map_provider.get_map(*self.bounds, progress_callback=callback)
            self.finished.emit(map_path, map_bounds)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RC Flight View")
        self.resize(1600, 900)
        
        # Set a default font to avoid QFont::setPointSize: Point size <= 0 (-1) warnings
        self.setFont(QFont("Segoe UI", 10))
        
        self.data_parser = None
        self.map_provider = MapProvider()
        self.df = None
        self.current_idx = 0
        self.is_playing = False
        self.base_step = 1.0 # Rows per frame for 1x speed
        self.unit_prefs = DEFAULT_UNITS.copy()
        self.raw_df = None
        self.param_config = [dict(p) for p in INAV_PARAMS] # Start with INAV as default
        self.blackbox_decode_path = None
        self.log_type = 'inav'  # 'inav' or 'ardupilot' — drives config file and UI routing
        
        self.init_ui()
        self.apply_dark_theme()
        
        self.map_worker = None
        self.flag_viewer = None
        self.flag_collapse_state = {}
        
        # Load persistent settings
        self.load_config()

        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)
        self.timer_interval = 33 # 30 FPS for better UI responsiveness
        
        self.playback_timer = QElapsedTimer()
        self.playback_idx = 0.0 # Float index for sub-frame interpolation

    def load_log_file(self, file_path):
        import os
        if os.path.exists(file_path):
            progress = QProgressDialog("Loading Log File...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Please Wait")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setAutoClose(True)
            progress.setAutoReset(True)
            progress.setMinimumDuration(0)
            progress.show()
            QApplication.processEvents()
            
            def update_progress(msg, pct):
                progress.setLabelText(msg)
                progress.setValue(pct)
                QApplication.processEvents()

            try:
                self.data_parser, self.log_type = detect_and_parse(
                    file_path,
                    decode_exe_path=self.blackbox_decode_path,
                    progress_callback=update_progress
                )
                
                # Reload config for the detected log type (ArduPilot vs INAV)
                # to apply firmware-specific units/inversions/etc.
                if self.log_type == 'ardupilot':
                    self.param_config = [dict(p) for p in ARDUPILOT_PARAMS]
                else:
                    self.param_config = [dict(p) for p in INAV_PARAMS]
                self.load_config()
                
                self.raw_df = self.data_parser.get_data()
                self.apply_units()
                self.lbl_file.setText(os.path.basename(file_path))
                
                # Hide RHS splash and show plots
                self.lbl_splash_rhs.setVisible(False)
                self.plot_widget.setVisible(True)
                
                # Update Firmware Version Display and Selector
                self.lbl_firmware.setText(self.data_parser.firmware_version)
                
                # Swap version selector items based on firmware type
                self.version_selector.blockSignals(True)
                self.version_selector.clear()
                if self.log_type == 'ardupilot':
                    vehicle = getattr(self.data_parser, 'vehicle_type', 'ArduPlane')
                    self.version_selector.addItems([vehicle])
                    self.version_selector.setCurrentIndex(0)
                else:
                    self.version_selector.addItems(["All", "INAV 7", "INAV 8", "INAV 9"])
                    if "INAV" in self.data_parser.firmware_version:
                        try:
                            version_num = self.data_parser.firmware_version.split(" ")[1]
                            major = version_num.split(".")[0]
                            target_text = f"INAV {major}"
                            index = self.version_selector.findText(target_text)
                            if index >= 0:
                                self.version_selector.setCurrentIndex(index)
                        except (IndexError, ValueError):
                            pass
                self.version_selector.blockSignals(False)
                
                # Update components with the selected version
                sel_version = self.version_selector.currentText()
                self.plot_widget.set_version(sel_version)
                if self.flag_viewer:
                    self.flag_viewer.set_version(sel_version)
                
                # Determine aircraft configuration from log data
                ac_type = "UNKNOWN"
                if self.log_type == 'ardupilot':
                    # Derive from vehicle type string
                    vt = getattr(self.data_parser, 'vehicle_type', '')
                    if getattr(self.data_parser, 'is_quadplane', False):
                        ac_type = 'QUADPLANE'
                    else:
                        ac_type_map = {'ArduPlane': 'AIRPLANE', 'ArduCopter': 'MULTIROTOR',
                                       'APMrover2': 'ROVER', 'Rover': 'ROVER'}
                        ac_type = ac_type_map.get(vt, vt.upper() if vt else "UNKNOWN")
                elif 'stateFlags (flags)' in self.df.columns:
                    # INAV: parse from stateFlags bitmask text
                    first_flags = str(self.df['stateFlags (flags)'].iloc[0])
                    type_keywords = ['AIRPLANE', 'MULTIROTOR', 'HELICOPTER', 'TRICOPTER', 'ROVER', 'BOAT']
                    for kw in type_keywords:
                        if kw in first_flags:
                            ac_type = kw
                            break
                
                # Determine active motors/servos by checking for any variation in the data
                # (ArduPilot logs all channels, so fixed values usually mean unused/ghost channels)
                motor_cols = [c for c in self.df.columns if c.startswith('motor[')]
                active_motors = sum(1 for c in motor_cols if self.df[c].max() != self.df[c].min())
                
                servo_cols = [c for c in self.df.columns if c.startswith('servo[')]
                active_servos = sum(1 for c in servo_cols if self.df[c].max() != self.df[c].min())
                
                # Special case: if it's a quad, we expect at least 4 motors even if idle
                if self.log_type == 'ardupilot' and 'MULTIROTOR' in ac_type and active_motors < 4:
                    # If they are all 1000, they are still 'motors'
                    present_motors = sum(1 for c in motor_cols if self.df[c].max() > 0)
                    active_motors = max(active_motors, min(4, present_motors))

                has_gps = 'Yes' if 'GPS_coord[0]' in self.df.columns else 'No'
                self.lbl_summary.setText(f"Type: {ac_type} | Motors: {active_motors} | Servos: {active_servos} | GPS: {has_gps}")
                self.btn_aircraft_info.setEnabled(True)
                
                # Hide Nav label for ArduPilot as it's redundant (Mode covers it)
                if self.log_type == 'ardupilot':
                    self.lbl_nav.hide()
                else:
                    self.lbl_nav.show()
                
                # Update UI
                self.slider.setMaximum(len(self.df) - 1)
                self.slider.setValue(0)
                self.slider.setEnabled(True)
                self.btn_play.setEnabled(True)
                
                # Update Path in 3D
                points = self.df[['pos_x', 'pos_y', 'pos_z']].values
                self.viewer_3d.set_path(points)
                self.viewer_3d.clear_ghost_trail()
                
                # Calculate base step for 1x speed
                # dt is in us
                dt_avg = self.df['time (us)'].diff().mean()
                if dt_avg > 0:
                    fps = 1000.0 / self.timer_interval # e.g. 50
                    rows_per_sec = 1000000.0 / dt_avg
                    self.base_step = rows_per_sec / fps
                else:
                    self.base_step = 1.0
                
                # Update Plots
                mappings = ARDUPILOT_ENCODED_PARAMS if self.log_type == 'ardupilot' else ENCODED_PARAMS
                self.plot_widget.set_mappings(mappings)
                self.plot_widget.update_params_config(self.param_config)
                self.plot_widget.set_data(self.df)
                
                if self.flag_viewer is not None and self.flag_viewer.isVisible():
                    self.flag_viewer.set_data(self.df)
                
                # Trigger Map Update (Async)
                self.trigger_map_update()
                
                # Update TimeSlider and Total Label
                total_s = (self.df['time (us)'].iloc[-1] - self.df['time (us)'].iloc[0]) / 1e6
                self.slider.set_data(self.df)
                
                tm, ts = divmod(total_s, 60)
                th, tm = divmod(tm, 60)
                if th > 0:
                    self.total_time_str = f"{int(th):02}:{int(tm):02}:{int(ts):02}"
                else:
                    self.total_time_str = f"{int(tm):02}:{int(ts):02}"
                

                
                # Sync trail coloring with current selection
                self.path_param_changed(self.combo_path_param.currentText())
                
                update_progress("Finalizing display...", 95)
                self.update_display(0)
                progress.setValue(100)

            except BlackboxDecodeMissingError:
                progress.cancel()
                self.handle_missing_blackbox_decode(file_path)
            except Exception as e:
                progress.cancel()
                import traceback
                error_msg = f"Error loading file: {e}\n\n{traceback.format_exc()}"
                print(error_msg)
                QMessageBox.critical(self, "Error Loading File", f"Failed to load the log file.\n\n{e}")

    def handle_missing_blackbox_decode(self, file_path):
        dlg = QDialog(self)
        dlg.setWindowTitle("Blackbox Decode Required")
        dlg.resize(400, 150)
        layout = QVBoxLayout(dlg)
        
        lbl = QLabel("The 'blackbox_decode.exe' tool is required to open this log file but was not found.\n\n"
                     "You can download the latest release from GitHub or locate it on your PC if already downloaded.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 10pt;")
        layout.addWidget(lbl)
        
        btn_layout = QHBoxLayout()
        
        btn_github = QPushButton("Download from GitHub")
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/iNavFlight/blackbox-tools/releases/latest")))
        btn_layout.addWidget(btn_github)
        
        btn_locate = QPushButton("Locate on PC")
        def locate():
            path, _ = QFileDialog.getOpenFileName(self, "Locate blackbox_decode.exe", "", "Executables (*.exe);;All Files (*)")
            if path:
                self.blackbox_decode_path = path
                self.save_config()
                dlg.accept()
                self.load_log_file(file_path)
        btn_locate.clicked.connect(locate)
        btn_layout.addWidget(btn_locate)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(dlg.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
        dlg.exec()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Toolbar / Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        self.btn_open = QPushButton("Open Log")
        self.btn_open.setFixedWidth(100)
        self.btn_open.clicked.connect(self.open_file)
        
        self.lbl_file = QLabel("No file loaded")
        self.lbl_file.setStyleSheet("color: #888888; font-size: 8.5pt;")
        
        self.lbl_firmware = QLabel("")
        self.lbl_firmware.setStyleSheet("color: #00aaff; font-weight: bold; font-size: 8.5pt; margin-left: 10pt;")
        
        self.lbl_summary = QLabel("")
        self.lbl_summary.setMinimumWidth(330)
        self.lbl_summary.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_summary.setStyleSheet("font-weight: bold; color: #00ffaa; font-size: 8.5pt;")

        self.btn_aircraft_info = QPushButton("i")
        self.btn_aircraft_info.setFixedSize(22, 22)
        self.btn_aircraft_info.setToolTip("Show aircraft configuration and output mapping")
        self.btn_aircraft_info.setEnabled(False)
        self.btn_aircraft_info.clicked.connect(self.open_aircraft_info)
        self.btn_aircraft_info.setStyleSheet("""
            QPushButton {
                color: #00ffaa;
                background-color: #1f1f1f;
                border: 1px solid #00aa77;
                border-radius: 11px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover { background-color: #263a33; }
            QPushButton:disabled {
                color: #555555;
                border-color: #444444;
                background-color: #1a1a1a;
            }
        """)
        
        self.lbl_mode = QLabel("Mode: ---")
        self.lbl_mode.setMinimumWidth(150)
        self.lbl_mode.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_mode.setStyleSheet("font-weight: bold; color: #ffaa00; font-size: 8.5pt;")
        
        self.lbl_nav = QLabel("Nav: ---")
        self.lbl_nav.setStyleSheet("font-weight: bold; color: #00aaff; font-size: 8.5pt;")
        
        self.lbl_telemetry = QLabel("X:0 Y:0 Z:0 T:0")
        self.lbl_telemetry.setStyleSheet("color: #888888; font-family: 'Consolas', 'Monaco', monospace; font-size: 8.5pt;")
        
        self.lbl_time = QLabel("00:00:00")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_time.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 11pt; color: #00aaff;")
        
        self.speed_selector = QComboBox()
        self.speed_selector.addItems(["0.1x", "0.2x", "0.5x", "1x", "2x", "5x", "8x", "10x", "12x", "16x", "24x", "32x", "64x"])
        self.speed_selector.setCurrentIndex(4) # Default to 2x
        self.speed_selector.setFixedWidth(65)
        self.speed_selector.setStyleSheet("QComboBox { background: #333; color: white; border: 1px solid #555; border-radius: 4pt; padding: 2pt 5pt; }")
        
        self.version_selector = QComboBox()
        self.version_selector.addItems(["All", "INAV 7", "INAV 8", "INAV 9"])  # Default; replaced when a log is loaded
        self.version_selector.setCurrentIndex(0) # Default to All
        self.version_selector.setFixedWidth(90)
        self.version_selector.setStyleSheet("QComboBox { background: #333; color: white; border: 1px solid #555; border-radius: 4pt; padding: 2pt 5pt; }")
        self.version_selector.currentIndexChanged.connect(self.on_version_changed)
        
        self.chk_ghost = QCheckBox("Breadcrumbs")
        self.chk_ghost.setChecked(True)
        self.chk_ghost.setStyleSheet("color: white; font-size: 8.5pt;")
        self.chk_ghost.stateChanged.connect(self.toggle_ghost)
        
        # Add to layout in order
        header_layout.addWidget(self.btn_open)
        header_layout.addWidget(self.lbl_file)
        header_layout.addWidget(self.lbl_firmware)
        header_layout.addStretch()
        header_layout.addSpacing(-25)
        header_layout.addWidget(self.btn_aircraft_info)
        header_layout.addWidget(self.lbl_summary)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.lbl_mode)
        header_layout.addWidget(self.lbl_nav)
        header_layout.addWidget(self.lbl_telemetry)
        header_layout.addStretch()
        self.btn_set_units = QPushButton("Set Units")
        self.btn_set_units.setFixedWidth(80)
        self.btn_set_units.clicked.connect(self.open_units_dialog)
        header_layout.addWidget(self.btn_set_units)
        
        header_layout.addSpacing(10)

        lbl_version = QLabel("Version:")
        lbl_version.setStyleSheet("color: #888888; font-size: 8.5pt;")
        header_layout.addWidget(lbl_version)
        header_layout.addWidget(self.version_selector)
        
        lbl_speed = QLabel("Speed:")
        lbl_speed.setStyleSheet("color: #888888; font-size: 8.5pt;")
        header_layout.addWidget(lbl_speed)
        header_layout.addWidget(self.speed_selector)
        
        main_layout.addLayout(header_layout)
        
        # Playback Controls (defined early so they can be added to RHS)
        controls_layout = QHBoxLayout()
        self.chk_center = QCheckBox("Plane in Centre")
        self.chk_center.setChecked(True)
        self.chk_center.setStyleSheet("color: white; font-size: 8.5pt;")
        
        self.btn_play = QPushButton("Play")
        self.btn_play.setFixedWidth(80)
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_play.setEnabled(False)
        controls_layout.addWidget(self.btn_play)
        
        chk_vbox = QVBoxLayout()
        chk_vbox.setSpacing(2)
        chk_vbox.addWidget(self.chk_center)
        chk_vbox.addWidget(self.chk_ghost)
        controls_layout.addLayout(chk_vbox)
        
        self.slider = TimeSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self.slider_changed)
        controls_layout.addWidget(self.slider)

        # Main Splitter (3D View and Plots)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 1. 3D Viewer Container (Left side)
        viewer_container = QWidget()
        viewer_vbox = QVBoxLayout(viewer_container)
        viewer_vbox.setContentsMargins(0,0,0,0)
        viewer_vbox.setSpacing(0)
        
        # Grid container to allow overlay
        viewer_grid_container = QWidget()
        viewer_grid = QGridLayout(viewer_grid_container)
        viewer_grid.setContentsMargins(0,0,0,0)
        
        self.viewer_3d = Viewer3D()
        viewer_grid.addWidget(self.viewer_3d, 0, 0)
        
        # Use a floating Tool Window parented to the main window to guarantee perfect OS-level compositing over OpenGL
        self.rc_overlay = RCSticksWidget(self)
        self.rc_overlay.show()
        
        # A 60 FPS timer keeps the floating window locked to the 3D viewer's top-right corner
        self.overlay_timer = QTimer(self)
        self.overlay_timer.timeout.connect(self.update_overlay_pos)
        self.overlay_timer.start(16)
        
        viewer_vbox.addWidget(viewer_grid_container)
        
        # Controls for the 3D viewer (Map visibility, Opacity, Trail Parameter)
        viewer_controls = QHBoxLayout()
        viewer_controls.setContentsMargins(10, 0, 10, 5)
        viewer_controls.setSpacing(10)
        
        self.chk_fpv = QCheckBox("Show FPV")
        self.chk_fpv.setChecked(True)
        self.chk_fpv.setStyleSheet("color: #888888; font-size: 7.5pt;")
        self.chk_fpv.stateChanged.connect(self.toggle_fpv)
        viewer_controls.addWidget(self.chk_fpv)

        self.chk_sticks = QCheckBox("Show Sticks")
        self.chk_sticks.setChecked(True)
        self.chk_sticks.setStyleSheet("color: #888888; font-size: 7.5pt;")
        self.chk_sticks.stateChanged.connect(self.toggle_sticks)
        viewer_controls.addWidget(self.chk_sticks)

        self.chk_map = QCheckBox("Show Map")
        self.chk_map.setChecked(True)
        self.chk_map.setStyleSheet("color: #888888; font-size: 7.5pt;")
        self.chk_map.stateChanged.connect(self.toggle_map)
        viewer_controls.addWidget(self.chk_map)
        

        
        viewer_controls.addSpacing(10)
        lbl_opacity = QLabel("Map Opacity:")
        lbl_opacity.setStyleSheet("color: #888888; font-size: 7.5pt;")
        viewer_controls.addWidget(lbl_opacity)
        
        self.slider_map_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_map_opacity.setRange(0, 100)
        self.slider_map_opacity.setValue(47)
        self.slider_map_opacity.setFixedWidth(60)
        self.slider_map_opacity.setStyleSheet("""
            QSlider::groove:horizontal { height: 4pt; background: #333; border-radius: 2pt; }
            QSlider::handle:horizontal { background: #888; width: 12pt; height: 12pt; margin: -4px 0; border-radius: 6pt; }
        """)
        self.slider_map_opacity.valueChanged.connect(self.on_map_opacity_changed)
        viewer_controls.addWidget(self.slider_map_opacity)
        
        viewer_controls.addSpacing(10)
        self.combo_map_provider = QComboBox()
        self.combo_map_provider.addItems(["Satellite (ESRI)", "Street (OSM)", "MapProxy / Custom"])
        self.combo_map_provider.setFixedWidth(130)
        self.combo_map_provider.setStyleSheet("QComboBox { background: #333; color: white; border: 1px solid #555; border-radius: 4pt; padding: 2pt 5pt; }")
        self.combo_map_provider.currentTextChanged.connect(self.on_map_provider_changed)
        viewer_controls.addWidget(self.combo_map_provider)

        self.btn_set_url = QPushButton("Set URL")
        self.btn_set_url.setFixedWidth(100)
        self.btn_set_url.setStyleSheet("color: #00aaff; font-weight: bold; background-color: #222; border: 1px solid #444;")
        self.btn_set_url.setVisible(False)
        self.btn_set_url.clicked.connect(self.open_custom_url_dialog)
        viewer_controls.addWidget(self.btn_set_url)
        
        viewer_controls.addStretch()
        
        self.lbl_map_progress = QLabel("")
        self.lbl_map_progress.setStyleSheet("color: #00aaff; font-size: 7.5pt; font-weight: bold; margin-right: 7.5pt;")
        self.lbl_map_progress.setVisible(False)
        viewer_controls.addWidget(self.lbl_map_progress)
        
        lbl_path = QLabel("Trail Parameter:")
        lbl_path.setStyleSheet("color: #888888; font-size: 7.5pt;")
        viewer_controls.addWidget(lbl_path)
        
        self.combo_path_param = QComboBox()
        self.update_trail_dropdown()
        self.combo_path_param.setCurrentText("Motor 1 Output")
        self.combo_path_param.currentTextChanged.connect(self.path_param_changed)
        self.combo_path_param.setFixedWidth(160)
        self.combo_path_param.setStyleSheet("QComboBox { background: #333; color: white; border: 1px solid #555; border-radius: 4pt; padding: 2pt 5pt; }")
        viewer_controls.addWidget(self.combo_path_param)
        viewer_vbox.addLayout(viewer_controls)
        
        # 2. RHS Container (Controls + Plots)
        self.rhs_container = QWidget()
        rhs_layout = QVBoxLayout(self.rhs_container)
        rhs_layout.setContentsMargins(5,0,0,0)
        
        # Inversion and Select Params row
        inv_layout = QHBoxLayout()
        inv_layout.setSpacing(15)
        self.chk_inv_roll = QCheckBox("Invert Roll")
        self.chk_inv_pitch = QCheckBox("Invert Pitch")
        self.chk_inv_pitch.setChecked(True)
        self.chk_inv_yaw = QCheckBox("Shift Yaw 180°")
        for chk in [self.chk_inv_roll, self.chk_inv_pitch, self.chk_inv_yaw]:
            chk.setStyleSheet("color: white; font-size: 7.5pt;")
            chk.toggled.connect(self.on_inversion_changed)
            inv_layout.addWidget(chk)
        inv_layout.addStretch()
        
        self.btn_select_params = QPushButton("Select Parameters")
        self.btn_select_params.setFixedWidth(140)
        self.btn_select_params.clicked.connect(self.open_param_selector)
        inv_layout.addWidget(self.btn_select_params)
        
        self.btn_flags = QPushButton("Flags")
        self.btn_flags.setFixedWidth(80)
        self.btn_flags.clicked.connect(self.open_flag_viewer)
        inv_layout.addWidget(self.btn_flags)
        
        lbl_columns = QLabel("Two Columns:")
        lbl_columns.setStyleSheet("color: #888888; font-size: 7.5pt; margin-left: 5pt;")
        inv_layout.addWidget(lbl_columns)
        
        self.combo_columns = QComboBox()
        self.combo_columns.addItems(["0", "6", "10", "20", "30"])
        self.combo_columns.setCurrentIndex(2) # Default to 10
        self.combo_columns.setFixedWidth(65)
        self.combo_columns.setStyleSheet("QComboBox { background: #333; color: white; border: 1px solid #555; border-radius: 4pt; padding: 2pt 5pt; }")
        self.combo_columns.currentIndexChanged.connect(self.update_column_threshold)
        inv_layout.addWidget(self.combo_columns)
        
        # Add components to RHS
        rhs_layout.addLayout(inv_layout)
        
        self.plot_widget = PlotWidget()
        self.plot_widget.timeClicked.connect(self._on_time_clicked)
        rhs_layout.addWidget(self.plot_widget)
        
        # Splash screen for RHS (visible only before log load)
        self.lbl_splash_rhs = QLabel()
        self.lbl_splash_rhs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_splash_rhs.setStyleSheet("background-color: #0b0b0b; border-radius: 10px;")
        
        base_path = os.path.dirname(os.path.abspath(__file__))
        splash_path = os.path.join(base_path, "splash.png")
        pix = QPixmap(splash_path)
        if not pix.isNull():
             grayscale_image = pix.toImage().convertToFormat(QImage.Format.Format_Grayscale8)
             pix = QPixmap.fromImage(grayscale_image)
             rhs_splash = pix.scaled(1000, 1000, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
             painter = QPainter(rhs_splash)
             painter.fillRect(rhs_splash.rect(), QColor(0, 0, 0, 140))
             painter.end()
             self.lbl_splash_rhs.setPixmap(rhs_splash)
        
        rhs_layout.addWidget(self.lbl_splash_rhs)
        self.plot_widget.setVisible(False)
        
        # Add both to splitter
        self.splitter.addWidget(viewer_container)
        self.splitter.addWidget(self.rhs_container)
        
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(self.splitter)
        
        # Bottom Playback Panel (Full Width)
        bottom_panel = QWidget()
        bottom_panel.setObjectName("bottomPanel")
        bottom_panel.setStyleSheet("#bottomPanel { border-top: 1px solid #333; }")
        bottom_vbox = QVBoxLayout(bottom_panel)
        bottom_vbox.setContentsMargins(10, 5, 10, 5)
        bottom_vbox.setSpacing(2)
        bottom_vbox.addLayout(controls_layout)
        
        # Centered time label at bottom of playback panel
        bottom_vbox.addWidget(self.lbl_time)
        
        main_layout.addWidget(bottom_panel)
        
        # Flight Stats Summary Bar (very bottom of window)
        self.stats_bar = QWidget()
        self.stats_bar.setObjectName("statsBar")
        self.stats_bar.setStyleSheet("""
            #statsBar {
                background-color: #1a1a2e;
                border-top: 1px solid #333;
            }
        """)
        self.stats_bar.setMinimumHeight(24)
        self.stats_bar.setVisible(True)
        
        stats_layout = QHBoxLayout(self.stats_bar)
        stats_layout.setContentsMargins(12, 4, 12, 4)
        stats_layout.setSpacing(0)
        
        self.lbl_flight_stats = QLabel("")
        self.lbl_flight_stats.setWordWrap(True)
        self.lbl_flight_stats.setStyleSheet(
            "color: #cccccc; font-family: 'Consolas', 'Monaco', monospace; font-size: 8pt;"
        )
        stats_layout.addWidget(self.lbl_flight_stats)
        
        main_layout.addWidget(self.stats_bar)


    def load_config(self):
        """Loads persistent settings from defaults_inav.cfg."""
        self._is_loading = True
        import os
        import json
        
        # Helper to get absolute path to config file in app directory
        def get_cfg_full_path(filename):
            base_path = os.path.dirname(os.path.abspath(__file__))
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            return os.path.join(base_path, filename)

        # Use separate config files for INAV vs ArduPilot
        cfg_name = "defaults_ardu.cfg" if getattr(self, 'log_type', 'inav') == 'ardupilot' else "defaults_inav.cfg"
        config_path = get_cfg_full_path(cfg_name)
        

        
        try:
            if not os.path.exists(config_path):

                self._is_loading = False
                return

            with open(config_path, "r") as f:
                config = json.load(f)
            
            # 0. Restore last log directory and blackbox tool path
            # Only restore if they are not already set in this session (to avoid overwriting what the user just picked)
            if "last_log_dir" in config and not getattr(self, 'last_log_dir', ''):
                self.last_log_dir = config["last_log_dir"]
            if "blackbox_decode_path" in config and not getattr(self, 'blackbox_decode_path', None):
                self.blackbox_decode_path = config["blackbox_decode_path"]
            
            if "units" in config:
                self.unit_prefs.update(config["units"])
                
            # 1. Restore Dropdowns & Checkboxes
            if "speed_index" in config:
                self.speed_selector.setCurrentIndex(min(config["speed_index"], self.speed_selector.count()-1))
            if "version_index" in config:
                self.version_selector.setCurrentIndex(min(config["version_index"], self.version_selector.count()-1))
            if "breadcrumbs" in config:
                self.chk_ghost.setChecked(config["breadcrumbs"])
            if "plane_in_centre" in config:
                self.chk_center.setChecked(config["plane_in_centre"])
            
            # Inversions
            if "invert_roll" in config:
                self.chk_inv_roll.setChecked(config["invert_roll"])
            if "invert_pitch" in config:
                self.chk_inv_pitch.setChecked(config["invert_pitch"])
            if "invert_yaw" in config:
                self.chk_inv_yaw.setChecked(config["invert_yaw"])
            
            # Map Controls
            if "show_map" in config:
                self.chk_map.setChecked(config["show_map"])

            if "map_opacity" in config:
                self.slider_map_opacity.setValue(config["map_opacity"])
            if "map_provider" in config:
                self.combo_map_provider.setCurrentText(config["map_provider"])
            if "custom_map_urls" in config:
                self.custom_map_urls = config["custom_map_urls"]
            else:
                self.custom_map_urls = []
            if "mapproxy_url" in config:
                self.current_mapproxy_url = config["mapproxy_url"]
            else:
                self.current_mapproxy_url = ""
            if "show_fpv" in config:
                self.chk_fpv.setChecked(config["show_fpv"])
            if "show_sticks" in config:
                self.chk_sticks.setChecked(config["show_sticks"])
            
            # 2. Restore Parameter Table (Order and Plot status)
            if "param_config" in config:
                saved_config = config["param_config"]
                new_param_config = []
                
                # Create a map of current params (those defined in code)
                current_params_map = {p['param']: p for p in self.param_config}
                
                # Add saved params in their saved order if they still exist in the code definitions
                for saved_p in saved_config:
                    p_id = saved_p['param']
                    if p_id in current_params_map:
                        p_item = current_params_map.pop(p_id)
                        p_item['plot'] = saved_p.get('plot', p_item['plot'])
                        p_item['trail'] = saved_p.get('trail', p_item.get('trail', False))
                        new_param_config.append(p_item)
                    else:
                        # Ad-hoc or removed parameter? Preserve it!
                        # We create a skeleton entry so the 'plot' and 'trail' choices are remembered.
                        # (The discovery logic in open_param_selector will fill in details if the column exists)
                        skeleton = {
                            "name": p_id,
                            "param": p_id,
                            "desc": f"Custom or discovered parameter: {p_id}",
                            "unit": "",
                            "color": "#ffffff",
                            "plot": saved_p.get('plot', False),
                            "trail": saved_p.get('trail', False)
                        }
                        new_param_config.append(skeleton)
                
                # Add any remaining params that are new in the code but weren't in the saved file
                for p_item in current_params_map.values():
                    new_param_config.append(p_item)
                
                self.param_config = new_param_config
                
                # Update plots to reflect loaded config
                self.plot_widget.update_params_config(self.param_config)
            
            # 3. Restore Trail Parameter (Outside param_config block)
            if "trail_param" in config:
                self.update_trail_dropdown()
                self.combo_path_param.setCurrentText(config["trail_param"])

            
            # Restore Flag Viewer state
            if "flag_collapse_state" in config:
                self.flag_collapse_state = config["flag_collapse_state"]
            if "flag_order" in config:
                self.flag_order = config["flag_order"]
            else:
                self.flag_order = None
            
            # Sync inversion state to plot widget
            self.on_inversion_changed(True)
            
            # Explicitly sync 3D viewer and overlay states
            # (setChecked doesn't fire signal if value matches UI default, causing sync issues)
            self.viewer_3d.set_fpv_active(self.chk_fpv.isChecked())
            self.viewer_3d.set_ghost_visible(self.chk_ghost.isChecked())
            self.viewer_3d.set_map_visible(self.chk_map.isChecked())
            if hasattr(self, 'rc_overlay'):
                self.rc_overlay.setVisible(self.chk_sticks.isChecked())

        except Exception as e:
            print(f"Error loading config: {e}")
        finally:
            self._is_loading = False

    def save_config(self):
        """Saves current GUI state to defaults_inav.cfg."""
        if getattr(self, '_is_loading', False):
            return
        


        config = {
            "units": getattr(self, 'unit_prefs', DEFAULT_UNITS.copy()),
            "speed_index": self.speed_selector.currentIndex(),
            "version_index": self.version_selector.currentIndex(),
            "breadcrumbs": self.chk_ghost.isChecked(),
            "plane_in_centre": self.chk_center.isChecked(),
            "invert_roll": self.chk_inv_roll.isChecked(),
            "invert_pitch": self.chk_inv_pitch.isChecked(),
            "invert_yaw": self.chk_inv_yaw.isChecked(),
            "show_map": self.chk_map.isChecked(),
            "extra_area": True,
            "show_fpv": self.chk_fpv.isChecked(),
            "show_sticks": self.chk_sticks.isChecked(),
            "map_opacity": self.slider_map_opacity.value(),
            "map_provider": self.combo_map_provider.currentText(),
            "mapproxy_url": getattr(self, 'current_mapproxy_url', ''),
            "custom_map_urls": getattr(self, 'custom_map_urls', []),
            "trail_param": self.combo_path_param.currentText(),
            "last_log_dir": getattr(self, 'last_log_dir', '') or '',
            "blackbox_decode_path": getattr(self, 'blackbox_decode_path', None),
            "param_config": [{"param": p["param"], "plot": p["plot"], "trail": p.get("trail", False)} for p in self.param_config],
            "flag_collapse_state": self.flag_collapse_state,
            "flag_order": getattr(self, "flag_order", None),
        }
        
        try:
            def get_cfg_full_path(filename):
                base_path = os.path.dirname(os.path.abspath(__file__))
                if getattr(sys, 'frozen', False):
                    base_path = os.path.dirname(sys.executable)
                return os.path.join(base_path, filename)

            is_ardu = getattr(self, 'log_type', 'inav') == 'ardupilot'
            cfg_name = "defaults_ardu.cfg" if is_ardu else "defaults_inav.cfg"
            config_path = get_cfg_full_path(cfg_name)
            

            
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
                
            # Always synchronize "Global" settings to the OTHER config file as well
            other_cfg_name = "defaults_inav.cfg" if is_ardu else "defaults_ardu.cfg"
            other_cfg_path = get_cfg_full_path(other_cfg_name)
            
            # If the other file exists, update it. If not, we don't necessarily need to create it yet.
            if os.path.exists(other_cfg_path):
                try:
                    other_data = {}
                    with open(other_cfg_path, "r") as f:
                        other_data = json.load(f)
                    
                    # Update global fields
                    globals_updated = False
                    for field in ["last_log_dir", "blackbox_decode_path", "map_provider", "mapproxy_url", "custom_map_urls"]:
                        new_val = config.get(field)
                        if new_val is not None:
                            other_data[field] = new_val
                            globals_updated = True
                    
                    if globals_updated:
                        with open(other_cfg_path, "w") as f:
                            json.dump(other_data, f, indent=4)
                except Exception as e:
                    print(f"Error syncing global settings to {other_cfg_name}: {e}")
                    
        except Exception as e:
            print(f"Error saving config: {e}")

    def closeEvent(self, event):
        # Persist flag viewer collapse state before saving config
        if self.flag_viewer is not None and self.flag_viewer.isVisible():
            self.flag_collapse_state = self.flag_viewer.get_collapse_state()
            self.flag_order = self.flag_viewer.get_section_order()
            self.flag_viewer.close()
        self.save_config()
        
        # Stop map worker thread
        if hasattr(self, 'map_worker') and self.map_worker is not None:
            if self.map_worker.isRunning():
                self.map_worker.quit()
                self.map_worker.wait(1000)
                
        # Stop timers
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'overlay_timer'):
            self.overlay_timer.stop()
            
        # Close overlay window
        if hasattr(self, 'rc_overlay'):
            self.rc_overlay.close()
            
        # Cleanup PyVista 3D Viewer
        if hasattr(self, 'viewer_3d'):
            try:
                self.viewer_3d.plotter.close()
            except Exception:
                pass
                
        super().closeEvent(event)
        
        # Force application quit
        QApplication.instance().quit()

    def apply_units(self):
        if self.raw_df is not None:
            self.df, self.param_config = apply_units_to_df(self.raw_df, self.param_config, self.unit_prefs)
            
            # Update the 3D path mesh FIRST so it matches the new df row count
            # before any trail/scalar updates reference it
            if hasattr(self, 'viewer_3d') and 'pos_x' in self.df.columns:
                dist_unit = self.unit_prefs.get('Distance', 'm')
                height_unit = self.unit_prefs.get('Height', 'm')
                self.viewer_3d.update_grid_units(dist_unit, height_unit)
                
                points = self.df[['pos_x', 'pos_y', 'pos_z']].values
                self.viewer_3d.set_path(points, reset_camera=False)
            
            # Now safe to update trail dropdown (which triggers path_param_changed)
            self.update_trail_dropdown()
            self.plot_widget.set_data(self.df)
            self.plot_widget.update_params_config(self.param_config)
            
            # If map is already loaded or needs redraw, we should ideally trigger that but it runs automatically on update_display
            
            # Update flight stats bar
            self.update_flight_stats()
            
    def update_flight_stats(self):
        """Compute and display key flight statistics in the stats bar."""
        if self.raw_df is None or self.df is None:
            self.lbl_flight_stats.setText("")
            return
        
        from unit_utils import convert_value
        dist_unit = self.unit_prefs.get('Distance', 'm')
        height_unit = self.unit_prefs.get('Height', 'm')
        speed_unit = self.unit_prefs.get('Speed', 'mph')
        
        raw = self.raw_df
        stats = []
        
        # Helper to format with unit
        def fmt(val, unit, decimals=1):
            if val is None:
                return "N/A"
            return f"{val:.{decimals}f}{unit}"
            
        # --- Home GPS Coordinates ---
        if self.data_parser and hasattr(self.data_parser, 'ref_lat') and self.data_parser.ref_lat is not None:
            lat_deg = np.degrees(self.data_parser.ref_lat)
            lon_deg = np.degrees(self.data_parser.ref_lon)
            stats.append(f"Home: {lat_deg:.6f}, {lon_deg:.6f}")
        
        # --- Max Speed (GPS ground speed, raw is m/s) ---
        if 'GPS_speed (m/s)' in raw.columns:
            max_speed_ms = raw['GPS_speed (m/s)'].max()
            conv, _ = convert_value(max_speed_ms, "Speed", "m/s", speed_unit)
            stats.append(f"Max Spd: {fmt(conv, speed_unit)}")
        
        # --- Max Altitude (pos_z, raw is meters) ---
        if 'pos_z' in raw.columns:
            max_alt_m = raw['pos_z'].max()
            conv, _ = convert_value(max_alt_m, "Height", "m", height_unit)
            stats.append(f"Max Alt: {fmt(conv, height_unit)}")
        
        # --- Max Current Draw (amperage (A)) ---
        if 'amperage (A)' in raw.columns:
            max_current = raw['amperage (A)'].max()
            stats.append(f"Max Current: {fmt(max_current, 'A')}")
        
        # --- Average Current Draw ---
        if 'amperage (A)' in raw.columns:
            avg_current = raw['amperage (A)'].mean()
            stats.append(f"Avg Current: {fmt(avg_current, 'A')}")
        
        # --- Min Battery Voltage ---
        if 'vbat (V)' in raw.columns:
            min_vbat = raw['vbat (V)'].min()
            stats.append(f"Min VBat: {fmt(min_vbat, 'V', 2)}")
        
        # --- Max Distance from Home (Euclidean XY) ---
        if 'pos_x' in raw.columns and 'pos_y' in raw.columns:
            dist_home = np.sqrt(raw['pos_x']**2 + raw['pos_y']**2)
            max_dist_m = dist_home.max()
            conv, _ = convert_value(max_dist_m, "Distance", "m", dist_unit)
            stats.append(f"Max Dist from Home: {fmt(conv, dist_unit)}")
        
        # --- Downrange Distance (max extent on X axis, matches 3D grid) ---
        if 'pos_x' in raw.columns:
            downrange_m = raw['pos_x'].max() - raw['pos_x'].min()
            conv, _ = convert_value(downrange_m, "Distance", "m", dist_unit)
            stats.append(f"Total Downrange: {fmt(conv, dist_unit)}")
        
        # --- Crossrange Distance (max extent on Y axis, matches 3D grid) ---
        if 'pos_y' in raw.columns:
            crossrange_m = raw['pos_y'].max() - raw['pos_y'].min()
            conv, _ = convert_value(crossrange_m, "Distance", "m", dist_unit)
            stats.append(f"Total Crossrange: {fmt(conv, dist_unit)}")
        
        # --- Max G (Horizontal) — from accSmooth X/Y, scale = 2048 LSB/G ---
        # (ArduPilot data is pre-scaled to this convention in ardupilot_parser.py)
        if 'accSmooth[0]' in raw.columns and 'accSmooth[1]' in raw.columns:
            g_hor = np.sqrt(raw['accSmooth[0]']**2 + raw['accSmooth[1]']**2) / 2048.0
            stats.append(f"Max G(Horz): {g_hor.max():.2f}G")
        
        # --- Max G (Vertical) — from accSmooth Z, subtract 1G gravity ---
        if 'accSmooth[2]' in raw.columns:
            g_vert = (raw['accSmooth[2]'] / 2048.0 - 1.0).abs()
            stats.append(f"Max G(Vert): {g_vert.max():.2f}G")
        
        # --- Min Satellites ---
        if 'GPS_numSat' in raw.columns:
            min_sats = int(raw['GPS_numSat'].min())
            stats.append(f"Min Sats: {min_sats}")
        
        # --- Min RSSI ---
        if 'rssi' in raw.columns:
            min_rssi = int(raw['rssi'].min())
            stats.append(f"Min RSSI: {min_rssi}")
        
        # --- Max RPM ---
        if 'escRPM' in raw.columns:
            max_rpm = int(raw['escRPM'].max())
            stats.append(f"Max RPM: {max_rpm}")
        # --- Total Distance Flown (cumulative path length) ---
        if 'pos_x' in raw.columns and 'pos_y' in raw.columns and 'pos_z' in raw.columns:
            dx = raw['pos_x'].diff().fillna(0)
            dy = raw['pos_y'].diff().fillna(0)
            dz = raw['pos_z'].diff().fillna(0)
            total_dist_m = np.sqrt(dx**2 + dy**2 + dz**2).sum()
            conv, _ = convert_value(total_dist_m, "Distance", "m", dist_unit)
            stats.append(f"Total Dist: {fmt(conv, dist_unit)}")
        
        # --- Total Armed Time ---
        if 'time (us)' in raw.columns:
            armed_mask = None
            if 'Armed' in raw.columns:
                armed_numeric = pd.to_numeric(raw['Armed'], errors='coerce')
                if armed_numeric.notna().any():
                    armed_mask = armed_numeric.fillna(0) != 0
                else:
                    armed_text = raw['Armed'].astype(str).str.strip().str.lower()
                    armed_mask = armed_text.isin({'1', 'true', 'armed', 'yes'})
            elif 'stateFlags (flags)' in raw.columns:
                flags = raw['stateFlags (flags)'].astype(str)
                armed_mask = flags.str.contains(r'(?:^|\|)ARMED(?:$|\|)', regex=True, na=False)
            elif 'flightModeFlags (flags)' in raw.columns:
                flags = raw['flightModeFlags (flags)'].astype(str)
                armed_mask = flags.str.contains(r'(?:^|\|)ARM(?:$|\|)', regex=True, na=False)

            if armed_mask is not None:
                armed_mask = pd.Series(armed_mask, index=raw.index).fillna(False).astype(bool)
                time_col = raw['time (us)']
                dt = time_col.diff().fillna(0)
                armed_us = dt[armed_mask].sum()
                armed_s = armed_us / 1e6
                am, as_ = divmod(armed_s, 60)
                stats.append(f"Armed: {int(am)}m{int(as_)}s")
        
        # Build the display string
        separator = "   \u2502   "  # │ character with spacing
        stats_text = separator.join(stats)
        
        self.lbl_flight_stats.setText(stats_text)
        # Force a layout refresh to prevent rendering artifacts
        self.centralWidget().update()

    def open_aircraft_info(self):
        if self.df is None or self.data_parser is None:
            QMessageBox.information(self, "Aircraft Information", "Load a log to view aircraft configuration details.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Aircraft Configuration")
        dlg.resize(720, 560)
        layout = QVBoxLayout(dlg)

        text = QTextBrowser()
        text.setOpenExternalLinks(False)
        text.setHtml(self.build_aircraft_info_html())
        text.setStyleSheet("""
            QTextBrowser {
                background-color: #151515;
                color: #e8e8e8;
                border: 1px solid #444;
                font-family: 'Segoe UI';
                font-size: 9pt;
            }
        """)
        layout.addWidget(text)

        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(90)
        btn_close.clicked.connect(dlg.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        dlg.exec()

    def build_aircraft_info_text(self):
        lines = []
        summary = self.lbl_summary.text().strip() or "No aircraft summary available"
        firmware = getattr(self.data_parser, 'firmware_version', 'Unknown')
        vehicle_type = getattr(self.data_parser, 'vehicle_type', None)
        is_quadplane = getattr(self.data_parser, 'is_quadplane', False)
        message_counts = getattr(self.data_parser, 'message_counts', {}) or {}

        lines.append("AIRCRAFT SUMMARY")
        lines.append(summary)
        lines.append(f"Firmware: {firmware}")
        if vehicle_type:
            lines.append(f"ArduPilot vehicle type: {vehicle_type}")
        if self.log_type == 'ardupilot':
            lines.append(f"QuadPlane: {'Yes' if is_quadplane else 'No'}")
        lines.append("")

        lines.extend(self._build_output_mapping_lines())
        lines.append("")
        lines.extend(self._build_hardware_lines(message_counts))
        return "\n".join(lines)

    def build_aircraft_info_html(self):
        data = self._collect_aircraft_info()
        styles = """
        <style>
            body { background:#151515; color:#e8e8e8; font-family:'Segoe UI', Arial, sans-serif; font-size:12px; }
            h1 { color:#00ffaa; font-size:20px; margin:0 0 10px 0; }
            h2 { color:#00aaff; font-size:15px; margin:18px 0 8px 0; border-bottom:1px solid #333; padding-bottom:4px; }
            .summary { background:#202020; border:1px solid #383838; border-radius:6px; padding:10px 12px; margin-bottom:8px; }
            .muted { color:#999; }
            .note { color:#b8d8ff; background:#1b2430; border-left:3px solid #00aaff; padding:7px 9px; margin-top:10px; }
            table { width:100%; border-collapse:collapse; margin:6px 0 12px 0; }
            th { background:#2d2d2d; color:#ffffff; text-align:left; padding:6px; border:1px solid #404040; }
            td { padding:6px; border:1px solid #343434; vertical-align:top; }
            tr:nth-child(even) td { background:#1d1d1d; }
            .ok { color:#00ffaa; font-weight:bold; }
            .warn { color:#ffaa00; font-weight:bold; }
            .mono { font-family:'Consolas', 'Monaco', monospace; }
            ul { margin-top:4px; padding-left:18px; }
            li { margin:4px 0; }
        </style>
        """

        parts = [styles, "<h1>Aircraft Configuration</h1>"]
        parts.append("<div class='summary'>")
        for line in data["summary"]:
            parts.append(f"<div>{html.escape(line)}</div>")
        parts.append("</div>")

        parts.append("<h2>Output Mapping</h2>")
        parts.append(self._output_rows_to_html("Motors", data["motors"]))
        parts.append(self._output_rows_to_html("Servos / Control Surfaces", data["servos"]))
        if data["mapping_note"]:
            parts.append("<div class='note'>")
            parts.append("<br>".join(html.escape(line) for line in data["mapping_note"]))
            parts.append("</div>")

        parts.append("<h2>Logged Hardware / Sensor Evidence</h2>")
        parts.append("<ul>")
        for item in data["hardware"]:
            cls = "ok" if item.get("status") == "yes" else "warn"
            detail = f" <span class='muted'>{html.escape(item['detail'])}</span>" if item.get("detail") else ""
            parts.append(f"<li><span class='{cls}'>{html.escape(item['label'])}</span>{detail}</li>")
        parts.append("</ul>")
        return "\n".join(parts)

    def _output_rows_to_html(self, title, rows):
        if not rows:
            return f"<p class='muted'>{html.escape(title)}: none found in the processed log.</p>"

        parts = [f"<h3>{html.escape(title)}</h3>", "<table>"]
        parts.append("<tr><th>Viewer</th><th>Source</th><th>Function ID</th><th>Description</th><th>Range</th><th>Mapping note</th></tr>")
        for row in rows:
            parts.append(
                "<tr>"
                f"<td class='mono'>{html.escape(row['viewer'])}</td>"
                f"<td class='mono'>{html.escape(row['source'])}</td>"
                f"<td class='mono'>{html.escape(row['function_id'])}</td>"
                f"<td>{html.escape(row['description'])}</td>"
                f"<td class='mono'>{html.escape(row['range'])}</td>"
                f"<td>{html.escape(row.get('note', ''))}</td>"
                "</tr>"
            )
        parts.append("</table>")
        return "\n".join(parts)

    def _collect_aircraft_info(self):
        summary = self.lbl_summary.text().strip() or "No aircraft summary available"
        firmware = getattr(self.data_parser, 'firmware_version', 'Unknown')
        vehicle_type = getattr(self.data_parser, 'vehicle_type', None)
        is_quadplane = getattr(self.data_parser, 'is_quadplane', False)
        message_counts = getattr(self.data_parser, 'message_counts', {}) or {}

        summary_lines = [summary, f"Firmware: {firmware}"]
        if vehicle_type:
            summary_lines.append(f"ArduPilot vehicle type: {vehicle_type}")
        if self.log_type == 'ardupilot':
            summary_lines.append(f"QuadPlane: {'Yes' if is_quadplane else 'No'}")

        motors, servos, mapping_note = self._collect_output_mapping()
        hardware = self._collect_hardware_info(message_counts)
        return {
            "summary": summary_lines,
            "motors": motors,
            "servos": servos,
            "mapping_note": mapping_note,
            "hardware": hardware,
        }

    def _build_output_mapping_lines(self):
        lines = ["OUTPUT MAPPING"]
        motors, servos, mapping_note = self._collect_output_mapping()
        for title, rows, empty in [
            ("Motors:", motors, "Motors: none found in the processed log."),
            ("Servos / control surfaces:", servos, "Servos / control surfaces: none found in the processed log."),
        ]:
            if rows:
                lines.append(title)
                for row in rows:
                    bits = [row["viewer"]]
                    if row["source"]:
                        bits.append(row["source"])
                    if row["function_id"]:
                        bits.append(row["function_id"])
                    if row["description"]:
                        bits.append(row["description"])
                    bits.append(row["range"])
                    lines.append("  " + ": ".join([bits[0], ", ".join(bits[1:])]))
                    if row.get("note"):
                        lines.append(f"    {row['note']}")
            else:
                lines.append(empty)
        if mapping_note:
            lines.append("")
            lines.append("ArduPilot mapping note:")
            lines.extend(f"  {line}" for line in mapping_note)
        return lines

    def _collect_output_mapping(self):
        motors = []
        servos = []
        mapping_note = []
        df = self.df
        output_mapping = getattr(self.data_parser, 'output_mapping', {}) or {}

        def output_index(col):
            match = re.search(r'\[(\d+)\]', col)
            return int(match.group(1)) if match else 999

        def range_text(col):
            if col not in df.columns:
                return "not present in processed data"
            values = pd.to_numeric(df[col], errors='coerce').dropna()
            if values.empty:
                return "no numeric output samples"
            mn = values.min()
            mx = values.max()
            state = "active" if mx != mn else "fixed"
            return f"{int(round(mn))}-{int(round(mx))} us, {state}"

        if output_mapping:
            motor_items = sorted(
                ((col, info) for col, info in output_mapping.items() if col.startswith('motor[')),
                key=lambda pair: output_index(pair[0])
            )
            servo_items = sorted(
                ((col, info) for col, info in output_mapping.items() if col.startswith('servo[')),
                key=lambda pair: output_index(pair[0])
            )

            if motor_items:
                for col, info in motor_items:
                    ch = info.get('channel', '?')
                    func_id = info.get('function_id')
                    func_name = info.get('function_name', 'Unknown')
                    motors.append({
                        "viewer": col,
                        "source": f"RCOU C{ch}",
                        "function_id": f"SERVO{ch}_FUNCTION={func_id}" if func_id is not None else "",
                        "description": func_name,
                        "range": range_text(col),
                        "note": info.get('note', ''),
                    })

            if servo_items:
                for col, info in servo_items:
                    ch = info.get('channel', '?')
                    func_id = info.get('function_id')
                    func_name = info.get('function_name', 'Unknown')
                    servos.append({
                        "viewer": col,
                        "source": f"RCOU C{ch}",
                        "function_id": f"SERVO{ch}_FUNCTION={func_id}" if func_id is not None else "",
                        "description": func_name,
                        "range": range_text(col),
                        "note": info.get('note', ''),
                    })
        else:
            motor_cols = sorted([c for c in df.columns if c.startswith('motor[')], key=output_index)
            servo_cols = sorted([c for c in df.columns if c.startswith('servo[')], key=output_index)
            for col in motor_cols:
                motors.append({
                    "viewer": col,
                    "source": "Processed log column",
                    "function_id": "",
                    "description": "Motor output",
                    "range": range_text(col),
                    "note": "",
                })
            for col in servo_cols:
                servos.append({
                    "viewer": col,
                    "source": "Processed log column",
                    "function_id": "",
                    "description": "Servo output",
                    "range": range_text(col),
                    "note": "",
                })

        if self.log_type == 'ardupilot':
            mapping_note = [
                "Numbered Motor functions are shown as motor[n]. Throttle-style outputs are mapped to motor slots.",
                "Servo/control-surface outputs keep their physical RCOU/SERVO channel as servo[channel-1].",
            ]
        return motors, servos, mapping_note

    def _build_hardware_lines(self, message_counts):
        lines = ["LOGGED HARDWARE / SENSOR EVIDENCE"]
        for item in self._collect_hardware_info(message_counts):
            detail = f" - {item['detail']}" if item.get("detail") else ""
            lines.append(f"  {item['label']}{detail}")
        return lines

    def _collect_hardware_info(self, message_counts):
        items = []
        df = self.df

        def has_col(*cols):
            return any(col in df.columns for col in cols)

        def msg_count(*names):
            return sum(message_counts.get(name, 0) for name in names)

        gps_bits = []
        if has_col('GPS_coord[0]', 'GPS_coord[1]') or msg_count('GPS'):
            if 'GPS_numSat' in df.columns:
                sats = pd.to_numeric(df['GPS_numSat'], errors='coerce').dropna()
                if not sats.empty:
                    gps_bits.append(f"satellites {int(sats.min())}-{int(sats.max())}")
            if 'GPS_fixType' in df.columns:
                fixes = sorted(str(v) for v in pd.Series(df['GPS_fixType']).dropna().unique()[:6])
                if fixes:
                    gps_bits.append(f"fix values {', '.join(fixes)}")
            if msg_count('GPS'):
                gps_bits.append(f"GPS messages {msg_count('GPS')}")
            items.append({"label": "GPS: Yes", "detail": "; ".join(gps_bits), "status": "yes"})
        else:
            items.append({"label": "GPS: No", "detail": "No GPS fields found", "status": "no"})

        if has_col('BaroAlt (cm)', 'Control Altitude (Copter)', 'Baro Altitude (Copter)') or msg_count('BARO'):
            detail = f"{msg_count('BARO')} BARO messages" if msg_count('BARO') else ""
            items.append({"label": "Barometer: Yes", "detail": detail, "status": "yes"})
        else:
            items.append({"label": "Barometer: No", "detail": "No BARO fields found", "status": "no"})

        airspeed_cols = [
            'CTUN_As', 'CTUN_SAs', 'CTUN_AsT', 'Target Airspeed',
            'TECS Airspeed', 'TECS Desired Airspeed', 'TECS_v', 'TECS_v_dem'
        ]
        if msg_count('ARSP'):
            items.append({"label": "Pitot / airspeed sensor: Yes", "detail": f"{msg_count('ARSP')} ARSP messages", "status": "yes"})
        elif has_col(*airspeed_cols):
            present = [col for col in airspeed_cols if col in df.columns]
            items.append({"label": "Pitot / airspeed sensor: Maybe", "detail": f"airspeed fields logged ({', '.join(present)}), but no ARSP message was logged", "status": "no"})
        else:
            items.append({"label": "Pitot / airspeed sensor: No", "detail": "No airspeed fields found", "status": "no"})

        if has_col('gyroADC[0]', 'accSmooth[0]') or msg_count('IMU'):
            detail = f"{msg_count('IMU')} IMU messages" if msg_count('IMU') else ""
            items.append({"label": "IMU / accelerometer / gyro: Yes", "detail": detail, "status": "yes"})
        if has_col('magADC[0]', 'Mag Health') or msg_count('MAG'):
            detail = f"{msg_count('MAG')} MAG messages" if msg_count('MAG') else ""
            items.append({"label": "Compass / magnetometer: Yes", "detail": detail, "status": "yes"})
        if has_col('vbat (V)', 'amperage (A)') or msg_count('BAT'):
            detail = f"{msg_count('BAT')} BAT messages" if msg_count('BAT') else ""
            items.append({"label": "Battery monitor: Yes", "detail": detail, "status": "yes"})
        if has_col('vibeX', 'vibeY', 'vibeZ') or msg_count('VIBE'):
            detail = f"{msg_count('VIBE')} VIBE messages" if msg_count('VIBE') else ""
            items.append({"label": "Vibration logging: Yes", "detail": detail, "status": "yes"})
        esc_messages = msg_count('ESC', 'ESC2')
        has_esc_fields = any(c.startswith('esc') for c in df.columns)
        if esc_messages:
            items.append({"label": "ESC telemetry: Yes", "detail": f"{esc_messages} ESC messages", "status": "yes"})
        elif has_esc_fields:
            items.append({"label": "ESC telemetry: Yes", "detail": "processed ESC fields found", "status": "yes"})

        rpm_messages = msg_count('RPM')
        if rpm_messages:
            items.append({"label": "RPM sensor/telemetry: Yes", "detail": f"{rpm_messages} RPM messages", "status": "yes"})
        elif has_col('escRPM'):
            items.append({"label": "RPM sensor/telemetry: Yes", "detail": "ESC RPM field found", "status": "yes"})
        if msg_count('RFND', 'RNGF') or any(c.startswith(('RFND_', 'RNGF_')) for c in df.columns):
            detail = f"{msg_count('RFND', 'RNGF')} rangefinder messages" if msg_count('RFND', 'RNGF') else "processed rangefinder fields found"
            items.append({"label": "Rangefinder: Yes", "detail": detail, "status": "yes"})
        if msg_count('CAM'):
            items.append({"label": "Camera trigger/events: Yes", "detail": f"{msg_count('CAM')} CAM messages", "status": "yes"})
        if msg_count('RCIN'):
            items.append({"label": "RC input: Yes", "detail": f"{msg_count('RCIN')} RCIN messages", "status": "yes"})
        if msg_count('RCOU', 'RCO2'):
            items.append({"label": "Servo/motor output: Yes", "detail": f"{msg_count('RCOU', 'RCO2')} RCOU/RCO2 messages", "status": "yes"})

        return items

    def open_units_dialog(self):
        dialog = UnitsDialog(current_prefs=self.unit_prefs, parent=self)
        if dialog.exec():
            self.unit_prefs = dialog.get_prefs()
            self.save_config()
            
            # Re-apply units to the loaded data and refresh display
            if self.raw_df is not None:
                current_time = self.df['time (us)'].iloc[self.current_idx] if self.df is not None and len(self.df) > self.current_idx else 0
                self.apply_units()
                
                # Update UI elements
                self.update_display(self.current_idx)
                if self.flag_viewer and self.flag_viewer.isVisible():
                    self.flag_viewer.set_data(self.df)
                    row = self.df.iloc[self.current_idx]
                    self.flag_viewer.update_flags(row)
                    
                # Re-scale existing map if loaded (no re-download needed)
                self._rescale_map()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #121212;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #1b5e20 !important;
                border: 1px solid #2e7d32;
                color: #ffffff;
                padding: 5pt 15pt;
                min-height: 25pt;
                border-radius: 20pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2e7d32;
                border: 1px solid #4caf50;
            }
            QPushButton:pressed {
                background-color: #0d3b0f;
            }
            QPushButton:disabled {
                color: #999999;
                background-color: #2a2a2a;
                border: 1px solid #444444;
            }
            QComboBox { 
                background: #333333;
                color: white; 
                border: 1px solid #555555; 
                border-radius: 4pt; 
                padding: 3pt 5pt; 
            }
            QComboBox:hover { border: 1px solid #00aaff; }
            QSlider::groove:horizontal {
                border: 1px solid #333;
                height: 6px;
                background: #222;
                margin: 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #0078d7;
                border: 1px solid white;
                width: 22pt;
                height: 22pt;
                margin: -11px 0;
                border-radius: 11pt;
            }
            QSplitter::handle {
                background: #333333;
            }
        """)

    def open_file(self):
        start_dir = getattr(self, 'last_log_dir', '') or ''
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Flight Log", start_dir, "Flight Logs (*.TXT *.BBL *.BIN);;INAV Blackbox (*.TXT *.BBL);;ArduPilot DataFlash (*.BIN);;All Files (*)")
        if file_path:
            self.last_log_dir = os.path.dirname(file_path)
            self.save_config()
            self.load_log_file(file_path)

    def toggle_play(self):
        if self.is_playing:
            self.timer.stop()
            self.btn_play.setText("Play")
            # Force a final render of any buffered breadcrumbs when pausing
            if hasattr(self.viewer_3d, '_update_ghost_mesh') and self.chk_ghost.isChecked():
                self.viewer_3d._update_ghost_mesh()
        else:
            self.playback_idx = float(self.current_idx)
            self.playback_timer.start()
            self.timer.start(self.timer_interval)
            self.btn_play.setText("Pause")
        self.is_playing = not self.is_playing

    def update_trail_dropdown(self):
        """Refreshes the 3D viewer dropdown based on the current config."""
        if not hasattr(self, 'combo_path_param'):
            return
        current = self.combo_path_param.currentText()
        self.combo_path_param.blockSignals(True)
        self.combo_path_param.clear()
        params = get_viewer_params_dict(self.param_config)
        self.combo_path_param.addItems(sorted(list(params.keys())))
        if current in params:
            self.combo_path_param.setCurrentText(current)
        self.combo_path_param.blockSignals(False)
        
        # Trigger an update to the 3D viewer to ensure sync
        self.path_param_changed(self.combo_path_param.currentText())

    def path_param_changed(self, text):
        if self.df is None:
            return
        
        # Get mapping from config
        params = get_viewer_params_dict(self.param_config)
        target = params.get(text)
        if not target:
            return
        
        # Find unit in config
        unit = ""
        for p in self.param_config:
            if p['name'] == text:
                unit = p.get('unit', "")
                break

        # Try direct match first
        if target in self.df.columns:
            scalars = self.df[target].values
            self.viewer_3d.update_path_scalars(scalars, text, unit)
            return

        # Try matching by stripping spaces or common variations
        clean_target = target.replace(" ", "")
        for col in self.df.columns:
            if col.replace(" ", "") == clean_target:
                scalars = self.df[col].values
                self.viewer_3d.update_path_scalars(scalars, text, unit)
                return
        
        # Fallback for motors (e.g. motor[0] vs motor_0)
        if "motor" in target:
            idx = target[target.find("[")+1 : target.find("]")]
            for col in self.df.columns:
                if "motor" in col.lower() and idx in col:
                    scalars = self.df[col].values
                    self.viewer_3d.update_path_scalars(scalars, text, unit)
                    return

        print(f"Parameter {target} not found in log.")
        self.save_config()

    def update_column_threshold(self):
        self.save_config()
        try:
            val = int(self.combo_columns.currentText())
            self.plot_widget.column_threshold = val
            if self.df is not None:
                self.plot_widget.refresh_plots()
        except:
            pass

    def open_param_selector(self):
        # Prepare lookup for descriptions etc
        base_params = ARDUPILOT_PARAMS if self.log_type == 'ardupilot' else INAV_PARAMS
        all_params_info = {p['param']: p for p in base_params}
        
        # If we have a log loaded, we might want to add ANY missing columns from the log to the config
        if self.df is not None:
            existing_params = [p['param'] for p in self.param_config]
            for col in self.df.columns:
                if col not in existing_params and col not in ['time (us)', 'pos_x', 'pos_y', 'pos_z']:
                    new_item = {
                        "name": col, 
                        "param": col, 
                        "desc": f"Additional data field: {col}", 
                        "unit": "", 
                        "color": "#ffffff", 
                        "plot": False
                    }
                    self.param_config.append(new_item)
                    all_params_info[col] = new_item

        available_cols = set(self.df.columns) if self.df is not None else None
        default_order = [p['param'] for p in base_params]
        dialog = ParameterSelector(self.param_config, all_params_info, self, 
                                   available_cols=available_cols, 
                                   default_order=default_order)
        if dialog.exec():
            # Update plots
            mappings = ARDUPILOT_ENCODED_PARAMS if self.log_type == 'ardupilot' else ENCODED_PARAMS
            self.plot_widget.set_mappings(mappings)
            self.plot_widget.update_params_config(self.param_config)
            # Update 3D viewer trail dropdown
            self.update_trail_dropdown()
            
            if self.df is not None:
                self.update_display(self.current_idx)
            self.save_config()

    def toggle_ghost(self, state):
        visible = (state == Qt.CheckState.Checked.value)
        self.viewer_3d.set_ghost_visible(visible)
        self.save_config()

    def on_version_changed(self):
        version = self.version_selector.currentText()
        # Propagate to plot widget
        self.plot_widget.set_version(version)
        # Propagate to flag viewer
        if self.flag_viewer is not None:
            self.flag_viewer.set_version(version)
        
        # Refresh current display to update labels
        if self.df is not None:
            self.update_display(self.current_idx)
        self.save_config()

    def open_flag_viewer(self):
        """Open (or re-show) the Flag and State Viewer."""
        if self.flag_viewer is None or not self.flag_viewer.isVisible():
            # Pass None as parent to allow the window to drop behind the main app
            self.flag_viewer = FlagViewer(None, 
                                          collapse_state=self.flag_collapse_state,
                                          order=getattr(self, 'flag_order', None),
                                          version=self.version_selector.currentText())
            self.flag_viewer.setWindowModality(Qt.WindowModality.NonModal)
            self.flag_viewer.stateChanged.connect(self._on_flag_viewer_closed)
            self.flag_viewer.finished.connect(self._on_flag_viewer_closed)
            self.flag_viewer.timeClicked.connect(self._on_time_clicked)
            self.flag_viewer.show()
            
            if self.df is not None:
                self.flag_viewer.set_data(self.df)
            
            # Immediately update with current row if data is loaded
            if self.df is not None and self.current_idx < len(self.df):
                row = self.df.iloc[self.current_idx]
                self.flag_viewer.update_flags(row)
        else:
            self.flag_viewer.raise_()
            self.flag_viewer.activateWindow()

    def _on_flag_viewer_closed(self):
        """Persist state when the Flag Viewer is closed."""
        if self.flag_viewer is not None:
            self.flag_collapse_state = self.flag_viewer.get_collapse_state()
            self.flag_order = self.flag_viewer.get_section_order()
            self.save_config()

    def _on_time_clicked(self, time_s):
        """Seek to the given time in seconds."""
        if self.df is None: return
        
        # Convert time_s (relative to start) to absolute time (us)
        t0_us = self.df['time (us)'].iloc[0]
        target_us = t0_us + (time_s * 1e6)
        
        # Find nearest row index
        idx = (self.df['time (us)'] - target_us).abs().idxmin()
        self.slider.setValue(int(idx))

    def toggle_map(self, state):
        visible = (state == Qt.CheckState.Checked.value)
        self.viewer_3d.set_map_visible(visible)
        self.save_config()

    def toggle_fpv(self, state):
        active = (state == Qt.CheckState.Checked.value)
        self.viewer_3d.set_fpv_active(active)
        self.save_config()

    def toggle_sticks(self, state):
        visible = (state == Qt.CheckState.Checked.value)
        if hasattr(self, 'rc_overlay'):
            self.rc_overlay.setVisible(visible)
        self.save_config()

    def update_overlay_pos(self):
        # Keeps the floating Tool Window locked to the top-right of the 3D viewer
        if hasattr(self, 'rc_overlay') and self.rc_overlay.isVisible():
            if self.viewer_3d.isVisible():
                # Get the top-right corner of the 3D viewer in global screen coordinates
                pos = self.viewer_3d.mapToGlobal(QPoint(self.viewer_3d.width(), 0))
                self.rc_overlay.move(pos.x() - self.rc_overlay.width(), pos.y())

    def trigger_map_update(self):
        if not hasattr(self, 'data_parser') or self.df is None:
            return
            
        bounds = self.data_parser.get_bounds()
        if not bounds:
            return
            
        min_lat, max_lat, min_lon, max_lon = bounds
        
        # Always double the map area to provide better context around the flight path
        lat_center = (min_lat + max_lat) / 2.0
        lon_center = (min_lon + max_lon) / 2.0
        lat_span = (max_lat - min_lat) * 2.0
        lon_span = (max_lon - min_lon) * 2.0
        min_lat, max_lat = lat_center - lat_span/2.0, lat_center + lat_span/2.0
        min_lon, max_lon = lon_center - lon_span/2.0, lon_center + lon_span/2.0
            
        # Update map provider settings before fetching
        current_custom_url = getattr(self, 'current_mapproxy_url', '')
        self.map_provider.set_provider(self.combo_map_provider.currentText(), current_custom_url)

        # Cancel existing worker if any
        if self.map_worker and self.map_worker.isRunning():
            self.map_worker.terminate()
            self.map_worker.wait()
            
        self.lbl_map_progress.setStyleSheet("color: #00aaff; font-size: 7.5pt; font-weight: bold; margin-right: 7.5pt;")
        self.lbl_map_progress.setText("Downloading Map...")
        self.lbl_map_progress.setVisible(True)
            
        self.map_worker = MapWorker(self.map_provider, (min_lat, max_lat, min_lon, max_lon))
        self.map_worker.finished.connect(self.on_map_ready)
        self.map_worker.progress.connect(self.on_map_progress)
        self.map_worker.error.connect(self.on_map_error)
        self.map_worker.start()

    def on_map_progress(self, curr, total):
        pct = int((curr / total) * 100)
        self.lbl_map_progress.setText(f"Map Download {pct}% ({curr}/{total})")

    def on_map_error(self, err):
        print(f"Map Worker Error: {err}")
        if "Could not connect to map provider" in err:
            self.lbl_map_progress.setStyleSheet("color: #ff5555; font-size: 7.5pt; font-weight: bold; margin-right: 7.5pt;")
            self.lbl_map_progress.setText("Invalid URL / Offline")
            self.lbl_map_progress.setVisible(True)
        else:
            self.lbl_map_progress.setVisible(False)

    def on_map_ready(self, map_path, map_bounds):
        self.lbl_map_progress.setVisible(False)
        if not hasattr(self, 'data_parser'):
            return
            
        # Convert map bounds to local XY and store original meter values
        try:
            x_min, y_min = self.data_parser.latlon_to_local(map_bounds[0], map_bounds[2])
            x_max, y_max = self.data_parser.latlon_to_local(map_bounds[1], map_bounds[3])
            
            # Store the meter-based bounds and texture path for re-scaling on unit change
            self._map_bounds_m = (x_min, x_max, y_min, y_max)
            self._map_texture_path = map_path
            
            # Apply unit conversion for distance if needed
            self._apply_map_with_units(map_path, x_min, x_max, y_min, y_max)
        except Exception as e:
            print(f"Failed to apply map: {e}")

    def _apply_map_with_units(self, map_path, x_min, x_max, y_min, y_max):
        """Apply unit conversion to meter-based bounds and update the 3D map."""
        dist_unit = self.unit_prefs.get('Distance', 'm')
        if dist_unit != 'm':
            from unit_utils import convert_value
            x_min, _ = convert_value(x_min, 'Distance', 'm', dist_unit)
            x_max, _ = convert_value(x_max, 'Distance', 'm', dist_unit)
            y_min, _ = convert_value(y_min, 'Distance', 'm', dist_unit)
            y_max, _ = convert_value(y_max, 'Distance', 'm', dist_unit)
        self.viewer_3d.set_map(map_path, (x_min, x_max, y_min, y_max))

    def _rescale_map(self):
        """Re-scale the existing map texture to match current units without re-downloading."""
        if hasattr(self, '_map_bounds_m') and hasattr(self, '_map_texture_path'):
            x_min, x_max, y_min, y_max = self._map_bounds_m
            try:
                self._apply_map_with_units(self._map_texture_path, x_min, x_max, y_min, y_max)
            except Exception as e:
                print(f"Failed to rescale map: {e}")

    def on_map_opacity_changed(self, value):
        opacity = value / 100.0
        self.viewer_3d.set_map_opacity(opacity)
        self.save_config()

    def on_map_provider_changed(self, provider):
        self.btn_set_url.setVisible(provider == "MapProxy / Custom")
        self.trigger_map_update()
        self.save_config()

    def open_custom_url_dialog(self):
        urls = getattr(self, 'custom_map_urls', [])
        current = getattr(self, 'current_mapproxy_url', '')
        dlg = CustomUrlDialog(self, config_urls=urls, current_url=current)
        if dlg.exec():
            self.current_mapproxy_url = dlg.selected_url
            self.custom_map_urls = dlg.get_urls()
            self.trigger_map_update()
            self.save_config()


    def on_inversion_changed(self, checked):
        # Update PlotWidget settings
        self.plot_widget.set_inversion('attitude[0]', self.chk_inv_roll.isChecked())
        self.plot_widget.set_inversion('attitude[1]', self.chk_inv_pitch.isChecked())
        self.plot_widget.set_yaw_shift(self.chk_inv_yaw.isChecked())
        
        # Trigger immediate refresh of both 3D view and Plot labels
        if self.df is not None:
            self.update_display(self.current_idx)
        self.save_config()

    def slider_changed(self, value):
        self.current_idx = value
        # If signals are not blocked, it means the user (not the timer) moved the slider.
        # We must sync the playback_idx so playback continues from this new point.
        if not self.slider.signalsBlocked():
            self.playback_idx = float(value)
        self.update_display(value)
        
        # When scrubbing manually, force the ghost mesh to update instantly
        if not self.is_playing and hasattr(self.viewer_3d, '_update_ghost_mesh') and self.chk_ghost.isChecked():
            self.viewer_3d._update_ghost_mesh()

    def next_frame(self):
        if self.df is not None:
            # Calculate elapsed rows based on real time
            dt_ms = self.playback_timer.restart()
            
            speed_str = self.speed_selector.currentText().replace('x', '')
            multiplier = float(speed_str)
            
            # Assume log is approx 1kHz or similar; we move 'multiplier' rows per ~20ms
            # But to be precise, we calculate rows per second.
            # Flight logs are usually high rate. We'll use the base_step (rows per frame at 1x)
            # as a reference for 'real time' speed.
            rows_per_second = 50.0 # Standard base rate
            
            self.playback_idx += (dt_ms / 1000.0) * rows_per_second * multiplier
            self.current_idx = int(self.playback_idx)
            
            if self.playback_idx < len(self.df):
                self.slider.blockSignals(True)
                self.slider.setValue(self.current_idx)
                self.slider.blockSignals(False)
                self.update_display(self.playback_idx)
            else:
                self.toggle_play()

    def update_display(self, idx):
        if self.df is None:
            return
        
        # Handle float index for visual interpolation
        idx_int = int(idx)
        if idx_int >= len(self.df):
            return
            
        frac = idx - idx_int
        row = self.df.iloc[idx_int]
        
        # Core visual parameters (Position and Attitude)
        if frac > 0 and idx_int < len(self.df) - 1:
            row2 = self.df.iloc[idx_int + 1]
            pos = (
                row['pos_x'] * (1-frac) + row2['pos_x'] * frac,
                row['pos_y'] * (1-frac) + row2['pos_y'] * frac,
                row['pos_z'] * (1-frac) + row2['pos_z'] * frac
            )
            
            roll = row.get('attitude[0]', 0) * (1-frac) + row2.get('attitude[0]', 0) * frac
            pitch = row.get('attitude[1]', 0) * (1-frac) + row2.get('attitude[1]', 0) * frac
            
            # Yaw interpolation with wrap-around handling
            y1 = row.get('attitude[2]', 0)
            y2 = row2.get('attitude[2]', 0)
            diff = (y2 - y1 + 180) % 360 - 180
            yaw = (y1 + diff * frac) % 360
        else:
            pos = (row['pos_x'], row['pos_y'], row['pos_z'])
            roll = row.get('attitude[0]', 0)
            pitch = row.get('attitude[1]', 0)
            yaw = row.get('attitude[2]', 0)

        self.current_idx = idx_int
        
        # Apply Inversions
        if self.chk_inv_roll.isChecked(): roll = -roll
        if self.chk_inv_pitch.isChecked(): pitch = -pitch
        if self.chk_inv_yaw.isChecked(): yaw = (yaw + 180) % 360
        
        # Ensure we get scalars (handling possible duplicates)
        if hasattr(roll, 'iloc'): roll = roll.iloc[0]
        if hasattr(pitch, 'iloc'): pitch = pitch.iloc[0]
        if hasattr(yaw, 'iloc'): yaw = yaw.iloc[0]
        
        # Update 3D Viewer (Must happen EVERY frame for smooth movement)
        self.viewer_3d.update_aircraft(pos, (float(roll), float(pitch), float(yaw)), idx)
        if self.chk_center.isChecked():
            self.viewer_3d.follow_aircraft(pos)
        self.viewer_3d.render()
        
        # Update RC Overlay
        if hasattr(self, 'rc_overlay'):
            rc_roll = row.get('rcData[0]', 1500)
            rc_pitch = row.get('rcData[1]', 1500)
            rc_yaw = row.get('rcData[2]', 1500)
            rc_throttle = row.get('rcData[3]', 1000)
            
            if hasattr(rc_roll, 'iloc'): rc_roll = rc_roll.iloc[0]
            if hasattr(rc_pitch, 'iloc'): rc_pitch = rc_pitch.iloc[0]
            if hasattr(rc_yaw, 'iloc'): rc_yaw = rc_yaw.iloc[0]
            if hasattr(rc_throttle, 'iloc'): rc_throttle = rc_throttle.iloc[0]
            
            self.rc_overlay.update_sticks(rc_roll, rc_pitch, rc_yaw, rc_throttle)

        # Update Labels — throttle during playback to reduce CPU load
        self._frame_counter = getattr(self, '_frame_counter', 0) + 1
        is_throttle_frame = self.is_playing and (self._frame_counter % 2 != 0)
        
        if not is_throttle_frame:
            dist_unit = self.unit_prefs.get('Distance', 'm')
            height_unit = self.unit_prefs.get('Height', 'm')
            self.lbl_telemetry.setText(f"X:{pos[0]:.1f}{dist_unit} Y:{pos[1]:.1f}{dist_unit} Z:{pos[2]:.1f}{height_unit}")
            
            # Update Modes
            mode_flags = str(row.get('flightModeFlags (flags)', '---'))
            self.lbl_mode.setText(f"Mode: {mode_flags}")
            
            # Update Nav Mode
            if self.log_type == 'ardupilot':
                # ArduPilot: mode is already a readable string; no separate navState
                if self.lbl_nav.isVisible():
                    self.lbl_nav.hide()
            else:
                if not self.lbl_nav.isVisible():
                    self.lbl_nav.show()
                nav_state = row.get('navState', 0)
                if hasattr(nav_state, 'iloc'): nav_state = nav_state.iloc[0]
                
                version = self.version_selector.currentText()
                # Use definitions from flag_viewer to be consistent
                from flag_viewer import get_flag_params
                params = get_flag_params(version)
                nav_map = params.get("navState", ("enum", {}))[1]
                    
                nav_name = nav_map.get(int(nav_state), f"STATE_{int(nav_state)}")
                self.lbl_nav.setText(f"Nav: {nav_name} ({int(nav_state)})")
            
            # Update Time Label
            elapsed_us = row['time (us)'] - self.df['time (us)'].iloc[0]
            s = elapsed_us / 1e6
            m, s = divmod(s, 60)
            h, m = divmod(m, 60)
            time_str = f"{int(h):02}:{int(m):02}:{s:05.2f}"
            if hasattr(self, 'total_time_str'):
                time_str += f" / {self.total_time_str}"
            self.lbl_time.setText(time_str)

        # Update Flag Viewer (every 3rd frame during playback)
        if self.flag_viewer is not None and self.flag_viewer.isVisible():
            if not self.is_playing or self._frame_counter % 3 == 0:
                self.flag_viewer.update_flags(row)

        # Update Plots — throttle during playback (every 3rd frame)
        if not self.is_playing or self._frame_counter % 3 == 0:
            self.plot_widget.update_cursor(row['time (us)'])

    def closeEvent(self, event):
        """Clean up child windows and save config on close."""
        if self.flag_viewer is not None:
            self.flag_viewer.close()
        self.save_config()
        super().closeEvent(event)

if __name__ == "__main__":
    window = MainWindow()
    window.show()
    splash.finish(window)
    sys.exit(app.exec())
