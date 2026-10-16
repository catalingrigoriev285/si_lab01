"""Interfață web pentru agent. Rulare: python web.py, apoi http://127.0.0.1:5000"""
import asyncio
import os
import threading
import uuid

from flask import Flask, jsonify, request, session
from openai import APIConnectionError, APIStatusError

from agent import SYSTEM_PROMPT, Agent

TIMEOUT = 120  # secunde de așteptare pentru un răspuns

# Agentul ține deschisă conexiunea stdio cu server.py, deci îl pornim o singură
# dată, într-o buclă asyncio care rulează permanent într-un fir separat.
loop = asyncio.new_event_loop()
threading.Thread(target=loop.run_forever, daemon=True).start()

async def start_agent() -> Agent:
    agent = Agent()
    await agent.__aenter__()
    return agent

agent = asyncio.run_coroutine_threadsafe(start_agent(), loop).result()
lock = asyncio.Lock()  # un singur Agent: întrebările se procesează pe rând
histories = {}  # istoricul conversației pentru fiecare sesiune (cookie)

async def ask(sid: str, text: str) -> str:
    """Pune istoricul sesiunii în Agent, întreabă, apoi salvează istoricul."""
    async with lock:
        agent.messages = histories.setdefault(
            sid, [{"role": "system", "content": SYSTEM_PROMPT}]
        )
        return await agent.ask(text)

app = Flask(__name__)
app.secret_key = os.urandom(16)

