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

import json
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QLabel)
from PyQt6.QtCore import Qt

class CustomUrlDialog(QDialog):
    def __init__(self, parent=None, config_urls=None, current_url=None):
        super().__init__(parent)
        self.setWindowTitle("Set Custom Map URL")
        self.resize(700, 400)
        self.selected_url = ""
        
        self.config_urls = config_urls if config_urls is not None else []
        self.initial_url = current_url
        
        self.init_ui()
        self.apply_dark_theme()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Select a predefined map provider or add your own custom MapProxy URL:")
        lbl.setStyleSheet("font-size: 10pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(lbl)
        
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Description", "URL {z}/{x}/{y}"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.table)
        
        self.populate_table()
        
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("Add Custom")
        self.btn_add.clicked.connect(self.add_row)
        btn_layout.addWidget(self.btn_add)
        
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.clicked.connect(self.remove_row)
        btn_layout.addWidget(self.btn_remove)
        
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet("background-color: #333333; border: 1px solid #555555;")
        btn_layout.addWidget(self.btn_cancel)
        
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.clicked.connect(self.apply_selection)
        btn_layout.addWidget(self.btn_apply)
        
        layout.addLayout(btn_layout)

    def populate_table(self):
        # We assume self.config_urls is a list of dicts: {"name": ..., "url": ...}
        defaults = [
            {"name": "OpenTopoMap (Topographical map with contour lines)", "url": "https://a.tile.opentopomap.org/{z}/{x}/{y}.png"},
            {"name": "ESRI World Topographic Map", "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"},
            {"name": "Google Maps Satellite", "url": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"},
            {"name": "Google Maps Terrain", "url": "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"}
        ]
        
        seen_urls = set()
        merged = []
        for d in defaults:
            merged.append(d)
            seen_urls.add(d["url"])
            
        for d in self.config_urls:
            # Handle old string format automatically just in case
            if isinstance(d, str):
                d = {"name": "Custom URL", "url": d}
            if d.get("url") not in seen_urls:
                merged.append(d)
                seen_urls.add(d.get("url"))
                
        self.table.setRowCount(len(merged))
        
        select_idx = 0
        for i, item in enumerate(merged):
            desc_item = QTableWidgetItem(item.get("name", ""))
            url_item = QTableWidgetItem(item.get("url", ""))
            self.table.setItem(i, 0, desc_item)
            self.table.setItem(i, 1, url_item)
            
            if item.get("url") == self.initial_url:
                select_idx = i
                
        if self.table.rowCount() > 0:
            self.table.selectRow(select_idx)
            
    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem("Custom URL"))
        self.table.setItem(row, 1, QTableWidgetItem("http://"))
        self.table.selectRow(row)
        self.table.editItem(self.table.item(row, 0))
        
    def remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            
    def get_urls(self):
        urls = []
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().strip()
            url = self.table.item(row, 1).text().strip()
            if url:
                urls.append({"name": name, "url": url})
        return urls

    def apply_selection(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a URL from the list.")
            return
            
        url = self.table.item(row, 1).text().strip()
        if "{z}" not in url or "{x}" not in url or "{y}" not in url:
            QMessageBox.warning(self, "Invalid URL", "The URL must contain {z}, {x}, and {y} placeholders.")
            return
            
        self.selected_url = url
        self.accept()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QDialog, QWidget {
                background-color: #121212;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #1b5e20;
                border: 1px solid #2e7d32;
                color: #ffffff;
                padding: 5pt 15pt;
                min-height: 25pt;
                border-radius: 4pt;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2e7d32; }
            QPushButton:pressed { background-color: #0d3b0f; }
            QTableWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                gridline-color: #333333;
                border: 1px solid #333333;
                selection-background-color: #005a9e;
            }
            QHeaderView::section {
                background-color: #333333;
                color: white;
                padding: 4px;
                border: 1px solid #444444;
            }
        """)
