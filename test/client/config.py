"""Configuration constants for VISCA Camera Control"""

# Network Configuration
DEFAULT_SERVER_IP = "10.91.60.15" # L'IP del simulatore
CLIENT_BIND_IP = "0.0.0.0"
VISCA_PORT = 52381        # Porta di destinazione (Simulatore)
CLIENT_PORT = 0           # <--- AGGIUNGI O MODIFICA QUESTA

# Window Configuration
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480

# Camera Configuration


DEFAULT_ZOOM = 2.0
MIN_ZOOM = 2.0
MAX_ZOOM = 4.0
ZOOM_STEP = 0.05

# Pan/Tilt Configuration
MIN_PAN_TILT = 0.0
MAX_PAN_TILT = 1.0
PAN_TILT_STEP = 0.01

# Face Detection Configuration
FACE_DETECTION_TIMEOUT = 2.0
FACE_MIN_ZOOM = 1.4
FACE_ZOOM_DECREASE_STEP = 0.02
FACE_PAN_SENSITIVITY = 0.0006
FACE_TILT_SENSITIVITY = 0.0006

# Video Thread Configuration
VIDEO_FRAME_DELAY = 0.03
SCAN_MODE_PAN_STEP = 0.008

# Drag Control Configuration
DRAG_PAN_SENSITIVITY = 0.05
DRAG_TILT_SENSITIVITY = 0.05
DRAG_CMD_SENSITIVITY = 5

# Mode Constants
# config.py
# Mode Constants
MODE_MANUAL = 0
MODE_SCAN = 1
MODE_TRACK = 2
MODE_NAMES = ["MANUAL", "SCAN", "TRACK"]  # Assicurati che sia così
# Colors (BGR format for OpenCV)
COLOR_MANUAL = (0, 255, 0)  # Green
COLOR_SCAN = (0, 165, 255)  # Orange
COLOR_TRACK = (255, 0, 0)   # Red
COLOR_CROSSHAIR = (0, 255, 0)  # Green

MAX_CAMERAS = 6 # Numero massimo di telecamere supportate dal backend