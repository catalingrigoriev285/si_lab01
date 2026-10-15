"""Agentul: o buclă între modelul de limbaj și instrumentele unui server MCP."""
import json
from pathlib import Path

from fastmcp import Client

from llm import create_chat, make_client

SERVER = Path(__file__).parent / "server.py"
MAX_STEPS = 6  # limită de siguranță pentru bucla de apeluri de instrumente
SYSTEM_PROMPT = (
    "Ești asistentul unei clădiri inteligente. Răspunde concis, în limba română. "
    "Pentru informații despre dispozitive, conflicte sau consum folosește instrumentele "
    "disponibile; nu inventa date. Dacă un instrument returnează o eroare, spune-o utilizatorului."
)

def mcp_to_openai_tool(tool) -> dict:
    """Descrierea unui instrument MCP, în formatul cerut de modelul de limbaj."""
    # versiunile noi de FastMCP folosesc input_schema, cele vechi inputSchema
    schema = getattr(tool, "input_schema", None) or tool.inputSchema
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": schema,
        },
    }

class Agent:
    def __init__(self):
        self.llm, self.model, self.provider = make_client()
        self.mcp = Client(SERVER)  # pornește server.py ca proces copil (stdio)
        self.tools = []
        self.reset()

    def reset(self):
        """Conversație nouă: păstrăm doar instrucțiunile de sistem."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    async def __aenter__(self):
        await self.mcp.__aenter__()
        self.tools = [mcp_to_openai_tool(t) for t in await self.mcp.list_tools()]
        return self

    async def __aexit__(self, *exc):
        await self.mcp.__aexit__(*exc)

    async def call_tool(self, call) -> str:
        """Execută printr-un client MCP un apel cerut de model."""
        name, args = call.function.name, {}
        try:
            args = json.loads(call.function.arguments or "{}")
            result = await self.mcp.call_tool(name, args)
            text = "\n".join(b.text for b in result.content if hasattr(b, "text"))
        except Exception as e:  # eroarea ajunge la model, care o poate explica
            text = f"Eroare la apelul {name}: {e}"
        print(f"  [instrument] {name}({args}) -> {text[:150]}")
        return text

    async def ask(self, text: str) -> str:
        self.messages.append({"role": "user", "content": text})
        for _ in range(MAX_STEPS):
            reply = create_chat(
                self.llm, model=self.model, messages=self.messages, tools=self.tools
            )
            msg = reply.choices[0].message
            if not msg.tool_calls:  # răspuns final, în text
                self.messages.append({"role": "assistant", "content": msg.content or ""})
                return msg.content or ""
            # Modelul cere instrumente: le păstrăm în istoric, le executăm, repetăm.
            self.messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [c.model_dump(exclude_none=True) for c in msg.tool_calls],
            })
            for call in msg.tool_calls:
                result = await self.call_tool(call)
                self.messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": result}
                )
        return "(Am atins limita de pași a agentului.)"