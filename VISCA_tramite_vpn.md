# VISCA tramite VPN

## Guida Teorica all'Utilizzo del Protocollo VISCA su Connessioni VPN

## Fondamenti di Rete per VISCA

### Il Modello OSI e VISCA

Per comprendere l'impatto di una VPN su VISCA, è necessario collocare entrambi i protocolli nel modello OSI:

| Livello OSI | VISCA nativo | VISCA su VPN |
|-------------|--------------|--------------|
| **7. Applicazione** | Comandi VISCA | Comandi VISCA |
| **6. Presentazione** | Nibble parting | Nibble parting |
| **5. Sessione** | Connectionless | Gestita dalla VPN |
| **4. Trasporto** | UDP | UDP incapsulato |
| **3. Rete** | IP | IP + Tunnel VPN |
| **2. Collegamento** | Ethernet | Ethernet |
| **1. Fisico** | Cavo/fibra | Infrastruttura WAN |

**Osservazione critica:** La VPN inserisce un **livello di incapsulamento aggiuntivo** tra il livello 3 e il livello 4 logico, alterando le caratteristiche di trasporto che il protocollo VISCA dà per scontate.

### Presupposti di Progetto di VISCA over IP

Quando Sony estese VISCA su IP nel 2005-2010, i presupposti architetturali erano:

1. **Rete locale non congestionata** (switch Gigabit dedicati)
2. **Latenza trascurabile** (< 1ms)
3. **Assenza di jitter significativo** (code FIFO deterministiche)
4. **Ordine di consegna preservato** (nella pratica UDP non garantisce ordine, ma su LAN avviene raramente fuori ordine)
5. **Nessuna frammentazione IP** (pacchetti < MTU)
6. **Nessuna crittografia** (protocollo in chiaro)

Questi presupposti **vengono sistematicamente violati** dall'introduzione di una VPN geografica.

---

## Il Problema dell'Incapsulamento

### Overhead e Frammentazione

VISCA over IP genera pacchetti di dimensione estremamente contenuta:

```
Pacchetto VISCA tipico: 12-32 byte
Header IP/UDP: 28 byte
TOTALE: 40-60 byte
```

L'incapsulamento VPN aggiunge un secondo header:

| Tipo VPN | Overhead | Pacchetto totale | Rischio frammentazione |
|----------|----------|------------------|------------------------|
| **OpenVPN (UDP)** | ~58 byte | 98-118 byte | Alto su DSL/ADSL |
| **WireGuard** | ~32 byte | 72-92 byte | Moderato |
| **IPSec ESP** | ~50-56 byte | 90-116 byte | Alto |
| **SSH Tunnel** | ~20-40 byte | 60-100 byte | Moderato |
| **SSL/TLS VPN** | ~40-60 byte | 80-120 byte | Alto |
| **GRE Tunnel** | ~24 byte | 64-84 byte | Basso |

**Problema fondamentale:** La **frammentazione IP** avviene quando il pacchetto incapsulato supera l'MTU del mezzo trasmissivo. I frammenti UDP:
- Viaggiano in modo indipendente
- Possono arrivare in ordine casuale
- La perdita di un singolo frammento corrompe l'intero pacchetto
- Riavvio complesso (UDP non ha meccanismi di reassembly intelligenti)

**Impatto su VISCA:** La camera riceve pacchetti incompleti o in ordine errato, generando errori di sintassi o ignorando silenziosamente il comando.

### Jitter di Incapsulamento

La VPN introduce **jitter di elaborazione**:

```
Rete locale:            [Pacchetto] → Switch → [Pacchetto]
                        0.1ms        0.1ms     0.1ms

Rete VPN:              [Pacchetto] → Crittografia → Buffer → WAN → Decrittografia
                        0.1ms       1-10ms       0-5ms   >1ms  1-5ms
```

