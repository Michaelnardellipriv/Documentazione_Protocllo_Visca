"""Video capture and processing thread - OPTIMIZED SMOOTH MOVEMENT"""

import time
import cv2
import numpy as np
from typing import Optional, Dict
from dataclasses import dataclass
import threading
from queue import Queue
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage
from visca_controller import ViscaController
from config import (
    MODE_MANUAL, MODE_SCAN, MODE_TRACK, MODE_NAMES,
    COLOR_MANUAL, COLOR_SCAN, COLOR_TRACK, 
    VIDEO_WIDTH, VIDEO_HEIGHT
)


@dataclass
class CameraDisplayState:
    """Stato display della telecamera per interpolazione"""
    zoom: float = 2.0
    pan: float = 0.5
    tilt: float = 0.5


class VideoThread(QThread):
    """Thread per acquisizione video con movimento fluido ottimizzato"""
    
    change_pixmap_signal = pyqtSignal(QImage)

    # Configurazione interpolazione ottimizzata
    INTERPOLATION_SPEED = 0.65  # Più veloce = meno lag
    SYNC_INTERVAL = 0.04  # 25 Hz sincronizzazione
    TARGET_FPS = 60
    FRAME_TIME = 1.0 / TARGET_FPS
    
    # Soglie per movimenti significativi
    MIN_MOVEMENT_THRESHOLD = 15  # pixels per face tracking
    
    def __init__(self, visca_controller: ViscaController):
        super().__init__()
        self.visca_controller = visca_controller
        self._run_flag = True
        
        # --- Sistema di cattura asincrona sicuro ---
        self.frame_lock = threading.Lock()
        self.latest_raw_frame = None
        self.capture_running = True
        self.cap = None # Inizializza prima
        
        # --- Coda thread-safe per frame (alternativa ai signals) ---
        self.frame_queue = Queue(maxsize=2)  # Keep only 2 latest frames
        # ------------------------------------------

        self.active_cam_id = 1
        self.cam_modes = {i: MODE_MANUAL for i in range(1, 7)}
        self.manual_override = {i: False for i in range(1, 7)}
        self.last_face_time = {i: time.time() for i in range(1, 7)}
        
        self.cmd_p = 0
        self.cmd_t = 0
        self.cmd_z = 0
        self.scan_dir = {i: 1 for i in range(1, 7)}
        
        self.cached_state = {i: CameraDisplayState() for i in range(1, 7)}
        self.display_state = {i: CameraDisplayState() for i in range(1, 7)}
        
        self.last_sync_time = time.time()
        self.last_scan_time = {i: 0.0 for i in range(1, 7)}
        self.last_track_time = {i: 0.0 for i in range(1, 7)}
        self.last_manual_input_time = 0
        
        self.face_cascade: Optional[cv2.CascadeClassifier] = None
        self._init_face_detection()
        
        # Fondamentale: apri la camera PRIMA di far partire il thread di lettura
        self.cap = self._init_video_capture()
        
        # Ora avvia il thread di lettura
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        self.frame_count = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0
    def _capture_loop(self):
        """Thread secondario: svuota il buffer hardware il più velocemente possibile"""
        while self.capture_running:
            if self.cap is not None and self.cap.isOpened():
                try:
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        # Operazione atomica: proteggiamo la scrittura del frame
                        with self.frame_lock:
                            # .copy() qui è essenziale per disconnettere la memoria
                            # dal buffer interno di OpenCV
                            self.latest_raw_frame = frame.copy()
                    else:
                        time.sleep(0.01)
                except Exception as e:
                    print(f"[CAPTURE ERROR] {e}")
                    time.sleep(0.1)
            else:
                time.sleep(0.1)
    def _init_face_detection(self):
        """Inizializza face detection con fallback"""
        try:
            # Carica il classificatore Haar Cascade per il rilevamento dei volti
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            
            if self.face_cascade.empty():
                print("[INIT] Haar Cascade file not found - Face detection disabled")
                self.face_cascade = None
            else:
                print(f"[INIT] Face detection enabled - using {cascade_path}")
        except Exception as e:
            print(f"[INIT] Face detection init error: {e}")
            self.face_cascade = None

    def _init_video_capture(self) -> cv2.VideoCapture:
        """Inizializza video capture con fallback - PROTETTO"""
        print("[INIT] Inizializzazione webcam...")
        
        cap = None
        try:
            cap = cv2.VideoCapture(0)
            print("[INIT] Tentativo VideoCapture(0)...")
            
            if not cap.isOpened():
                print("[INIT] VideoCapture(0) failed - tentando /dev/video0...")
                cap = cv2.VideoCapture("/dev/video0")
            
            if cap.isOpened():
                # Ottimizza parametri capture
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Riduce latenza
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"[INIT] Webcam OK: {w}x{h}")
                except Exception as e:
                    print(f"[INIT] Error setting camera properties: {e}")
            else:
                print("[INIT] Nessuna webcam trovata - modalità simulazione")
                cap = None
                
        except Exception as e:
            print(f"[INIT] Exception in video capture init: {e}")
            cap = None
        
        return cap

    def run(self):
        """Loop principale QThread - PROTETTO DA SEGFAULT"""
        print("[RUN] Thread logica video avviato")
        
        frame_count = 0
        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 10
        
        # Delay iniziale per dare tempo all'UI di inizializzarsi
        time.sleep(1.0)
        print("[RUN] Inizio emissione frame...")
        
        while self._run_flag:
            try:
                # Prova a recuperare frame dalla webcam PRIMA
                debug_frame = None
                
                try:
                    if self.cap is not None and self.cap.isOpened():
                        ret, frame = self.cap.read()
                        if ret and frame is not None and frame.size > 0:
                            debug_frame = frame
                except Exception as cap_err:
                    print(f"[RUN] Camera read error: {cap_err}")
                    debug_frame = None
                
                # Se non c'è frame dalla camera, crea uno di debug
                if debug_frame is None:
                    try:
                        debug_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                        # Prova a usare cv2.putText, ma ha fallback
                        try:
                            cv2.putText(debug_frame, f"Debug Frame {frame_count}", (50, 100),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        except Exception as put_text_err:
                            # Fallback: disegna manualmente senza cv2
                            debug_frame.fill(50)  # Grigio scuro
                            # Riempi un angolo per indicare che è vivo
                            debug_frame[10:20, 10:40] = [0, 255, 0]
                    except Exception as frame_err:
                        print(f"[RUN] Debug frame creation error: {frame_err}")
                        consecutive_errors += 1
                        if consecutive_errors > MAX_CONSECUTIVE_ERRORS:
                            print("[RUN] Stopping thread due to repeated errors")
                            break
                        time.sleep(0.1)
                        continue
                
                frame_count += 1
                consecutive_errors = 0  # Reset on success
                
                # Aggiorna logica dei comandi (pan/tilt/zoom)
                try:
                    self._process_camera_commands()
                except Exception as cmd_err:
                    print(f"[RUN] Camera command error: {cmd_err}")
                
                # Sincronizza lo stato dal backend VISCA (essenziale per SCAN/TRACK)
                try:
                    self._sync_state_from_backend()
                except Exception as sync_err:
                    print(f"[RUN] Sync error: {sync_err}")
                
                # Processa modalità TRACK se attiva
                try:
                    cid = self.active_cam_id
                    mode = self.cam_modes[cid]
                    if mode == MODE_TRACK:
                        # Recupera frame dalla webcam per face detection
                        frame_for_tracking = self._capture_frame()
                        self._process_track_mode(frame_for_tracking, cid)
                except Exception as track_err:
                    print(f"[RUN] Track mode error: {track_err}")
                
                # Interpola gli stati display per movimento fluido
                try:
                    self._interpolate_display_state()
                except Exception as interp_err:
                    print(f"[RUN] Interpolation error: {interp_err}")
                
                # Applica elaborazioni al frame (zoom digitale, pan, tilt)
                try:
                    cid = self.active_cam_id
                    
                    # Applica zoom digitale
                    processed_frame = self.digital_zoom(debug_frame, cid)
                    
                    # Disegna OSD (On-Screen Display)
                    self.draw_osd(processed_frame, cid)
                except Exception as proc_err:
                    print(f"[RUN] Frame processing error: {proc_err}")
                    processed_frame = debug_frame
                
                # Prova a emettere il frame CON protezione
                try:
                    self._emit_frame(processed_frame)
                except Exception as emit_err:
                    print(f"[RUN] Emit error: {emit_err}")
                    consecutive_errors += 1
                
                # Aggiorna FPS counter
                try:
                    self._update_fps_counter()
                except Exception as fps_err:
                    print(f"[RUN] FPS counter error: {fps_err}")
                
                # Piccolo sleep per non bruciare CPU
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                print(f"[RUN ERROR] Unexpected error: {e}")
                consecutive_errors += 1
                if consecutive_errors > MAX_CONSECUTIVE_ERRORS:
                    print("[RUN] Stopping thread due to repeated errors")
                    break
                time.sleep(0.1)
    def get_latest_frame(self) -> Optional[QImage]:
        """Recupera il frame più recente dalla coda (thread-safe)"""
        try:
            # Non bloccare - solo prova a leggere
            return self.frame_queue.get_nowait()
        except:
            return None

    def _capture_frame(self) -> np.ndarray:
        """Recupera l'ultimo frame in modo thread-safe"""
        with self.frame_lock:
            if self.latest_raw_frame is not None:
                # Restituiamo una copia per evitare che il thread di cattura 
                # sovrascriva mentre facciamo face detection
                return self.latest_raw_frame.copy()
        
        # Fallback: se non c'è ancora un frame, creiamo una matrice nera
        return np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), np.uint8)
    def _interpolate_display_state(self):
        """Interpola tutti gli stati display verso target"""
        for cid in range(1, 7):
            target = self.cached_state[cid]
            current = self.display_state[cid]
            
            # Lerp con velocità ottimizzata
            current.zoom = self._lerp(current.zoom, target.zoom, self.INTERPOLATION_SPEED)
            current.pan = self._lerp(current.pan, target.pan, self.INTERPOLATION_SPEED)
            current.tilt = self._lerp(current.tilt, target.tilt, self.INTERPOLATION_SPEED)

    def _lerp(self, current: float, target: float, speed: float) -> float:
        """Linear interpolation ottimizzata"""
        diff = target - current
        
        # Se differenza molto piccola, snap al target per evitare oscillazioni
        if abs(diff) < 0.001:
            return target
        
        return current + diff * speed

    def _process_camera_commands(self):
        cid = self.active_cam_id
        current_time = time.time()
        mode = self.cam_modes[cid]
        
        # 1. Gestione Input manuale
        is_manual_input = (self.cmd_p != 0 or self.cmd_t != 0 or self.cmd_z != 0)
        
        if is_manual_input:
            self.last_manual_input_time = current_time
            self.manual_override[cid] = True
            self._send_manual_commands(cid)
        else:
            if current_time - self.last_manual_input_time > 3.0:
                self.manual_override[cid] = False
                
        # 2. Modalità Automatiche
        if not self.manual_override[cid]:
            if mode == MODE_SCAN:
                self._process_scan_mode(cid, current_time)
            # NOTA: MODE_TRACK viene elaborato in _prepare_display_frame() per avere
            # accesso al frame PRIMA del digital_zoom e delle modifiche di rendering
    def _send_manual_commands(self, cid: int):
        """Invia comandi manuali e aggiorna localmente il target per feedback immediato"""
        commands_sent = False
        target = self.cached_state[cid]
        
        # 1. FEEDBACK LOCALE (Client-Side Prediction)
        # Muoviamo subito il target interno. L'interpolazione (LERP) 
        # renderà il movimento fluido nel prossimo frame.
        step = 0.02  # Sensibilità movimento digitale
        z_step = 0.05 # Sensibilità zoom digitale
        
        # Gestione Pan (Orizzontale)
        if self.cmd_p != 0:
            target.pan = max(0.0, min(1.0, target.pan + (self.cmd_p * step)))
            commands_sent = True

        # Gestione Tilt (Verticale)
        if self.cmd_t != 0:
            target.tilt = max(0.0, min(1.0, target.tilt + (self.cmd_t * step)))
            commands_sent = True
            
        # Gestione Zoom
        if self.cmd_z != 0:
            target.zoom = max(1.0, min(4.0, target.zoom + (self.cmd_z * z_step)))
            commands_sent = True

        if self.cmd_z != 0:
            # Forza un cambiamento visibile: 0.1 per ogni scatto
            cambio = 0.1 * self.cmd_z
            target.zoom += cambio
            
            # Mantieni nei limiti
            if target.zoom < 2.0: target.zoom = 2.0
            if target.zoom > 4.0: target.zoom = 4.0
            
            # Invia al simulatore
            cmd = "01040702FF" if self.cmd_z > 0 else "01040703FF"
            self.visca_controller.send(cid, cmd, retry=False)
           
            # 2. INVIO COMANDI REALI AL SIMULATORE (VISCA)
        # Inviamo i comandi solo se c'è un cambiamento di stato
        if commands_sent:
            # Pan/Tilt combinati
            pan_dir = "01" if self.cmd_p < 0 else ("02" if self.cmd_p > 0 else "03")
            tilt_dir = "01" if self.cmd_t < 0 else ("02" if self.cmd_t > 0 else "03")
            
            pan_tilt_hex = f"0106010505{pan_dir}{tilt_dir}FF"
            self.visca_controller.send(cid, pan_tilt_hex, retry=False)
            
            
                        
        self.last_face_time[cid] = time.time()
