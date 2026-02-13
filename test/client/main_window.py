"""Main application window - IMPROVED VERSION"""

import sys
from typing import Optional, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QGridLayout, QPushButton, QInputDialog, 
    QLabel, QMessageBox, QStatusBar
) 
from PyQt6.QtGui import QImage, QPixmap, QMouseEvent, QFont
from PyQt6.QtCore import Qt, QTimer
from config import MODE_MANUAL, MODE_SCAN, MODE_TRACK, MODE_NAMES

from config import (
    DEFAULT_SERVER_IP, WINDOW_WIDTH, WINDOW_HEIGHT, VIDEO_WIDTH, VIDEO_HEIGHT,
    DRAG_CMD_SENSITIVITY
)


class MainWindow(QMainWindow):
    """Main application window for camera control - IMPROVED"""
    
    # Configurazione UI
    CAMERA_BUTTON_WIDTH = 80
    CONTROL_BUTTON_SIZE = 60
    ERROR_DISPLAY_TIME = 3000  # ms
    STATUS_MESSAGE_TIME = 2000  # ms
    
    def __init__(self):
        """Initialize the main window"""
        super().__init__()
        
        # Import qui per evitare dipendenze circolari
        from visca_controller import ViscaController
        from interactive_video_label import InteractiveVideoLabel
        from video_thread import VideoThread
        
        # Get server IP from user
        current_ip = self._get_server_ip()
        if not current_ip:
            current_ip = "localhost"  # Default fallback

        # Initialize VISCA controller
        try:
            self.visca = ViscaController(current_ip)
        except Exception as e:
            print(f"[WARNING] VISCA init: {e}")
            self.visca = ViscaController("localhost")
        
        # Setup window
        self.setWindowTitle(f"Camera Control - Server: {current_ip}")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Create main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create video label
        self.lbl = InteractiveVideoLabel()
        self.lbl.setScaledContents(True)
        self.lbl.setMinimumSize(VIDEO_WIDTH, VIDEO_HEIGHT)
        main_layout.addWidget(self.lbl, 70)

        # Create control panel
        ctrl_layout = self._create_control_panel()
        main_layout.addLayout(ctrl_layout, 30)
        
        # Setup video thread
        self.th = VideoThread(self.visca)
        # NON connettere signal - useremo polling invece (evita crash Wayland)
        # self.th.change_pixmap_signal.connect(self.update_image)
        self.lbl.on_drag_signal.connect(self.handle_drag_input)
        self.lbl.mouseReleaseEvent = self.stop_drag
        
        # Timer per aggiornamento stato
        self.state_timer = QTimer()
        self.state_timer.timeout.connect(self._update_camera_state_display)
        self.state_timer.start(500)  # Aggiorna ogni 500ms
        
        # Timer per polling frame dal video thread
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self._poll_and_update_frame)
        self.frame_timer.start(33)  # ~30 FPS
        
        # Status bar
        self.statusBar().showMessage("Ready - Camera 1 selected")
        
        # Start video thread
        self.th.start()
        self.set_cam(1)

    def _get_server_ip(self) -> Optional[str]:
        """
        Richiedi IP server all'utente con validazione
        
        Returns:
            str: IP server o None se annullato
        """
        while True:
            ip, ok = QInputDialog.getText(
                self, 
                "Server IP", 
                "Inserisci l'indirizzo IP del server VISCA:",
                text=DEFAULT_SERVER_IP
            )
            
            if not ok:
                return None
            
            if ip and self._validate_ip(ip):
                return ip
            
            QMessageBox.warning(
                self,
                "IP Non Valido",
                "Inserisci un indirizzo IP valido (es: 192.168.1.100)"
            )

    def _validate_ip(self, ip: str) -> bool:
        """Validazione base IP"""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False

    def _create_control_panel(self) -> QVBoxLayout:
        """
        Crea pannello di controllo
        
        Returns:
            QVBoxLayout: Layout del pannello
        """
        ctrl_layout = QVBoxLayout()
        
        # Camera selection buttons
        self.cam_buttons: List[QPushButton] = []
        for i in range(1, 7):
            btn = QPushButton(f"CAM {i}")
            btn.setMinimumWidth(self.CAMERA_BUTTON_WIDTH)
            btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            btn.clicked.connect(lambda checked, cam=i: self.set_cam(cam))
            ctrl_layout.addWidget(btn)
            self.cam_buttons.append(btn)
        
        # Separatore
        ctrl_layout.addSpacing(10)
        
        # Mode cycling button
        self.btn_mode = QPushButton("CHANGE MODE")
        self.btn_mode.setMinimumWidth(self.CAMERA_BUTTON_WIDTH)
        self.btn_mode.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_mode.clicked.connect(self.cycle_mode)
        ctrl_layout.addWidget(self.btn_mode)
        
        # Separatore
        ctrl_layout.addSpacing(10)

        # Camera control grid
        grid = self._create_control_grid()
        ctrl_layout.addLayout(grid)
        
        ctrl_layout.addStretch()
        
        # Label per gli errori
        self.error_label = QLabel("")
        self.error_label.setStyleSheet(
            "color: red; font-weight: bold; background: #ffe6e6; "
            "padding: 5px; border-radius: 3px;"
        )
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        ctrl_layout.addWidget(self.error_label)
        
        # Label per info telecamera
        self.info_label = QLabel("")
        self.info_label.setStyleSheet(
            "color: #333; font-size: 11px; padding: 5px;"
        )
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_layout.addWidget(self.info_label)
        
        return ctrl_layout

    def _create_control_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(5)
        
        moves = [
            ("⬆\nUP", 0, 1, "01060105050301FF"),
            ("⬅\nLT", 1, 0, "01060105050103FF"),
            ("⬇\nDN", 2, 1, "01060105050302FF"),
            ("➡\nRT", 1, 2, "01060105050203FF"),
            ("+\nZOOM", 0, 2, "01040702FF"),
            ("-\nZOOM", 2, 2, "01040703FF")
        ]
        
        for text, row, col, hex_cmd in moves:
            btn = QPushButton(text)
            btn.setMinimumSize(self.CONTROL_BUTTON_SIZE, self.CONTROL_BUTTON_SIZE)
            btn.setFont(QFont("Arial", 9))
            
            # Passiamo sia 'direction' (UP/DN/ZOOM) sia 'text' (+/UP, -/ZOOM)
            direction_id = text.split('\n')[1]
            btn.pressed.connect(
                lambda d=direction_id, h=hex_cmd, t=text: self.move_camera(d, h, t)
            )
            btn.released.connect(self.stop)
            grid.addWidget(btn, row, col)
        
        stop_btn = QPushButton("STOP")
        stop_btn.setMinimumSize(self.CONTROL_BUTTON_SIZE, self.CONTROL_BUTTON_SIZE)
        stop_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        stop_btn.setStyleSheet("background-color: #ffcccc;")
        stop_btn.clicked.connect(self.stop)
        grid.addWidget(stop_btn, 1, 1)
        
        return grid

    def _poll_and_update_frame(self):
        """Poll video thread for new frames (avoids PyQt signal crash)"""
        if self.th is None:
            return
        
        # Prova a recuperare il frame più recente
        frame = self.th.get_latest_frame()
        if frame is not None:
            self.update_image(frame)

    def update_image(self, img: QImage):
        """
        Update the displayed video frame
        
        Args:
            img: QImage to display
        """
        self.lbl.setPixmap(QPixmap.fromImage(img))

    def handle_drag_input(self, dx: float, dy: float):
        """
        Handle mouse drag input for camera control
        
        Args:
            dx: Normalized horizontal drag amount [-1, 1]
            dy: Normalized vertical drag amount [-1, 1]
        """
        cid = self.th.active_cam_id
        self.th.manual_override[cid] = True
        
        # Calcola i comandi
        self.th.cmd_p = int(dx * DRAG_CMD_SENSITIVITY)
        self.th.cmd_t = int(dy * DRAG_CMD_SENSITIVITY)
        
        # Invia comando pan/tilt solo se c'è movimento
        if self.th.cmd_p != 0 or self.th.cmd_t != 0:
            pan_dir = "01" if self.th.cmd_p < 0 else ("02" if self.th.cmd_p > 0 else "03")
            tilt_dir = "01" if self.th.cmd_t < 0 else ("02" if self.th.cmd_t > 0 else "03")
            
            pan_tilt_hex = f"0106010505{pan_dir}{tilt_dir}FF"
            
            # Invia e controlla errore
            error_msg = self.visca.send(cid, pan_tilt_hex, retry=False)
            
            if error_msg:
                self.show_error_message(error_msg)
                self.stop_drag()

    def stop_drag(self, ev: Optional[QMouseEvent] = None):
        """
        Handle mouse release to stop camera movement
        
        Args:
            ev: QMouseEvent (optional)
        """
        cid = self.th.active_cam_id
        self.th.manual_override[cid] = False
        self.th.cmd_p = 0
        self.th.cmd_t = 0
        
        # Invia comandi stop
        self.visca.send_without_response(cid, "01060105050303FF")

    def set_cam(self, cam_id: int):
        """
        Set the active camera
        
        Args:
            cam_id: Camera ID (1-6)
        """
        if self.th is not None:
            self.th.active_cam_id = cam_id
        
        # Aggiorna stile pulsanti
        for idx, btn in enumerate(self.cam_buttons, 1):
            if idx == cam_id:
                btn.setStyleSheet(
                    "background-color: #4CAF50; color: white; font-weight: bold;"
                )
            else:
                btn.setStyleSheet("")
        
        # Aggiorna status bar
        if self.th is not None:
            mode_name = MODE_NAMES[self.th.cam_modes[cam_id]]
        else:
            mode_name = "N/A"
        self.statusBar().showMessage(
            f"Camera {cam_id} selezionata - Modalità: {mode_name}",
            self.STATUS_MESSAGE_TIME
        )
        
        # Aggiorna display info
        self._update_camera_state_display()

    def cycle_mode(self):
        """Cycle through camera modes (MANUAL -> SCAN -> TRACK -> MANUAL)"""
        if self.th is None:
            return
            
        cid = self.th.active_cam_id
        
        # Calcola nuova modalità
        old_mode = self.th.cam_modes[cid]
        new_mode = (old_mode + 1) % 3
        
        # Aggiorna modalità
        self.th.cam_modes[cid] = new_mode
        
        # Messaggio informativo
        old_name = MODE_NAMES[old_mode]
        new_name = MODE_NAMES[new_mode]
        
        print(f"[MODE CHANGE] Camera {cid}: {old_name} -> {new_name}")
        
        # Reset timer per modalità SCAN
        if new_mode == MODE_SCAN:
            self.th.last_scan_time[cid] = 0
        
        # Aggiorna UI
        self.statusBar().showMessage(
            f"Camera {cid}: Modalità cambiata a {new_name}",
            self.STATUS_MESSAGE_TIME
        )
        
        # Aggiorna colore pulsante mode
        mode_colors = {
            MODE_MANUAL: "#4CAF50",  # Verde
            MODE_SCAN: "#FF9800",    # Arancione
            MODE_TRACK: "#2196F3"    # Blu
        }
        self.btn_mode.setStyleSheet(
            f"background-color: {mode_colors[new_mode]}; color: white; font-weight: bold;"
        )
        
    # Prima era: def move_camera(self, direction: str, hex_cmd: str):
    # Deve diventare:
    def move_camera(self, direction: str, hex_cmd: str, full_text: str = ""):
        """Sposta la telecamera e attiva lo zoom digitale"""
        if self.th is None:
            return
            
        cid = self.th.active_cam_id
        self.th.manual_override[cid] = True
        
        # Logica Pan/Tilt
        self.th.cmd_p = -1 if direction == "LT" else (1 if direction == "RT" else 0)
        self.th.cmd_t = -1 if direction == "UP" else (1 if direction == "DN" else 0)
        
        # LOGICA ZOOM (Adesso cerchiamo i simboli nel testo completo del bottone)
        if "+" in full_text:
            self.th.cmd_z = 1
        elif "-" in full_text:
            self.th.cmd_z = -1
        else:
            self.th.cmd_z = 0
            
        # Invia comando al simulatore
        error_msg = self.visca.send(cid, hex_cmd, retry=False)
        
        if error_msg:
            self.show_error_message(error_msg)
            self.stop()
            
    def stop(self):
        """Stop all camera movement with grace period"""
        # Guard: Se il VideoThread non è inizializzato, esci
        if self.th is None:
            return
        
        cid = self.th.active_cam_id
        
        # 1. Invia comandi stop reali
        self.visca.send_without_response(cid, "01060105050303FF")
        self.visca.send_without_response(cid, "01040700FF")
        
        # 2. Reset comandi di velocità
        self.th.cmd_p = 0
        self.th.cmd_t = 0
        self.th.cmd_z = 0
        
        # 3. NON spegnere subito l'override. 
        # Aggiorniamo il timestamp così il VideoThread aspetta 0.5s 
        # (se hai implementato il grace period nel VideoThread)
        import time
        self.th.last_manual_input_time = time.time()
        
        # Opzionale: Se vuoi essere sicuro, mantieni l'override True per un istante
        # Verrà spento dal VideoThread dopo mezzo secondo
        self.th.manual_override[cid] = True

    def show_error_message(self, message: str):
        """
        Show error message in UI
        
        Args:
            message: Error message to display
        """
        # Status bar
        self.statusBar().showMessage(f"⚠ {message}", self.ERROR_DISPLAY_TIME)
        
        # Error label
        self.error_label.setText(f"⚠ {message}")
        self.error_label.show()
        
        # Console log
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[ERROR {timestamp}] {message}")
        
        # Timer per nascondere errore
        QTimer.singleShot(self.ERROR_DISPLAY_TIME, lambda: self.error_label.hide())

    def _update_camera_state_display(self):
        """Aggiorna display dello stato telecamera"""
        if self.th is None:
            return
            
        cid = self.th.active_cam_id
        
        try:
            state = self.visca.get_camera_state_normalized(cid)
            mode_name = MODE_NAMES[self.th.cam_modes[cid]]
            
            info_text = (
                f"Modalità: {mode_name}\n"
                f"Zoom: {state['zoom']:.2f}x\n"
                f"Pan: {state['pan']*100:.0f}% | "
                f"Tilt: {state['tilt']*100:.0f}%"
            )
            
            self.info_label.setText(info_text)
            
        except Exception as e:
            self.info_label.setText(f"Errore stato: {e}")

    def closeEvent(self, event):
        """Handle window close event"""
        print("\n[SHUTDOWN] Chiusura applicazione...")
        
        # Ferma video thread
        if hasattr(self, 'th'):
            self.th.stop()
            self.th.wait(2000)  # Aspetta max 2 secondi
        
        # Chiudi VISCA controller
        if hasattr(self, 'visca'):
            self.visca.close()
        
        # Stampa statistiche
        if hasattr(self, 'visca'):
            stats = self.visca.get_statistics()
            print(f"[STATS] Statistiche sessione:")
            print(f"  - Comandi inviati: {stats.get('commands_sent', 0)}")
            print(f"  - Risposte ricevute: {stats.get('responses_received', 0)}")
            print(f"  - Errori: {stats.get('errors', 0)}")
            print(f"  - Timeout: {stats.get('timeouts', 0)}")
        
        print("[SHUTDOWN] Applicazione chiusa.\n")
        
        event.accept()