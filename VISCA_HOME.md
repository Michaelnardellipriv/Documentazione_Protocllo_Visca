
# VISCA HOME

## Introduzione

Il VISCA (**Video System Control Architecture**) è il protocollo standard industriale per il controllo remoto di telecamere PTZ. Sviluppato originariamente da Sony, è diventato lo standard di riferimento nel settore broadcast e professionale, permettendo la gestione precisa di movimenti meccanici, parametri ottici e impostazioni d'immagine.

---

## Flusso di Apprendimento Consigliato

1. **Inizia qui** -> Leggi questa introduzione

2. **Fondamenti** -> [Struttura pacchetti](Struttura_del_pacchetto_VISCA.md) -> [Seriale](COME_FUNZIONA_IN_SERIALE.md) -> [IP](VISCA_SOPRA_IP.md)

3. **Sviluppo** -> [Guida sviluppo](Guida_allo_Sviluppo_di_un_Controller_VISCA.md)

4. **Riferimento** -> [Hardware](VISCA_HARDWARE_GUIDE.md) -> [Integrazione](VISCA%20Software%20Integration%20Guide.md)

5. **Risoluzione problemi** -> [Quick Reference](VISCA%20Protocol%20-%20Quick%20Reference%20&%20Troubleshooting%20Guide.md)

---

## Indice Tecnico Completo

### Fondamenti del Protocollo

- [Struttura del pacchetto VISCA](Struttura_del_pacchetto_VISCA.md) - Analisi dettagliata di Header, Message e Terminatore

- [Come funziona in Seriale](COME_FUNZIONA_IN_SERIALE.md) - RS-232/422, Daisy Chain, Address Set e cablaggio

- [VISCA over IP](VISCA_SOPRA_IP.md) - Specifiche UDP, Sequence Number, Configurazione DIP Switch

### Sviluppo Software

- [Guida allo Sviluppo di un Controller](Guida_allo_Sviluppo_di_un_Controller_VISCA.md) - Architettura, Nibble Parting, Gestione Socket

- [VISCA Software Integration Guide](VISCA%20Software%20Integration%20Guide.md) - Integrazione con OBS, vMix, sistemi di automazione

### Documentazione di Riferimento

- [VISCA_HARDWARE_GUIDE.md](VISCA_HARDWARE_GUIDE.md) - Specifiche hardware, pinout, schemi cablaggio

- [VISCA Protocol - Quick Reference & Troubleshooting Guide.md](VISCA%20Protocol%20-%20Quick%20Reference%20&%20Troubleshooting%20Guide.md) - Troubleshooting e comandi essenziali

### Riferimenti Rapidi

- Comandi Esadecimali - Pan-Tilt, Zoom, Preset (questa pagina)

- Messaggi di Risposta - ACK, Completion, Errori (questa pagina)

- Testing Pratico - Strumenti e procedure (questa pagina)

### Appendici Tecniche

- Troubleshooting Strutturato - Diagnostica e soluzioni (questa pagina)

- Riferimenti Tecnici Esterni - Standard, RFC, Manuali (questa pagina)

- Compatibilità Produttori - Tabelle e driver specifici (questa pagina)

- Termini Ricorrenti - Glossario tecnico completo (questa pagina)

---

## Navigazione Rapida per Caso d'Uso

### Per l'Installatore / Tecnico

1. [VISCA_HARDWARE_GUIDE](VISCA_HARDWARE_GUIDE.md) - Cablaggio, connettori, alimentazione

