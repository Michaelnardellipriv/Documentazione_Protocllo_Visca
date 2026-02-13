"""
VISCA Controller - Interfaccia per comunicare con backend VISCA-over-IP
Tenta di usare la vera libreria, fallback a mock se non disponibile
"""

from typing import Dict
import threading
import time


class CameraState:
    """Stato snapshot della telecamera"""
    def __init__(self):
        self.pan: float = 0.0
        self.tilt: float = 0.0
        self.zoom: float = 1.0


# Tenta di importare la vera libreria
try:
    from visca_over_ip import Camera as ViscaCamera
    HAS_VISCA_LIBRARY = True
    print("[VISCA] Libreria visca_over_ip disponibile")
except ImportError:
    print("[VISCA] Libreria visca_over_ip non disponibile, usero mock")
    HAS_VISCA_LIBRARY = False
    ViscaCamera = None


class ViscaController:
    """Controller VISCA-over-IP per telecamere con fallback a mock"""
    
    def __init__(self, host: str = "localhost", port: int = 52381):
        """
        Inizializza il controller VISCA
        
        Args:
            host: Indirizzo IP del server VISCA (default: localhost)
            port: Porta VISCA (default: 52381)
        """
        self.host = host
        self.port = port
        self.cameras: Dict[int, any] = {}
        self.camera_states: Dict[int, CameraState] = {
            i: CameraState() for i in range(1, 7)
        }
        self.state_lock = threading.RLock()
        self.is_mock = not HAS_VISCA_LIBRARY
        
        print(f"[VISCA] Modalità: {'MOCK' if self.is_mock else 'REALE'}")
        print(f"[VISCA] Host: {host}:{port}")
        
        if not self.is_mock and ViscaCamera:
            # Connetti alle 6 telecamere con vera libreria
            # La libreria usa solo host, non port (VISCA-over-IP)
            for cam_id in range(1, 7):
                try:
                    cam = ViscaCamera(self.host)
                    self.cameras[cam_id] = cam
                    print(f"[VISCA] Camera {cam_id} connessa")
                except Exception as e:
                    print(f"[VISCA] Errore camera {cam_id}: {e}")
                    self.is_mock = True  # Fallback a mock
                    break
        else:
            # Mock: crea stub per tutte le telecamere
            for cam_id in range(1, 7):
                self.cameras[cam_id] = None
        
        # Thread di sincronizzazione stato
        self.sync_running = True
        self.sync_thread = threading.Thread(target=self._sync_state_loop, daemon=True)
        self.sync_thread.start()
    
    def _sync_state_loop(self):
        """Thread che legge periodicamente lo stato dalle telecamere"""
        while self.sync_running:
            try:
                if not self.is_mock:
                    # Leggi dallo stato reale
                    for cam_id in range(1, 7):
                        if cam_id in self.cameras and self.cameras[cam_id]:
                            cam = self.cameras[cam_id]
                            try:
                                pan = cam.get_pan()
                                tilt = cam.get_tilt()
                                zoom = cam.get_zoom()
                                
                                with self.state_lock:
                                    self.camera_states[cam_id].pan = float(pan) if pan is not None else 0.0
                                    self.camera_states[cam_id].tilt = float(tilt) if tilt is not None else 0.0
                                    self.camera_states[cam_id].zoom = (float(zoom) / 10.0) if zoom is not None else 1.0
                            except Exception as e:
                                pass
                
                time.sleep(0.05)
            except Exception as e:
                time.sleep(0.1)
    
    def send(self, camera_id: int, command_hex: str, retry: bool = False) -> bool:
        """Invia comando VISCA alla telecamera"""
        if self.is_mock:
            return True  # Finto successo in modalità mock
        
        if camera_id not in self.cameras or not self.cameras[camera_id]:
            return False
        
        try:
            cam = self.cameras[camera_id]
            cam._send_command(bytes.fromhex(command_hex))
            return True
        except Exception as e:
            return False
    
    def get_camera_state(self, camera_id: int) -> Dict:
        """Ritorna lo stato raw della telecamera"""
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
            
            # Pan/Tilt: da [-1000, 1000] a [0.0, 1.0]
            pan_norm = max(0.0, min(1.0, (state.pan + 1000.0) / 2000.0))
            tilt_norm = max(0.0, min(1.0, (state.tilt + 1000.0) / 2000.0))
            
            # Zoom: da 1.0x a 20.0x, mappato a 1.0-4.0 per UI
            zoom_ui = 1.0 + max(0.0, (state.zoom - 1.0) * 3.0 / 19.0)
            zoom_ui = max(1.0, min(4.0, zoom_ui))
            
            return {
                "pan": pan_norm,
                "tilt": tilt_norm,
                "zoom": zoom_ui
            }
    
    def close(self):
        """Chiude le connessioni"""
        self.sync_running = False
        if hasattr(self, 'sync_thread'):
            self.sync_thread.join(timeout=1.0)
        
        if not self.is_mock:
            for cam in self.cameras.values():
                try:
                    if cam:
                        cam.close()
                except:
                    pass
        
        print("[VISCA] Controller chiuso")

