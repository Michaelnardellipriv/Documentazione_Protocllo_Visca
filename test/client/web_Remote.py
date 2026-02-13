import cv2
import time
import logging
from threading import Lock
from functools import lru_cache
from flask import Flask, render_template_string, Response, request, jsonify
import numpy as np
from queue import Queue
from typing import Optional, Dict, Any

# === IMPORTIAMO I MODULI ESISTENTI ===
from visca_controller import ViscaController
from visca_protocol_reference import VISCA_COMMANDS
import config

# ================= CONFIGURAZIONE =================
TARGET_IP = "127.0.0.1"  # IP del Simulatore C#
CAMERA_ID = 0
MAX_ZOOM = 15.0  # Aumentato lo zoom massimo
MIN_ZOOM = 3.0
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
OUTPUT_WIDTH = 640
OUTPUT_HEIGHT = 480
FPS_LIMIT = 30
# ==================================================

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VISCA-Web')

app = Flask(__name__)

# Connessione al Backend C#
try:
    controller = ViscaController(TARGET_IP)
    logger.info(f"Connesso al controller {TARGET_IP}")
except Exception as e:
    controller = None
    logger.warning(f"Controller non connesso: {e} (solo simulazione video)")

# === STATO GLOBALE PER IL CAMBIO MODALITÀ E TELECAMERA ===
class GlobalState:
    """Gestisce lo stato globale dell'applicazione"""
    def __init__(self):
        self.current_mode = 0  # 0=Manual, 1=Scan, 2=Track
        self.current_camera = 1  # 1-6
        self.lock = Lock()
    
    def set_mode(self, mode):
        with self.lock:
            self.current_mode = mode
            logger.info(f"Modalità impostata: {mode}")
    
    def set_camera(self, camera):
        with self.lock:
            if 1 <= camera <= 6:
                self.current_camera = camera
                logger.info(f"Telecamera impostata: CAM {camera}")
    
    def get_state(self):
        with self.lock:
            return {'mode': self.current_mode, 'camera': self.current_camera}

global_state = GlobalState()

# --- SIMULAZIONE MOVIMENTO (DIGITAL PTZ) CON MIGLIORAMENTI ---
class DigitalCamState:
    def __init__(self):
        self.x = 0.5
        self.y = 0.5
        self.zoom = 1.0
        self.current_action: Optional[str] = None
        self.last_update = time.time()
        self.speed = 0.5
        self.zoom_speed = 1.5
        self.lock = Lock()  # Thread safety
        
        # Smoothing dei movimenti
        self.target_x = 0.5
        self.target_y = 0.5
        self.target_zoom = 1.0
        self.smooth_factor = 0.15
        
    def update_loop(self):
        """Calcola la nuova posizione con smoothing"""
        now = time.time()
        dt = min(now - self.last_update, 0.1)  # Cap a 100ms per evitare salti
        self.last_update = now
        
        with self.lock:
            # Smooth movement verso il target
            self.x += (self.target_x - self.x) * self.smooth_factor
            self.y += (self.target_y - self.y) * self.smooth_factor
            self.zoom += (self.target_zoom - self.zoom) * self.smooth_factor * 2
            
            # Movimento continuo basato sull'azione corrente
            if self.current_action:
                move_step = (self.speed * dt) / self.zoom
                
                if self.current_action == 'left':
                    self.target_x = max(0.0, self.target_x - move_step)
                elif self.current_action == 'right':
                    self.target_x = min(1.0, self.target_x + move_step)
                elif self.current_action == 'up':
                    self.target_y = max(0.0, self.target_y - move_step)
                elif self.current_action == 'down':
                    self.target_y = min(1.0, self.target_y + move_step)
                elif self.current_action == 'zoom_in':
                    self.target_zoom = min(MAX_ZOOM, self.target_zoom + (self.zoom_speed * dt))
                elif self.current_action == 'zoom_out':
                    self.target_zoom = max(MIN_ZOOM, self.target_zoom - (self.zoom_speed * dt))

    def set_action(self, action: str):
        """Imposta l'azione corrente"""
        with self.lock:
            if action in ['stop', 'zoom_stop']:
                self.current_action = None
            else:
                self.current_action = action
        self.last_update = time.time()
    
    def get_state(self) -> Dict[str, Any]:
        """Restituisce lo stato corrente per API"""
        with self.lock:
            return {
                'x': round(self.x, 3),
                'y': round(self.y, 3),
                'zoom': round(self.zoom, 2),
                'action': self.current_action
            }
    
    def reset_position(self):
        """Reset posizione al centro"""
        with self.lock:
            self.target_x = 0.5
            self.target_y = 0.5
            self.target_zoom = 1.0
            self.current_action = None

