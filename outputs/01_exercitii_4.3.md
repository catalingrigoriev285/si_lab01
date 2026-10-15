# Exercițiile din secțiunea 4.3 (MCP Inspector)

Rezultatele de mai jos sunt reale. Le-am obținut cu serverul din `server.py`, apelat prin MCP Inspector (`npx @modelcontextprotocol/inspector --cli python server.py ...`). Interfața web arată exact aceleași răspunsuri JSON.

> **Captura de ecran din Inspector** (cerință obligatorie): trebuie făcută manual din interfața web și salvată ca `outputs/inspector_apel_reusit.png`. Pașii sunt descriși la finalul acestui fișier.

---

## 1. Instrumente: `list_devices` și `get_device_info`

**`list_devices`** întoarce lista sortată a dispozitivelor:

```json
"content": [{ "type": "text", "text": "[\"aer_conditionat\",\"jaluzele\",\"lampa_led\",\"radiator\",\"senzor_miscare\",\"ventilatie\"]" }],
"isError": false
```

**`get_device_info(name="radiator")`** întoarce un dicționar cu datele dispozitivului:

```json
"structuredContent": {
  "nume": "radiator",
  "categorie": "încălzire",
  "putere_w": 1500,
  "note": "Controlat de termostatul camerei."
},
"isError": false
```

**`get_device_info(name="frigider")`** (dispozitiv inexistent):

```json
"structuredContent": {
  "eroare": "Dispozitiv necunoscut: frigider",
  "cunoscute": ["aer_conditionat", "jaluzele", "lampa_led", "radiator", "senzor_miscare", "ventilatie"]
},
"isError": false
```

**Răspuns.** În ambele cazuri serverul întoarce **o dată obișnuită**, nu o excepție (`isError: false`). Pentru frigider, eroarea este codificată ca date: un câmp `eroare` și lista dispozitivelor `cunoscute`. Alegerea e intenționată. Modelul primește rezultatul ca pe orice alt răspuns, înțelege că numele e greșit și poate reîncerca cu un nume valid din listă. O excepție ar opri apelul și nu i-ar spune modelului ce variante are.

---

## 2. Conflicte: `check_conflict`

| Apel | Rezultat |
|---|---|
| `check_conflict("radiator", "aer_conditionat")` | `RIDICAT - încălzire și răcire simultană, consum inutil.` |
| `check_conflict("aer_conditionat", "radiator")` (inversat) | `RIDICAT - încălzire și răcire simultană, consum inutil.` |
| `check_conflict("lampa_led", "jaluzele")` (fără conflict) | `Niciun conflict înregistrat în setul de date de test.` |