Le fasi critiche:
1. **Crittografia**: Operazioni asimmetriche/blocco
2. **Buffering**: Accumulo pacchetti per efficienza
3. **Coda WAN**: Gestione congestione ISP
4. **Decrittografia**: Lato ricevente

Il jitter risultante (variazione della latenza) può superare ampiamente i 20-30ms, un valore che VISCA non è progettato per gestire.

---

## Latenza e Comportamento del Protocollo

### Il Timeout Implicito in VISCA

VISCA over IP **non specifica un timeout formale**. L'implementazione è lasciata al controller. Tuttavia, esiste un timeout implicito nel comportamento atteso:

```
Sequenza nominale (LAN):
t=0ms:   Controller → [Comando] → Camera
t=0.5ms: Camera → [ACK] → Controller
t=50ms:  Camera → [Completion] → Controller
        (movimento fisico completato)

Timeout tipico implementato: 100-500ms
```

Su VPN geografica:

```
t=0ms:    Controller → [Comando] → VPN → Internet → Camera
t=25ms:   Camera → [ACK] → Internet → VPN → Controller
t=75ms:   Camera → [Completion] → Internet → VPN → Controller

Timeout tipico: ancora 100-500ms → FUNZIONA
```

**Il problema emerge con jitter elevato:**

```
t=0ms:    Controller → [Comando]
t=45ms:   (ritardo imprevisto) Pacchetto ancora in coda VPN
t=120ms:  Controller assume timeout → Ritrasmissione
t=121ms:  Pacchetto originale arriva alla camera
t=122ms:  Pacchetto ritrasmesso arriva alla camera
t=150ms:  Camera → [ACK per comando 1]
t=151ms:  Camera → [ACK per comando 2]  (stessa sequenza?)
```

**Conseguenza:** La camera riceve due comandi identici con lo stesso sequence number. Il comportamento non è specificato; alcune camere ignorano il duplicato, altre generano errore.

### Relazione tra Latenza e Throughput

VISCA è un protocollo a basso throughput ma **sincrono nella logica applicativa**:

```
Comando 1: Inviato → attesa ACK → attesa Completion → Comando 2
```

La latenza di andata-ritorno (RTT) diventa **parte del tempo di esecuzione** percepito dall'operatore:

```
RTT 1ms:   Comando → ACK = 1ms  → operazione fluida
RTT 50ms:  Comando → ACK = 50ms → ritardo percepibile
RTT 150ms: Comando → ACK = 150ms → esperienza degradata
```

**Legge fondamentale:** In VISCA, **la latenza si somma al tempo di movimento**. Un movimento di 500ms su LAN diventa 650ms su VPN con RTT 150ms.

---

## Sequence Number in Ambienti Non Deterministici

### Il Ruolo del Sequence Number

VISCA over IP utilizza un **contatore a 32-bit** nell'header IP:

```
Byte 0-1:   Tipo pacchetto (01 00 = comando)
Byte 2-3:   Lunghezza payload
Byte 4-7:   Sequence number (32-bit)
Byte 8-n:   Payload VISCA
```

**Funzione prevista:** Garantire l'ordinamento e rilevare duplicati in ambienti LAN dove:
- I pacchetti arrivano quasi sempre in ordine
- I duplicati sono rari
- Il jitter è contenuto

**Funzione reale su VPN:** Il sequence number diventa un **vincolo fragile** perché:

1. **Fuori ordine**: Due percorsi diversi (ECMP) possono consegnare il pacchetto 2 prima del 1
2. **Duplicazione**: Ritrasmissioni del livello trasporto o applicativo
3. **Reset involontari**: La perdita di sincronizzazione richiede il comando `02 00 00 00 00 00 00 00`

### Il Problema della Finestra di Ricezione

La camera mantiene **l'ultimo sequence number ricevuto**. La logica implementata (non documentata ufficialmente, ma osservata) è approssimativamente:

```
if (seq_num == last_seq + 1):
    esegui comando
    last_seq = seq_num
else if (seq_num > last_seq + 1):
    # Pacchetto saltato - comportamento variabile
    # Alcune camere scartano, altre eseguono ma resettano attesa
    scarta comando
    genera errore 60 02? (syntax error)
else if (seq_num <= last_seq):
    # Pacchetto già visto o vecchio
    scarta silenziosamente
    (nessun errore, nessun ACK)
```

**Implicazione:** Su VPN con jitter, la semplice variazione dell'ordine di arrivo causa:
- Comandi eseguiti fuori sequenza logica
- Comandi scartati senza notifica
- Desincronizzazione controller-camera

---

## NAT Traversal e Indirizzamento

### La Natura di VISCA over IP

VISCA over IP è un protocollo **simplex nella direzione di controllo**:

```
Controller: porta ephemeral → Camera:52381
Camera:     porta ephemeral → Controller:porta ephemeral
```

Non utilizza:
- Connessione persistente
- Keepalive
- Stateful inspection

**Problema con NAT:** Il NAT mantiene un'associazione basata su traffico bidirezionale. Se la camera risponde, il mapping rimane attivo. Tuttavia:

1. **Timeout NAT**: I router domestici hanno timeout UDP tipicamente 30-300 secondi
2. **NAT simmetrico**: Alcuni NAT cambiano porta per ogni destinazione
3. **Hairpinning**: Comunicazione NAT→stesso NAT richiede supporto specifico

### Doppio NAT e VISCA

Lo scenario più complesso: **Camera su NAT A, Controller su NAT B, VPN termina su uno dei due**

``` text
Internet
    ↑
┌───┴───┐      ┌────────┐      ┌────────┐
│ NAT A │──────│ VPN    │──────│ NAT B  │
│ Camera│      │ Server │      │ Ctrl   │
└───────┘      └────────┘      └────────┘
  192.168.1.10   10.8.0.1      192.168.0.100
```


Il problema dell'**indirizzamento multiplo**:

- La camera conosce il proprio IP come 192.168.1.10
- Il controller vede la camera come 10.8.0.x (VPN) o come IP pubblico?
- Il sequence number è legato all'IP sorgente?

**Osservazione:** Alcune implementazioni VISCA legano parzialmente lo stato del sequence number all'indirizzo IP sorgente. Un cambio di percorso (IP pubblico vs IP VPN) può causare reset impliciti.

---

## Modelli di Connettività

### Modello 1: Bridge di Livello 2 (L2VPN)

**Concetto:** Estendere logicamente la stessa subnet fisica attraverso la VPN.

```
[Sede A - VLAN 100] ←→ [VPN L2] ←→ [Sede B - VLAN 100]
     Camera: 192.168.1.10            Controller: 192.168.1.200
```

**Proprietà:**
- Stessa subnet, stesso broadcast domain
- ARP funziona attraverso il tunnel
- VISCA opera come se fosse in LAN
- **Vincolo:** L2VPN su lunghe distanze è fragile (broadcast storm, loop)

**Implicazioni teoriche:**
VISCA non utilizza broadcast. L'unico traffico ARP è per la risoluzione iniziale. L2VPN è tecnicamente la soluzione più trasparente, ma la più complessa da realizzare su WAN.

### Modello 2: Routing Statico (L3VPN)

**Concetto:** Reti separate, routing esplicito.

``` text
[Sede A - 192.168.1.0/24] ←→ [VPN L3] ←→ [Sede B - 10.0.0.0/24]
     Camera: 192.168.1.10            Controller: 10.0.0.50
                                     Routing: 192.168.1.0 → VPN
```

**Proprietà:**
- Subnet distinte
- Routing statico o dinamico
- NAT opzionale
- VISCA opera cross-subnet

**Implicazioni teoriche:**
VISCA non ha dipendenze dalla subnet. Funziona cross-subnet purché il routing sia corretto. Il controller deve conoscere l'IP della camera nella sua rete nativa (es. 192.168.1.10) e il routing deve portare i pacchetti attraverso la VPN.

