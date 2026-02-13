"""
VISCA Backend Configuration and Setup
"""

# Backend Server Configuration
BACKEND_TYPE = "CSHARP_EXTERNAL"  # Tipo di backend utilizzato

# Server C# Information
CSHARP_SERVER_DESCRIPTION = """
Server VISCA implementato in C# .NET
- Supporta 6 telecamere virtuali
- Protocolo VISCA over IP su UDP porta 52381
- Elabora comandi di Pan, Tilt, Zoom
"""

# Backend Setup Instructions
SETUP_INSTRUCTIONS = """
===== SETUP BACKEND C# =====

1. Cartella del backend: vedi /backend o la cartella separata con il progetto C#

2. Compilare il server:
   dotnet build

3. Eseguire il server:
   dotnet run
   
   Oppure eseguire il file compilato:
   ./ViscaOverIpSimulator  (Linux/Mac)
   ViscaOverIpSimulator.exe  (Windows)

4. Il server ascolterà su:
   - UDP Port 52381 per comandi VISCA
   - TCP Port 8554 per RTSP (fake)
   - Tutte le interfacce di rete (0.0.0.0)

5. Nota l'IP locale mostrato nel console (es: 10.0.0.10)
   Usa questo IP nel client Python

===== BACKEND CAPABILITIES =====

- Numero telecamere: 6 (MAX_CAMERAS = 6)
- Protocollo: VISCA over IP
- Porta UDP: 52381
- Comandi supportati:
  * Zoom in/out
  * Pan sinistra/destra
  * Tilt su/giù
  * Stop
  
- Ogni telecamera ha parametri indipendenti:
  * pan[0..5]
  * tilt[0..5]
  * zoom[0..5] (range 100-300)

===== TROUBLESHOOTING =====

- Se la connessione fallisce: verificare l'IP corretto
- Se i comandi non funzionano: controllare la porta 52381 non sia bloccata
- Se il server non parte: verificare dipendenze .NET installate
"""

def print_setup_guide():
    """Stampa la guida di setup completa"""
    print(CSHARP_SERVER_DESCRIPTION)
    print(SETUP_INSTRUCTIONS)


if __name__ == "__main__":
    print_setup_guide()