#scan mode: muove la telecamera continuamente tra i bordi, invertendo direzione ai limiti. La logica di controllo è eseguita ogni 0.5s per garantire reattività senza sovraccaricare il backend con comandi troppo frequenti.
    # In video_thread.py -> scanmode
    def _process_scan_mode(self, cid: int, current_time: float):
        self.manual_override[cid] = False
        
        if current_time - self.last_scan_time[cid] < 0.15:
            return
        self.last_scan_time[cid] = current_time

        self.visca_controller.send(cid, "81090612FF", retry=False)

        # --- MODIFICA QUI ---
        # Invece di state = self.get_camera_state(cid)
        # Accediamo direttamente all'oggetto per evitare filtri
        state_obj = self.visca_controller.camera_states[cid]
        
        # Proviamo a leggere 'pan' (che nel tuo controller abbiamo salvato come intero)
        current_pan = float(state_obj.pan) 

        # Questo log DEVE mostrare -1000 o 1000, non 0.00!
        print(f">>> TEST FINALE: Pan={current_pan:.2f} | Dir={self.scan_dir[cid]}")

        # LOGICA DI INVERSIONE (Soglie basate su 1000)
        if self.scan_dir[cid] > 0 and current_pan >= 950:
            print("!!! INVERTO A DESTRA")
            self.scan_dir[cid] = -1
            self.visca_controller.send(cid, "01060100000303FF", retry=False)
            return

        elif self.scan_dir[cid] < 0 and current_pan <= -950:
            print("!!! INVERTO A SINISTRA")
            self.scan_dir[cid] = 1
            self.visca_controller.send(cid, "01060100000303FF", retry=False)
            return

        # Movimento
        p_dir = "02" if self.scan_dir[cid] > 0 else "01"
        self.visca_controller.send(cid, f"0106010505{p_dir}03FF", retry=False)
    def _process_track_mode_simple(self, frame: Optional[np.ndarray], cid: int):
        """
        Modalità tracking semplificata - senza face detection.
        Simula il movimento automatico verso il centro.
        """
        current_time = time.time()
        if current_time - self.last_track_time[cid] < 0.05:
            return
        self.last_track_time[cid] = current_time
        
        target = self.cached_state[cid]
        
        # Simula movimento graduale verso il centro
        # Pan: avanza verso 0.5 (centro)
        pan_diff = 0.5 - target.pan
        if abs(pan_diff) > 0.05:
            target.pan += pan_diff * 0.05  # Movimento lento verso centro
            print(f"[TRACK SIMPLE] CAM {cid} Pan: {target.pan:.3f}")
        
        # Tilt: avanza verso 0.5 (centro)
        tilt_diff = 0.5 - target.tilt
        if abs(tilt_diff) > 0.05:
            target.tilt += tilt_diff * 0.05
            print(f"[TRACK SIMPLE] CAM {cid} Tilt: {target.tilt:.3f}")
        
        # Zoom: avanza verso 2.0x (medio)
        zoom_diff = 2.0 - target.zoom
        if abs(zoom_diff) > 0.1:
            target.zoom += zoom_diff * 0.02
            target.zoom = max(1.0, min(4.0, target.zoom))
            print(f"[TRACK SIMPLE] CAM {cid} Zoom: {target.zoom:.2f}")
    
    def _process_track_mode(self, frame: Optional[np.ndarray], cid: int):
        """
        Modalità tracciamento automatico del viso.
        Usa zoom digitale per centrare e seguire il viso.
        """
        if frame is None or self.face_cascade is None:
            return
        
        # Protezione: verifica che il frame sia valido
        if frame.size == 0 or len(frame.shape) != 3:
            print(f"[TRACK ERROR] Frame non valido: shape={frame.shape if frame is not None else 'None'}")
            return
        
        # 1. Throttling per evitare troppi comandi
        current_time = time.time()
        if current_time - self.last_track_time[cid] < 0.05:  # 50ms tra aggiornamenti (20 Hz)
            return
        self.last_track_time[cid] = current_time

        # 2. Rilevamento volti
        try:
            # Converti a grayscale in modo sicuro
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            except Exception as cvt_err:
                # Fallback: usa slicing manuale
                gray = frame[:, :, 0]  # Prendi solo il canale B
            
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 6, minSize=(50, 50))
            
            if len(faces) == 0:
                # Quando non rilevato: riporta gradualmente al centro
                target = self.cached_state[cid]
                target.pan = target.pan + (0.5 - target.pan) * 0.1  # Ritorna lentamente al centro
                target.tilt = target.tilt + (0.5 - target.tilt) * 0.1
                self.visca_controller.send(cid, "01060105050303FF", retry=False)
                return
            
        except Exception as e:
            print(f"[TRACK ERROR] Face detection failed: {e}")
            return
        
        try:
            # 3. Seleziona il volto più grande
            fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            
            # Protezione: verifica indici validi
            if not (0 <= fx < frame.shape[1] and 0 <= fy < frame.shape[0]):
                return
            
            # Dimensioni frame
            frame_h, frame_w = frame.shape[:2]
            if frame_h <= 0 or frame_w <= 0:
                return
            
            frame_center_x = frame_w / 2
            frame_center_y = frame_h / 2
            
            # CENTRO DEL VOLTO (questo è il punto che tracciamo)
            face_center_x = fx + (fw / 2)
            face_center_y = fy + (fh / 2)
            
            # Offset dal centro (in pixel)
            offset_x = face_center_x - frame_center_x
            offset_y = face_center_y - frame_center_y
        
        except Exception as e:
            print(f"[TRACK ERROR] Errore nel calcolo offset: {e}")
            return
        
        try:
            # 4. Accedi al cached_state per aggiornamenti fluidi (DIGITAL ZOOM)
            target = self.cached_state[cid]
            
            # Sensibilità di tracking - AUMENTATA per reattività
            tracking_speed = 0.15  # Velocità di movimento verso il target (0-1)
            zoom_base = 2.0    # Zoom di partenza
            
            # 5. Calcola deadzone (tolleranza prima di muoversi)
            tolerance_x = 40  # pixel - aumentato per ridurre tremori
            tolerance_y = 40  # pixel - aumentato per ridurre tremori
            
            pan_offset = offset_x / frame_w  # Normalizza a [-0.5, 0.5]
            tilt_offset = offset_y / frame_h  # Normalizza a [-0.5, 0.5]
            
            # 6. CALCOLA IL TARGET PERFETTO (dove DOVREBBE essere la telecamera)
            # Se il viso è esattamente al centro, pan_target = 0.5, tilt_target = 0.5
            pan_target = 0.5 + pan_offset  # Center + offset
            tilt_target = 0.5 + tilt_offset  # Center + offset
            
            # Clamp ai limiti
            pan_target = max(0.0, min(1.0, pan_target))
            tilt_target = max(0.0, min(1.0, tilt_target))
            
            # 7. PROTEZIONE ANTI-BLOCCO: Se siamo ai limiti (0 o 1), forza il ritorno al centro
            # Questo previene che la camera rimanga bloccata negli angoli
            current_pan = target.pan
            current_tilt = target.tilt
            
            if current_pan >= 0.95:
                target.pan = target.pan - 0.05  # Ritira un po'
            elif current_pan <= 0.05:
                target.pan = target.pan + 0.05  # Sposta un po' a destra
                
            if current_tilt >= 0.95:
                target.tilt = target.tilt - 0.05  # Ritira un po'
            elif current_tilt <= 0.05:
                target.tilt = target.tilt + 0.05  # Sposta un po' in basso
            
            # 8. MUOVI VERSO IL TARGET
            if abs(offset_x) > tolerance_x:
                # Muovi il pan verso il target (velocità proporzionale alla distanza)
                distance_ratio = min(1.0, abs(pan_target - target.pan) / 0.5)
                speed = tracking_speed * (0.5 + 0.5 * distance_ratio)  # Accelera se lontano
                target.pan = target.pan + (pan_target - target.pan) * speed
                target.pan = max(0.0, min(1.0, target.pan))
            else:
                # Se il viso è centrato in X, convergi lentamente al centro
                target.pan = target.pan + (0.5 - target.pan) * 0.08
            
            # 8. MUOVI TILT VERSO IL TARGET
            if abs(offset_y) > tolerance_y:
                # Muovi il tilt verso il target (velocità proporzionale alla distanza)
                distance_ratio = min(1.0, abs(tilt_target - target.tilt) / 0.5)
                speed = tracking_speed * (0.5 + 0.5 * distance_ratio)  # Accelera se lontano
                target.tilt = target.tilt + (tilt_target - target.tilt) * speed
                target.tilt = max(0.0, min(1.0, target.tilt))
            else:
                # Se il viso è centrato in Y, convergi lentamente al centro
                target.tilt = target.tilt + (0.5 - target.tilt) * 0.08
            
            # 9. ZOOM DIGITALE - Basato sulla dimensione del volto
            # Se il volto è piccolo, zoom in; se è grande, zoom out
            face_area = fw * fh
            frame_area = frame_w * frame_h
            face_ratio = face_area / frame_area  # 0 a 1
            
            # Calcola zoom target in base alla grandezza del volto
            # Obiettivo: il volto dovrebbe occupare circa il 20-25% dello schermo
            if face_ratio < 0.05:
                target_zoom = 3.5
            elif face_ratio < 0.10:
                target_zoom = 3.0
            elif face_ratio < 0.15:
                target_zoom = 2.5
            elif face_ratio < 0.25:
                target_zoom = 2.0
            else:
                target_zoom = 1.8  # Volto troppo grande, zoom out
            
            # Muovi lo zoom gradualmente verso il target (più lentamente del pan/tilt)
            zoom_lerp_speed = 0.02  # Ridotto per movimento più stabile
            target.zoom = target.zoom + (target_zoom - target.zoom) * zoom_lerp_speed
            target.zoom = max(1.0, min(4.0, target.zoom))
            
            # 9. INVIO COMANDI VISCA PER COMPATIBILITÀ
            # (Se c'è un vero server, potrebbe usarli)
            state_obj = self.visca_controller.camera_states[cid]
            curr_p = float(state_obj.pan)
            curr_t = float(state_obj.tilt)
            
            # Protezione limiti
            p_dir = "03"
            t_dir = "03"
            
            if abs(offset_x) > tolerance_x:
                p_dir = "02" if offset_x > 0 else "01"
                
                # Protezione dal superare i limiti
                if p_dir == "02" and curr_p >= 950:
                    p_dir = "03"
                elif p_dir == "01" and curr_p <= -950:
                    p_dir = "03"
            
            if abs(offset_y) > tolerance_y:
                t_dir = "02" if offset_y > 0 else "01"
                
                # Protezione dal superare i limiti
                if t_dir == "02" and curr_t >= 950:
                    t_dir = "03"
                elif t_dir == "01" and curr_t <= -950:
                    t_dir = "03"
            
            # Invia comando VISCA combinato
            if p_dir != "03" or t_dir != "03":
                cmd = f"0106010505{p_dir}{t_dir}FF"
                self.visca_controller.send(cid, cmd, retry=False)
                
        except Exception as e:
            print(f"[TRACK ERROR] Errore nel processing: {e}")
    def _prepare_display_frame(self, frame: np.ndarray) -> np.ndarray:
        """Prepara frame per display con OSD - DEBUG MODE"""
        try:
            cid = self.active_cam_id
            
            # SOLO RITORNA IL FRAME ORIGINALE - DEBUG
            return frame.copy()
        except Exception as e:
            print(f"[DEBUG] Error in _prepare_display_frame: {e}")
            return np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), np.uint8)

    def _create_simulator_frame(self, frame: np.ndarray) -> np.ndarray:
        """Crea frame simulatore"""
        cv2.putText(
            frame, "SIMULATOR", 
            (VIDEO_WIDTH//2-60, VIDEO_HEIGHT//2), 
            cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2
        )
        cv2.line(frame, (0, 0), (VIDEO_WIDTH, VIDEO_HEIGHT), (50, 50, 50), 2)
        cv2.line(frame, (VIDEO_WIDTH, 0), (0, VIDEO_HEIGHT), (50, 50, 50), 2)
        return frame

    def _emit_frame(self, frame: np.ndarray):
        """Mette il frame in una coda thread-safe - NON USA SIGNALS"""
        if frame is None or frame.size == 0:
            return

        try:
            h, w = frame.shape[:2]
            if h <= 0 or w <= 0:
                return
            
            # Converti BGR → RGB manualmente per evitare crash di cv2.cvtColor con Wayland
            try:
                rgb = frame[:, :, ::-1].copy()  # BGR -> RGB tramite slice inverso
            except Exception as cv_err:
                rgb = frame.copy()
            
            # Assicura che la memoria sia contigua
            if not rgb.flags['C_CONTIGUOUS']:
                rgb = np.ascontiguousarray(rgb)
            
            # Crea QImage da bytes
            try:
                qt_img = QImage(rgb.tobytes(), w, h, w * 3, 
                               QImage.Format.Format_RGB888)
            except Exception as qimg_err:
                print(f"[EMIT] QImage creation error: {qimg_err}")
                return
            
            # Metti in coda invece di emettere signal (evita crash Wayland)
            try:
                # Non attendere se la coda è piena - scarta frame vecchio
                self.frame_queue.put_nowait(qt_img)
            except Exception as queue_err:
                # Coda piena - rimuovi frame vecchio e metti il nuovo
                try:
                    self.frame_queue.get_nowait()
                    self.frame_queue.put_nowait(qt_img)
                except:
                    pass
            
        except Exception as e:
            print(f"[EMIT ERROR] {type(e).__name__}: {e}")

    def _update_fps_counter(self):
        """Aggiorna contatore FPS"""
        self.frame_count += 1
        
        if self.frame_count % 30 == 0:  # Ogni 30 frame
            elapsed = time.time() - self.fps_start_time
            self.current_fps = 30.0 / elapsed
            self.fps_start_time = time.time()

    def _sync_state_from_backend(self):
        cid = self.active_cam_id
        mode = self.cam_modes[cid]  # Prendi la modalità attuale

        # Se l'utente sta toccando i tasti, non sincronizzare
        if self.manual_override[cid]:
            return 

        try:
            new_state = self.visca_controller.get_camera_state_normalized(cid)
            target = self.cached_state[cid]
            
            # Per SCAN e TRACK: sincronizziamo SEMPRE senza filtri
            # (questi due modi si affidano al feedback dello stato per funzionare)
            if mode == MODE_SCAN or mode == MODE_TRACK:
                target.zoom = new_state["zoom"]
                target.pan = new_state["pan"]
                target.tilt = new_state["tilt"]
                return

            # Per MANUAL: logica di protezione per evitare jitter
            diff_pan = abs(new_state["pan"] - target.pan)
            diff_tilt = abs(new_state["tilt"] - target.tilt)
            
            if diff_pan < 0.1 and diff_tilt < 0.1:
                target.zoom = new_state["zoom"]
                target.pan = new_state["pan"]
                target.tilt = new_state["tilt"]
                
        except Exception as e:
            print(f"[SYNC ERROR] {e}")

    def get_camera_state(self, cid: int) -> Dict[str, float]:
        """Ottieni stato INTERPOLATO per display fluido"""
        state = self.display_state.get(cid)
        if state:
            return {
                "zoom": state.zoom,
                "pan": state.pan,
                "tilt": state.tilt
            }
        return {"zoom": 2.0, "pan": 0.5, "tilt": 0.5}

    def digital_zoom(self, frame: np.ndarray, cid: int) -> np.ndarray:
        try:
            if frame is None or frame.size == 0:
                return frame
                
            state = self.get_camera_state(cid)
            z = state["zoom"]
            
            # Se lo zoom è vicino a 1, non fare nulla
            if z <= 1.05:
                return frame
                
            h, w = frame.shape[:2]
            if h <= 0 or w <= 0:
                return frame
            
            # 1. Calcola quanto deve essere grande l'area visibile
            new_w = max(1, int(w / z))
            new_h = max(1, int(h / z))
            
            # 2. Centra l'area (0.5 è il centro perfetto)
            pan = max(0.0, min(1.0, state["pan"]))
            tilt = max(0.0, min(1.0, state["tilt"]))
            cx = int(w * pan)
            cy = int(h * tilt)
            
            # 3. Definisci i bordi del rettangolo di ritaglio con protezioni
            x1 = max(0, cx - new_w // 2)
            y1 = max(0, cy - new_h // 2)
            x2 = min(w, x1 + new_w)
            y2 = min(h, y1 + new_h)
            
            # Protezione: assicura che il crop sia valido
            if x2 <= x1 or y2 <= y1:
                return frame
            
            # 4. Ritaglia e riporta alle dimensioni originali
            cropped = frame[y1:y2, x1:x2]
            if cropped.size > 0 and cropped.shape[0] > 0 and cropped.shape[1] > 0:
                return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
            return frame
        except Exception as e:
            print(f"[ZOOM ERROR] {e}")
            return frame

    def draw_faces(self, frame: np.ndarray):
        """Disegna volti rilevati"""
        if frame is None or frame.size == 0 or self.face_cascade is None:
            return
        
        try:
            h_frame, w_frame = frame.shape[:2]
            if h_frame <= 0 or w_frame <= 0:
                return
                
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            for (x, y, w, h) in faces:
                # Protezione: verifica che le coordinate siano valide
                if x < 0 or y < 0 or w <= 0 or h <= 0:
                    continue
                if (x + w) > w_frame or (y + h) > h_frame:
                    continue
                    
                try:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cx, cy = x + w//2, y + h//2
                    cv2.circle(frame, (cx, cy), 3, (0, 255, 0), -1)
                except Exception as rect_err:
                    continue
        except Exception as e:
            print(f"[FACE ERROR] {e}")

    def draw_osd(self, frame: np.ndarray, cid: int):
        """Disegna OSD con informazioni stato"""
        if frame is None or frame.size == 0:
            return
            
        try:
            mode_idx = self.cam_modes[cid]
            mode_text = MODE_NAMES[mode_idx]
            
            color_map: Dict[int, tuple] = {
                MODE_MANUAL: COLOR_MANUAL,
                MODE_SCAN: COLOR_SCAN,
                MODE_TRACK: COLOR_TRACK
            }
            color: tuple = color_map.get(mode_idx, COLOR_MANUAL)
            
            if self.manual_override[cid]:
                mode_text += " (OVERRIDE)"
            
            state_dict = self.get_camera_state(cid)
            
            # Proteggi ogni putText
            try:
                cv2.putText(
                    frame, 
                    f"CAM {cid} [{mode_text}] Z:{state_dict['zoom']:.2f}x",
                    (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.7, color, 2
                )
            except Exception:
                pass
            
            pan_pct = int(state_dict["pan"] * 100)
            tilt_pct = int(state_dict["tilt"] * 100)
            try:
                cv2.putText(
                    frame,
                    f"Pan:{pan_pct:3d}% Tilt:{tilt_pct:3d}%",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, color, 1
                )
            except Exception:
                pass
            
            if self.current_fps > 0:
                try:
                    cv2.putText(
                        frame,
                        f"FPS:{self.current_fps:.1f}",
                        (VIDEO_WIDTH - 100, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (255, 255, 255), 1
                    )
                except Exception:
                    pass
        except Exception as e:
            print(f"[OSD ERROR] {e}")

    def stop(self):
        """Arresto coordinato dei thread"""
        print("[VIDEO] Arresto in corso...")
        self._run_flag = False
        self.capture_running = False
        
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except:
            pass
        
        try:
            if hasattr(self, 'capture_thread') and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=0.5)
        except:
            pass
        
        print("[VIDEO] Risorse rilasciate")