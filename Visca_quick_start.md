# VISCA Quick Start — Muovi una telecamera in 5 minuti

Questa guida è pensata per chi non ha mai usato VISCA e vuole vedere subito una telecamera muoversi.

##  Collega la telecamera

- Collega la telecamera al PC tramite cavo Ethernet (stessa rete, stesso switch)
- Alimenta la telecamera (12V DC o PoE)

##  Abilita VISCA over IP

Quasi tutte le telecamere PTZ hanno un blocco di micro-interruttori (DIP switch).

1. Cerca il blocco **SETUP** sul retro o sotto la base
2. Imposta lo **Switch n. 3** sulla posizione **ON**
3. **Spegni e riaccendi** la telecamera (legge gli switch solo all'avvio)

Se non trovi gli switch, consulta il manuale della camera.

## Trova l'indirizzo IP della telecamera

**Opzione A — Software del produttore**  
Usa il tool di discovery (Sony, Panasonic, PTZOptics, ecc.)

**Opzione B — Da terminale (ARP)**  
Apri il terminale e digita:

- **Windows:** `arp -a` (cerca indirizzi con MAC di telecamere)
- **Linux/Mac:** `arp -a | grep -i "sony\|ptz"`

**Opzione C — IP predefiniti**  
Prova uno di questi (comuni su molte camere):
- `192.168.1.100`
- `192.168.0.100`
- `192.168.1.168`

##  Invia il tuo primo comando

Scarica [**Packet Sender**](https://packetsender.com/) (gratuito, multi-piattaforma).

1. Apri Packet Sender
2. Imposta:
   - **Protocollo:** UDP
   - **IP:** [l'indirizzo trovato]
   - **Porta:** `52381`
3. Nel campo **Hex**, incolla:
01 00 00 05 00 00 00 01 81 01 06 04 FF

text
4. Clicca **Send**

Se tutto funziona, la telecamera torna in posizione centrale (home).

##  Altri comandi da provare

Dopo il primo successo, prova questi (sempre con Packet Sender):

| Comando | Effetto |
|--------|---------|
| `01 00 00 05 00 00 00 02 81 01 04 07 02 FF` | Zoom In (Tele) |
| `01 00 00 05 00 00 00 03 81 01 04 07 03 FF` | Zoom Out (Wide) |
| `01 00 00 05 00 00 00 04 81 01 06 01 08 08 03 01 FF` | Movimento su/sinistra (velocità media) |

**Nota:** il Sequence Number (byte 4-7) deve incrementare a ogni invio. Negli esempi sopra è stato incrementato manualmente (`00 00 00 01`, `00 00 00 02`, ...).

## Se non funziona

- [ ] Lo switch 3 è **ON**?
- [ ] Hai **riavviato** la telecamera dopo aver cambiato lo switch?
- [ ] La telecamera risponde al ping? `ping [indirizzo IP]`
- [ ] Il firewall del PC blocca la porta `52381`? (prova a disabilitarlo temporaneamente)
- [ ] Hai usato la porta **52381** (UDP) e non TCP?

## Approfondimenti

Ora che hai visto la camera muoversi, puoi esplorare il resto della documentazione:

- [**VISCA_HOME.md**](VISCA_HOME.md) — introduzione e indice completo
- [**VISCA_SOPRA_IP.md**](VISCA_SOPRA_IP.md) — dettagli su Sequence Number e configurazione IP
- [**VISCA_GLOSSARY.md**](VISCA_GLOSSARY.md) — spiegazione di tutti i termini tecnici
- [**Guida allo Sviluppo**](Guida_allo_Sviluppo_di_un_Controller_VISCA.md) — per scrivere il tuo controller