cam_state = DigitalCamState()

ACTION_MAP = {
    'up': VISCA_COMMANDS["TILT_UP"],
    'down': VISCA_COMMANDS["TILT_DOWN"],
    'left': VISCA_COMMANDS["PAN_LEFT"],
    'right': VISCA_COMMANDS["PAN_RIGHT"],
    'stop': VISCA_COMMANDS["PAN_TILT_STOP"],
    'zoom_in': VISCA_COMMANDS["ZOOM_IN"],
    'zoom_out': VISCA_COMMANDS["ZOOM_OUT"],
    'zoom_stop': VISCA_COMMANDS["ZOOM_STOP"]
}

# --- MAPPING TASTIERA ---
KEYBOARD_MAP = {
    # Frecce per movimento
    'ArrowUp': 'up',
    'ArrowDown': 'down', 
    'ArrowLeft': 'left',
    'ArrowRight': 'right',
    
    # WASD per movimento alternativo
    'w': 'up',
    's': 'down',
    'a': 'left',
    'd': 'right',
    
    # Zoom con tasti + e - (sia numerici che normali)
    '+': 'zoom_in',
    '-': 'zoom_out',
    '=': 'zoom_in',  # Shift + = produce +
    '_': 'zoom_out', # Shift + - produce _
    
    # Zoom alternativo con Z e X
    'z': 'zoom_out',
    'x': 'zoom_in',
    
    # Tasti per zoom (keypad)
    'NumpadAdd': 'zoom_in',
    'NumpadSubtract': 'zoom_out',
    
    # Reset posizione
    'r': 'reset',
    'R': 'reset',  # Maiuscola
    'Home': 'reset',
    
    # Stop con spazio o ESC
    ' ': 'stop',
    'Escape': 'stop'
}