### Modello 3: Overlay Network (ZeroTier/Tailscale)

**Concetto:** Assegnare un IP virtuale a ogni dispositivo, creando una overlay network indipendente.

```text
Camera:     IP fisico 192.168.1.10
            IP overlay 172.20.0.1

Controller: IP fisico 10.0.0.50
            IP overlay 172.20.0.2

Comunicazione: Controller(172.20.0.2) → Camera(172.20.0.1):52381
```

**Proprietà:**
- Indirizzamento indipendente dalla rete fisica
- Crittografia end-to-end
- NAT traversal automatico
- **Vincolo:** L'overlay aggiunge latenza e jitter

**Implicazioni teoriche:**
VISCA opera su IP overlay come se fosse IP nativo. Il sequence number è legato all'IP overlay, che è stabile anche se l'IP fisico cambia. Questo è il modello più resiliente ai cambi di connettività.

---

## Considerazioni sulla Sicurezza

### Crittografia e Integrità

VISCA in chiaro su VPN eredita la crittografia del tunnel. **Considerazioni**:

1. **Confidenzialità**: I comandi VISCA rivelano attività (zoom, movimento, preset). In contesti sensibili, il tunnel VPN deve fornire crittografia forte.
2. **Integrità**: La VPN deve garantire che i pacchetti non siano alterati. Una modifica anche di 1 byte nel payload VISCA può causare comportamenti imprevisti.
3. **Autenticazione**: VISCA non ha autenticazione. La VPN deve autenticare i peer per prevenire controllo non autorizzato.

### Isolamento del Traffico VISCA

In ambienti VPN condivisi, il traffico VISCA dovrebbe essere **isolato logicamente**:

``` text
┌─────────────────────────────────────┐
│         Tunnel VPN Principale        │
├─────────────────────────────────────┤
│   VLAN 100 - Dati Aziendali         │
├─────────────────────────────────────┤
│   VLAN 200 - VoIP                   │
├─────────────────────────────────────┤
│   VLAN 300 - Controllo VISCA        │  ← Prioritizzato, isolato
└─────────────────────────────────────┘
```

**Motivazione:** VISCA è sensibile a congestione e jitter. Condividere il tunnel con traffico bulk (backup, trasferimenti file) degrada le prestazioni in modo imprevedibile.

---

## Limiti Teorici e Vincoli

### Limite 1: Latenza Massima Tollerabile

Non esiste una specifica ufficiale, ma dall'analisi del comportamento:

| Latenza (RTT) | Effetto sul Controllo | Operatività           |
| ------------- | --------------------- | --------------------- |
| < 10 ms       | Impercettibile        | Fluida                |
| 10-30 ms      | Leggero ritardo       | Accettabile           |
| 30-80 ms      | Ritardo evidente      | Operativa ma faticosa |
| 80-150 ms     | Ritardo significativo | Operazioni semplici   |
| > 150 ms      | Movimenti a scatti    | Critica               |
| > 300 ms      | Timeout frequenti     | Inutilizzabile        |

**Fondamento teorico:** La percezione umana richiede feedback < 100ms per associazione causa-effetto. Oltre 150ms, l'operatore tende a "inseguire" il movimento.

### Limite 2: Jitter Massimo Tollerabile

Più critico della latenza assoluta:

| Jitter (deviazione) | Effetto              | Causa              |
| ------------------- | -------------------- | ------------------ |
| < 5 ms              | Impercettibile       | Variazioni normali |
| 5-15 ms             | Occasionali ritardi  | Congestione lieve  |
| 15-30 ms            | Movimenti irregolari | Buffer bloat       |
| 30-50 ms            | Comandi saltati      | Jitter critico     |
| > 50 ms             | Perdita sequenza     | Inutilizzabile     |

