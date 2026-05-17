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

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
import pandas as pd
import numpy as np
import textwrap

from flag_viewer import get_flag_params, HW_HEALTH_BITS, decode_flag_value

class PlotWidget(QWidget):
    timeClicked = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.figure = Figure(figsize=(6, 12), tight_layout=False)
        self.canvas = FigureCanvas(self.figure)
        # Explicitly set canvas font to match the app default to prevent warnings
        self.canvas.setFont(self.font())
        self.layout.addWidget(self.canvas)
        
        # Connect click event
        self.canvas.mpl_connect('button_press_event', self._on_click)
        
        self.figure.patch.set_facecolor('#1e1e1e')
        # Increased left margin to 0.3 to accommodate multi-line wrapped labels
        self.figure.subplots_adjust(left=0.3, right=0.95, top=0.98, bottom=0.05, hspace=0.3)
        
        self.axes = []
        self.df = None
        self.cursor_lines = []
        self.value_texts = []
        self.inversions = {}
        self.active_params = []
        self.param_config = [] 
        self.mappings = {} # param_name -> {val: label}
        self.yaw_shift = False
        self.column_threshold = 10
        self.flag_texts = {}
        self.version = "All"
        self.params = get_flag_params("All")

    def set_version(self, version):
        self.version = version
        self.params = get_flag_params(version)
        if self.df is not None:
            self.refresh_plots()

    def set_data(self, df):
        self.df = df
        if self.param_config:
            self.refresh_plots()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'last_time_us') and self.df is not None:
            self.update_cursor(self.last_time_us)

    def set_yaw_shift(self, shift):
        self.yaw_shift = shift
        # Clear any stale inversion on yaw when using shift mode
        if shift:
            self.inversions.pop('attitude[2]', None)
        if self.df is not None:
            self.refresh_plots()

    def set_mappings(self, mappings):
        """Pass a dictionary of {param_name: {val: label}}."""
        self.mappings = mappings

    def update_params_config(self, config):
        """Update the configuration and redraw plots."""
        self.param_config = config
        if self.df is not None:
            self.refresh_plots()

    def refresh_plots(self):
        if self.df is None: return
        
        self.figure.clear()
        
        # Filter: must exist in DF and 'plot' must be True. Flag/text fields
        # are handled below by the flag-indicator renderer instead of lines.
        self.active_params = [p for p in self.param_config 
                             if p.get('plot', False) and p['param'] in self.df.columns]
        
        if not self.active_params:
            self.axes = []
            self.canvas.draw()
            return

        n = len(self.active_params)
        # If threshold is 0, always stay in 1 column (Off mode)
        n_cols = 1 if self.column_threshold == 0 else (2 if n > self.column_threshold else 1)
        n_rows = (n + n_cols - 1) // n_cols
        
        # Adjust margins: 2-column layout needs more width but can afford less left margin per axis
        left_margin = 0.15 if n_cols == 2 else 0.3
        self.figure.subplots_adjust(left=left_margin, right=0.95, top=0.98, bottom=0.08, hspace=0.5, wspace=0.3)
        
        # Calculate dynamic font size and wrap width based on precise physical axis height
        fig_height_px = self.figure.get_figheight() * self.figure.dpi
        total_axes_height = fig_height_px * 0.90 # Account for top=0.98, bottom=0.08 margins
        
        # Calculate single axis height accounting for hspace=0.5
        axis_height_px = total_axes_height / max(1, 1.5 * n_rows - 0.5)
        
        # Calculate ideal font size. Cap between 6 and 11 points.
        fs_ideal = (axis_height_px * 0.15) * (72.0 / self.figure.dpi)
        fs = max(6, min(11, int(fs_ideal)))
        
        # Rotated text vertical length is constrained by the character's advance width.
        # Average sans-serif advance width is ~0.6 * point size (in pixels)
        char_advance_px = fs * (self.figure.dpi / 72.0) * 0.6
        
        # Limit text width to 90% of the axis height to prevent vertical overlapping
        wrap_width = max(8, int((axis_height_px * 0.90) / max(1, char_advance_px)))
            
        self._last_fs = fs
        self._last_wrap_width = wrap_width
        
        self.axes = []
        self.value_texts = []
        self.flag_texts = {}
        time_s = (self.df['time (us)'] - self.df['time (us)'].iloc[0]) / 1e6
        
        for i, p in enumerate(self.active_params):
            # Share X axis with the first subplot
            sharex = self.axes[0] if self.axes else None
            ax = self.figure.add_subplot(n_rows, n_cols, i + 1, sharex=sharex)
            self.axes.append(ax)
            
            ax.set_facecolor('#121212')
            col = p['param']
            if col not in self.df.columns:
                continue
                
            color = p.get('color', '#ffffff')
            
            # Safely handle potentially non-numeric data (like Flight Modes)
            try:
                plot_data = pd.to_numeric(self.df[col], errors='coerce').copy()
            except Exception:
                plot_data = self.df[col].copy() # Fallback
                
            if col == 'attitude[2]' and self.yaw_shift:
                plot_data = (plot_data + 180) % 360
                
            is_flag_plot = False
            if col in self.params:
                seen_flags = set()
                seen_errors = set()
                unique_vals = self.df[col].dropna().unique()
                for val in unique_vals:
                    act, err = decode_flag_value(col, val, self.params)
                    seen_flags.update(act)
                    seen_errors.update(err)
                
                all_flags = sorted(list(seen_flags | seen_errors))
                
                if all_flags:
                    ax.set_yticks([])
                    ax.set_yticklabels([])
                    ax.spines['left'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    ax.spines['top'].set_visible(False)
                    ax.spines['bottom'].set_visible(False)
                    
                    ax.set_ylim(0, 1)
                    
                    n_flags = len(all_flags)
                    cols = min(3, n_flags)
                    if cols == 0: cols = 1
                    rows = (n_flags + cols - 1) // cols
                    
                    # Calculate dynamic split line based on number of rows
                    max_split = 0.75
                    min_split = 0.25
                    row_height = 0.2
                    split_y = min(max_split, max(min_split, rows * row_height + 0.1))
                    marker_y = split_y + (1.0 - split_y) / 2.0
                    # Top half time axis markers
                    raw_data = self.df[col].ffill().bfill()
                    
                    # Robust change detection by decoding unique values
                    unique_vals = raw_data.unique()
                    mapping = {}
                    for uv in unique_vals:
                        active, errors = decode_flag_value(col, uv, self.params)
                        mapping[uv] = tuple(sorted(list(active))) + tuple(sorted(list(errors)))
                        
                    canonical_state = raw_data.map(mapping)
                    changes = canonical_state != canonical_state.shift(1)
                    # First row always triggers vs NaN; skip it
                    changes.iloc[0] = False
                    change_times = time_s[changes]
                    ax.plot(change_times, [marker_y] * len(change_times), marker='d', linestyle='None', color=color, markersize=5, zorder=3, alpha=0.8)
                    
                    # Cover the bottom half
                    ax.axhspan(0, split_y, facecolor='#121212', edgecolor='none', zorder=10)
                    ax.axhline(split_y, color='#333333', linewidth=1, zorder=11, alpha=0.5)
                    
                    self.flag_texts[i] = {}
                    
                    for idx_flag, flag_name in enumerate(all_flags):
                        r = idx_flag // cols
                        c = idx_flag % cols
                        
                        x = 0.05 + c * (0.90 / cols)
                        
                        step = split_y / rows
                        y = split_y - (r + 0.5) * step
                            
                        txt = ax.text(x, y, flag_name, ha="left", va="center",
                                      transform=ax.transAxes,
                                      bbox=dict(boxstyle="round,pad=0.4", fc="#333333", ec="none"),
                                      color="#888888", fontsize=self._last_fs-1, weight='bold', zorder=12)
                        self.flag_texts[i][flag_name] = txt
                    is_flag_plot = True
                else:
                    ax.plot(time_s, plot_data, color=color, linewidth=1)
            else:
                ax.plot(time_s, plot_data, color=color, linewidth=1)

            if not is_flag_plot and self._is_pwm_output_param(col):
                numeric_data = pd.to_numeric(plot_data, errors='coerce')
                if numeric_data.notna().any():
                    data_min = numeric_data.min()
                    data_max = numeric_data.max()
                    y_min = min(1000.0, data_min)
                    y_max = max(2000.0, data_max)
                    padding = max(25.0, (y_max - y_min) * 0.03)
                    ax.set_ylim(y_min - padding, y_max + padding)
            
            label = p.get('name', col)
            wrapped_label = textwrap.fill(label, width=self._last_wrap_width)
            unit = p.get('unit', '')
            
            ax.set_ylabel(f"{wrapped_label}\n({unit})", color=color, fontsize=self._last_fs, fontweight='bold')
            ax.tick_params(axis='both', colors='white', labelsize=self._last_fs-1)
            ax.grid(True, color='#333333', linestyle='--', alpha=0.5)
            
            if not is_flag_plot:
                import matplotlib.ticker as ticker
                def comma_tick_formatter(x, pos):
                    try:
                        val_float = float(x)
                        if abs(val_float) >= 1000:
                            if val_float == int(val_float):
                                return f"{int(val_float):,}"
                            else:
                                return f"{val_float:,.1f}"
                        else:
                            if val_float == int(val_float):
                                return f"{int(val_float)}"
                            s = f"{val_float:.3f}".rstrip('0').rstrip('.')
                            return s if s else "0"
                    except Exception:
                        return str(x)
                ax.yaxis.set_major_formatter(ticker.FuncFormatter(comma_tick_formatter))
            
            # We'll use the ylabel object itself to update text later
            self.value_texts.append(ax.yaxis.label)
            
        self.axes[-1].set_xlabel('Time (s)', color='white')
        self.cursor_lines = [ax.axvline(0, color='white', linestyle='-', alpha=0.8, linewidth=1.5) for ax in self.axes]
        self.canvas.draw()

    @staticmethod
    def _is_pwm_output_param(col):
        return (
            col.startswith('motor[')
            or col.startswith('servo[')
            or col.startswith('rcData[')
            or col.startswith('rcou_C')
        )

    def set_inversion(self, col, inverted):
        self.inversions[col] = inverted

    def update_cursor(self, current_time_us):
        self.last_time_us = current_time_us
        if self.df is None or len(self.axes) == 0:
            return
        
        n = len(self.active_params)
        n_cols = 1 if self.column_threshold == 0 else (2 if n > self.column_threshold else 1)
        n_rows = (n + n_cols - 1) // max(1, n_cols)
        
        # Calculate dynamic font size and wrap width based on precise physical axis height
        fig_height_px = self.figure.get_figheight() * self.figure.dpi
        total_axes_height = fig_height_px * 0.90 # Account for top=0.98, bottom=0.08 margins
        
        # Calculate single axis height accounting for hspace=0.5
        axis_height_px = total_axes_height / max(1, 1.5 * n_rows - 0.5)
        
        # Calculate ideal font size. Cap between 6 and 11 points.
        fs_ideal = (axis_height_px * 0.15) * (72.0 / self.figure.dpi)
        fs = max(6, min(11, int(fs_ideal)))
        
        # Rotated text vertical length is constrained by the character's advance width.
        # Average sans-serif advance width is ~0.6 * point size (in pixels)
        char_advance_px = fs * (self.figure.dpi / 72.0) * 0.6
        
        # Limit text width to 90% of the axis height to prevent vertical overlapping
        wrap_width = max(8, int((axis_height_px * 0.90) / max(1, char_advance_px)))
        
        needs_tick_update = False


        if getattr(self, '_last_fs', None) != fs:
            self._last_fs = fs
            needs_tick_update = True
        self._last_wrap_width = wrap_width
        
        idx = (self.df['time (us)'] - current_time_us).abs().idxmin()
        row = self.df.iloc[idx]
        
        time_s = (current_time_us - self.df['time (us)'].iloc[0]) / 1e6
        for i, line in enumerate(self.cursor_lines):
            line.set_xdata([time_s, time_s])
            
            p = self.active_params[i]
            col = p['param']
            label = p.get('name', col)
            unit = p.get('unit', '')
            
            val = row[col]
            if hasattr(val, 'iloc'): val = val.iloc[0]
            
            if col == 'attitude[2]' and self.yaw_shift:
                val = (val + 180) % 360
            elif self.inversions.get(col, False):
                val = -val
                
            # Check for mapping (e.g. 26 -> LAUNCH_IDLE)
            mapping = self.mappings.get(col)
            if mapping and int(val) in mapping:
                val_display = f"{int(val)} ({mapping[int(val)]})"
            else:
                try:
                    val_float = float(val)
                    if abs(val_float) >= 1000:
                        if val_float == int(val_float):
                            val_str = f"{int(val_float):,}"
                        else:
                            val_str = f"{val_float:,.1f}"
                    else:
                        if val_float == int(val_float):
                            val_str = f"{int(val_float)}"
                        else:
                            val_str = f"{val_float:.1f}"
                    val_display = f"{val_str} {unit}" if unit else val_str
                except (ValueError, TypeError):
                    val_display = f"{val} {unit}" if unit else str(val)
                    
            if i in self.flag_texts:
                active, errors = decode_flag_value(col, val, self.params)
                for flag_name, txt in self.flag_texts[i].items():
                    if flag_name in errors:
                        txt.set_bbox(dict(boxstyle="round,pad=0.4", fc="#ff4444", ec="none"))
                        txt.set_color("#ffffff")
                    elif flag_name in active:
                        txt.set_bbox(dict(boxstyle="round,pad=0.4", fc="#00ee66", ec="none"))
                        txt.set_color("#000000")
                    else:
                        txt.set_bbox(dict(boxstyle="round,pad=0.4", fc="#333333", ec="none"))
                        txt.set_color("#888888")
                val_display = ""
                
            wrapped_label = textwrap.fill(label, width=self._last_wrap_width)
            if val_display:
                self.value_texts[i].set_text(f"{wrapped_label}\n{val_display}")
            else:
                self.value_texts[i].set_text(f"{wrapped_label}")
            
            if needs_tick_update:
                self.value_texts[i].set_fontsize(self._last_fs)
                self.axes[i].tick_params(axis='both', labelsize=self._last_fs-1)
                
        self.canvas.draw_idle()

    def _on_click(self, event):
        if event.inaxes and event.xdata is not None:
            self.timeClicked.emit(float(event.xdata))
