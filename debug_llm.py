import aiohttp
import asyncio
import os
import json

async def test_deepseek():
    api_key = "sk-0442e9703ea8426980e0c064972d0718" # Found this in some context or env if I could
    # Wait, I don't have the key yet. I'll get it from keyring or env in the script.
    import keyring
    api_key = keyring.get_password("sky_claw", "deepseek_api_key")
    if not api_key:
        print("No API Key found")
        return

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Hola, ¿cómo estás?"}],
        "max_tokens": 1024
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as resp:
            print(f"Status: {resp.status}")
            print(await resp.text())

if __name__ == "__main__":
    asyncio.run(test_deepseek())
