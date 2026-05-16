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

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QComboBox, QPushButton)
from PyQt6.QtCore import Qt
from unit_utils import DEFAULT_UNITS

class UnitsDialog(QDialog):
    def __init__(self, current_prefs=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Units")
        self.setFixedSize(280, 220)
        self.prefs = current_prefs or DEFAULT_UNITS.copy()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        def create_row(label_text, items, current_val):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            combo = QComboBox()
            combo.addItems(items)
            combo.setCurrentText(current_val)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(combo)
            layout.addLayout(row)
            return combo
            
        self.combo_dist = create_row("Distance:", ["m", "ft", "km", "miles"], self.prefs.get("Distance", "m"))
        self.combo_height = create_row("Height:", ["m", "ft", "km", "miles"], self.prefs.get("Height", "m"))
        self.combo_speed = create_row("Speed:", ["m/s", "km/h", "mph"], self.prefs.get("Speed", "mph"))
        self.combo_temp = create_row("Temperature:", ["C", "F"], self.prefs.get("Temperature", "C"))
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("""
            QDialog { background-color: #121212; color: #e0e0e0; }
            QLabel { color: #e0e0e0; font-size: 9pt; }
            QComboBox { 
                background: #333333; 
                color: white; 
                border: 1px solid #555555; 
                border-radius: 4pt; 
                padding: 3pt 5pt; 
                min-width: 80px;
            }
            QComboBox:hover { border: 1px solid #00aaff; }
            QPushButton { 
                background-color: #1b5e20; 
                border: 1px solid #2e7d32; 
                color: #ffffff; 
                padding: 5pt 15pt; 
                border-radius: 12pt; 
                font-weight: bold; 
            }
            QPushButton:hover { 
                background-color: #2e7d32; 
                border: 1px solid #4caf50; 
            }
            QPushButton:pressed { 
                background-color: #0d3b0f; 
            }
        """)

    def get_prefs(self):
        return {
            "Distance": self.combo_dist.currentText(),
            "Height": self.combo_height.currentText(),
            "Speed": self.combo_speed.currentText(),
            "Temperature": self.combo_temp.currentText()
        }
