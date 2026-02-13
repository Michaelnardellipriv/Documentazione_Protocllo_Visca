# VISCA Protocol - Quick Reference & Troubleshooting Guide

> [!info] **Nota Compatibilità**
> I dati e le procedure contenute in questa guida sono **testati internamente** su telecamere Sony serie EVI, BRC, e device VISCA-over-IP conformi al protocollo standard.
> Per modelli specifici o vendor non listati, è consigliato controllare la documentazione del produttore.
> Report dettagliati di compatibilità per hardware specifico sono disponibili su richiesta.

## Indice Rapido di Troubleshooting

### Problemi Critici (Immediata Risoluzione)

| Problema | Primo Controllo | Azione Immediata | Diagnostica Avanzata |
|----------|----------------|------------------|----------------------|
| Nessuna comunicazione | 1. Alimentazione camera 2. LED di rete 3. Ping all'IP | 1. Riavviare camera 2. Controllare switch DIP 3. Reset VISCA (`02 00`) | `tcpdump -i any port 52381` |
| Movimento intermittente | 1. Velocità impostata 2. Stato limit switch 3. Congestione rete | 1. Ridurre velocità a `01` 2. Verificare comando `81 09 06 12 FF` 3. Isolare rete | Monitorare latenza con `ping -f` |
| Perdita di presets | 1. Alimentazione stabile 2. Batteria backup 3. Memoria camera | 1. Salvare nuovamente preset 2. Eseguire backup configurazione 3. Verificare firmware | Controllare log errori camera |

---

## Tabella di Compatibilità Protocollo

### Versioni VISCA Supportate

| Versione | Anno | Caratteristiche | Limitazioni |
|----------|------|-----------------|-------------|
| VISCA v1.0 | 1990 | RS-232, 7 dispositivi, comandi base | Solo seriale, no feedback esteso |
| VISCA v2.0 | 1995 | RS-422, extended commands, presets | Velocità limitata (9600 baud) |
| VISCA v3.0 | 2005 | Supporto IP, UDP, sequence number | Compatibilità backward parziale |
| VISCA over IP | 2010 | Full UDP, 1000 dispositivi, streaming | Richiede switch DIP abilitato |

---

## Mappa dei Comandi per Sviluppatori

### Struttura Pacchetto Base

``` merdamind
[Header IP: 8 byte] + [Header VISCA: 1 byte] + [Message: 1-14 byte] + [Terminator: 1 byte FF]
```

### Template Comuni (Hex Format)

#### 1. Comandi di Movimento (Pan-Tilt)

```
81 01 06 01 VV WW 03 01 FF
```

- VV: Velocità Pan (01-18 hex)
- WW: Velocità Tilt (01-14 hex)

#### 2. Comandi Zoom

```
81 01 04 07 TT FF
```

- TT: 02=Tele, 03=Wide, 00=Stop

#### 3. Inquiry (Richiesta Stato)

```
81 09 CC SS FF
```

- CC: Categoria (04=Camera, 06=PanTilt)
- SS: Sub-code (specifica parametro)

#### 4. Reset Comunicazione IP

```
02 00 00 00 00 00 00 00
```

- Importante: Sequence number resettato a 0

---

## Tabella Velocità Pan-Tilt

### Modalità "Slow" (Precisione)

| Hex Value | Gradi/Secondo | Utilizzo Tipico |
|-----------|---------------|-----------------|
| 01 | 0.4° | Micro-aggiustamenti, macro |
| 02 | 0.8° | Tracking lento |
| 04 | 1.6° | Movimenti fluidi studio |
| 08 | 3.2° | Transizioni standard |
| 10 | 6.4° | Riposizionamento rapido |
| 18 | 40° | Massima velocità |

### Modalità "Normal" (Standard)

| Hex Value | Gradi/Secondo | Note |
|-----------|---------------|------|
| 01-09 | 0.4°-14.4° | Lineare |
| 0A-18 | 16°-60° | Esponenziale (sport) |

---

## Codici Errore Estesi

### Errore Generici (Byte 3 = 60)

| Codice | Significato | Azione Correttiva |
|--------|-------------|-------------------|
| 60 01 | Lunghezza messaggio errata | Verificare conteggio byte |
| 60 02 | Syntax error | Controllare terminatore FF |
| 60 03 | Command buffer full | Attendere o cancellare comando |
| 60 04 | Command canceled | Comando annullato dal sistema |

### Errori Specifici Socket (Byte 3 = 6y)

| Codice | Socket | Significato |
|--------|--------|-------------|
| 61 41 | Socket 1 | Comando non eseguibile ora |
| 62 41 | Socket 2 | Comando non eseguibile ora |
| 61 05 | Socket 1 | No socket (già vuoto) |
| 62 05 | Socket 2 | No socket (già vuoto) |

---

## Procedure di Emergenza

### 1. Camera Non Risponde (Soft Reset)

