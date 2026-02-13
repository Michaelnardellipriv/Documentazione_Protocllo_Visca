# VISCA Hardware Guide

## Connettori e Pinout

### RJ-45 (VISCA over IP)

Pin 1: TD+ (Transmit Data+)  
Pin 2: TD- (Transmit Data-)  
Pin 3: RD+ (Receive Data+)  
Pin 6: RD- (Receive Data-)  
Pin 4,5,7,8: Non utilizzati

 

### RS-232 (VISCA Seriale)

Pin 1: FG (Frame Ground)  
Pin 2: SD (Transmit Data)  
Pin 3: RD (Receive Data)  
Pin 4: RS (Request to Send)  
Pin 5: CS (Clear to Send)  
Pin 6: DR (Data Set Ready)  
Pin 7: SG (Signal Ground)  
Pin 8: ER (Data Carrier Detect)  
Pin 9: +5V (solo alcune telecamere)

 

### RS-422 (VISCA Seriale Lunga Distanza)

Pin 1: TX+ (Transmit Data+)  
Pin 2: TX- (Transmit Data-)  
Pin 3: RX+ (Receive Data+)  
Pin 4: RX- (Receive Data-)  
Pin 5: GND (Ground)

# Schemi Cablaggio

### Scenario 1: Collegamento Diretto PC-Camera (RS-232)

PC (DB9) Camera (RJ-45/DB9)  
Pin 2 (TX) → Pin 3 (RX)  
Pin 3 (RX) → Pin 2 (TX)  
Pin 5 (GND) → Pin 7 (GND)

 

### Scenario 2: Daisy Chain Multipla (RS-422)

Controller → Camera 1 → Camera 2 → Camera 3  
TX+/TX- IN/OUT IN/OUT IN  
RX+/RX- IN/OUT IN/OUT IN

 

### Scenario 3: Rete IP Switched

Controller → Switch Gigabit → Telecamere  
(Eth) (VLAN 100) (Eth)

 

## Specifiche Alimentazione

### Telecamere PTZ Standard

Voltaggio: 12V DC ±10%  
Corrente: 2.0A - 3.0A (max durante movimento)  
Connettore: Jack 5.5x2.1mm center-positive  
Potenza: 24W - 36W

 

### Telecamere PTZ Professional

Voltaggio: 24V AC o 48V PoE  
Corrente: 0.5A - 1.5A  
Standard PoE: 802.3af/at (Classe 3-4)  
Potenza: 12W - 36W

 

## Requisiti Ambientali

### Temperatura Operativa

Range: 0°C a +40°C (standard)  
Range esteso: -20°C a +50°C (outdoor)  
Gradiente max: 10°C/ora

 

### Umidità

Operativa: 20% - 80% RH (non condensa)  
Storage: 10% - 90% RH

 

### Vibrazioni e Shock

Vibrazioni: 10-55 Hz, 0.35mm amplitudine  
Shock: 100 m/s², 11ms durata

 

## Cavi Consigliati

### Ethernet (VISCA over IP)

Categoria: Cat6 o superiore  
Shield: STP (Shielded Twisted Pair)  
Lunghezza max: 100m (per segmento)  
Connettori: RJ-45 gold plated



### RS-422 (Lunga Distanza)

Tipo: 4-conductor shielded  
Gauge: 22-24 AWG  
Capacità: < 100 pF/m  
Impedenza: 100Ω  
Lunghezza max: 1200m



### Alimentazione

Gauge: 18 AWG (fino a 5m)  
16 AWG (5-10m)  
14 AWG (10-20m)  
Isolamento: Doppio isolamento


## Adattatori e Convertitori

### USB to RS-422

Chipset consigliato: FTDI FT4232H  
Velocità: Fino a 3 Mbps  
Isolamento: Opto-isolated (consigliato)  
Alimentazione: USB bus-powered



### RS-232 to RS-422

Converter: Bi-directional automatico  
Terminazione: Jumpers per 120Ω  
Alimentazione: 9-30V DC  
Isolamento: 1500V (opzionale)



### PoE Injector/Splitter

Standard: 802.3af/at compatibile  
Porte: Data + Power combinati  
Potenza: 15W/30W disponibile  
Protection: Surge protection


## Checklist Installazione Fisica

### Pre-Installazione

- [ ] Verificare supporto capacità peso
- [ ] Testare range movimento completo
- [ ] Verificare accesso cavi posteriori
- [ ] Controllare illuminazione ambiente

### Durante Installazione

- [ ] Usare strumentazione antistatica
- [ ] Non piegare cavi oltre raggio minimo
- [ ] Lasciare slack per movimenti
- [ ] Proteggere connettori da umidità

### Post-Installazione

- [ ] Testare tutti movimenti estremi
- [ ] Verificare assenza vibrazioni
- [ ] Controllare temperatura operativa
- [ ] Documentare posizione cablaggio
