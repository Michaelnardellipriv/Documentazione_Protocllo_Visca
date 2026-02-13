# VISCA Dual Camera Control - Struttura OOP

## Architettura

``` merdamind
┌─────────────────────────────────────────┐
│   Client GUI (Python + PyQt6)           │
│  - Controllo telecamere                 │
│  - Visualizzazione video                │
│  - Interfaccia utente interattiva       │
└────────────────┬────────────────────────┘
                 │
                 │ UDP Port 52381
                 │ VISCA Protocol
                 │
┌────────────────▼────────────────────────┐
│   Server VISCA (C# .NET)                │
│  - Elabora comandi VISCA                │
│  - Gestisce 6 telecamere virtuali       │
│  - Pan, Tilt, Zoom virtuali             │
└─────────────────────────────────────────┘
```

## Panoramica della Struttura Client

Il progetto client è stato rifattorizzato seguendo i principi della Programmazione Orientata agli Oggetti (OOP) con file separate per ogni classe principale.

## Struttura dei File

### `main.py` (Punto di Ingresso)

- **Scopo**: Entry point dell'applicazione
- **Contenuto**: Funzione `main()` che inizializza l'applicazione PyQt6
- **Dipendenze**: Importa `MainWindow` da `main_window.py`

### `config.py` (Configurazioni)

- **Scopo**: Centralizza tutte le costanti di configurazione
- **Contenuto**:
  - Configurazione di rete (IP, porte)
  - Configurazione della finestra (dimensioni)
  - Parametri della telecamera (zoom, pan/tilt)
  - Configurazione di tracciamento dei volti
  - Costanti di colore e modalità

### `visca_controller.py` (Controllo VISCA)

- **Classe**: `ViscaController`
- **Responsabilità**: Gestione della comunicazione con il server VISCA tramite UDP
- **Metodi Principali**:
  - `__init__(ip: str)`: Inizializza la connessione socket
  - `send(cam_id: int, hex_cmd: str)`: Invia comandi VISCA al server

### `interactive_video_label.py` (Widget Video Interattivo)

- **Classe**: `InteractiveVideoLabel` (estende `QLabel`)
- **Responsabilità**: Gestisce l'interazione del mouse con il video
- **Segnali**: `on_drag_signal(dx, dy)` - Emesso quando l'utente trascina il mouse
- **Metodi Principali**:
  - `mousePressEvent()`: Gestisce il click del mouse
  - `mouseMoveEvent()`: Gestisce lo spostamento del mouse
  - `handle_mouse()`: Elabora gli eventi del mouse e normalizza le coordinate

### `video_thread.py` (Thread di Cattura Video)

- **Classe**: `VideoThread` (estende `QThread`)
- **Responsabilità**: Cattura, elaborazione e visualizzazione del video in tempo reale
- **Funzionalità Principali**:
  - Cattura video da webcam
  - Elaborazione comandi di controllo della telecamera
  - Tracciamento automatico dei volti
  - Modalità di scansione (pan automatico)
  - Zoom digitale
  - Sovrapposizione di informazioni (OSD)
- **Modalità Telecamera**:
  - `MODE_MANUAL` (0): Controllo manuale
  - `MODE_SCAN` (1): Scansione panoramica automatica
  - `MODE_TRACK` (2): Tracciamento automatico dei volti
- **Segnali**: `change_pixmap_signal(QImage)` - Emesso quando un nuovo frame è disponibile

### `main_window.py` (Finestra Principale)

- **Classe**: `MainWindow` (estende `QMainWindow`)
- **Responsabilità**: Gestione dell'interfaccia utente e coordinamento dei componenti
- **Componenti UI**:
  - Video label interattivo
  - Pulsanti di selezione telecamera
  - Pulsante di cambio modalità
  - Grid di comandi direzionali e zoom
- **Metodi Principali**:
  - `__init__()`: Inizializza l'interfaccia
  - `handle_drag_input()`: Gestisce i comandi da trascinamento del mouse
  - `move_camera()`: Invia comandi di movimento
  - `stop()`: Arresta il movimento della telecamera
  - `set_cam()`: Seleziona la telecamera attiva
  - `cycle_mode()`: Cambia la modalità di operazione