**Răspuns.** Da, rezultatul este **simetric**. Cheile din dicționarul `CONFLICTE` sunt de tip `frozenset`, adică mulțimi neordonate și imuabile. `frozenset({"radiator", "aer_conditionat"})` și `frozenset({"aer_conditionat", "radiator"})` sunt egale și au același hash, deci găsesc aceeași intrare din dicționar. Dacă cheia ar fi fost un tuplu `(a, b)`, ordinea ar fi contat și apelul inversat n-ar fi găsit conflictul. Pentru o relație simetrică prin natura ei („A intră în conflict cu B"), `frozenset` este structura potrivită.

---

## 3. Schema de intrare: `estimate_energy`

**`estimate_energy(name="radiator", hours=2)`**:

```json
"structuredContent": { "nume": "radiator", "ore": 2, "energie_kwh": 3 },
"isError": false
```

(1500 W × 2 h / 1000 = 3 kWh.) În interfața web, Inspector construiește formularul din `inputSchema`. Adnotarea `hours: float` devine `"type": "number"`, deci câmpul `hours` este numeric, iar `name: str` devine un câmp text.

**Din linia de comandă, cu `--tool-arg hours=abc`:**

```
WARNING  Invalid arguments for tool 'estimate_energy': {'error_count': 1, 'error_types': ['float_type']}
{
  "content": [{
    "type": "text",
    "text": "1 validation error for call[estimate_energy]\nhours\n  Input should be a valid number [type=float_type, input_value=None, input_type=NoneType]\n    For further information visit https://errors.pydantic.dev/2.14/v/float_type"
  }],
  "isError": true
}
{"error":{"code":"tool_is_error","message":"Tool 'estimate_energy' returned isError:true."}}
```

**Cine a produs eroarea?** **Serverul**, mai exact stratul de validare din FastMCP (Pydantic). Funcția `estimate_energy` nici nu ajunge să ruleze. FastMCP verifică argumentele primite față de schema generată din adnotările de tip, vede că `hours` nu este un număr și întoarce un rezultat cu `isError: true` și mesajul Pydantic `Input should be a valid number`. Ultima linie (`tool_is_error`) o adaugă doar Inspector CLI, ca să semnaleze că instrumentul a raportat eroare.

Detaliu observat: `input_value=None` arată că Inspector a încercat să convertească `abc` în număr după schemă, iar valoarea invalidă a ajuns la server ca `null`. Validarea propriu-zisă și mesajul vin însă de la server.

Diferența față de exercițiul 1:
- **frigider**: eroare logică, întoarsă *de cod* ca date (`isError: false`);
- **hours=abc**: eroare de tip, întoarsă *de framework* înainte de execuție (`isError: true`).

---

## 4. Resurse: `device://radiator/manual`

```json
{
  "contents": [{
    "uri": "device://radiator/manual",
    "mimeType": "text/plain",
    "text": "radiator: încălzire. Controlat de termostatul camerei."
  }]
}
```

Resursa apare în Inspector la **Resource Templates**, pentru că URI-ul conține parametrul `{name}`. După completarea `name = radiator`, se citește manualul de o linie. Resursa e doar pentru citire și e identificată prin URI, nu printr-un nume de funcție.

---

## 5. Șabloane de prompt: `energy_review`

Randat cu `devices = "radiator, aer_conditionat"`:

```json
{
  "description": "Șablon de prompt: cere unui LLM să analizeze o listă de dispozitive.",
  "messages": [{
    "role": "user",
    "content": {
      "type": "text",
      "text": "Analizează această listă de dispozitive: radiator, aer_conditionat. Folosește instrumentele pentru a verifica conflictele și a estima consumul."
    }
  }]
}
```

**Cine îl folosește?** **Utilizatorul.** Promptul este un șablon pe care utilizatorul îl alege explicit (într-o gazdă MCP apare de obicei ca o comandă de tip „/energy_review”). Rezultatul este un mesaj cu `role: "user"`, gata de trimis modelului. Se potrivește cu tabelul din secțiunea 1.2:

| Primitivă | Cine decide |
|---|---|
| Tools | modelul |
| Resources | aplicația (gazda) |
| **Prompts** | **utilizatorul** |

Modelul nici nu vede prompturile: agentul nostru îi trimite doar lista de *instrumente* (`list_tools`), nu și pe cea de prompturi.

---

## 6. Protocol: schimbul JSON-RPC pentru `check_conflict`

Mesajele capturate pe stdio pentru apelul inversat de la exercițiul 2. Înaintea lor are loc handshake-ul `initialize` / `notifications/initialized`.

**Cererea (client → server):**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "check_conflict",
    "arguments": { "device_a": "aer_conditionat", "device_b": "radiator" }
  }
}
```

**Răspunsul (server → client):**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{ "type": "text", "text": "RIDICAT - încălzire și răcire simultană, consum inutil." }],
    "structuredContent": { "result": "RIDICAT - încălzire și răcire simultană, consum inutil." },
    "isError": false
  }
}
```

- **Metoda JSON-RPC:** `tools/call`. Numele instrumentului nu este metoda, ci parametrul `params.name`.
- **Argumentele:** `params.arguments` = `{"device_a": "aer_conditionat", "device_b": "radiator"}`.
- **Rezultatul:** `result.content[0].text` (textul pentru model), `result.structuredContent` (aceeași valoare, structurată) și `result.isError = false`.
- Câmpul `id: 1` leagă răspunsul de cerere. Mesajul `notifications/initialized` nu are `id`, pentru că este o notificare și nu așteaptă răspuns.

---

## 7. Modificarea serverului

Față de varianta din fișa de laborator, în `server.py` am adăugat:

```python
# al șaselea dispozitiv, în DEVICES
"senzor_miscare": {"categorie": "securitate", "putere_w": 5, "note": "Detectează mișcarea în cameră."},

# conflict nou, în CONFLICTE
frozenset({"senzor_miscare", "jaluzele"}): "MEDIU - mișcarea jaluzelelor poate fi detectată de senzorul de mișcare.",
```

După repornirea conexiunii în Inspector (comutatorul oprit, apoi pornit):

- `list_devices` întoarce 6 dispozitive, inclusiv `senzor_miscare` (vezi exercițiul 1);
- `check_conflict("senzor_miscare", "jaluzele")` → `MEDIU - mișcarea jaluzelelor poate fi detectată de senzorul de mișcare.`

Repornirea este necesară pentru că Inspector pornește `server.py` ca proces copil. Datele sunt încărcate în memorie la pornire, deci modificările din fișier se văd doar într-un proces nou.

---

## Cum se face captura de ecran din Inspector

1. Cu mediul virtual activat: `npx @modelcontextprotocol/inspector python server.py`
2. Deschideți adresa cu token afișată în terminal și porniți conexiunea cu comutatorul serverului.
3. Tab **Tools** → `total_power` (sau `check_conflict`) → completați argumentele → **Run Tool**.
4. Faceți captura când se vede rezultatul cu `isError: false` și salvați-o ca `outputs/inspector_apel_reusit.png`.
