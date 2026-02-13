  
# Glossario Tecnico VISCA

## Come usare questo glossario

- **Clicca sui termini** nei documenti principali per saltare direttamente qui

- I termini sono organizzati per **categoria funzionale**

- Ogni definizione include **contesto d'uso** e **riferimenti incrociati**

---
## Indice Navigabile

- [Glossario Tecnico VISCA](#glossario-tecnico-visca)
  - [Come usare questo glossario](#come-usare-questo-glossario)
  - [Indice Navigabile](#indice-navigabile)
  - [PROTOCOLLO E PACCHETTI](#protocollo-e-pacchetti)
  - [COMUNICAZIONE SERIALE (RS-232/422)](#comunicazione-seriale-rs-232422)
  - [COMUNICAZIONE IP (VISCA over IP)](#comunicazione-ip-visca-over-ip)
  - [MESSAGGI DI RISPOSTA E STATI](#messaggi-di-risposta-e-stati)
  - [GESTIONE SOCKET](#gestione-socket)
  - [COMANDI E PARAMETRI](#comandi-e-parametri)
  - [DATI POSIZIONALI E NIBBLE PARTING](#dati-posizionali-e-nibble-parting)
  - [SVILUPPO SOFTWARE](#sviluppo-software)
  - [RETI E VPN](#reti-e-vpn)
  - [HARDWARE E FISICO](#hardware-e-fisico)
  - [TERMINI OPERATIVI](#termini-operativi)
  - [NOTAZIONI E CONVENZIONI](#notazioni-e-convenzioni)

---
## PROTOCOLLO E PACCHETTI

| Termine              | Definizione                         | Contesto                                                                                                      | Vedi anche          |
| -------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------- |
| **VISCA**            | _Video System Control Architecture_ | Protocollo proprietario Sony (1990) per controllo telecamere PTZ. Standard de facto nell'industria broadcast. | —                   |
| **Packet**           | Unità fondamentale di comunicazione | Sequenza di byte: [Header] + [Message] + [Terminator FF]. Max 16 byte in seriale.                             | Header, Terminator  |
| **Header**           | Primo byte del pacchetto            | Codifica mittente (bit 6-4) e destinatario (bit 2-0). MSB (bit 7) sempre 1.                                   | MSB, Address        |
| **Terminator (FFh)** | Byte `FF` che chiude ogni comando   | Segnale di "fine lettura". La camera interrompe l'interpretazione appena lo incontra.                         | Nibble Parting      |
| **Message**          | Corpo del comando (1-14 byte)       | Struttura: [COM-MODE] + [CATEGORIA] + [Sub-code] + [PARAMETRI]                                                | COM-MODE, CATEGORIA |
| **COM-MODE**         | Primo byte del Message              | `01` = Command, `09` = Inquiry, `00` = Net-keeping                                                            | Inquiry, Command    |
| **CATEGORIA**        | Secondo byte del Message            | Identifica il sottosistema: `04` = Camera, `06` = Pan-Tilt, `05` = Video                                      | —                   |
| **Sub-code**         | Terzo byte del Message              | Specifica l'azione: `02` = Movimento Assoluto, `07` = Zoom, `3F` = Preset                                     | —                   |
| **PARAMETRI**        | Byte 4-14 del Message               | Dati variabili: velocità, coordinate, stati on/off                                                            | Nibble Parting      |
| **Nibble**           | Metà byte (4 bit)                   | Unità base per codifica posizioni (0p 0q 0r 0s). Previene `FF` accidentali nei dati.                          | Nibble Parting      |
| **FFh**              | Valore esadecimale 255              | Terminatore. MAI usato come dato nei parametri.                                                               | Terminator          |

---

## COMUNICAZIONE SERIALE (RS-232/422)

| Termine         | Definizione                   | Contesto                                                                    | Vedi anche  |
| --------------- | ----------------------------- | --------------------------------------------------------------------------- | ----------- |
| **RS-232**      | Standard seriale corto raggio | Max 15m. Collegamento diretto PC-Camera. Usato in stanza.                   | Daisy Chain |
| **RS-422**      | Standard seriale lungo raggio | Max 1200m. Segnale differenziale. Usato in stadi, auditorium.               | —           |
| **Daisy Chain** | Configurazione a cascata      | Controller → Camera1 → Camera2 → ... Max 7 dispositivi.                     | Address Set |
| **Address**     | Identificativo camera (1-7)   | Assegnato automaticamente via Address Set. Non persistente.                 | Address Set |
| **Address Set** | Comando `88 30 01 FF`         | Procedura di auto-assegnazione indirizzi in catena. Obbligatorio all'avvio. | Daisy Chain |
| **Baud Rate**   | Velocità trasmissione seriale | Standard VISCA: **9600 bps**. Alcune camere supportano 38400.               | —           |
| **Hot-Swap**    | Sostituzione a caldo          | **NON SUPPORTATO**. Ogni modifica fisica richiede nuovo Address Set.        | —           |

---

## COMUNICAZIONE IP (VISCA over IP)

| Termine             | Definizione                           | Contesto                                                                  | Vedi anche                                                    |
| ------------------- | ------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------- |
| **VISCA over IP**   | Incapsulamento VISCA in UDP           | Porta **52381**. Aggiunge header 8 byte prima del pacchetto VISCA.        | [VISCA_SOPRA_IP](visca_sopra_ip.md)                           |
| **Sequence Number** | Contatore 32-bit (byte 4-7 header IP) | Identifica l'ordine dei pacchetti. Deve incrementare di 1 per ogni invio. | Reset Command                                                 |
| **Reset Command**   | Pacchetto `02 00 00 00 00 00 00 00`   | Azzera il sequence number della camera. Obbligatorio all'avvio sessione.  | Sequence Number                                               |
| **Payload Type**    | Byte 0-1 header IP                    | `01 00` = Command, `01 10` = Inquiry, `02 00` = Reset                     | —                                                             |
| **Payload Length**  | Byte 2-3 header IP                    | Lunghezza del comando VISCA (senza header IP).                            | —                                                             |
| **DIP Switch**      | Interruttori fisici camera            | Switch n.3 = ON per abilitare VISCA over IP. Letto solo all'avvio.        | [VISCA_SOPRA_IP](visca_sopra_ip.md#attivazione-fisica-per-ip) |

---

## MESSAGGI DI RISPOSTA E STATI

| Termine                 | Definizione                  | Contesto                                                                      | Vedi anche |
| ----------------------- | ---------------------------- | ----------------------------------------------------------------------------- | ---------- |
| **ACK**                 | _Acknowledge_ (`z0 4y FF`)   | Conferma ricezione comando. Occupa un socket.                                 | Socket     |
| **Completion**          | `z0 5y FF`                   | Fine esecuzione comando. Libera il socket.                                    | Socket     |
| **Information Return**  | `z0 50 ... FF`               | Risposta a Inquiry. Contiene i dati richiesti.                                | Inquiry    |
| **Syntax Error**        | `z0 60 02 FF`                | Formato pacchetto errato. Causa comune: padding `00` dopo FF.                 | —          |
| **Command Buffer Full** | `z0 60 03 FF`                | Entrambi i socket occupati. Accodare o attendere.                             | Socket     |
| **Not Executable**      | `z0 6y 41 FF`                | Comando valido ma non eseguibile ora (es. camera in standby).                 | —          |
| **z**                   | Notazione indirizzo risposta | Nelle risposte, `z` = indirizzo camera + 8 (es. Camera 1 risponde con `9...`) | Address    |
| **y**                   | Notazione socket             | Nelle risposte, `y` = numero socket (1 o 2)                                   | Socket     |

---

## GESTIONE SOCKET

| Termine                 | Definizione                   | Contesto                                                      | Vedi anche          |
| ----------------------- | ----------------------------- | ------------------------------------------------------------- | ------------------- |
| **Socket**              | Buffer memoria interno camera | Ogni camera ha **2 socket** per esecuzione parallela comandi. | ACK, Completion     |
| **Socket 1**            | Primo buffer                  | Tipicamente per comandi di movimento.                         | —                   |
| **Socket 2**            | Secondo buffer                | Tipicamente per comandi di immagine (zoom, focus, WB).        | —                   |
| **Command Buffer Full** | Errore `z0 60 03 FF`          | Entrambi i socket occupati. Il software deve accodare.        | Command Buffer Full |
| **Cancel Command**      | `z0 6y 04 FF`                 | Annulla comando in esecuzione sul socket y. Libera il socket. | —                   |
| **No Socket**           | `z0 6y 05 FF`                 | Tentativo di cancellare socket già vuoto.                     | —                   |

---

## COMANDI E PARAMETRI

| Termine          | Definizione           | Contesto                                                                      | Vedi anche         |
| ---------------- | --------------------- | ----------------------------------------------------------------------------- | ------------------ |
| **Command**      | COM-MODE = `01`       | Ordine operativo (muovi, zoom, preset). Richiede ACK + Completion.            | COM-MODE           |
| **Inquiry**      | COM-MODE = `09`       | Richiesta stato (dove sei?, che zoom?). Risposta immediata.                   | Information Return |
| **Net-keeping**  | COM-MODE = `00`       | Gestione rete e indirizzi. Es. Address Set.                                   | Address Set        |
| **Pan**          | Movimento orizzontale | Velocità VV: `01`-`18` (Slow), `01`-`18` (Normal)                             | VV/WW              |
| **Tilt**         | Movimento verticale   | Velocità WW: `01`-`14` (Slow), `01`-`18` (Normal)                             | VV/WW              |
| **Zoom**         | Ingrandimento ottico  | `02` = Tele (ingrandisci), `03` = Wide (allarga), `00` = Stop                 | —                  |
| **Preset**       | Memoria posizione     | Salva (`01`), Richiama (`02`), Cancella (`00`). Parametro pp = numero preset. | —                  |
| **VV/WW**        | Parametri velocità    | VV = velocità Pan, WW = velocità Tilt. Valori esadecimali.                    | Pan, Tilt          |
| **Limit Switch** | Fine corsa meccanico  | Bit di stato segnala blocco fisico. Inibire movimento.                        | —                  |

---

## DATI POSIZIONALI E NIBBLE PARTING

| Termine                | Definizione                | Contesto                                                        | Vedi anche |
| ---------------------- | -------------------------- | --------------------------------------------------------------- | ---------- |
| **Nibble Parting**     | Tecnica di spacchettamento | Divide un byte in due nibbles (4+4 bit). Formato `0p 0q 0r 0s`. | Nibble     |
| **Posizione Assoluta** | Coordinate Pan/Tilt        | 4 nibbles per asse. Range: 0x0000 - 0x18C0 (step).              | —          |
| **p, q, r, s**         | Notazione nibbles          | Segnaposto per mezzo byte. Valore 0-15 (0x0-0xF).               | —          |
| **Bitmasking**         | Isolamento bit via AND     | Tecnica per estrarre nibbles o bit di stato.                    | —          |

---

## SVILUPPO SOFTWARE

| Termine                | Definizione         | Contesto                                                                   | Vedi anche                  | Wikipedia |
| ---------------------- | ------------------- | -------------------------------------------------------------------------- | --------------------------- | --------- |
| **Protocol Handshake** | Validazione 3-step  | 1. Ping, 2. Port scan, 3. Inquiry Version. Previene falsi positivi.        | [Guida_allo_Sviluppo](Guida_allo_Sviluppo_di_un_Controller_VISCA.md#validazione-del-dispositivo-protocol-handshake) | [Link](https://it.wikipedia.org/wiki/Handshake) |
| **Self-Healing**       | Recupero automatico | Tracciamento MAC → riassociazione IP dopo cambio DHCP.                     | [Guida_allo_Sviluppo](Guida_allo_Sviluppo_di_un_Controller_VISCA.md#strategia-self-healing-tracciamento-mac-address) | — |
| **Adaptive Timeout**   | Timeout variabile   | Regolato dinamicamente su RTT misurato. Previene ritrasmissioni premature. | —                           | — |
| **Command Queue**      | Coda comandi        | Pattern producer-consumer per gestire buffer full.                         | [Guida_allo_Sviluppo](Guida_allo_Sviluppo_di_un_Controller_VISCA.md#architettura-a-due-code-gestione-socket) | [Link](https://it.wikipedia.org/wiki/Coda_(struttura_dati)) |
| **State Machine**      | Macchina a stati    | Gestisce transizioni IDLE → WAITING_ACK → EXECUTING → COMPLETE             | [Guida_allo_Sviluppo](Guida_allo_Sviluppo_di_un_Controller_VISCA.md#architettura-a-due-code-gestione-socket) | [Link](https://it.wikipedia.org/wiki/Macchina_a_stati_finiti) |

---

## RETI E VPN

| Termine               | Definizione                 | Contesto                                                              | Vedi anche                                 | Wikipedia |
| --------------------- | --------------------------- | --------------------------------------------------------------------- | ------------------------------------------ | --------- |
| **Jitter**            | Variazione latenza          | Critico per VISCA: >30ms causa pacchetti fuori ordine.                | [VISCA_tramite_vpn](VISCA_tramite_vpn.md) | [Link](https://it.wikipedia.org/wiki/Jitter) |
| **MTU**               | _Maximum Transmission Unit_ | Default 1500 byte. Incapsulamento VPN può causare frammentazione.     | [VISCA_tramite_vpn](VISCA_tramite_vpn.md) | [Link](https://it.wikipedia.org/wiki/Maximum_transmission_unit) |
| **Frammentazione IP** | Split pacchetto > MTU       | Letale per VISCA: perdita 1 frammento = perdita intero comando.       | [VISCA_tramite_vpn](VISCA_tramite_vpn.md) | [Link](https://it.wikipedia.org/wiki/Frammentazione_(reti)) |
| **NAT Traversal**     | Attraversamento NAT         | Problema: timeout mapping UDP (30-300s). Soluzione: overlay/ZeroTier. | [VISCA_tramite_vpn](VISCA_tramite_vpn.md) | [Link](https://it.wikipedia.org/wiki/Network_address_translation) |
| **L2VPN**             | Bridge livello 2            | Estende stesso broadcast domain. Trasparente ma fragile su WAN.       | [VISCA_tramite_vpn](VISCA_tramite_vpn.md) | — |
| **L3VPN**             | Routing statico             | Subnet separate. Richiede routing esplicito.                          | [VISCA_tramite_vpn](VISCA_tramite_vpn.md) | — |
| **Overlay Network**   | IP virtuale                 | ZeroTier/Tailscale. Più resiliente a cambi IP fisici.                 | [VISCA_tramite_vpn](VISCA_tramite_vpn.md) | [Link](https://it.wikipedia.org/wiki/Overlay_network) |

---

## HARDWARE E FISICO

| Termine        | Definizione           | Contesto                                          | Vedi anche                                      | Wikipedia |
| -------------- | --------------------- | ------------------------------------------------- | ----------------------------------------------- | --------- |
| **PTZ**        | _Pan-Tilt-Zoom_       | Tipologia telecamera con movimento motorizzato.   | [VISCA_HARDWARE_GUIDE](VISCA_HARDWARE_GUIDE.md) | [Link](https://it.wikipedia.org/wiki/Pan-tilt-zoom_camera) |
| **RJ-45**      | Connettore Ethernet   | VISCA over IP: pin 1,2,3,6 utilizzati.            | [VISCA_HARDWARE_GUIDE](VISCA_HARDWARE_GUIDE.md) | [Link](https://it.wikipedia.org/wiki/RJ45) |
| **PoE**        | _Power over Ethernet_ | Alimentazione via cavo rete. Standard 802.3af/at. | [VISCA_HARDWARE_GUIDE](VISCA_HARDWARE_GUIDE.md) | [Link](https://it.wikipedia.org/wiki/Power_over_Ethernet) |
| **DIP Switch** | Interruttori fisici   | Configurazione hardware. Switch 3 = IP enable.    | [VISCA_HARDWARE_GUIDE](VISCA_HARDWARE_GUIDE.md) | [Link](https://it.wikipedia.org/wiki/DIP_switch) |
| **RS-232/422** | Standard seriali      | Vedi sezione 2.                                   | [COME_FUNZIONA_IN_SERIALE](COME_FUNZIONA_IN_SERIALE.md) | [Link](https://it.wikipedia.org/wiki/EIA_RS-232) |

---

## TERMINI OPERATIVI

| Termine       | Definizione                   | Contesto                                                 | Wikipedia |
| ------------- | ----------------------------- | -------------------------------------------------------- | --------- |
| **Broadcast** | Produzione video live         | Contesto d'uso principale VISCA. Richiede bassa latenza. | [Link](https://it.wikipedia.org/wiki/Televisione) |
| **Studio**    | Ambiente controllato          | Cablaggio fisso, preset, movimenti ripetuti.             | — |
| **Stadio**    | Lunghe distanze               | Uso RS-422 o IP su fibra. Latenza accettabile <80ms.     | — |
| **EFP**       | _Electronic Field Production_ | Produzione in esterna. Spesso VPN o 4G. Sfida per VISCA. | — |

---

## NOTAZIONI E CONVENZIONI

| Termine         | Definizione             | Esempio                                                 |
| --------------- | ----------------------- | ------------------------------------------------------- |
| **MSB**         | _Most Significant Bit_  | Bit 7 (valore 128). Nell'header è sempre 1.             |
| **LSB**         | _Least Significant Bit_ | Bit 0 (valore 1).                                       |
| **Big Endian**  | Ordine byte MSB primo   | VISCA usa Big Endian.                                   |
| **Hex**         | Esadecimale             | Base 16. Prefisso `0x` o suffisso `h`. Es: `FFh` = 255. |
| **0p 0q 0r 0s** | Pattern nibble          | Ogni cifra = 4 bit, preceduta da 0. Es: `0A 0B 0C 0D`   |
