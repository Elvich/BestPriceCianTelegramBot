
import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.parser.logic.proxy_manager import ProxyManager
from core.config import config

logging.basicConfig(level=logging.INFO)

async def main():
    print("🚀 Starting ProxyManager Validation...")
    
    # Enable fetching public proxies for test
    # config.PROXY_LIST is likely empty in dev env, so it should fetch
    
    manager = ProxyManager()
    await manager.initialize()
    
    print(f"\n✅ Initialization complete.")
    print(f"📊 Total Proxies Found: {len(manager.proxies)}")
    print(f"🟢 Working Proxies: {len(manager.working_proxies)}")
    
    if manager.working_proxies:
        print("\nUsing a proxy to test connection:")
        proxy = await manager.get_proxy()
        print(f"   Target: {config.PROXY_CHECK_URL}")
        print(f"   Selected Proxy: {proxy}")
        
        # Test validation logic explicitly
        is_valid = await manager._validate_proxy(proxy)
        print(f"   Validation Check: {'PASSED' if is_valid else 'FAILED'}")
    else:
        print("\n⚠️ No working proxies found. This is common with public lists.")

if __name__ == "__main__":
    asyncio.run(main())
