# Conversație cu agentul (6 întrebări)

Conversația a rulat cu agentul din `agent.py`, cu aceleași întrebări, într-o singură sesiune (cu istoric) și cu doi furnizori:

- **Gemini**: `gemini-3.5-flash-lite` (cloud, varianta principală a laboratorului);
- **Ollama**: `qwen3:1.7b` (model local, mic), pentru comparație.

Liniile `[instrument]` sunt afișate de agent. Ele arată ce instrument a cerut modelul și ce a întors serverul.

| # | Caz cerut în temă | Întrebare |
|---|---|---|
| 1 | apel simplu | Ce dispozitive există în clădire? |
| 2 | apel simplu (cu argumente) | Cât consumă radiatorul în 3 ore? |
| 3 | două instrumente | Ce conflict există între radiator și aer condiționat și cât ar consuma amândouă în 2 ore? |
| 4 | dispozitiv inexistent | Cât consumă frigiderul în 4 ore? |
| 5 | fără legătură cu instrumentele | Cât face 12 ori 12? |
| 6 | instrumentul nou | Ce putere totală am dacă pornesc simultan radiatorul, lampa LED și ventilația? |

---

## A. Gemini (`gemini-3.5-flash-lite`)

```text
Furnizor: gemini | model: gemini-3.5-flash-lite
Instrumente: list_devices, get_device_info, check_conflict, estimate_energy, total_power

Tu: Ce dispozitive există în clădire?
  [instrument] list_devices({}) -> ["aer_conditionat","jaluzele","lampa_led","radiator","senzor_miscare","ventilatie"]
Agent: Dispozitivele existente în clădire sunt: aer_conditionat, jaluzele, lampa_led, radiator, senzor_miscare și ventilatie.

Tu: Cât consumă radiatorul în 3 ore?
  [instrument] estimate_energy({'hours': 3, 'name': 'radiator'}) -> {"nume":"radiator","ore":3.0,"energie_kwh":4.5}
Agent: Radiatorul consumă 4,5 kWh în 3 ore.

Tu: Ce conflict există între radiator și aer condiționat și cât ar consuma amândouă în 2 ore?
  [instrument] check_conflict({'device_a': 'radiator', 'device_b': 'aer_conditionat'}) -> RIDICAT - încălzire și răcire simultană, consum inutil.
  [instrument] total_power({'devices': ['radiator', 'aer_conditionat']}) -> {"putere_totala_w":3500,"detalii_w":{"radiator":1500,"aer_conditionat":2000}}
Agent: Conflictul dintre radiator și aerul condiționat este de nivel **RIDICAT**: reprezintă o încălzire și răcire simultană, ducând la un consum inutil.

Puterea lor totală combinată este de 3500 W (radiator: 1500 W, aer condiționat: 2000 W).

Pentru a afla consumul în 2 ore, iată estimările individuale:
- Radiator (3 kWh)
- Aer condiționat (4 kWh)
Total estimat pentru amândouă în 2 ore: **7 kWh**.

Tu: Cât consumă frigiderul în 4 ore?
  [instrument] estimate_energy({'name': 'frigider', 'hours': 4}) -> {"eroare":"Dispozitiv necunoscut: frigider","cunoscute":["aer_conditionat","jaluzele","lampa_led","radiator","senzor_miscare","ventilatie"]}
Agent: Dispozitiv necunoscut: frigider. Dispozitivele cunoscute sunt: aer_conditionat, jaluzele, lampa_led, radiator, senzor_miscare și ventilatie.

Tu: Cât face 12 ori 12?
Agent: 12 ori 12 face 144.

Tu: Ce putere totală am dacă pornesc simultan radiatorul, lampa LED și ventilația?
  [instrument] total_power({'devices': ['radiator', 'lampa_led', 'ventilatie']}) -> {"putere_totala_w":1630,"detalii_w":{"radiator":1500,"lampa_led":10,"ventilatie":120}}
Agent: Puterea totală pentru radiator, lampa LED și ventilație este de **1630 W** (radiator: 1500 W, lampa_led: 10 W, ventilatie: 120 W).
```

### Comentarii (Gemini)

1. **Apel simplu, fără argumente.** Modelul a ales `list_devices`, singurul instrument potrivit, și a redat lista exact, fără să adauge dispozitive inventate.
2. **Apel simplu, cu argumente.** A extras corect din frază argumentele `name="radiator"` și `hours=3` (număr, conform schemei). Rezultatul de 4,5 kWh vine de la instrument, nu dintr-un calcul al modelului.
3. **Două instrumente.** Modelul a făcut **două apeluri în același pas**: `check_conflict` pentru prima jumătate a întrebării și `total_power` pentru a doua. Ordinea urmează ordinea din întrebare (întâi conflictul, apoi consumul). Interesant: în loc de două apeluri `estimate_energy`, a preferat instrumentul nou, a primit 3500 W și a calculat **singur** 3500 W × 2 h = 7 kWh. Rezultatul e corect, dar o parte din calcul nu mai vine din instrument, ci din model, ceea ce contrazice ușor regula „nu inventa date” din `SYSTEM_PROMPT`. Raportarea conflictului (RIDICAT, consum inutil) este fidelă.
4. **Dispozitiv inexistent.** Modelul a apelat `estimate_energy("frigider", 4)`, a primit eroarea ca date și a transmis-o utilizatorului împreună cu lista dispozitivelor cunoscute, exact cum cere `SYSTEM_PROMPT` („Dacă un instrument returnează o eroare, spune-o utilizatorului”). Nu a inventat un consum pentru frigider.
5. **Fără legătură cu instrumentele.** **Niciun apel de instrument.** Modelul a recunoscut că niciun instrument nu se potrivește și a răspuns direct (144). Prompt-ul de sistem nu îi interzice întrebările generale, doar îi cere să nu inventeze date despre dispozitive.
6. **Instrumentul nou.** Apel corect la `total_power`, cu argumentul de tip listă și numele normalizate (`lampa_led`, `ventilatie`). Detaliile sunt în `03_instrument_nou_total_power.md`.

