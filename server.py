"""Laborator 1 SI - un server MCP minimal: clădire inteligentă (date de test)."""
from fastmcp import FastMCP

mcp = FastMCP("smart-building-demo")

# Date de test, inventate pentru laborator.
DEVICES = {
    "lampa_led": {"categorie": "iluminat", "putere_w": 10, "note": "Se poate regla pe trepte de intensitate."},
    "radiator": {"categorie": "încălzire", "putere_w": 1500, "note": "Controlat de termostatul camerei."},
    "aer_conditionat": {"categorie": "climatizare", "putere_w": 2000, "note": "Nu se folosește cu ferestrele deschise."},
    "jaluzele": {"categorie": "umbrire", "putere_w": 30, "note": "Motor electric, consum doar la mișcare."},
    "ventilatie": {"categorie": "ventilație", "putere_w": 120, "note": "Aduce aer proaspăt din exterior."},
    "senzor_miscare": {"categorie": "securitate", "putere_w": 5, "note": "Detectează mișcarea în cameră."},
}

CONFLICTE = {
    frozenset({"radiator", "aer_conditionat"}): "RIDICAT - încălzire și răcire simultană, consum inutil.",
    frozenset({"aer_conditionat", "ventilatie"}): "MEDIU - aerul exterior scade eficiența climatizării.",
}

@mcp.tool
def list_devices() -> list[str]:
    """Returnează numele tuturor dispozitivelor cunoscute din clădire."""
    return sorted(DEVICES)

@mcp.tool
def get_device_info(name: str) -> dict:
    """Returnează informații de bază despre un dispozitiv (categorie, putere în W, note)."""
    info = DEVICES.get(name.strip().lower())
    if info is None:
        return {"eroare": f"Dispozitiv necunoscut: {name}", "cunoscute": sorted(DEVICES)}
    return {"nume": name.strip().lower(), **info}


@mcp.tool
def check_conflict(device_a: str, device_b: str) -> str:
    """Verifică dacă două dispozitive au un conflict de funcționare cunoscut."""
    cheie = frozenset({device_a.strip().lower(), device_b.strip().lower()})
    return CONFLICTE.get(cheie, "Niciun conflict înregistrat în setul de date de test.")

@mcp.tool
def estimate_energy(name: str, hours: float) -> dict:
    """Estimează energia consumată (în kWh) de un dispozitiv care funcționează un număr de ore."""
    info = DEVICES.get(name.strip().lower())
    if info is None:
        return {"eroare": f"Dispozitiv necunoscut: {name}", "cunoscute": sorted(DEVICES)}
    return {
        "nume": name.strip().lower(),
        "ore": hours,
        "energie_kwh": round(info["putere_w"] * hours / 1000, 3),
    }

@mcp.resource("device://{name}/manual")
def manual(name: str) -> str:
    """Un manual (fictiv) de o linie, expus ca resursă."""
    info = DEVICES.get(name.lower())
    return f"{name}: {info['categorie']}. {info['note']}" if info else f"Nu există manual pentru {name}."

@mcp.prompt
def energy_review(devices: str) -> str:
    """Șablon de prompt: cere unui LLM să analizeze o listă de dispozitive."""
    return (
        f"Analizează această listă de dispozitive: {devices}. "
        "Folosește instrumentele pentru a verifica conflictele și a estima consumul."
    )

if __name__ == "__main__":
    mcp.run(show_banner=False)  # stdio, implicit