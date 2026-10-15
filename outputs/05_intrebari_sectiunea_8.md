# Întrebări de verificare (secțiunea 8)

## 1. Cine decide când se apelează un instrument: modelul sau agentul? Cine îl execută?

**Modelul decide, agentul execută.** Modelul primește întrebarea împreună cu lista instrumentelor și hotărăște dacă are nevoie de unul. În acest caz nu răspunde cu text, ci cu o cerere de apel (`tool_calls`: numele instrumentului și argumentele în JSON). Modelul nu execută nimic. Agentul (gazda, `agent.py`) preia cererea, o trimite prin clientul MCP la server (`tools/call`), unde rulează funcția Python, apoi pune rezultatul înapoi în conversație. În conversația noastră, la „Cât face 12 ori 12?” Gemini a decis să nu apeleze nimic, iar agentul nu a avut ce executa.

## 2. Care este rolul `tool_call_id` în istoricul conversației?

Leagă **fiecare rezultat de cererea căreia îi răspunde**. Când modelul cere mai multe instrumente în același pas (de exemplu `check_conflict` și `total_power` la întrebarea 3 din conversație), fiecare cerere are un `id` unic. Agentul adaugă fiecare rezultat ca mesaj `{"role": "tool", "tool_call_id": <id>, "content": ...}`. Fără acest identificator, modelul n-ar ști care rezultat aparține cărui apel, iar API-ul respinge de regulă un mesaj `tool` care nu corespunde unei cereri din mesajul `assistant` anterior. Este același mecanism ca `id`-ul din JSON-RPC, dar la nivelul conversației cu modelul.

## 3. Care sunt cele trei primitive MCP și cine decide să folosească fiecare?

| Primitivă | Cine decide | Rol | Exemplu |
|---|---|---|---|
| **Tools** (instrumente) | **modelul** | funcții apelabile, eventual cu efecte | `check_conflict`, `total_power` |
| **Resources** (resurse) | **aplicația** (gazda) | date doar pentru citire, identificate prin URI | `device://radiator/manual` |
| **Prompts** (șabloane) | **utilizatorul** | șabloane de prompt reutilizabile, cu argumente | `energy_review(devices)` |

## 4. De ce contează docstring-urile și adnotările de tip ale unui instrument MCP?

Pentru că **sunt singurul lucru pe care modelul îl vede** despre instrument. FastMCP transformă:
- **docstring-ul** în `description`, din care modelul înțelege *când* să folosească instrumentul;
- **adnotările de tip** (`name: str`, `hours: float`, `devices: list[str]`) în schema JSON de intrare (`inputSchema`), din care modelul înțelege *cum* să construiască argumentele.

Tot schema este folosită de server pentru **validare**. La exercițiul 4.3.3, `hours=abc` a fost respins de FastMCP/Pydantic cu `Input should be a valid number`, înainte ca funcția să ruleze. Un docstring vag sau o adnotare lipsă duce la instrumente ignorate, apelate în situații greșite sau cu argumente de tip greșit. Pentru `total_power`, modelul a trimis corect o listă tocmai pentru că schema cerea `"type": "array"`.

## 5. Ce este un conector în codul nostru și ce trei lucruri se schimbă când trecem de la Gemini la Ollama?

**Conectorul** este stratul subțire din `llm.py` (`make_client` + `create_chat`). El creează clientul către modelul de limbaj și ascunde diferențele dintre furnizori. Toți furnizorii (Gemini, Mistral, Ollama, LM Studio) expun un API compatibil OpenAI, deci folosim același client `OpenAI(...)` și același apel `chat.completions.create`. Restul agentului nu știe cu cine vorbește. `create_chat` adaugă și reîncercări cu exponential backoff pentru erori temporare (403/429/500/503).

La trecerea de la Gemini la Ollama se schimbă **trei lucruri**:
1. **adresa de bază** (`base_url`): `https://generativelanguage.googleapis.com/v1beta/openai/` → `http://localhost:11434/v1`;
2. **cheia API**: `GEMINI_API_KEY` din `.env` → nicio cheie reală (se trimite `"local"`, o valoare oarecare cerută doar de bibliotecă);
3. **numele modelului**: `gemini-3.5-flash-lite` → `qwen3:1.7b`.

Practic, schimbarea se face dintr-o singură linie din `.env`: `LLM_PROVIDER=ollama`.

## 6. De ce există `MAX_STEPS`?

Este o **limită de siguranță pentru bucla agentului**. În `ask()`, cât timp modelul răspunde cu cereri de instrumente, agentul le execută și îl întreabă din nou. Un model care cere la nesfârșit instrumente (de exemplu reîncearcă mereu același apel eșuat sau intră într-un ciclu) ar bloca agentul, ar consuma cota de cereri a cheii și ar putea genera costuri. După `MAX_STEPS = 6` iterații, agentul se oprește și întoarce „(Am atins limita de pași a agentului.)”. Limita restrânge și câte apeluri succesive poate face modelul într-un singur răspuns.

## 7. De ce nu punem cheia API în cod și ce facem dacă am expus-o din greșeală?

**De ce nu în cod:** cheia identifică proiectul nostru la furnizor, iar consumul se contorizează pe ea. Oricine o are ne poate folosi cota sau, pe un cont cu facturare, ne poate genera costuri. Codul ajunge ușor în locuri publice (GitHub, capturi de ecran, mesaje, forumuri), iar istoricul Git păstrează cheia chiar și după ce o ștergem din fișier. De aceea cheia stă în `.env`, citit cu `python-dotenv`, iar `.env` e trecut în `.gitignore` înainte de primul commit. În repo urcăm doar `.env.example`, fără valori. Același lucru e valabil pentru ieșirile predate: `smoke_test.py` afișează furnizorul, modelul și adresa, dar niciodată cheia.

**Dacă am expus-o:** o **revocăm/ștergem imediat** din consola furnizorului (AI Studio → API keys) și **generăm una nouă**, pe care o punem doar în `.env`. Simpla ștergere din cod sau un commit nou nu ajută, pentru că cheia rămâne în istoric și poate fi deja copiată de roboții care scanează GitHub. Apoi verificăm în consolă dacă a existat consum neobișnuit.
