"""Interactive video label widget for mouse-based camera control"""

from typing import Optional

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent


class InteractiveVideoLabel(QLabel):
    """QLabel that emits signals on mouse drag events for camera control"""
    
    on_drag_signal = pyqtSignal(float, float)
    
    def __init__(self):
        """Initialize the interactive video label"""
        super().__init__()
        self.setMouseTracking(False)
        self.setStyleSheet("border: 2px solid #444; background: black;")
        self.setCursor(Qt.CursorShape.CrossCursor)

    def mousePressEvent(self, ev: Optional[QMouseEvent]):
        """Handle mouse press events"""
        if ev:
            self.handle_mouse(ev)

    def mouseMoveEvent(self, ev: Optional[QMouseEvent]):
        """Handle mouse move events"""
        if ev:
            self.handle_mouse(ev)

    def handle_mouse(self, ev: QMouseEvent):
        """
        Process mouse events and emit drag signal
        
        Args:
            ev: QMouseEvent object
        """
        w, h = self.width(), self.height()
        x, y = ev.position().x(), ev.position().y()
        # Normalize coordinates to [-1, 1] range
        dx = (x - w/2) / (w/2)
        dy = (y - h/2) / (h/2)
        # type: ignore (Pylance strict non vede emit su segnali custom)
        self.on_drag_signal.emit(dx, dy)