## Flusso di Dati

```
Utente Interazione
    ↓
InteractiveVideoLabel (emit on_drag_signal)
    ↓
MainWindow.handle_drag_input() / move_camera()
    ↓
VideoThread (aggiorna cmd_p, cmd_t, cmd_z)
    ↓
ViscaController.send() (invia comandi UDP)
    ↓
Backend VISCA Server
```

## Flusso Video

```
VideoThread.run()
    ↓
cv2.VideoCapture (legge frame)
    ↓
Elaborazione (tracciamento, zoom)
    ↓
change_pixmap_signal (emette QImage)
    ↓
MainWindow.update_image()
    ↓
InteractiveVideoLabel (visualizza)
```

## Vantaggi della Struttura OOP

1. **Separazione dei Compiti**: Ogni classe ha una responsabilità ben definita
2. **Manutenibilità**: Modifiche a una classe non impattano le altre
3. **Riusabilità**: Classi possono essere riutilizzate in altri progetti
4. **Testabilità**: Componenti singoli possono essere testati indipendentemente
5. **Scalabilità**: Facile aggiungere nuove funzionalità
6. **Leggibilità**: Codice più organizzato e facile da capire

## Dipendenze

- `PyQt6`: Framework GUI
- `OpenCV (cv2)`: Cattura e elaborazione video
- `NumPy`: Elaborazione array
- `.NET Runtime`: Per il server VISCA C# (backend)

## Struttura del Progetto

```
client/
├── main.py                          # Entry point
├── config.py                        # Configurazioni centralizzate
├── visca_controller.py              # Comunicazione VISCA
├── interactive_video_label.py       # Widget video interattivo
├── video_thread.py                  # Thread di cattura video
├── main_window.py                   # Interfaccia principale
├── backend_setup.py                 # Guida setup backend C#
├── setup_wizard.py                  # Wizard di setup iniziale
├── visca_protocol_reference.py      # Riferimento protocollo VISCA
└── README.md                        # Questo file
```

## File di Configurazione

- [config.py](config.py) - Costanti di configurazione (IP, porte, parametri)
- [backend_setup.py](backend_setup.py) - Istruzioni setup backend C#
- [visca_protocol_reference.py](visca_protocol_reference.py) - Riferimento comandi VISCA

## Comandi Supportati

Vedi [visca_protocol_reference.py](visca_protocol_reference.py) per i dettagli completi del protocollo VISCA.

**Comandi di base:**
- Pan/Tilt: Sinistra, Destra, Su, Giù, Stop
- Zoom: Zoom In, Zoom Out, Stop
- 6 telecamere virtuali supportate dal backend

## Avvio dell'Applicazione

### 1. Avviare il Server VISCA (Backend C#)

Compila ed esegui il server C# (.NET) in una cartella separata:

```bash
dotnet run
```

**Output atteso:**
```
==================================================
   TENVEO SERVER - NETWORK EDITION
==================================================
[INFO]   Server Running on Arch/Linux/Windows
[IP]     YOUR SERVER IP IS: 10.0.0.10
[CAMS]   6 Virtual Cameras
[VISCA] Listening on UDP 52381
[RTSP]  Server on TCP 8554
==================================================
```

### 2. Avviare il Client Python

Nel progetto Python:

```bash
python3 main.py
```

**Al primo avvio:**
- Verrà chiesto l'IP del server VISCA (default: `10.0.0.10`)
- Immettere l'IP donde è in esecuzione il server C#
- La GUI si aprirà e si connetterà al server

### 3. Usare l'Applicazione

- **Selezionare telecamera**: Cliccare su CAM 1 o CAM 2 (fino a 6 telecamere supportate dal backend)
- **Controllare movimento**: 
  - Pulsanti UP/DN/LT/RT per pan/tilt
  - Pulsanti Z+/Z- per zoom
  - Trascinare il mouse sul video per controllo fluido
- **Cambiare modalità**: Cliccare MODE per ciclare tra MANUAL → SCAN → TRACK
