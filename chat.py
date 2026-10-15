"""Chatbot în linia de comandă. Rulare: python chat.py"""
import asyncio

from openai import APIConnectionError, APIStatusError

from agent import Agent

async def main():
    async with Agent() as agent:
        print(f"Furnizor: {agent.provider} | model: {agent.model}")
        print("Instrumente:", ", ".join(t["function"]["name"] for t in agent.tools))
        print("Comenzi: /reset (conversație nouă), /iesire\n")
        while True:
            try:
                text = input("Tu: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if text == "/iesire":
                break
            if text == "/reset":
                agent.reset()
                print("(conversație nouă)")
                continue
            if not text:
                continue
            try:
                print("Agent:", await agent.ask(text), "\n")
            except APIStatusError as e:
                print(f"Eroare HTTP {e.status_code}: {str(e.body or e.message)[:200]}\n")
            except APIConnectionError:
                print("Nu mă pot conecta la model (server oprit sau fără internet).\n")

if __name__ == "__main__":
    asyncio.run(main())
