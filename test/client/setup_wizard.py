"""
VISCA Client - Quick Start Guide
"""

# Rimuovi la riga import os se non usata
# from backend_setup import print_setup_guide

def show_setup_menu():
    """Mostra il menu di setup iniziale"""
    print("\n" + "="*60)
    print("  VISCA DUAL CAMERA CONTROL - SETUP WIZARD")
    print("="*60 + "\n")
    
    print("Questa applicazione è un CLIENT che si connette a un")
    print("SERVER VISCA esterno implementato in C# .NET\n")
    
    print("Opzioni:")
    print("1. Visualizza guida di setup del backend C#")
    print("2. Avvia l'applicazione client")
    print("3. Esci\n")
    
    choice = input("Seleziona un'opzione (1-3): ").strip()
    
    if choice == "1":
        # Import locale per evitare dipendenze circolari
        from backend_setup import print_setup_guide
        print_setup_guide()
        print("\n" + "="*60)
        input("Premi INVIO per continuare...")
        show_setup_menu()
    elif choice == "2":
        start_client()
    elif choice == "3":
        print("Arrivederci!")
        exit(0)
    else:
        print("Opzione non valida!")
        show_setup_menu()

def start_client():
    """Avvia il client"""
    print("\n" + "="*60)
    print("  Avvio del Client VISCA")
    print("="*60 + "\n")
    
    from PyQt6.QtWidgets import QApplication
    from main_window import MainWindow
    import sys
    
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    show_setup_menu()