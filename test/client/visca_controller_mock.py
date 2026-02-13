"""
VISCA Controller Mock - Stub per testing senza libreria VISCA
Sostituisce visca_controller.py con un'implementazione semplificata
"""

from dataclasses import dataclass
from typing import Dict
import threading


@dataclass
class CameraState:
    """Stato simulato della telecamera"""
    pan: float = 0.0
    tilt: float = 0.0
    zoom: float = 1.0


class ViscaController:
    """Mock VISCA Controller - Non fa niente, solo simula lo stato"""
    
    def __init__(self, port: str = None, baudrate: int = 9600, timeout: float = 0.1):
        """Inizializza il controller mock"""
        self.camera_states: Dict[int, CameraState] = {
            i: CameraState() for i in range(1, 7)
        }
        self.state_lock = threading.RLock()
        print("[VISCA MOCK] Controller inizializzato (nessun dispositivo reale)")
    
    def send(self, camera_id: int, command_hex: str, retry: bool = False) -> bool:
        """Simula invio comando VISCA"""
        # Non fa niente - è solo uno stub per compatibility
        return True
    
    def get_camera_state(self, camera_id: int) -> Dict:
        """Ritorna lo stato della telecamera"""
        with self.state_lock:
            state = self.camera_states[camera_id]
            return {
                "pan": int(state.pan),
                "tilt": int(state.tilt),
                "zoom": state.zoom
            }
    
    def get_camera_state_normalized(self, camera_id: int) -> Dict[str, float]:
        """Ritorna lo stato normalizzato (0.0-1.0)"""
        with self.state_lock:
            state = self.camera_states[camera_id]
            # Converte da range [-1000, 1000] a [0.0, 1.0]
            pan_norm = max(0.0, min(1.0, (state.pan + 1000) / 2000))
            tilt_norm = max(0.0, min(1.0, (state.tilt + 1000) / 2000))
            
            return {
                "pan": pan_norm,
                "tilt": tilt_norm,
                "zoom": max(1.0, min(4.0, state.zoom))
            }
    
    def set_camera_state(self, camera_id: int, pan: float, tilt: float, zoom: float):
        """Aggiorna lo stato della telecamera"""
        with self.state_lock:
            self.camera_states[camera_id].pan = pan
            self.camera_states[camera_id].tilt = tilt
            self.camera_states[camera_id].zoom = zoom
    
    def close(self):
        """Chiude la connessione (no-op per mock)"""
        print("[VISCA MOCK] Controller chiuso")