PAGE = """<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#F9F9F9">
<title>Asistent clădire</title>
<style>
  :root {
    --blue: #007AFF;
    --red: #FF3B30;
    --label: #000;
    --label-2: rgba(60, 60, 67, .6);
    --label-3: rgba(60, 60, 67, .3);
    --separator: rgba(60, 60, 67, .29);
    --bg: #FFFFFF;
    --bg-grouped: #F2F2F7;
    --bar: #F9F9F9;
    --fill: #E9E9EB;
    --pressed: #D1D1D6;
  }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body { height: 100%; margin: 0; }
  body {
    background: var(--bg-grouped);
    color: var(--label);
    font: 17px/1.3 -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", system-ui, Roboto, "Helvetica Neue", Arial, sans-serif;
    letter-spacing: -.01em;
    -webkit-font-smoothing: antialiased;
  }
  button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }

  .app {
    display: flex; flex-direction: column; height: 100%;
    max-width: 760px; margin: 0 auto; background: var(--bg);
    box-shadow: 0 0 0 .5px var(--separator);
  }

  /* Bara de navigare */
  .nav {
    display: grid; grid-template-columns: 44px 1fr 44px; align-items: center;
    padding: 10px 12px 8px; background: var(--bar);
    border-bottom: .5px solid var(--separator);
  }
  .contact { display: flex; flex-direction: column; align-items: center; gap: 4px; min-width: 0; }
  .avatar {
    width: 44px; height: 44px; border-radius: 50%;
    display: grid; place-items: center; background: var(--blue); color: #fff;
  }
  .avatar svg { width: 24px; height: 24px; }
  .contact h1 { margin: 0; font-size: 13px; font-weight: 500; letter-spacing: 0; }
  .contact p {
    margin: 0; max-width: 100%; font-size: 11px; color: var(--label-2);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .icon-btn {
    width: 44px; height: 44px; display: grid; place-items: center;
    color: var(--blue); border-radius: 10px;
  }
  .icon-btn { transition: background .15s; }
  .icon-btn:hover { background: rgba(0, 122, 255, .1); }
  .icon-btn:active { opacity: .35; }
  .icon-btn svg { width: 24px; height: 24px; }

  /* Mesaje */
  .log { flex: 1; overflow-y: auto; padding: 16px 16px 12px; }
  .stamp { text-align: center; font-size: 11px; color: var(--label-2); margin: 0 0 12px; }
  .stamp b { font-weight: 600; }
  .row { display: flex; margin-top: 10px; animation: pop .22s ease-out both; }
  .row.me { justify-content: flex-end; }
  @keyframes pop { from { opacity: 0; transform: translateY(6px) scale(.97); } }

  .bubble {
    --b: var(--fill);
    position: relative; max-width: 75%;
    padding: 8px 13px; border-radius: 18px;
    background: var(--b); color: var(--label);
    white-space: pre-wrap; overflow-wrap: anywhere;
  }
  .bubble.me { --b: var(--blue); color: #fff; }
  .bubble.err { --b: #FFE5E3; color: #D70015; }
  /* coada bulei, ca în Messages */
  .bubble::before, .bubble::after { content: ""; position: absolute; bottom: 0; height: 20px; }
  .bubble.them::before, .bubble.err::before { left: -7px; width: 20px; background: var(--b); border-bottom-right-radius: 16px; }
  .bubble.them::after, .bubble.err::after { left: -10px; width: 10px; background: var(--bg); border-bottom-right-radius: 10px; }
  .bubble.me::before { right: -7px; width: 20px; background: var(--b); border-bottom-left-radius: 16px; }
  .bubble.me::after { right: -10px; width: 10px; background: var(--bg); border-bottom-left-radius: 10px; }

  .typing { display: flex; gap: 4px; padding: 13px 14px; }
  .typing i { width: 8px; height: 8px; border-radius: 50%; background: #8E8E93; animation: blink 1.4s infinite both; }
  .typing i:nth-child(2) { animation-delay: .2s; }
  .typing i:nth-child(3) { animation-delay: .4s; }
  @keyframes blink { 0%, 80%, 100% { opacity: .3; } 40% { opacity: 1; } }

  /* Ecran gol: listă grupată */
  .empty { min-height: 100%; display: flex; flex-direction: column; justify-content: center; padding: 24px 4px; }
  .empty.hidden { display: none; }
  .hero { text-align: center; margin-bottom: 28px; }
  .hero h2 { margin: 0 0 4px; font-size: 22px; font-weight: 700; letter-spacing: -.02em; }
  .hero p { margin: 0; font-size: 15px; color: var(--label-2); }
  .section-title { margin: 0 16px 6px; font-size: 13px; color: var(--label-2); text-transform: uppercase; letter-spacing: 0; }
  .list { background: var(--bg-grouped); border-radius: 10px; overflow: hidden; }
  .hint {
    width: 100%; display: flex; align-items: center; gap: 12px;
    padding: 11px 16px; text-align: left; position: relative;
    transition: background .15s;
  }
  .hint + .hint::before {
    content: ""; position: absolute; top: 0; left: 16px; right: 0;
    border-top: .5px solid var(--separator);
  }
  .hint:hover { background: var(--fill); }
  .hint:hover .chev { color: var(--label-2); }
  .hint:active { background: var(--pressed); }
  .hint span { flex: 1; }
  .hint .chev { flex: none; width: 8px; height: 14px; color: var(--label-3); transition: color .15s; }

  /* Bara de scriere */
  .composer { background: var(--bar); border-top: .5px solid var(--separator); padding: 8px 12px calc(8px + env(safe-area-inset-bottom)); }
  .field {
    display: flex; align-items: flex-end; gap: 6px;
    background: var(--bg); border: 1px solid #C6C6C8; border-radius: 20px;
    padding: 3px 3px 3px 14px;
  }
  .field textarea {
    flex: 1; max-height: 160px; resize: none; border: 0; outline: 0; background: transparent;
    font: inherit; color: inherit; padding: 5px 0; line-height: 22px;
  }
  .field textarea::placeholder { color: var(--label-3); }
  .send {
    flex: none; width: 30px; height: 30px; border-radius: 50%;
    display: grid; place-items: center; background: var(--blue); color: #fff;
    transition: background .15s, transform .15s;
  }
  .send:not(:disabled):hover { background: #0062CC; transform: scale(1.06); }
  .send svg { width: 16px; height: 16px; }
  .send:active { filter: brightness(.85); }
  .send:disabled { background: #C7C7CC; cursor: not-allowed; }
  .footnote { margin: 6px 0 0; text-align: center; font-size: 11px; color: var(--label-2); }
</style>
</head>
<body>
<div class="app">

  <header class="nav">
    <span></span>
    <div class="contact">
      <div class="avatar" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M5 21V5a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v4h1a2 2 0 0 1 2 2v10h1v1H4v-1h1Zm3-14v2h2V7H8Zm4 0v2h2V7h-2Zm-4 4v2h2v-2H8Zm4 0v2h2v-2h-2Zm-4 4v2h2v-2H8Zm4 0v2h2v-2h-2Zm4-2v2h1v-2h-1Zm0 4v2h1v-2h-1Z"/></svg>
      </div>
      <h1>Asistent clădire inteligentă</h1>
      <p>{provider} · {model}</p>
    </div>
    <button id="reset" class="icon-btn" title="Conversație nouă" aria-label="Conversație nouă">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5"/><path d="M17.6 3.4a2 2 0 0 1 2.9 2.9L12 14.8l-3.6.8.8-3.6 8.4-8.6Z"/></svg>
    </button>
  </header>

  <main id="log" class="log">
    <div id="empty" class="empty">
      <div class="hero">
        <h2>Cu ce te pot ajuta?</h2>
        <p>Întreabă despre dispozitive, conflicte sau consum.</p>
      </div>
      <p class="section-title">Sugestii</p>
      <div class="list">
        <button class="hint">
          <span>Ce dispozitive există în clădire?</span>
          <svg class="chev" viewBox="0 0 8 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m1 1 6 6-6 6"/></svg>
        </button>
        <button class="hint">
          <span>Există conflicte între dispozitive?</span>
          <svg class="chev" viewBox="0 0 8 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m1 1 6 6-6 6"/></svg>
        </button>
        <button class="hint">
          <span>Cât consumă radiatorul?</span>
          <svg class="chev" viewBox="0 0 8 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m1 1 6 6-6 6"/></svg>
        </button>
      </div>
    </div>
  </main>

  <form id="f" class="composer">
    <div class="field">
      <textarea id="q" rows="1" placeholder="Mesaj" autofocus></textarea>
      <button id="send" class="send" aria-label="Trimite">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 13V3M3.5 7.5 8 3l4.5 4.5"/></svg>
      </button>
    </div>
    <p class="footnote">Enter trimite · Shift+Enter rând nou</p>
  </form>
</div>

<script>
const log = document.getElementById("log"), q = document.getElementById("q");
const send = document.getElementById("send"), empty = document.getElementById("empty");

function add(kind, text) {
  if (!empty.classList.contains("hidden")) {
    empty.classList.add("hidden");
    const stamp = document.createElement("p");
    stamp.className = "stamp";
    stamp.innerHTML = "<b>Astăzi</b> " + new Date().toLocaleTimeString("ro-RO", {hour: "2-digit", minute: "2-digit"});
    log.appendChild(stamp);
  }
  const row = document.createElement("div");
  row.className = "row " + kind;
  const bubble = document.createElement("div");
  bubble.className = "bubble " + kind;
  if (text === null) {
    bubble.classList.add("typing");
    bubble.innerHTML = "<i></i><i></i><i></i>";
  } else {
    bubble.textContent = text;
  }
  row.appendChild(bubble); log.appendChild(row);
  log.scrollTop = log.scrollHeight;
  return bubble;
}

function fill(bubble, kind, text) {
  bubble.className = "bubble " + kind;
  bubble.textContent = text;
  log.scrollTop = log.scrollHeight;
}

async function askQuestion(text) {
  add("me", text);
  const bubble = add("them", null);
  send.disabled = true;
  try {
    const r = await fetch("/ask", {method: "POST", headers: {"Content-Type": "application/json"},
                                   body: JSON.stringify({question: text})});
    const data = await r.json();
    data.error ? fill(bubble, "err", data.error) : fill(bubble, "them", data.answer);
  } catch (err) {
    fill(bubble, "err", "Serverul web nu răspunde.");
  } finally {
    send.disabled = false; q.focus();
  }
}

document.getElementById("f").onsubmit = (e) => {
  e.preventDefault();
  const text = q.value.trim();
  if (!text || send.disabled) return;
  q.value = ""; q.style.height = "";
  askQuestion(text);
};
q.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); document.getElementById("f").requestSubmit(); }
});
q.addEventListener("input", () => { q.style.height = ""; q.style.height = q.scrollHeight + "px"; });
document.querySelectorAll(".hint").forEach((b) => b.onclick = () => askQuestion(b.querySelector("span").textContent));
document.getElementById("reset").onclick = async () => {
  await fetch("/reset", {method: "POST"});
  log.replaceChildren(empty); empty.classList.remove("hidden"); q.focus();
};
</script>
</body>
</html>"""

def session_id() -> str:
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
    return session["sid"]

@app.get("/")
def index():
    session_id()
    return PAGE.replace("{provider}", agent.provider).replace("{model}", agent.model)

@app.post("/ask")
def ask_route():
    text = ((request.get_json(silent=True) or {}).get("question") or "").strip()
    if not text:
        return jsonify(error="Întrebarea este goală."), 400
    future = asyncio.run_coroutine_threadsafe(ask(session_id(), text), loop)
    try:
        return jsonify(answer=future.result(timeout=TIMEOUT))
    except APIStatusError as e:
        return jsonify(error=f"Eroare HTTP {e.status_code}: {str(e.body or e.message)[:200]}"), 502
    except APIConnectionError:
        return jsonify(error="Nu mă pot conecta la model (server oprit sau fără internet)."), 502
    except TimeoutError:
        future.cancel()
        return jsonify(error="Modelul nu a răspuns la timp."), 504

@app.post("/reset")
def reset_route():
    histories.pop(session_id(), None)
    return jsonify(ok=True)

if __name__ == "__main__":
    # fără reloader: altfel Flask ar importa modulul de două ori (două agenți)
    app.run(debug=False, use_reloader=False)