```
1. Spegnere alimentazione camera
2. Attendere 30 secondi
3. Tenere premuto tasto SETUP (se presente) durante accensione
4. Attendere boot completo (LED verde fisso)
5. Testare con comando base: 81 01 06 04 FF
```

### 2. Comunicazione IP Persa (Hard Reset)

```
1. Disabilitare switch DIP 3 (OFF)
2. Riavviare camera
3. Collegarsi via seriale (Hercules)
4. Inviare: 81 01 06 04 FF
5. Se risponde, riabilitare switch 3 (ON)
6. Riavviare e testare su IP
```

### 3. Sequence Number Bloccato

```
1. Inviare reset: 02 00 00 00 00 00 00 00
2. Attendere 2 secondi
3. Inviare inquiry: 01 00 00 05 00 00 00 01 81 09 00 02 FF
4. Se timeout, ripetere passi 1-3
```

---

## Configurazione Rete Consigliata

### Per Ambiente Production

```
Network Configuration:
  IP Assignment: Static IP o DHCP Reservation
  Subnet: 192.168.1.0/24 (dedicata per PTZ)
  Gateway: 192.168.1.1
  DNS: 8.8.8.8 (opzionale)
  MTU: 1500 (standard)
  QoS: Prioritize UDP port 52381

Camera Settings:
  UDP Port: 52381 (fixed)
  Protocol: VISCA over IP v3.0
  Keepalive: Disabled (VISCA è connectionless)
  Multicast: Disabled

Security:
  VLAN: Isolata per video controllo
  Firewall: Allow only controller IP → Camera IP:52381
  Authentication: None (VISCA non supporta nativo)
```

### Per Ambiente Testing/Development

```
Network Configuration:
  IP Assignment: DHCP (per testing rapido)
  Subnet: 192.168.0.0/24
  Controller IP: 192.168.0.100
  Camera IP Range: 192.168.0.101-110

Tools:
  Packet Sender: UDP testing
  Wireshark: Capture filter: udp.port == 52381
  Python Script: Simple controller per test
```

---

## Checklist Pre-Produzione

### Prima dell'Installazione

- [ ] Verificare firmware camera (ultima versione)
- [ ] Testare tutti i movimenti base (Pan, Tilt, Zoom)
- [ ] Verificare risposta a comandi inquiry
- [ ] Testare salvataggio/richiamo di almeno 3 preset
- [ ] Verificare comunicazione su tutta la distanza cablaggio

### Configurazione Rete

- [ ] IP statici configurati su tutte le camere
- [ ] DHCP reservation configurata sul router
- [ ] Porta 52381 aperta nel firewall
- [ ] VLAN configurata (se richiesto)
- [ ] QoS abilitato per traffico UDP

### Test Finali

- [ ] Comunicazione stabile per 24h consecutive
- [ ] Test stress (1000+ comandi in sequenza)
- [ ] Test failover (riavvio router/camera)
- [ ] Documentazione aggiornata con IP/MAC
- [ ] Backup configurazione camera

---

## Quick Commands Reference Card

### Comandi Essenziali (Camera 1)

``` text
# Home Position
81 01 06 04 FF

# Stop Movement
81 01 06 01 00 00 03 03 FF

# Zoom In
81 01 04 07 02 FF

# Zoom Out
81 01 04 07 03 FF

# Set Preset 1
81 01 04 3F 01 01 FF

# Recall Preset 1
81 01 04 3F 02 01 FF

# Inquiry Pan-Tilt Position
81 09 06 12 FF

# Inquiry Zoom Position
81 09 04 47 FF
```

### Comandi di Sistema

```
# Address Set (Daisy Chain)
88 30 01 FF

# Reset VISCA over IP
02 00 00 00 00 00 00 00

# Power ON Inquiry
81 09 00 02 FF
```

---

## Metriche di Performance

### Valori Attesi (Gigabit Ethernet)

| Metrica | Valore Minimo | Valore Ottimale | Note |
|---------|---------------|-----------------|------|
| Latenza Ping | < 5ms | < 1ms | Rete isolata |
| Jitter UDP | < 10ms | < 2ms | Critico per movimento fluido |
| Packet Loss | 0% | 0% | Inaccettabile > 0.1% |
| Tempo Risposta | < 50ms | < 20ms | Comando → ACK |
| Throughput | 1 Mbps | 10 Mbps | Con video streaming |

### Valori Attesi (RS-422)

| Metrica | Valore | Note |
|---------|--------|------|
| Baud Rate | 9600/38400 bps | Dipende da camera |
| Max Distance | 1200m | Con cavo schermato |
| Dispositivi Max | 7 | Per Daisy Chain |
| Tempo Risposta | 100-200ms | Più lento di IP |

---

**Nota:** Questo documento è da considerarsi parte integrante della documentazione VISCA. Mantenere aggiornato con le specifiche delle telecamere in uso.

Per problemi non risolti da questa guida, consultare:

- Manuale tecnico della camera
- [VISCA HOME](VISCA_HOME.md) per i fondamenti
- Supporto tecnico del produttore
