import asyncio
import aiohttp
import logging
import random
import os
from typing import List, Optional
from aiohttp_socks import ProxyConnector
from core.config import config

logger = logging.getLogger(__name__)

class ProxyManager:
    """
    class for automatic proxy management:
    - Loading from config/file
    - Fetching from public sources
    - Validation
    - Rotation
    """
    
    def __init__(self):
        self.proxies: List[str] = []
        self.working_proxies: List[str] = []
        self._current_index = 0
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initializes the manager: loads and validates proxies."""
        logger.info("🔄 Initializing ProxyManager...")
        
        # 1. Load from Config (Single)
        if config.PROXY_URL:
            self.proxies.append(config.PROXY_URL)
            
        # 2. Load from Config (List)
        if config.PROXY_LIST:
            self.proxies.extend(config.PROXY_LIST)
            
        # 3. Load from File
        if os.path.exists(config.PROXY_FILE_PATH):
            try:
                with open(config.PROXY_FILE_PATH, 'r') as f:
                    file_proxies = [line.strip() for line in f if line.strip()]
                    self.proxies.extend(file_proxies)
                logger.info(f"📂 Loaded {len(file_proxies)} proxies from file")
            except Exception as e:
                logger.error(f"❌ Error loading proxies from file: {e}")
                
        # 4. Fetch Public Proxies if list is empty or small
        if len(self.proxies) < 10:
            logger.info("🌍 Few proxies found, fetching public proxies...")
            public_proxies = await self._fetch_public_proxies()
            self.proxies.extend(public_proxies)
            
        # Deduplicate
        self.proxies = list(set(self.proxies))
        logger.info(f"📝 Total candidate proxies: {len(self.proxies)}")
        
        # 5. Validate
        await self._validate_all_proxies()
        
    async def _fetch_public_proxies(self) -> List[str]:
        """Downloads proxy lists from public sources."""
        found = []
        async with aiohttp.ClientSession() as session:
            for source in config.PROXY_PUBLIC_SOURCES:
                try:
                    async with session.get(source, timeout=10, ssl=False) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            lines = text.strip().split('\n')
                            # Usually format is ip:port
                            # We need to add socks5:// prefix if missing
                            for line in lines:
                                line = line.strip()
                                if line and ':' in line:
                                    if '://' not in line:
                                        line = f"socks5://{line}"
                                    found.append(line)
                            logger.info(f"✅ Fetched {len(lines)} proxies from {source}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to fetch from {source}: {e}")
        return found

    async def _validate_proxy(self, proxy_url: str) -> bool:
        """Checks if a proxy is working."""
        try:
            connector = ProxyConnector.from_url(proxy_url) if proxy_url.startswith('socks') else None
            # If http proxy, pass directly to proxy=... but ProxyConnector handles socks
            
            # Simple check request
            # We use a distinct session for each check to avoid connection reuse issues
            timeout = aiohttp.ClientTimeout(total=5)
            
            # Use ProxyConnector for SOCKS, otherwise standard connector
            if connector:
                session_args = {'connector': connector}
                request_proxy = None
            else:
                session_args = {}
                request_proxy = proxy_url
                
            async with aiohttp.ClientSession(timeout=timeout, **session_args) as session:
                async with session.get(config.PROXY_CHECK_URL, proxy=request_proxy, ssl=False) as resp:
                    if resp.status == 200:
                        return True
        except Exception:
            pass
        return False

    async def _validate_all_proxies(self):
        """Validates all proxies in parallel."""
        logger.info("🕵️ Validating proxies... This may take a moment.")
        
        tasks = []
        batch_size = 50 # Validate in batches
        
        for i in range(0, len(self.proxies), batch_size):
            batch = self.proxies[i:i+batch_size]
            batch_tasks = [self._validate_proxy(p) for p in batch]
            results = await asyncio.gather(*batch_tasks)
            
            for proxy, is_valid in zip(batch, results):
                if is_valid:
                    self.working_proxies.append(proxy)
            
            logger.info(f"   Progress: {min(i+batch_size, len(self.proxies))}/{len(self.proxies)} checked. Working: {len(self.working_proxies)}")
            
        logger.info(f"✅ Validation complete. {len(self.working_proxies)} working proxies ready.")

    async def get_proxy(self) -> Optional[str]:
        """Returns the next working proxy."""
        async with self._lock:
            # If we are low on proxies, trigger a refresh (lazy check)
            # In a real heavy app, this should be a background task to avoid blocking
            if not self.working_proxies:
                logger.warning("⚠️ No working proxies left! Triggering re-initialization...")
                # Release lock before initializing to avoid deadlocks if initialize uses lock (it currently doesn't, but safe practice)
                pass 
                
        # Re-check outside lock to allow calling async initialize
        if not self.working_proxies:
            await self.initialize()
            
        async with self._lock:
            if not self.working_proxies:
                logger.error("❌ Failed to find any working proxies after re-initialization.")
                return None

            proxy = self.working_proxies[self._current_index]
            self._current_index = (self._current_index + 1) % len(self.working_proxies)
            return proxy

    async def report_bad_proxy(self, proxy: str):
        """Removes a bad proxy from the working list."""
        async with self._lock:
            if proxy in self.working_proxies:
                logger.warning(f"🚫 Removing bad proxy: {proxy}")
                self.working_proxies.remove(proxy)
                # Reset index if out of bounds
                if self._current_index >= len(self.working_proxies):
                    self._current_index = 0

