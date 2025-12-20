from aiogram import Router
from .base import router as base_router
from .browser import router as browser_router
from .stats import router as stats_router
from .export import router as export_router

# Создаем главный роутер
router = Router()

# Подключаем все дочерние роутеры
router.include_router(base_router)
router.include_router(browser_router)
router.include_router(stats_router)
router.include_router(export_router)

