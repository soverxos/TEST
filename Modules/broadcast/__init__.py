from aiogram import Router
from core.schemas.module_manifest import ModuleManifest
from .handlers import router as handlers_router

async def setup_module(dp, bot, manifest: ModuleManifest):
    """
    Setup Broadcast module.
    """
    dp.include_router(handlers_router)
    print(f"Module {manifest.name} loaded successfully!")