**Fondamento teorico:** VISCA non ha buffer di riordino. Ogni pacchetto è indipendente. Se la variazione di latenza supera la separazione temporale tra comandi consecutivi, questi possono arrivare fuori ordine.

### Limite 3: Packet Loss

VISCA over UDP non ha ritrasmissione automatica:

| Packet Loss | Effetto                                    |
| ----------- | ------------------------------------------ |
| 0%          | Ideale                                     |
| 0.01%       | Occasionale comando perso (impercettibile) |
| 0.1%        | Comandi persi visibili                     |
| 0.5%        | Operatività compromessa                    |
| > 1%        | Inutilizzabile                             |

**Fondamento teorico:** La perdita di un pacchetto di movimento causa arresto imprevisto. La perdita di un preset causa mancata esecuzione. Non c'è notifica di perdita.

---

## Casi di Studio Teorici

### Caso A: Produzione Sportiva Intercontinentale

**Scenario:**
- Regia: Milano
- Camera: New York
- Distanza: ~6500 km
- Latenza teorica fibra: ~65 ms
- Latenza reale VPN: ~75-85 ms
- Jitter: 5-15 ms

**Analisi:**
La latenza è al limite dell'operatività per movimenti rapidi (sport). Il jitter di 15 ms può causare occasionali fuori ordine. **Soluzione teorica**: Ridurre velocità movimento, utilizzare preset memorizzati localmente, bufferizzazione lato controller.

**Vincolo fisico:** La velocità della luce nel fibra (200.000 km/s) impone un minimo teorico di 32.5 ms per tratta. Non superabile.

### Caso B: Sedi Multiple con VPN Hub-and-Spoke

**Scenario:**
- 5 sedi, ciascuna con 2-4 telecamere
- Hub VPN centralizzato in cloud
- Controller principale in sede A
- Controller secondari in altre sedi

**Analisi:**
Il traffico VISCA segue percorso: Controller → Hub Cloud → Camera
Questo raddoppia la latenza. **Soluzione teorica**: VPN mesh invece di hub-and-spoke, routing diretto tra sedi.

### Caso C: VPN su Reti Mobili (4G/5G)

**Scenario:**
- Camera fissa in sede
- Controller su tablet connesso in 4G
- VPN per accesso remoto

**Analisi:**
Reti mobili hanno:
- Latenza variabile (30-100ms)
- Jitter elevato (20-50ms)
- Perdita pacchetti occasionale
- Cambio cella con reset connessione

**Soluzione teorica:** Il protocollo VISCA non è progettato per questo ambiente. Necessario strato di adattamento con buffer, ritrasmissione selettiva, gestione stato.

---

## Sintesi Concettuale

| Aspetto | In LAN | Su VPN | Criticità |
|--------|--------|--------|-----------|
| **Latenza** | <1ms | 10-150ms | Feedback operatore |
| **Jitter** | <2ms | 5-50ms | Ordine pacchetti |
| **Perdita** | 0% | 0-1% | Comandi persi |
| **Sequence** | Consecutivo | Fuori ordine | Scarto comandi |
| **NAT** | Assente | Quasi sempre | Indirizzamento |
| **MTU** | 1500 | Frammentato | Corruzione |
| **Crittografia** | No | Sì | Overhead |

### Teorema Fondamentale di VISCA su VPN

> **Un sistema VISCA su VPN geografica non può eguagliare le prestazioni di un sistema VISCA su LAN. L'obiettivo non è la trasparenza, ma la tolleranza.**

Il controller VISCA per VPN deve essere **riprogettato** con:
- Timeout adattivi basati su RTT misurato
- Buffer di riordino lato client
- Ritrasmissione selettiva intelligente
- Feedback all'operatore sullo stato della connessione
- Riduzione automatica della velocità di movimento

Solo riconoscendo che la VPN **modifica fondamentalmente il mezzo trasmissivo** si può progettare un sistema di controllo remoto robusto.