2. [COME_FUNZIONA_IN_SERIALE](COME_FUNZIONA_IN_SERIALE.md#gestione-della-rete-daisy-chain) - Daisy Chain e Address Set

3. [VISCA_SOPRA_IP](VISCA_SOPRA_IP.md#attivazione-fisica-per-ip) - Configurazione DIP Switch

### Per lo Sviluppatore Software

1. [Guida_allo_Sviluppo_di_un_Controller_VISCA](Guida_allo_Sviluppo_di_un_Controller_VISCA.md) - Architettura e best practices

2. [VISCA Hardware Guide](VISCA%20Hardware%20Guide%20-%20Specifiche%20Fisiche%20e%20Cablaggio.md) - Riferimento hardware completo

3. [VISCA Software Integration Guide](VISCA%20Software%20Integration%20Guide.md) - Integrazione con software terzi

### Per l'Operatore / Utente Finale

1. Guida Rapida Comandi - Comandi essenziali

2. [VISCA Protocol - Quick Reference & Troubleshooting Guide](VISCA%20Protocol%20-%20Quick%20Reference%20&%20Troubleshooting%20Guide.md) - Troubleshooting rapido

3. Testing Pratico - Test base

### Per il Progettista di Sistema

1. [VISCA_SOPRA_IP](VISCA_SOPRA_IP.md#configurazione-avanzata-di-rete) - VLAN, QoS, sicurezza

2. Compatibilità Produttori - Scelta hardware

3. [VISCA Software Integration Guide](VISCA%20Software%20Integration%20Guide.md) - Integrazione sistemi esistenti

---
## Storia e Funzionalità

### Cenni storici

Nato negli anni '90 per gestire le telecamere da studio analogiche tramite RS-232, il VISCA si è evoluto attraverso tre generazioni tecnologiche. Dalle prime connessioni seriali a corto raggio, è passato alla RS-422 per coprire distanze elevate (fino a 1,2 km), fino alla moderna versione **VISCA over IP**, che incapsula i comandi in pacchetti UDP per l'integrazione in reti locali e flussi NDI.

### Caratteristiche principali

- **Feedback Bidirezionale:** La camera non solo riceve, ma risponde con messaggi di **ACK**, garantendo che il controller conosca sempre lo stato del dispositivo.

- **Multi-Socket:** Permette di gestire più comandi in parallelo (ad esempio, muovere la testa mentre si regola lo zoom). [Vedi gestione socket](Guida_allo_Sviluppo_di_un_Controller_VISCA.md#architettura-a-due-code-gestione-socket)

- **Controllo Totale:** Oltre al movimento, permette di manipolare ogni parametro del sensore (Shutter, Gain, White Balance, Iris).

- **Cross-Platform:** Supporta comunicazione seriale (RS-232/422) e di rete (UDP/IP).

- **Scalabile:** Da singola telecamera a sistemi complessi con centinaia di dispositivi.

### Evoluzione del Protocollo

text

1990 -> VISCA v1.0: RS-232, 7 dispositivi, comandi base
1995 -> VISCA v2.0: RS-422, extended commands, presets
2005 -> VISCA v3.0: Supporto IP, UDP, sequence number
2010 -> VISCA over IP: Full UDP, 1000+ dispositivi, streaming
2020 -> Integrazione cloud, API REST, automazione avanzata

---

## Guida Rapida ai Comandi (Cheat Sheet)

### MESSAGGI DA INVIARE - Camera 1 (Header `81`)

#### Controllo Movimento e Zoom

| Funzione          | Comando Esadecimale                            | Descrizione                     | Documentazione     |
| ----------------- | ---------------------------------------------- | ------------------------------- | ------------------ |
| Pan-Tilt Home     | `81 01 06 04 FF`                               | Reset posizione asse centrale   | Movimento Pan-Tilt |
| Stop Movimento    | `81 01 06 01 00 00 03 03 FF`                   | Arresto immediato Pan/Tilt      | Comandi Stop       |
| Zoom In (Tele)    | `81 01 04 07 02 FF`                            | Avvio ingrandimento ottico      | Controllo Zoom     |
| Zoom Out (Wide)   | `81 01 04 07 03 FF`                            | Avvio grandangolo               | Controllo Zoom     |
| Zoom Stop         | `81 01 04 07 00 FF`                            | Arresto motore zoom             | Controllo Zoom     |
| Pan-Tilt Assoluto | `81 01 06 02 VV WW 0Y 0Y 0Y 0Y 0Z 0Z 0Z 0Z FF` | Movimento a posizione specifica | Comandi Assoluti   |

#### Gestione Preset (Memorie)

| Funzione      | Comando Esadecimale    | Descrizione                               | Documentazione   |
| ------------- | ---------------------- | ----------------------------------------- | ---------------- |
| Set Preset    | `81 01 04 3F 01 pp FF` | Salvataggio posizione preset `pp` (00-FF) | Sistema e Preset |
| Recall Preset | `81 01 04 3F 02 pp FF` | Richiamo posizione preset `pp`            | Sistema e Preset |
| Clear Preset  | `81 01 04 3F 00 pp FF` | Cancellazione preset `pp`                 | Sistema e Preset |

#### Controllo Immagine (Esempi)

| Funzione           | Comando Esadecimale | Descrizione                        | Documentazione                                                                          |
| ------------------ | ------------------- | ---------------------------------- | --------------------------------------------------------------------------------------- |
| White Balance Auto | `81 01 04 35 00 FF` | Bilanciamento bianco automatico    | [White Balance](VISCA%20Hardware%20Guide%20-%20Specifiche%20Fisiche%20e%20Cablaggio.md) |
| Exposure Manual    | `81 01 04 39 03 FF` | Esposizione manuale                | [Exposure](VISCA%20Hardware%20Guide%20-%20Specifiche%20Fisiche%20e%20Cablaggio.md)      |
| Gain Valore        | `81 01 04 0C PP FF` | Imposta gain a valore `PP` (00-0F) | [Gain](VISCA%20Hardware%20Guide%20-%20Specifiche%20Fisiche%20e%20Cablaggio.md)          |

> Riferimento Completo Comandi  
> Per la lista completa di tutti i comandi VISCA organizzati per categoria:  
> [VISCA Hardware Guide](VISCA%20Hardware%20Guide%20-%20Specifiche%20Fisiche%20e%20Cablaggio.md)
>
> Per comandi specifici del produttore consultare:  
> La cartella Fonti o Schede Tecniche da parte del produttore

---

## MESSAGGI DI RISPOSTA E GESTIONE SOCKET

### Cos'è un Socket?

Il **Socket** è un buffer di memoria interno alla telecamera che memorizza comandi in esecuzione. Ogni telecamera ha **due socket** che permettono l'esecuzione parallela di comandi.

Socket 1: Comando in esecuzione ->  Completion libera il socket
Socket 2:  Vuoto / Pronto ->  Nuovo comando può occuparlo

Gestione critica: Il software deve monitorare lo stato dei socket per evitare l'errore "Command Buffer Full". [Vedi gestione avanzata](Guida_allo_Sviluppo_di_un_Controller_VISCA.md#architettura-a-due-code-gestione-socket)

### ACK MESSAGE (Handshake)

| Funzione           | Codice Esadecimale | Descrizione                               | Stato Socket           |
| ------------------ | ------------------ | ----------------------------------------- | ---------------------- |
| ACK                | `z0 4y FF`         | Conferma ricezione comando nel socket `y` | Socket `y` -> Occupato |
| Completion         | `z0 5y FF`         | Conferma fine esecuzione nel socket `y`   | Socket `y` -> Libero   |
| Information Return | `z0 50 ... FF`     | Risposta a Inquiry con dati richiesti     | Nessun cambio stato    |
| Address Set Reply  | `88 30 pp FF`      | Risposta auto-indirizzamento Daisy Chain  | Configurazione rete    |
| Power ON Message   | `z0 38 FF`         | Segnale presenza all'accensione           | Stato sistema          |

> Convenzione di notazione
>
> - `z`: Indirizzo camera + 8 (Camera 1 = `1`, Risposta = `9`)
>
> - `y`: Numero socket (1 o 2)
>
> - `pp`: Parametro variabile
>

### MESSAGGI DI ERRORE

| Errore              | Codice Esadecimale | Causa Probabile                   | Azione Correttiva       | Riferimento       |
| ------------------- | ------------------ | --------------------------------- | ----------------------- | ----------------- |
| Syntax Error        | `z0 60 02 FF`      | Formato pacchetto errato          | Verificare formato      | Troubleshooting   |
| Command Buffer Full | `z0 60 03 FF`      | Entrambi i socket occupati        | Attendere Completion    | Gestione Socket   |
| Command Canceled    | `z0 6y 04 FF`      | Comando annullato volontariamente | Comando interrotto      | Cancel Command    |
| No Socket           | `z0 6y 05 FF`      | Tentativo cancellare socket vuoto | Verificare stato socket | No Socket         |
| Not Executable      | `z0 6y 41 FF`      | Comando impossibile ora           | Cambiare modalità       | Errori Esecuzione |

---

## Testing Pratico: Validazione dei Comandi

### Strumenti Consigliati

- Packet Sender - Per invio pacchetti UDP sulla porta `52381`

- Hercules SETUP Utility - Terminale esadecimale per RS-232/422

- Wireshark - Analizzatore di rete per debug pacchetti

- Putty/Serial Terminal - Per test seriali base

### Procedura di Test (VISCA over IP)

Per verificare la connessione con una telecamera (es. IP `192.168.1.100`):

1. Protocollo: UDP

2. Destinazione: `192.168.1.100:52381`

3. Comando HEX: `01 00 00 05 00 00 00 01 81 09 00 02 FF`

4. Attesa Risposta: La telecamera deve rispondere entro 2 secondi

**Cosa osservare:**

- Invio (TX): Il pacchetto parte correttamente

- Ricezione (RX): Risposta attesa: `01 11 ... 90 50 ...`

- Sequence Number: Deve corrispondere tra invio e ricezione

### Test Seriale

Per test seriali, configurare Hercules con:


```text

Baud Rate: 9600 (o 38400 se supportato)
Data Bits: 8
Stop Bits: 1
Parity: None
Flow Control: None

> Attenzione al Sequence Number  
> Se usi Packet Sender, i byte in posizione 5-8 dell'header IP (`00 00 00 01`) sono il contatore. Se invii due volte lo stesso pacchetto senza incrementare questo numero, la telecamera **ignorerà il secondo invio**. [Vedi gestione Sequence Number](VISCA_SOPRA_IP.md#la-gestione-del-sequence-number-su-ip)
> Test di Validazione Dispositivo  
> Prima di assumere che un IP sia una telecamera VISCA, esegui il **3-Way Handshake** per evitare falsi positivi. [Vedi algoritmo](Guida_allo_Sviluppo_di_un_Controller_VISCA.md#validazione-del-dispositivo-protocol-handshake)
```

---

## Troubleshooting Strutturato

### Problemi Critici (Risoluzione Immediata)

| Sintomo                                         | Primo Controllo                                              | Azioni Immediate                                                                               | Diagnostica Avanzata                                     | Riferimento       |
| ----------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------- | ----------------- |
| Timeout su tutti i comandi                      | 1. Alimentazione camera<br>2. LED di rete<br>3. Ping all'IP  | 1. Riavviare camera<br>2. Controllare switch DIP<br>3. Reset VISCA (`02 00`)                   | `tcpdump -i any port 52381`<br>Analisi pacchetti         | Configurazione IP |
| Camera risponde al ping ma non ai comandi VISCA | 1. Sequence Number<br>2. Header IP<br>3. Terminatore FF      | 1. Inviare Reset (`02 00`)<br>2. Verificare header IP (8 byte)<br>3. Controllare FF finale     | Wireshark capture<br>Packet analysis                     | Sequence Number   |
| Errore `z0 60 03 FF` (Buffer Full)              | Stato socket occupati                                        | 1. Attendere Completion<br>2. Inviare Cancel (`z0 6y 04 FF`)<br>3. Rallentare invio            | Monitorare ACK/Completion<br>Log stato socket            | Gestione Socket   |
| Camera non si muove ma risponde ad Inquiry      | 1. Comando malformato<br>2. Velocità zero<br>3. Limit switch | 1. Verificare parametri VV/WW<br>2. Usare velocità `01`-`18`<br>3. Controllare stato meccanico | Inquiry stato: `81 09 06 12 FF`<br>Test comando semplice | Comandi Movimento |
| Daisy Chain: solo prima camera risponde         | 1. Cablaggio IN/OUT<br>2. Address Set<br>3. Cavo difettoso   | 1. Verificare connessioni<br>2. Inviare `88 30 01 FF`<br>3. Testare cavi                       | Controllare LED attività<br>Test segmenti separati       | Daisy Chain       |

### Altri Problemi Comuni

| Problema                       | Soluzione                                                                   | Documentazione         |
| ------------------------------ | --------------------------------------------------------------------------- | ---------------------- |
| Cambio IP imprevisto (DHCP)    | 1. Configurare IP statico<br>2. DHCP Reservation<br>3. Tracciamento MAC     | Strategia Self-Healing |
| Risposta lenta o intermittente | 1. Isolare rete VISCA<br>2. Cavi schermati<br>3. Implementare QoS           | Configurazione Rete    |
| Perdita di presets             | 1. Salvare nuovamente<br>2. Backup configurazione<br>3. Verificare firmware | Gestione Preset        |

---

## Riferimenti Tecnici Esterni

### Standard di Rete

- **RFC 768 - User Datagram Protocol (UDP)** - Specifica del protocollo senza connessione

- **IEEE 802.3 - Ethernet** - Standard per reti cablate (10/100/1000BASE-T)

- **RFC 2131 - Dynamic Host Configuration Protocol (DHCP)** - Gestione indirizzi IP dinamici

- **RFC 791 - Internet Protocol (IPv4)** - Protocollo di rete sottostante

- **IEEE 802.1Q - VLAN Tagging** - Isolamento traffico di rete

### Standard Seriali

- **TIA/EIA-232-F (RS-232)** - Comunicazione seriale a corto raggio (fino a 15m)

- **TIA/EIA-422-B (RS-422)** - Comunicazione seriale differenziale a lunga distanza (fino a 1200m)

- **TIA/EIA-485 (RS-485)** - Standard multi-drop per comunicazioni industriali

### Documentazione Ufficiale VISCA

- **Sony VISCA Protocol Specification** - Manuale tecnico originale (disponibile su richiesta)

- **VISCA over IP Application Note** - Note di implementazione IP (Panasonic, Canon, Sony)

- **VISCA Serial Communication Interface** - Documentazione specifica seriale

### Strumenti di Testing e Sviluppo

- **Packet Sender** - Utility per invio pacchetti UDP/TCP raw

- **Hercules SETUP Utility** - Terminale seriale avanzato per test RS-232/422

- **Wireshark** - Analizzatore di rete per cattura e debug pacchetti

- **Serial Port Monitor** - Analizzatore traffico seriale

---

## Compatibilità Produttori

### Tabella Compatibilità Principale

|Produttore|Modelli Supportati|Estensioni VISCA|Note|Versioni Testate|
|---|---|---|---|---|
|Sony|BRC-X400, SRG-X400, EVI-H100|Comandi proprietari focus/exposure|Full compliance|v2.00+|
|Panasonic|AW-UE100, AW-HE130, AW-UE70|Extended preset (100+), NDI integrato|Supporto NDI/SDI|v1.5+|
|Canon|CR-N500, CR-N300, CR-X300|Lens control avanzato|Qualità ottica eccellente|v1.2.0+|
|PTZOptics|20X-NDI, 30X-SDI, 12X-USBFHD|Auto-tracking, Preset patterns|Clone Sony VISCA|v3.0+|

### Versioni Firmware Consigliate

- **Sony**: v2.00+ per VISCA over IP (fix bug sequence number)

- **Panasonic**: v1.5+ per stabilità UDP e fix multicast

- **Canon**: v1.2.0+ per bug fix sequence number

- **PTZOptics**: v3.0+ per compatibilità completa

### Driver e Software Specifici

- **Sony Camera Control SDK** - API ufficiale per integrazione

- **Panasonic AW Utilities** - Configurazione rete e preset

- **Canon PTZ Controller** - Software di riferimento

- **ONVIF Device Manager** - Scoperta automatica dispositivi

> Documentazione Hardware Completa  
> Per specifiche dettagliate, pinout, schemi cablaggio e requisiti ambientali:  
> [VISCA_HARDWARE_GUIDE](VISCA_HARDWARE_GUIDE.md)

---

## TERMINI RICORRENTI

### Glossario Tecnico Completo

| Termine                     | Definizione                                            | Riferimento          |
| --------------------------- | ------------------------------------------------------ | -------------------- |
| FFH (Terminatore)           | Byte `FF` (255 decimale) che chiude ogni comando VISCA | Struttura Pacchetto  |
| ACK (Acknowledge)           | Segnale di conferma ricezione comando                  | Messaggi Risposta    |
| MSB (Most Significant Bit)  | Bit più a sinistra in un byte (valore più alto)        | Ordine Bit           |
| LSB (Least Significant Bit) | Bit più a destra (valore più basso)                    | Ordine Bit           |
| Daisy Chain                 | Configurazione seriale a catena di dispositivi         | Daisy Chain          |
| Nibble                      | Metà byte (4 bit), usato per codifica valori           | Nibble Parting       |
| Socket (VISCA)              | Buffer memoria interno per comandi in esecuzione       | Gestione Socket      |
| Sequence Number             | Contatore 32-bit per ordine pacchetti IP               | Sequence Number      |
| DIP Switch                  | Interruttori fisici per configurazione hardware        | DIP Switch           |
| DHCP Reservation            | Associazione permanente IP-MAC su server DHCP          | Gestione IP          |
| Protocol Handshake          | Scambio iniziale per verifica compatibilità            | Validazione          |
| RTSP                        | Protocollo per streaming video da telecamere           | Integrazione Video   |
| VLAN                        | Rete logica per isolamento traffico                    | Configurazione Rete  |
| QoS                         | Meccanismo prioritizzazione traffico di rete           | Configurazione Rete  |
| Jitter                      | Variazione latenza tra pacchetti consecutivi           | Metriche Performance |

