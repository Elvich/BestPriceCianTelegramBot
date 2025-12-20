import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    print("Checking imports...")
    from services.bot.handlers import router
    print("✅ Successfully imported main router")
    
    from services.bot.handlers.base import router as base_router
    print("✅ Successfully imported base router")
    
    from services.bot.handlers.browser import router as browser_router
    print("✅ Successfully imported browser router")
    
    from services.bot.handlers.stats import router as stats_router
    print("✅ Successfully imported stats router")
    
    from services.bot.handlers.export import router as export_router
    print("✅ Successfully imported export router")
    
    print("🎉 All imports verified!")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