class WebVideoStreamer:
    def __init__(self, src=0):
        self.src = src
        self.video = None
        self.frame_queue = Queue(maxsize=2)
        self.running = True
        self.lock = Lock()
        self._init_camera()
        
    def _init_camera(self):
        """Inizializza o re-inizializza la camera"""
        try:
            if self.video:
                self.video.release()
            
            self.video = cv2.VideoCapture(self.src)
            self.video.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
            self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
            self.video.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.video.set(cv2.CAP_PROP_FPS, FPS_LIMIT)
            
            logger.info(f"Camera inizializzata: {self.src}")
            return True
        except Exception as e:
            logger.error(f"Errore inizializzazione camera: {e}")
            return False
    
    @lru_cache(maxsize=32)
    def _get_crop_coordinates(self, zoom: float, x: float, y: float, 
                             frame_width: int, frame_height: int) -> tuple:
        """Calcola coordinate di crop con caching per performance"""
        new_h = int(frame_height / zoom)
        new_w = int(frame_width / zoom)
        
        center_x = int(x * frame_width)
        center_y = int(y * frame_height)
        
        top = max(0, center_y - new_h // 2)
        left = max(0, center_x - new_w // 2)
        
        # Clamp
        if top + new_h > frame_height:
            top = frame_height - new_h
        if left + new_w > frame_width:
            left = frame_width - new_w
            
        return top, left, new_h, new_w
    
    def get_frame(self):
        """Ottiene e processa il frame corrente"""
        cam_state.update_loop()
        
        with self.lock:
            if not self.video or not self.video.isOpened():
                if not self._init_camera():
                    return self._get_error_frame()
            
            success, frame = self.video.read()
            
        if not success:
            return self._get_error_frame()
            
        try:
            h, w, _ = frame.shape
            state = cam_state.get_state()
            
            # Ottieni coordinate di crop (cached)
            top, left, new_h, new_w = self._get_crop_coordinates(
                state['zoom'], state['x'], state['y'], w, h
            )
            
            # Crop e resize
            cropped = frame[top:top+new_h, left:left+new_w]
            final = cv2.resize(cropped, (OUTPUT_WIDTH, OUTPUT_HEIGHT), 
                             interpolation=cv2.INTER_LANCZOS4)
            
            # HUD migliorato
            final = self._draw_hud(final, state)
            
            # Compressione JPEG ottimizzata
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 75,
                           cv2.IMWRITE_JPEG_PROGRESSIVE, 1,
                           cv2.IMWRITE_JPEG_OPTIMIZE, 1]
            
            ret, jpeg = cv2.imencode('.jpg', final, encode_params)
            
            if not ret:
                return self._get_error_frame()
                
            return jpeg.tobytes()
            
        except Exception as e:
            logger.error(f"Errore processing frame: {e}")
            return self._get_error_frame()
    
    def _draw_hud(self, frame: np.ndarray, state: Dict[str, Any]) -> np.ndarray:
        """Disegna HUD informativo sul frame"""
        h, w = frame.shape[:2]
        
        # Sfondo semitrasparente per il testo
        overlay = frame.copy()
        cv2.rectangle(overlay, (5, 5), (280, 110), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Testo stato
        color = (0, 255, 0) if state['action'] else (200, 200, 200)
        status = state['action'] or 'STOP'
        cv2.putText(frame, f"CMD: {status}", (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Zoom level
        cv2.putText(frame, f"ZOOM: {state['zoom']:.1f}x", (10, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Posizione
        cv2.putText(frame, f"POS: {state['x']:.2f}, {state['y']:.2f}", (10, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Hint tastiera
        cv2.putText(frame, "KEY: WASD/Arrows | +/- Zoom | R Reset", (10, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
        
        # Reticolo di mira
        cv2.circle(frame, (w//2, h//2), 20, (255, 255, 255), 1)
        cv2.line(frame, (w//2 - 30, h//2), (w//2 - 10, h//2), (255, 255, 255), 1)
        cv2.line(frame, (w//2 + 10, h//2), (w//2 + 30, h//2), (255, 255, 255), 1)
        cv2.line(frame, (w//2, h//2 - 30), (w//2, h//2 - 10), (255, 255, 255), 1)
        cv2.line(frame, (w//2, h//2 + 10), (w//2, h//2 + 30), (255, 255, 255), 1)
        
        return frame
    
    def _get_error_frame(self):
        """Genera un frame di errore"""
        error_img = np.zeros((OUTPUT_HEIGHT, OUTPUT_WIDTH, 3), dtype=np.uint8)
        cv2.putText(error_img, "Camera Error", (200, 240),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        ret, jpeg = cv2.imencode('.jpg', error_img)
        return jpeg.tobytes()
    
    def release(self):
        """Rilascia le risorse"""
        self.running = False
        if self.video:
            self.video.release()

# --- INTERFACCIA JAVASCRIPT CON SUPPORTO TASTIERA ---
HTML_UI = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>VISCA Touch Pro - Keyboard Ready</title>
    <style>
        * { 
            user-select: none; 
            -webkit-user-select: none; 
            -webkit-touch-callout: none; 
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body { 
            margin: 0; 
            background: #000; 
            height: 100vh; 
            overflow: hidden; 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        .video-bg { 
            position: absolute; 
            top: 0; 
            left: 0; 
            width: 100%; 
            height: 100%; 
            object-fit: cover; 
            z-index: 1; 
        }
        
        .ui-layer { 
            position: absolute; 
            top: 0; 
            left: 0; 
            width: 100%; 
            height: 100%; 
            z-index: 2; 
            display: flex; 
            flex-direction: column; 
            justify-content: flex-end; 
            padding: 20px; 
            box-sizing: border-box;
            background: linear-gradient(to top, rgba(0,0,0,0.3) 0%, transparent 30%);
        }
        
        .controls-row { 
            display: flex; 
            justify-content: space-between; 
            align-items: flex-end; 
            width: 100%; 
            margin-bottom: 20px; 
        }
        
        .d-pad { 
            display: grid; 
            grid-template-columns: 70px 70px 70px; 
            grid-template-rows: 70px 70px 70px; 
            gap: 8px; 
        }
        
        .zoom-pad { 
            display: flex; 
            flex-direction: column; 
            gap: 12px; 
        }
        
        button {
            background: rgba(20, 20, 30, 0.7); 
            border: 2px solid rgba(255, 255, 255, 0.3);
            backdrop-filter: blur(10px); 
            color: white; 
            border-radius: 16px; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            font-size: 28px;
            font-weight: 500;
            transition: all 0.08s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            cursor: pointer;
            touch-action: manipulation;
        }
        
        button:active, button.active, .key-press { 
            background: rgba(0, 200, 100, 0.8); 
            border-color: #00ff88;
            transform: scale(0.92);
            box-shadow: 0 0 20px rgba(0, 255, 100, 0.3);
        }
        
        .btn-dir { 
            width: 100%; 
            height: 100%; 
        }
        
        .btn-zoom { 
            width: 90px; 
            height: 90px; 
            border-radius: 50%; 
            font-size: 16px; 
            font-weight: bold;
            background: rgba(40, 40, 60, 0.8);
        }
        
        .ph { visibility: hidden; }
        
        .status-bar {
            position: absolute;
            top: 20px;
            left: 20px;
            right: 20px;
            background: rgba(0,0,0,0.5);
            backdrop-filter: blur(5px);
            padding: 12px 20px;
            border-radius: 30px;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 3;
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .reset-btn {
            background: rgba(255,60,60,0.3);
            border-color: rgba(255,100,100,0.5);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
        }
        
        .mode-selector, .camera-selector {
            display: flex;
            gap: 8px;
            margin-top: 10px;
        }
        
        .mode-btn, .camera-btn {
            flex: 1;
            padding: 10px;
            background: rgba(50,50,70,0.6);
            border: 2px solid rgba(255,255,255,0.2);
            color: white;
            border-radius: 12px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            transition: all 0.2s ease;
            backdrop-filter: blur(5px);
        }
        
        .mode-btn:hover, .camera-btn:hover {
            border-color: rgba(255,255,255,0.4);
            background: rgba(70,70,90,0.7);
        }
        
        .mode-btn.active {
            background: rgba(0,150,255,0.8);
            border-color: rgba(0,200,255,1);
            box-shadow: 0 0 15px rgba(0,200,255,0.4);
        }
        
        .camera-btn.active {
            background: rgba(100,200,100,0.8);
            border-color: rgba(100,255,100,1);
            box-shadow: 0 0 15px rgba(100,255,100,0.4);
        }
        
        .connection-status {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #00ff00;
            display: inline-block;
            margin-right: 8px;
        }
        
        .keyboard-hint {
            position: absolute;
            bottom: 140px;
            left: 20px;
            background: rgba(0,0,0,0.6);
            backdrop-filter: blur(5px);
            padding: 12px 20px;
            border-radius: 30px;
            color: #aaa;
            font-size: 13px;
            border: 1px solid rgba(255,255,255,0.2);
            z-index: 3;
        }
        
        @media (max-width: 480px) {
            .d-pad { grid-template-columns: 60px 60px 60px; grid-template-rows: 60px 60px 60px; }
            .btn-zoom { width: 70px; height: 70px; }
            .status-bar { font-size: 14px; }
            .keyboard-hint { display: none; } /* Nascondi hint su mobile */
        }
    </style>
</head>
<body>
    <div class="status-bar">
        <div>
            <span class="connection-status" id="conn-status"></span>
            <span id="status-text">VISCA Touch Pro</span>
        </div>
        <button id="reset-btn" class="reset-btn">⭮ RESET</button>
    </div>
    
    <div style="position: absolute; top: 90px; left: 20px; right: 20px; z-index: 3;">
        <div class="mode-selector">
            <button class="mode-btn active" data-mode="0">🎮 MANUAL</button>
            <button class="mode-btn" data-mode="1">🔄 SCAN</button>
            <button class="mode-btn" data-mode="2">👁️ TRACK</button>
        </div>
        <div class="camera-selector">
            <button class="camera-btn active" data-camera="1">CAM 1</button>
            <button class="camera-btn" data-camera="2">CAM 2</button>
            <button class="camera-btn" data-camera="3">CAM 3</button>
            <button class="camera-btn" data-camera="4">CAM 4</button>
            <button class="camera-btn" data-camera="5">CAM 5</button>
            <button class="camera-btn" data-camera="6">CAM 6</button>
        </div>
    </div>
    
    <div class="keyboard-hint">
        ⌨️ Tastiera: WASD/Frecce | +/- Zoom | Spazio Stop | R Reset
    </div>
    
    <img src="/video_feed" class="video-bg" id="video-feed">
    
    <div class="ui-layer">
        <div class="controls-row">
            <div class="d-pad">
                <div class="ph"></div> 
                <button id="up" class="btn-dir">▲</button> 
                <div class="ph"></div>
                
                <button id="left" class="btn-dir">◀</button> 
                <div class="ph"></div> 
                <button id="right" class="btn-dir">▶</button>
                
                <div class="ph"></div> 
                <button id="down" class="btn-dir">▼</button> 
                <div class="ph"></div>
            </div>
            <div class="zoom-pad">
                <button id="z-in" class="btn-zoom">ZOOM +</button>
                <button id="z-out" class="btn-zoom">ZOOM -</button>
            </div>
        </div>
    </div>

    <script>
        // Gestione connessione e comandi
        const send = async (cmd) => {
            if (navigator.vibrate && !cmd.includes('stop')) {
                navigator.vibrate(15);
            }
            
            try {
                const response = await fetch('/cmd/' + cmd, { 
                    method: 'POST',
                    cache: 'no-cache'
                });
                if (!response.ok) throw new Error('Network error');
                return true;
            } catch (err) {
                console.error('Command error:', err);
                updateConnectionStatus(false);
                return false;
            }
        };

        const bindButton = (id, startCmd, stopCmd) => {
            const btn = document.getElementById(id);
            if (!btn) return;
            
            let isPressed = false;
            
            const startAction = async (e) => {
                e.preventDefault();
                if (isPressed) return;
                isPressed = true;
                btn.classList.add('active');
                await send(startCmd);
            };
            
            const stopAction = async (e) => {
                e.preventDefault();
                if (!isPressed) return;
                isPressed = false;
                btn.classList.remove('active');
                await send(stopCmd);
            };

            // Mouse events
            btn.addEventListener('mousedown', startAction);
            btn.addEventListener('mouseup', stopAction);
            btn.addEventListener('mouseleave', stopAction);

            // Touch events
            btn.addEventListener('touchstart', startAction, { passive: false });
            btn.addEventListener('touchend', stopAction, { passive: false });
            btn.addEventListener('touchcancel', stopAction, { passive: false });
        };

        // === GESTIONE TASTIERA ===
        const activeKeys = new Set();
        let lastStopTime = 0;
        const STOP_DELAY = 50; // ms

        const getCommandFromKey = (key) => {
            const keyMap = {
                // Frecce
                'ArrowUp': 'up',
                'ArrowDown': 'down',
                'ArrowLeft': 'left',
                'ArrowRight': 'right',
                
                // WASD
                'w': 'up',
                'a': 'left',
                's': 'down',
                'd': 'right',
                'W': 'up',
                'A': 'left',
                'S': 'down',
                'D': 'right',
                
                // Zoom
                '+': 'zoom_in',
                '-': 'zoom_out',
                '=': 'zoom_in',
                '_': 'zoom_out',
                'z': 'zoom_out',
                'x': 'zoom_in',
                'Z': 'zoom_out',
                'X': 'zoom_in',
                
                // Reset
                'r': 'reset',
                'R': 'reset',
                
                // Stop
                ' ': 'stop',
                'Escape': 'stop'
            };
            
            return keyMap[key];
        };

        const handleKeyDown = async (e) => {
            // Previeni comportamenti di default per i tasti di controllo
            const controlKeys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', ' ', 'w', 'a', 's', 'd', '+', '-', '=', '_', 'z', 'x', 'r'];
            if (controlKeys.includes(e.key) || e.key.startsWith('Arrow')) {
                e.preventDefault();
            }
            
            const cmd = getCommandFromKey(e.key);
            if (!cmd) return;
            
            // Gestione speciale per reset
            if (cmd === 'reset') {
                await send('reset');
                return;
            }
            
            // Evita comandi duplicati
            if (activeKeys.has(cmd)) return;
            
            activeKeys.add(cmd);
            
            // Mostra feedback visivo
            showKeyFeedback(e.key);
            
            // Invia comando start
            await send(cmd);
        };

        const handleKeyUp = async (e) => {
            e.preventDefault();
            
            const cmd = getCommandFromKey(e.key);
            if (!cmd) return;
            
            // Non inviare stop per reset
            if (cmd === 'reset') return;
            
            activeKeys.delete(cmd);
            
            // Determina il comando stop appropriato
            let stopCmd = 'stop';
            if (cmd === 'zoom_in' || cmd === 'zoom_out') {
                stopCmd = 'zoom_stop';
            }
            
            // Debounce per evitare troppi stop
            const now = Date.now();
            if (now - lastStopTime > STOP_DELAY) {
                lastStopTime = now;
                await send(stopCmd);
            }
            
            // Rimuovi feedback visivo
            removeKeyFeedback(e.key);
        };

        // Feedback visivo per i tasti premuti
        const showKeyFeedback = (key) => {
            let buttonId = null;
            
            // Mappa tasti a bottoni UI
            if (key === 'ArrowUp' || key === 'w' || key === 'W') buttonId = 'up';
            if (key === 'ArrowDown' || key === 's' || key === 'S') buttonId = 'down';
            if (key === 'ArrowLeft' || key === 'a' || key === 'A') buttonId = 'left';
            if (key === 'ArrowRight' || key === 'd' || key === 'D') buttonId = 'right';
            if (key === '+' || key === '=' || key === 'x' || key === 'X') buttonId = 'z-in';
            if (key === '-' || key === '_' || key === 'z' || key === 'Z') buttonId = 'z-out';
            
            if (buttonId) {
                const btn = document.getElementById(buttonId);
                if (btn) btn.classList.add('key-press');
            }
        };

        const removeKeyFeedback = (key) => {
            let buttonId = null;
            
            if (key === 'ArrowUp' || key === 'w' || key === 'W') buttonId = 'up';
            if (key === 'ArrowDown' || key === 's' || key === 'S') buttonId = 'down';
            if (key === 'ArrowLeft' || key === 'a' || key === 'A') buttonId = 'left';
            if (key === 'ArrowRight' || key === 'd' || key === 'D') buttonId = 'right';
            if (key === '+' || key === '=' || key === 'x' || key === 'X') buttonId = 'z-in';
            if (key === '-' || key === '_' || key === 'z' || key === 'Z') buttonId = 'z-out';
            
            if (buttonId) {
                const btn = document.getElementById(buttonId);
                if (btn) btn.classList.remove('key-press');
            }
        };

        const updateConnectionStatus = (isConnected) => {
            const statusEl = document.getElementById('conn-status');
            const textEl = document.getElementById('status-text');
            
            if (statusEl) {
                statusEl.style.background = isConnected ? '#00ff00' : '#ff0000';
            }
            if (textEl) {
                textEl.textContent = isConnected ? 'Connesso' : 'Riconnessione...';
            }
        };

        // Verifica connessione periodica
        const checkConnection = async () => {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateConnectionStatus(data.controller_connected);
            } catch (err) {
                updateConnectionStatus(false);
            }
        };

        window.onload = () => {
            // Bind controlli touch/mouse
            bindButton('up', 'up', 'stop');
            bindButton('down', 'down', 'stop');
            bindButton('left', 'left', 'stop');
            bindButton('right', 'right', 'stop');
            bindButton('z-in', 'zoom_in', 'zoom_stop');
            bindButton('z-out', 'zoom_out', 'zoom_stop');
            
            // === FUNZIONE PER SINCRONIZZARE LO STATO UI ===
            const syncState = async () => {
                try {
                    const response = await fetch('/api/get-state');
                    const data = await response.json();
                    
                    // Aggiorna UI modalità
                    document.querySelectorAll('.mode-btn').forEach((btn, idx) => {
                        if (parseInt(btn.dataset.mode) === data.mode) {
                            btn.classList.add('active');
                        } else {
                            btn.classList.remove('active');
                        }
                    });
                    
                    // Aggiorna UI telecamera
                    document.querySelectorAll('.camera-btn').forEach((btn) => {
                        if (parseInt(btn.dataset.camera) === data.camera) {
                            btn.classList.add('active');
                        } else {
                            btn.classList.remove('active');
                        }
                    });
                } catch (err) {
                    console.error('Errore sincronizzazione stato:', err);
                }
            };
            
            // === GESTIONE MODALITÀ ===
            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const mode = e.target.dataset.mode;
                    
                    // Invia comando al server
                    try {
                        const response = await fetch(`/api/set-mode/${mode}`, {method: 'POST'});
                        const data = await response.json();
                        console.log('Modalità impostata:', data);
                        
                        // Sincronizza UI
                        setTimeout(syncState, 100);
                    } catch (err) {
                        console.error('Errore cambio modalità:', err);
                    }
                });
            });
            
            // === GESTIONE TELECAMERA ===
            document.querySelectorAll('.camera-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const camera = e.target.dataset.camera;
                    
                    // Invia comando al server
                    try {
                        const response = await fetch(`/api/set-camera/${camera}`, {method: 'POST'});
                        const data = await response.json();
                        console.log('Telecamera impostata:', data);
                        
                        // Sincronizza UI
                        setTimeout(syncState, 100);
                    } catch (err) {
                        console.error('Errore cambio telecamera:', err);
                    }
                });
            });
            
            // Reset button
            document.getElementById('reset-btn').addEventListener('click', async () => {
                await send('reset');
            });
            
            // Keyboard event listeners
            window.addEventListener('keydown', handleKeyDown);
            window.addEventListener('keyup', handleKeyUp);
            
            // Previeni comportamenti di default per tasti freccia su tutta la pagina
            window.addEventListener('keydown', (e) => {
                if (e.key.startsWith('Arrow') || e.key === ' ') {
                    e.preventDefault();
                }
            }, false);
            
            // Sincronizza stato iniziale
            syncState();
            
            // Connection check ogni 3 secondi
            checkConnection();
            setInterval(checkConnection, 3000);
            
            // Sincronizza stato ogni 2 secondi
            setInterval(syncState, 2000);
            
            // Gestione errori video
            const videoFeed = document.getElementById('video-feed');
            videoFeed.onerror = () => {
                setTimeout(() => {
                    videoFeed.src = '/video_feed?' + new Date().getTime();
                }, 1000);
            };
            
            // Cleanup
            window.addEventListener('beforeunload', () => {
                window.removeEventListener('keydown', handleKeyDown);
                window.removeEventListener('keyup', handleKeyUp);
            });
        };
    </script>
</body>
</html>
"""

# ============= ROUTES FLASK =============
@app.route('/')
def index():
    return render_template_string(HTML_UI)

def generate_frames(streamer):
    """Generator per lo streaming video"""
    while True:
        try:
            frame = streamer.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                time.sleep(0.05)
        except GeneratorExit:
            break
        except Exception as e:
            logger.error(f"Errore nel generator: {e}")
            time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    """Endpoint streaming video"""
    streamer = WebVideoStreamer(0)
    return Response(
        generate_frames(streamer),
        mimetype='multipart/x-mixed-replace; boundary=frame',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )

@app.route('/cmd/<action>', methods=['POST'])
def command(action):
    """Endpoint comandi PTZ"""
    try:
        # Comando speciale reset
        if action == 'reset':
            cam_state.reset_position()
            logger.info("Reset posizione camera")
            return jsonify({'status': 'ok', 'message': 'Reset eseguito'}), 200
        
        # Aggiorna stato interno
        cam_state.set_action(action)
        
        # Invia comando al simulatore C#
        if controller and action in ACTION_MAP:
            controller.send(CAMERA_ID, ACTION_MAP[action], retry=False)
        
        return jsonify({'status': 'ok', 'action': action}), 200
        
    except Exception as e:
        logger.error(f"Errore comando {action}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/status')
def api_status():
    """Endpoint API per lo stato"""
    return jsonify({
        'controller_connected': controller is not None,
        'camera_state': cam_state.get_state(),
        'timestamp': time.time()
    })

@app.route('/api/keyboard-map')
def keyboard_map():
    """Endpoint per ottenere il mapping tastiera"""
    return jsonify(KEYBOARD_MAP)

@app.route('/api/set-mode/<int:mode>', methods=['POST'])
def set_mode(mode):
    """Cambia la modalità della telecamera (0=Manual, 1=Scan, 2=Track)"""
    try:
        if mode in [0, 1, 2]:
            global_state.set_mode(mode)
            mode_names = ['MANUAL', 'SCAN', 'TRACK']
            return jsonify({'status': 'ok', 'mode': mode, 'mode_name': mode_names[mode]}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Modalità non valida'}), 400
    except Exception as e:
        logger.error(f"Errore cambio modalità: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/set-camera/<int:camera>', methods=['POST'])
def set_camera(camera):
    """Cambia la telecamera attiva (1-6)"""
    try:
        if 1 <= camera <= 6:
            global_state.set_camera(camera)
            return jsonify({'status': 'ok', 'camera': camera}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Telecamera non valida'}), 400
    except Exception as e:
        logger.error(f"Errore cambio telecamera: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/get-state')
def get_state_api():
    """Restituisce lo stato attuale"""
    state = global_state.get_state()
    mode_names = ['MANUAL', 'SCAN', 'TRACK']
    return jsonify({
        'mode': state['mode'],
        'mode_name': mode_names[state['mode']],
        'camera': state['camera'],
        'timestamp': time.time()
    }), 200

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Risorsa non trovata'}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Errore interno: {e}")
    return jsonify({'error': 'Errore interno del server'}), 500

if __name__ == '__main__':
    logger.info("=== AVVIO WEB REMOTE TOUCH PRO CON SUPPORTO TASTIERA ===")
    print("\n🎮 Controllo da tastiera attivo!")
    print("   ↑/W: Muovi su     ↓/S: Muovi giù")
    print("   ←/A: Muovi sinistra →/D: Muovi destra")
    print("   +/-: Zoom in/out   Z/X: Zoom alternativo")
    print("   Spazio/ESC: Stop   R: Reset posizione\n")
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            threaded=True,
            debug=False  # Disabilita debug in produzione
        )
    except KeyboardInterrupt:
        logger.info("Server fermato dall'utente")
    except Exception as e:
        logger.error(f"Errore fatale: {e}")
    finally:
        logger.info("Chiusura server...")