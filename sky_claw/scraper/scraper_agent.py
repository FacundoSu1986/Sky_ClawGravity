import asyncio
import time
import logging
from playwright.async_api import async_playwright
from sky_claw.core.models import ModMetadataQuery, CircuitBreakerTripped
from sky_claw.core.database import DatabaseAgent

logger = logging.getLogger("SkyClaw.Scraper")

class ScraperAgent:
    def __init__(self, db: DatabaseAgent):
        self.db = db
        self.nexus_api_key = None # Se carga vía config segura (ej. keyring)
        self.max_failures = 3

    async def query_nexus(self, params: ModMetadataQuery) -> dict:
        """Enrutador Híbrido: Intenta API, si falla o fuerza stealth, usa Playwright. Pasa por el Circuit Breaker."""
        domain = "nexusmods.com"
        state = await self.db.get_circuit_breaker_state(domain)
        
        # 1. Evaluar Circuit Breaker
        if time.time() < state["locked_until"]:
            logger.error(f"RCA: Circuit Breaker abierto para {domain}. Abortando para proteger IP local.")
            raise CircuitBreakerTripped(f"Bloqueo activo hasta {state['locked_until']}")

        try:
            if not params.force_stealth and self.nexus_api_key:
                return await self._api_request(params)
            else:
                return await self._stealth_scrape(params)
                
        except Exception as e:
            # 2. RCA del fallo y actualización del Circuit Breaker
            new_failures = state["failures"] + 1
            lock_time = time.time() + (300 * new_failures) if new_failures >= self.max_failures else 0
            await self.db.update_circuit_breaker(domain, new_failures, lock_time)
            
            logger.warning(f"Fallo de extracción en {domain}. Fallos: {new_failures}. Error: {str(e)}")
            return {"status": "error", "data": None, "reason": str(e)}

    async def _api_request(self, params: ModMetadataQuery) -> dict:
        # Lógica aiohttp REST estándar con manejo de HTTP 429
        # (Omitido por brevedad, simula éxito)
        return {"status": "success", "source": "API", "data": {"nexus_id": params.nexus_id}}

    async def _stealth_scrape(self, params: ModMetadataQuery) -> dict:
        """Scraping con Playwright inyectando jitter."""
        logger.info(f"Iniciando Stealth Scraping para Mod ID {params.nexus_id}")
        async with async_playwright() as p:
            # En producción se usaría stealth plugin + proxy rotativo si es necesario
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
            )
            page = await context.new_page()
            
            # Simular Jitter (2 a 7 segundos) para evadir heurísticas
            import random
            await asyncio.sleep(random.uniform(2.0, 7.0))
            
            await page.goto(f"https://www.nexusmods.com/skyrimspecialedition/mods/{params.nexus_id}")
            
            # Extraer DOM (Ejemplo simplificado)
            title = await page.locator("h1.mod-title").inner_text()
            await browser.close()
            
            return {"status": "success", "source": "Playwright", "data": {"title": title}}