import socket
import threading
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from config import VISCA_PORT, CLIENT_BIND_IP


@dataclass
class CameraState:
    """Thread-safe camera state container"""
    pan: int = 0  # RAW: -1000 to 1000
    tilt: int = 0  # RAW: -1000 to 1000
    zoom: int = 200  # RAW: 100 to 400
    last_update: float = field(default_factory=time.time)
    
    def copy(self) -> 'CameraState':
        """Create a deep copy of the state"""
        return CameraState(
            pan=self.pan,
            tilt=self.tilt,
            zoom=self.zoom,
            last_update=self.last_update
        )


class ViscaController:
    """Gestisce la comunicazione protocollo VISCA con il server telecamere"""
    
    # Costanti di configurazione
    RESPONSE_TIMEOUT = 0.15  # Aumentato per reti più lente
    SYNC_INTERVAL = 0.3  # Sincronizzazione ogni 300ms
    STATE_TIMEOUT = 3.0  # Considera stale dopo 3 secondi
    MAX_RETRIES = 3
    RETRY_DELAY = 0.05
    
    def __init__(self, ip: str):
        """
        Inizializza il controller VISCA
        
        Args:
            ip: Indirizzo IP del server
        """
        self.server_ip = ip

        self.sequence = 1
        self._running = True
        
        # Stato sincronizzato delle telecamere
        self.camera_states: Dict[int, CameraState] = {
            i: CameraState() for i in range(1, 7)
        }
        
        # Lock separati per migliore concorrenza
        self._state_locks = {i: threading.RLock() for i in range(1, 7)}
        self._socket_lock = threading.Lock()
        
        # Statistiche e diagnostica
        self._stats = {
            "commands_sent": 0,
            "responses_received": 0,
            "errors": 0,
            "timeouts": 0
        }
        self._stats_lock = threading.Lock()
        
        # Mappatura codici errore
        self.error_codes = {
            0x40: "ZOOM_MAX - Zoom massimo raggiunto",
            0x41: "ZOOM_MIN - Zoom minimo raggiunto",
            0x42: "PAN_RIGHT_MAX - Pan destra massimo",
            0x43: "PAN_LEFT_MAX - Pan sinistra massimo",
            0x44: "TILT_UP_MAX - Tilt su massimo",
            0x45: "TILT_DOWN_MAX - Tilt giù massimo",
            0x4F: "GENERAL_ERROR - Errore generico telecamera"
        }
        
        # Inizializza socket
        self._init_socket()
        
        # Thread per sincronizzazione periodica
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        
        print(f"[VISCA] Controller inizializzato per server {ip}")
        print(f"[VISCA] Timeout risposta: {self.RESPONSE_TIMEOUT}s")
        print(f"[VISCA] Intervallo sync: {self.SYNC_INTERVAL}s")

    def _init_socket(self) -> bool:
        """
        Inizializza il socket UDP
        
        Returns:
            bool: True se successo
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((CLIENT_BIND_IP, 0))
            self.sock.settimeout(self.RESPONSE_TIMEOUT)
            print(f"[VISCA] Socket bound to {CLIENT_BIND_IP}")
            return True
        except Exception as e:
            print(f"[VISCA ERROR] Bind fallito: {e}")
            self.sock = None
            return False

    def send(self, cam_id: int, hex_cmd: str, retry: bool = True) -> Optional[str]:
        """
        Invia un comando VISCA over IP con gestione della sequenza e risposta asincrona.
        """
        if not self.sock:
            return "Errore: Socket non inizializzato"
        
        try:
            # 1. PULIZIA BUFFER (Evita di leggere risposte vecchie)
            self.sock.setblocking(False)
            while True:
                try:
                    self.sock.recvfrom(1024)
                except (BlockingIOError, socket.error):
                    break
            self.sock.setblocking(True)
            self.sock.settimeout(self.RESPONSE_TIMEOUT)

            # 2. PREPARAZIONE BYTE E INDIRIZZAMENTO (81, 82, ecc.)
            cmd_bytes = bytearray.fromhex(hex_cmd)
            # Forza l'ID telecamera nel primo byte (0x80 | cam_id)
            cmd_bytes[0] = 0x80 | (cam_id & 0x0F)
            
            # 3. COSTRUZIONE HEADER VISCA OVER IP E INVIO
            with self._socket_lock:
                # Byte 0-1: Tipo (01 00 = Comando), Byte 2-3: Lunghezza, Byte 4-7: Sequenza
                header = b'\x01\x00' + len(cmd_bytes).to_bytes(2, 'big') + self.sequence.to_bytes(4, 'big')
                
                full_packet = header + cmd_bytes
                state = self.get_camera_state(cam_id)
                pan = state["pan"]
                print(f"[UDP SEND] {full_packet.hex().upper()} | Pan letto: {pan:.4f}")
                self.sock.sendto(full_packet, (self.server_ip, VISCA_PORT))
                
                # Incrementiamo la sequenza per il prossimo comando
                self.sequence += 1
                
                # Piccola pausa per i comandi di movimento (SCAN/TRACK) 
                # per evitare congestione nel simulatore C#
                if "0601" in hex_cmd or "0407" in hex_cmd:
                    time.sleep(0.005)

            self._increment_stat("commands_sent")

            # 4. GESTIONE RICEZIONE
            # Se è un movimento (Pan/Tilt/Zoom), elaboriamo la risposta in background 
            # per non causare micro-scatti alla GUI durante lo SCAN o il TRACK.
            if "0601" in hex_cmd or "0407" in hex_cmd:
                threading.Thread(
                    target=self._process_response, 
                    args=(cam_id,), 
                    daemon=True
                ).start()
                return None 
            
            # Per comandi critici (Inquiry o Setup), attendiamo la risposta in linea
            return self._process_response(cam_id)

        except Exception as e:
            self._increment_stat("errors")
            return f"Errore invio VISCA: {e}"
        
    def send_without_response(self, cam_id: int, hex_cmd: str):
        """
        Invia comando VISCA senza aspettare risposta (per comandi di stop)
        
        Args:
            cam_id: ID telecamera (1-6)
            hex_cmd: Comando in stringa esadecimale
        """
        if not self.sock:
            return
        
        try:
            cmd_bytes = bytearray.fromhex(hex_cmd)
            cmd_bytes[0] = 0x80 | cam_id
            
            with self._socket_lock:
                header = (
                    b'\x01\x00' + 
                    len(cmd_bytes).to_bytes(2, 'big') + 
                    self.sequence.to_bytes(4, 'big')
                )
                self.sequence += 1
                self.sock.sendto(header + cmd_bytes, (self.server_ip, VISCA_PORT))
            
            self._increment_stat("commands_sent")
            
        except Exception as e:
            print(f"[VISCA ERROR] Send without response: {e}")

    def _process_response(self, cam_id: int) -> Optional[str]:
        try:
            # Ricezione dal socket
            response, _ = self.sock.recvfrom(1024)  
            self._increment_stat("responses_received")
            
            if not response: 
                return None
            
            # 8 byte di header VISCA over IP, il resto è il messaggio
            payload = response[8:] if response[0] == 0x01 else response

            if len(payload) >= 8:
                # Accettiamo 0x90 o 0x91 (Risposte dal simulatore C#)
                if payload[0] in [0x90, 0x91]:
                    self._update_state_from_response(cam_id, payload)
                    return None

        except (BlockingIOError, socket.timeout):
            return None 
        except Exception as e:
            if self._running:
                print(f"[VISCA DEBUG] Errore ricezione: {e}")
        return None

    def _parse_standard_response(self, cam_id: int, response: bytes) -> Optional[str]:
        """
        Analizza una risposta standard VISCA
        
        Args:
            cam_id: ID telecamera
            response: Bytes della risposta
            
        Returns:
            str: Messaggio di errore o None
        """
        if len(response) < 3:
            return None
            
        response_cam_id = response[1] & 0x0F
        completion_code = response[2]
        
        # Verifica telecamera corretta
        if response_cam_id != cam_id:
            return None  # Ignora risposte per altre telecamere
        
        # Codici di successo
        if completion_code == 0x00:
            # Richiedi stato aggiornato in background
            threading.Thread(
                target=self._request_status,
                args=(cam_id,),
                daemon=True
            ).start()
            return None
        
        # Codici di errore
        error_messages = {
            0x02: "Errore sintassi nel comando",
            0x03: "Buffer comandi telecamera pieno",
            0x04: "Comando cancellato",
            0x05: "Nessun socket disponibile"
        }
        
        if completion_code in error_messages:
            return error_messages[completion_code]
        
        # Errori limite
        if 0x40 <= completion_code <= 0x4F:
            return self.error_codes.get(
                completion_code,
                f"Errore 0x{completion_code:02X}"
            )
            
        return None

    def _update_state_from_response(self, cam_id: int, response: bytes):
        """Decodifica valori dal simulatore C# e aggiorna lo stato interno"""
        try:
            # Byte 2-3: Pan, 4-5: Tilt, 6-7: Zoom
            pan_raw = (response[2] << 8) | response[3]
            tilt_raw = (response[4] << 8) | response[5]
            zoom_raw = (response[6] << 8) | response[7]
            
            # Conversione in INTERI per la classe CameraState
            # Il C# manda 0..2000, noi salviamo -1000..1000
            new_pan = int(pan_raw - 1000)
            new_tilt = int(tilt_raw - 1000)
            new_zoom = int(zoom_raw)
            
            with self._state_locks[cam_id]:
                state = self.camera_states[cam_id]
                state.pan = new_pan
                state.tilt = new_tilt
                state.zoom = new_zoom
                state.last_update = time.time()
                
        except Exception as e:
            print(f"[VISCA ERROR] Update state cam {cam_id}: {e}")

    def _request_status(self, cam_id: int):
        """
        Richiede stato aggiornato della telecamera
        
        Args:
            cam_id: ID telecamera
        """
        if not self.sock:
            return
        
        try:
            inquiry_cmd = bytearray([0x80 | cam_id, 0x09, 0x06, 0x12, 0xFF])
            
            with self._socket_lock:
                header = (
                    b'\x01\x00' + 
                    len(inquiry_cmd).to_bytes(2, 'big') + 
                    self.sequence.to_bytes(4, 'big')
                )
                self.sequence += 1
                self.sock.sendto(header + inquiry_cmd, (self.server_ip, VISCA_PORT))
            
        except Exception as e:
            print(f"[VISCA ERROR] Request status: {e}")

    def _sync_loop(self):
        """Loop di sincronizzazione periodica ottimizzato"""
        print("[VISCA] Sync loop avviato")
        
        while self._running:
            try:
                current_time = time.time()
                
                for cam_id in range(1, 7):
                    # Verifica se stato è stale
                    with self._state_locks[cam_id]:
                        last_update = self.camera_states[cam_id].last_update
                    
                    if current_time - last_update > self.STATE_TIMEOUT:
                        self._request_status(cam_id)
                        time.sleep(0.02)  # Piccola pausa tra richieste
                
                time.sleep(self.SYNC_INTERVAL)
                
            except Exception as e:
                print(f"[VISCA ERROR] Sync loop: {e}")
                time.sleep(1)
        
        print("[VISCA] Sync loop terminato")

    def get_camera_state(self, cam_id: int) -> Dict[str, Any]:
        """
        Ottieni stato corrente della telecamera (valori RAW)
        
        Args:
            cam_id: ID telecamera (1-6)
            
        Returns:
            dict: Stato con valori RAW
        """
        with self._state_locks[cam_id]:
            state = self.camera_states[cam_id]
            return {
                "pan": state.pan,
                "tilt": state.tilt,
                "zoom": state.zoom,
                "last_update": state.last_update
            }

    def get_camera_state_normalized(self, cam_id: int) -> Dict[str, float]:
        """
        Ottieni stato normalizzato per display
        
        Args:
            cam_id: ID telecamera (1-6)
            
        Returns:
            dict: Stato normalizzato
        """
        with self._state_locks[cam_id]:
            state = self.camera_states[cam_id]
            
            # Normalizzazione
            pan_norm = (state.pan + 1000) / 2000.0
            tilt_norm = (state.tilt + 1000) / 2000.0
            zoom_display = state.zoom / 100.0
            
            # Clamp ai limiti
            return {
                "pan": max(0.0, min(1.0, pan_norm)),
                "tilt": max(0.0, min(1.0, tilt_norm)),
                "zoom": max(1.0, min(4.0, zoom_display))
            }

    def is_camera_at_limit(self, cam_id: int, axis: str) -> bool:
        """
        Controlla se la telecamera è al limite
        
        Args:
            cam_id: ID telecamera (1-6)
            axis: 'pan', 'tilt', o 'zoom'
            
        Returns:
            bool: True se al limite
        """
        with self._state_locks[cam_id]:
            state = self.camera_states[cam_id]
            
            limits = {
                "pan": (state.pan <= -1000 or state.pan >= 1000),
                "tilt": (state.tilt <= -1000 or state.tilt >= 1000),
                "zoom": (state.zoom <= 100 or state.zoom >= 400)
            }
            
            return limits.get(axis, False)

    def _increment_stat(self, stat_name: str):
        """Incrementa contatore statistiche in modo thread-safe"""
        with self._stats_lock:
            self._stats[stat_name] = self._stats.get(stat_name, 0) + 1

    def get_statistics(self) -> Dict[str, int]:
        """
        Ottieni statistiche di utilizzo
        
        Returns:
            dict: Statistiche correnti
        """
        with self._stats_lock:
            return self._stats.copy()

    def close(self):
        """Chiudi connessione e ferma thread"""
        print("[VISCA] Chiusura controller...")
        self._running = False
        
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=2.0)
        
        if self.sock:
            try:
                self.sock.close()
                print("[VISCA] Socket chiuso")
            except:
                pass
        
        # Stampa statistiche finali
        stats = self.get_statistics()
        print(f"[VISCA] Statistiche finali: {stats}")