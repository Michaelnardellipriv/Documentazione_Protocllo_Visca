"""
Quick reference for VISCA Protocol Commands Used
"""

VISCA_COMMANDS = {
    "PAN_LEFT": "01060105050103FF",
    "PAN_RIGHT": "01060105050203FF",
    "TILT_UP": "01060105050301FF",
    "TILT_DOWN": "01060105050302FF",
    "PAN_TILT_STOP": "01060105050303FF",
    
    "ZOOM_IN": "01040702FF",
    "ZOOM_OUT": "01040703FF",
    "ZOOM_STOP": "01040700FF",
}

VISCA_PROTOCOL_INFO = """
╔════════════════════════════════════════════════════════════════╗
║             VISCA Protocol - Command Reference                ║
╚════════════════════════════════════════════════════════════════╝

FORMATO PACCHETTO VISCA over IP:
┌─────────────────────────────────────────┐
│ Header (8 bytes)                        │
│  - 0x01 0x00 (Magic)                   │
│  - Length (2 bytes, big-endian)        │
│  - Sequence (4 bytes, big-endian)      │
├─────────────────────────────────────────┤
│ Payload (variabile)                     │
│  - Command bytes                        │
└─────────────────────────────────────────┘

COMANDO PAN/TILT:
  Byte 0: 0x01 | Camera ID (0x80 | cam_id)
  Byte 1: 0x06 (Command category)
  Byte 2: 0x01 (Pan/Tilt)
  Byte 3: 0x05 (Inquiry type)
  Byte 4: 0x05 (Reserved)
  Byte 5: Pan direction (0x01=left, 0x02=right, 0x03=stop)
  Byte 6: Tilt direction (0x01=up, 0x02=down, 0x03=stop)
  Byte 7: 0xFF (Terminator)

COMANDO ZOOM:
  Byte 0: 0x01 | Camera ID
  Byte 1: 0x04 (Zoom command)
  Byte 2: 0x07 (Operation)
  Byte 3: Direction (0x02=zoom in, 0x03=zoom out, 0x00=stop)
  Byte 4: 0xFF (Terminator)

COMANDI IMPLEMENTATI:
═══════════════════════════════════════════════════════════════

Pan/Tilt:
  • LEFT:  0x01060105050103FF
  • RIGHT: 0x01060105050203FF
  • UP:    0x01060105050301FF
  • DOWN:  0x01060105050302FF
  • STOP:  0x01060105050303FF

Zoom:
  • ZOOM_IN:   0x01040702FF
  • ZOOM_OUT:  0x01040703FF
  • ZOOM_STOP: 0x01040700FF

COMUNICAZIONE:
═══════════════════════════════════════════════════════════════

Protocollo: UDP
Porta: 52381
Indirizzo destinazione: Server VISCA (es: 10.0.0.10)

FLOW:
1. Client crea comando VISCA (hex string)
2. Costruisce header VISCA over IP
3. Invia pacchetto UDP al server
4. Server riceve e elabora il comando
5. Server aggiorna stato della telecamera (pan, tilt, zoom)

CAMERA ID:
═══════════════════════════════════════════════════════════════

Supportate da 1 a 6 telecamere virtuali
ID mapping: 1-based per l'utente, convertito a 0-based nel protocollo

Esempio per CAM 2:
  • User seleziona: CAM 2
  • Camera ID trasmesso: 0x02
  • Nel byte: 0x80 | 0x02 = 0x82
"""

def print_command_reference():
    """Stampa la guida dei comandi"""
    print(VISCA_PROTOCOL_INFO)
    print("\nComandi disponibili:")
    for cmd_name, hex_cmd in VISCA_COMMANDS.items():
        print(f"  {cmd_name:20} → {hex_cmd}")

if __name__ == "__main__":
    print_command_reference()
