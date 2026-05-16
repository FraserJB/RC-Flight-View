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

from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap
from PyQt6.QtCore import Qt, QRect

class RCSticksWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # 170x90 content + 20px top margin + 20px right margin = 190x110
        self.setFixedSize(190, 110) 
        self.rc_data = [1500, 1500, 1500, 1000] # roll, pitch, yaw, throttle
        self._draw_sticks()
        
    def update_sticks(self, roll, pitch, yaw, throttle):
        """Updates the internal state and triggers a repaint."""
        self.rc_data = [roll, pitch, yaw, throttle]
        self._draw_sticks()
        
    def _draw_sticks(self):
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 60% opacity for the internal drawing
        painter.setOpacity(0.6)
        
        # Draw background squares (dark semi-transparent)
        painter.setBrush(QBrush(QColor(20, 20, 20, 220)))
        painter.setPen(QPen(QColor(100, 100, 100, 255), 1))
        
        # Internal offsets (leaving 20px top padding and 20px right padding for placement)
        # Content is drawn from x=0 to 170, and y=20 to 110.
        off_x = 10
        off_y = 30 # 10px internal padding + 20px top margin
        
        # Left stick area (yaw, throttle)
        left_rect = QRect(off_x, off_y, 70, 70)
        painter.drawRect(left_rect)
        
        # Right stick area (roll, pitch)
        right_rect = QRect(off_x + 80, off_y, 70, 70)
        painter.drawRect(right_rect)
        
        # Draw crosshairs
        painter.setPen(QPen(QColor(150, 150, 150, 150), 1, Qt.PenStyle.DashLine))
        
        # Left crosshair
        painter.drawLine(off_x, off_y + 35, off_x + 70, off_y + 35)
        painter.drawLine(off_x + 35, off_y, off_x + 35, off_y + 70)
        
        # Right crosshair
        painter.drawLine(off_x + 80, off_y + 35, off_x + 150, off_y + 35)
        painter.drawLine(off_x + 115, off_y, off_x + 115, off_y + 70)
        
        # Draw Stick positions
        painter.setBrush(QBrush(QColor(0, 170, 255, 255))) # Cyan/Blue circle
        painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
        
        # Mapping 1000-2000 to 0-70 pixel range inside the box
        def map_val(v):
            v = max(1000, min(2000, v))
            return ((v - 1000) / 1000.0) * 70
            
        roll, pitch, yaw, throttle = self.rc_data
        
        # Left stick (yaw, throttle)
        lx = off_x + map_val(yaw)
        ly = off_y + (70 - map_val(throttle))
        painter.drawEllipse(int(lx) - 5, int(ly) - 5, 10, 10)
        
        # Right stick (roll, pitch)
        rx = off_x + 80 + map_val(roll)
        ry = off_y + (70 - map_val(pitch))
        painter.drawEllipse(int(rx) - 5, int(ry) - 5, 10, 10)

        # Draw the Outer Border (matching FPV style)
        painter.setOpacity(1.0)
        border_color = QColor(0, 168, 255) # Matches (0.0, 0.66, 1.0)
        painter.setPen(QPen(border_color, 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Border bounds: starts at x=1, y=21, width=168, height=88
        painter.drawRect(1, 21, 168, 88)
        
        painter.end()
        self.setPixmap(pixmap)

