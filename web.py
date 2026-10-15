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
<html lang="ro" class="h-full">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Asistent clădire</title>
<script src="https://cdn.tailwindcss.com/3.4.16"></script>
<style>
  @keyframes blink { 0%, 80%, 100% { opacity: .2 } 40% { opacity: 1 } }
  .dot { animation: blink 1.4s infinite both; }
  .dot:nth-child(2) { animation-delay: .2s; }
  .dot:nth-child(3) { animation-delay: .4s; }
</style>
</head>
<body class="h-full bg-slate-100 text-slate-800 dark:bg-slate-950 dark:text-slate-100">
<div class="mx-auto flex h-full max-w-3xl flex-col">

  <header class="flex items-center gap-3 border-b border-slate-200 bg-white/80 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
    <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-xl text-white shadow">🏢</div>
    <div class="min-w-0 flex-1">
      <h1 class="font-semibold leading-tight">Asistent clădire inteligentă</h1>
      <p class="truncate text-xs text-slate-500 dark:text-slate-400">{provider} · {model}</p>
    </div>
    <button id="reset" class="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800">
      Conversație nouă
    </button>
  </header>

  <main id="log" class="flex-1 space-y-4 overflow-y-auto px-4 py-6">
    <div id="empty" class="flex h-full flex-col items-center justify-center text-center">
      <div class="mb-3 text-5xl">💬</div>
      <h2 class="text-lg font-semibold">Cu ce te pot ajuta?</h2>
      <p class="mb-5 text-sm text-slate-500 dark:text-slate-400">Întreabă despre dispozitive, conflicte sau consum.</p>
      <div class="flex flex-wrap justify-center gap-2">
        <button class="hint rounded-full border border-slate-300 bg-white px-4 py-2 text-sm hover:border-indigo-400 hover:text-indigo-600 dark:border-slate-700 dark:bg-slate-900">Ce dispozitive există în clădire?</button>
        <button class="hint rounded-full border border-slate-300 bg-white px-4 py-2 text-sm hover:border-indigo-400 hover:text-indigo-600 dark:border-slate-700 dark:bg-slate-900">Există conflicte între dispozitive?</button>
        <button class="hint rounded-full border border-slate-300 bg-white px-4 py-2 text-sm hover:border-indigo-400 hover:text-indigo-600 dark:border-slate-700 dark:bg-slate-900">Cât consumă radiatorul?</button>
      </div>
    </div>
  </main>

  <form id="f" class="border-t border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
    <div class="flex items-end gap-2 rounded-2xl border border-slate-300 bg-slate-50 p-2 focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-800">
      <textarea id="q" rows="1" placeholder="Scrie o întrebare…" autofocus
        class="max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 outline-none placeholder:text-slate-400"></textarea>
      <button id="send" class="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50">
        Trimite
      </button>
    </div>
    <p class="mt-1.5 text-center text-xs text-slate-400">Enter trimite · Shift+Enter rând nou</p>
  </form>
</div>

<script>
const log = document.getElementById("log"), q = document.getElementById("q");
const send = document.getElementById("send"), empty = document.getElementById("empty");
const BUBBLE = {
  tu: "ml-auto bg-indigo-600 text-white rounded-br-md",
  agent: "bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-bl-md",
  err: "bg-red-50 text-red-700 border border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-900 rounded-bl-md",
};

function add(kind, text) {
  empty.classList.add("hidden");
  const row = document.createElement("div");
  row.className = "flex " + (kind === "tu" ? "justify-end" : "justify-start");
  const bubble = document.createElement("div");
  bubble.className = "max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 shadow-sm " + BUBBLE[kind];
  if (text === null) {
    bubble.innerHTML = '<span class="dot">●</span> <span class="dot">●</span> <span class="dot">●</span>';
  } else {
    bubble.textContent = text;
  }
  row.appendChild(bubble); log.appendChild(row);
  log.scrollTop = log.scrollHeight;
  return bubble;
}

function fill(bubble, kind, text) {
  bubble.className = bubble.className.replace(BUBBLE.agent, BUBBLE[kind]);
  bubble.textContent = text;
  log.scrollTop = log.scrollHeight;
}

async function askQuestion(text) {
  add("tu", text);
  const bubble = add("agent", null);
  send.disabled = true;
  try {
    const r = await fetch("/ask", {method: "POST", headers: {"Content-Type": "application/json"},
                                   body: JSON.stringify({question: text})});
    const data = await r.json();
    data.error ? fill(bubble, "err", data.error) : fill(bubble, "agent", data.answer);
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
document.querySelectorAll(".hint").forEach((b) => b.onclick = () => askQuestion(b.textContent));
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