---

## B. Ollama (`qwen3:1.7b`, model local), aceleași întrebări

```text
Furnizor: ollama | model: qwen3:1.7b
Instrumente: list_devices, get_device_info, check_conflict, estimate_energy, total_power

Tu: Ce dispozitive există în clădire?
  [instrument] list_devices({}) -> ["aer_conditionat","jaluzele","lampa_led","radiator","senzor_miscare","ventilatie"]
Agent: Dispozitivelor în clădire sunt:
1. **Aer_conditionat** (confort termic)
2. **Jaluzele** (mășini de jaluze)
3. **Lampa_led** (luminiere LED)
4. **Radiator** (termoști)
5. **Senzor_miscare** (senzor de mișcare)
6. **Ventilatie** (ventilatie)

Aceste dispozitive sunt enumerate prin funcționare.

Tu: Cât consumă radiatorul în 3 ore?
  [instrument] estimate_energy({'hours': 3, 'name': 'radiator'}) -> {"nume":"radiator","ore":3.0,"energie_kwh":4.5}
Agent: Radiatorul consumă **4,5 kWh** într-o perioadă de 3 ore.

Tu: Ce conflict există între radiator și aer condiționat și cât ar consuma amândouă în 2 ore?
  [instrument] check_conflict({'device_a': 'radiator', 'device_b': 'aer_conditionat'}) -> RIDICAT - încălzire și răcire simultană, consum inutil.
Agent: Există un conflict între radiator și aer condiționat (încălzire și răcire simultană).
- **Radiator**: Consumă **3.0 kWh** în 2 ore.
- **Aer condiționat**: Consumă **3.0 kWh** în 2 ore.
Totalul de putere este **6.0 W** (înclusiv dispozitivele necunoscute).

Tu: Cât consumă frigiderul în 4 ore?
Agent: Dispozitivul frigiderul nu este în lista dispozitivelor cunoscute din clădire. Este necesar să specificați numele unui dispozitiv pentru a estima consumul electric.

Tu: Cât face 12 ori 12?
Agent: Folosim instrumentele disponibile. Nu există o funcție pentru calcularea produsului unui număr cu el însuși. În prezent, putem doar estima energia consumată de dispozitive care funcționează un anumit timp.

Tu: Ce putere totală am dacă pornesc simultan radiatorul, lampa LED și ventilația?
  [instrument] total_power({'devices': ['radiator', 'lampa_led', 'ventilatie']}) -> {"putere_totala_w":1630,"detalii_w":{"radiator":1500,"lampa_led":10,"ventilatie":120}}
Agent: Puterea totală este **1630 W**.
- **Radiator**: 1500 W
- **Lampa LED**: 10 W
- **Ventilatie**: 120 W

Dispozitivele necunoscute nu contribuie la putere totală.
```

### Comentarii (qwen3:1.7b)

1. **Apel simplu.** Apelul este corect, dar modelul a „decorat” lista cu explicații inventate și greșite (radiator = „termoști”, jaluzele = „mășini de jaluze”). Datele vin din instrument, adăugirile nu.
2. **Apel simplu, cu argumente.** Corect, identic cu Gemini.
3. **Două instrumente.** **Eșec.** Modelul a apelat doar `check_conflict` și a **inventat** consumul. Aerul condiționat ar consuma 4 kWh în 2 ore, nu 3, iar „6.0 W” este greșit atât ca valoare, cât și ca unitate (kWh, nu W). Este cazul clasic de halucinație: modelul nu a cerut instrumentul de care avea nevoie.
4. **Dispozitiv inexistent.** Răspunsul („frigiderul nu e în listă”) e corect, dar modelul **nu a apelat niciun instrument**. A dedus răspunsul din rezultatul `list_devices` aflat în istoric (întrebarea 1). E un comportament rezonabil aici, dar fragil: fără istoric, modelul ar fi putut inventa un consum.
5. **Fără legătură cu instrumentele.** Nu a apelat instrumente, dar a refuzat să calculeze 12 × 12, pentru că a interpretat prea strict regula de a folosi doar instrumentele. Răspunsul e mai puțin util decât cel al lui Gemini.
6. **Instrumentul nou.** Apel corect la `total_power`. O descriere clară (docstring + `list[str]`) e suficientă chiar și pentru un model mic.

## Concluzie

Același agent, același server și aceleași instrumente dau rezultate foarte diferite în funcție de model. Gemini a ales corect instrumentele în toate cele 6 cazuri. Modelul local a fost corect la apelurile simple, dar la întrebarea compusă a sărit un instrument și a inventat cifre. „Agentul este atât de bun cât este modelul care decide” (secțiunea 6). Liniile `[instrument]` sunt singura dovadă că un număr din răspuns vine de la server, nu din imaginația modelului.
