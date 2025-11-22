"""
FastAPI application for SwiftDevBot web dashboard.
Serves React frontend and provides API endpoints.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from Systems.core.database.core_models import User as DBUser


class BlockUserRequest(BaseModel):
    block: bool


class ModuleToggleRequest(BaseModel):
    enable: bool


def _persist_enabled_modules(enabled_modules: List[str], config_path: Path) -> List[str]:
    unique_module_names = sorted({name.strip() for name in enabled_modules if name and name.strip()})
    data_to_save = {
        "active_modules": unique_module_names,
        "disabled_modules": [],
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
    return unique_module_names


def create_app(sdb_services=None, debug: bool = False) -> FastAPI:
    """
    Create and configure FastAPI application for SwiftDevBot web dashboard.
    
    Args:
        sdb_services: BotServicesProvider instance (optional)
        debug: Enable debug mode
        
    Returns:
        Configured FastAPI application
    """
    # Get web directory path
    web_dir = Path(__file__).parent
    dist_dir = web_dir / "dist"
    
    # Create FastAPI app
    app = FastAPI(
        title="SwiftDevBot Dashboard",
        description="Futuristic Liquid Glass Dashboard for SwiftDevBot",
        version="0.2.0",
        debug=debug,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files (Vite build output)
    if dist_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")
        
        # Mount locales directory for translations (from dist, copied from public by Vite)
        dist_locales_dir = dist_dir / "locales"
        if dist_locales_dir.exists():
            app.mount("/locales", StaticFiles(directory=str(dist_locales_dir)), name="locales")
        
        # Serve index.html for root
        @app.get("/", response_class=HTMLResponse)
        async def read_root():
            """Serve the main dashboard page."""
            index_path = dist_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            return HTMLResponse("<h1>SwiftDevBot Dashboard</h1><p>Please build the frontend: npm run build</p>")
    
    # API routes
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        if sdb_services:
            from Systems.core.monitoring.health import HealthChecker
            health_checker = HealthChecker(sdb_services)
            return await health_checker.get_health_summary()
        return {
            "status": "healthy",
            "service": "SwiftDevBot Dashboard",
            "version": "0.2.0"
        }
    
    @app.get("/api/health/detailed")
    async def health_check_detailed():
        """Detailed health check endpoint."""
        if sdb_services:
            from Systems.core.monitoring.health import HealthChecker
            health_checker = HealthChecker(sdb_services)
            return await health_checker.check_all()
        return {
            "status": "healthy",
            "service": "SwiftDevBot Dashboard",
            "version": "0.2.0",
            "checks": {}
        }
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        if sdb_services:
            from Systems.core.monitoring.metrics import get_metrics_collector
            metrics_collector = get_metrics_collector()
            return Response(
                content=metrics_collector.get_prometheus_format(),
                media_type="text/plain"
            )
        return Response(content="# No metrics available\n", media_type="text/plain")
    
    @app.get("/api/stats")
    async def get_stats():
        """Get bot statistics."""
        # This would normally fetch from sdb_services
        # For now, return mock data
        return {
            "uptime": "2d 5h 30m",
            "messages_today": 1234,
            "total_users": 567,
            "active_modules": 8,
            "total_modules": 12
        }
    
    @app.get("/api/modules")
    async def get_modules():
        """Get modules list."""
        if sdb_services:
            modules_info = sdb_services.modules.get_all_modules_info()
            modules_payload = []
            for info in modules_info:
                modules_payload.append({
                    "name": info.name,
                    "status": "active" if info.is_enabled else "inactive",
                    "description": info.manifest.description if info.manifest and info.manifest.description else "",
                    "display_name": info.manifest.display_name if info.manifest and info.manifest.display_name else info.name,
                    "is_system_module": info.is_system_module,
                    "version": info.manifest.version if info.manifest and info.manifest.version else None,
                })
            return modules_payload

        # Fallback mock data
        return [
            {
                "name": "sys_status",
                "status": "active",
                "description": "Системный модуль статуса"
            },
            {
                "name": "universal_template",
                "status": "active",
                "description": "Универсальный шаблон модуля"
            },
            {
                "name": "example_module",
                "status": "inactive",
                "description": "Пример модуля"
            }
        ]
    
    @app.get("/api/users")
    async def get_users():
        """Get users list."""
        if sdb_services:
            async with sdb_services.db.get_session() as session:
                stmt = select(DBUser).options(selectinload(DBUser.roles)).order_by(DBUser.id)
                result = await session.execute(stmt)
                db_users = result.scalars().all()
                payload = []
                for user in db_users:
                    primary_role = user.roles[0].name if user.roles else "user"
                    avatar = user.username[:1].upper() if user.username else "U"
                    payload.append({
                        "id": user.id,
                        "username": user.username or "",
                        "role": primary_role,
                        "avatar": avatar,
                        "is_blocked": user.is_bot_blocked
                    })
                return payload

        # Fallback mock data
        return [
            {
                "id": 1,
                "username": "user1",
                "role": "user",
                "avatar": "U"
            },
            {
                "id": 2,
                "username": "admin",
                "role": "admin",
                "avatar": "A"
            },
            {
                "id": 3,
                "username": "user2",
                "role": "user",
                "avatar": "U"
            }
        ]

    @app.post("/api/users/{user_db_id}/block")
    async def block_user(user_db_id: int, payload: BlockUserRequest):
        """Block or unblock a user."""
        if not sdb_services:
            raise HTTPException(status_code=503, detail="SwiftDevBot services are not initialized.")

        async with sdb_services.db.get_session() as session:
            user = await session.get(DBUser, user_db_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found.")

            if user.telegram_id in sdb_services.config.core.super_admins:
                raise HTTPException(status_code=403, detail="Cannot change block status of super administrators.")

            changed = await sdb_services.user_service.set_user_bot_blocked_status(user, payload.block, session)

            if changed:
                await session.commit()
            else:
                await session.rollback()

            return {"success": changed, "is_blocked": user.is_bot_blocked}

    @app.post("/api/modules/{module_name}/toggle")
    async def toggle_module(module_name: str, payload: ModuleToggleRequest):
        """Enable or disable a plugin from the dashboard."""
        if not sdb_services:
            raise HTTPException(status_code=503, detail="SwiftDevBot services are not initialized.")

        module_info = sdb_services.modules.get_module_info(module_name)
        if not module_info:
            raise HTTPException(status_code=404, detail="Module not found.")

        if module_info.is_system_module:
            raise HTTPException(status_code=400, detail="System modules cannot be toggled via dashboard.")

        desired_status = payload.enable
        current_enabled = list(sdb_services.modules.enabled_plugin_names)

        if desired_status and module_name not in current_enabled:
            current_enabled.append(module_name)
        elif not desired_status and module_name in current_enabled:
            current_enabled.remove(module_name)

        try:
            saved_list = _persist_enabled_modules(current_enabled, sdb_services.config.core.enabled_modules_config_path)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to persist enabled modules: {exc}")

        sdb_services.modules.enabled_plugin_names = saved_list
        if module_info:
            module_info.is_enabled = desired_status

        outcome = "active" if desired_status else "inactive"
        return {
            "success": True,
            "module": {
                "name": module_name,
                "status": outcome,
                "description": module_info.manifest.description if module_info.manifest and module_info.manifest.description else "",
                "display_name": module_info.manifest.display_name if module_info.manifest and module_info.manifest.display_name else module_name,
            },
            "enabled_modules": saved_list,
        }
    
    @app.get("/api/logs")
    async def get_logs(limit: int = 100, level: Optional[str] = None):
        """Get logs."""
        # This would normally fetch from sdb_services
        # For now, return mock data
        logs = [
            {
                "level": "info",
                "message": "Bot started successfully",
                "timestamp": "2025-11-04T10:00:00Z"
            },
            {
                "level": "info",
                "message": "Module sys_status loaded",
                "timestamp": "2025-11-04T10:00:01Z"
            },
            {
                "level": "warning",
                "message": "High memory usage detected",
                "timestamp": "2025-11-04T10:00:02Z"
            },
            {
                "level": "info",
                "message": "User connected",
                "timestamp": "2025-11-04T10:00:03Z"
            }
        ]
        
        if level and level != "all":
            logs = [log for log in logs if log["level"] == level]
        
        return logs[:limit]
    
    # Authentication routes
    @app.post("/api/auth/login")
    async def login(request: Request):
        """Login endpoint - supports both username/password and token-based auth."""
        try:
            data = await request.json()
            
            # Token-based authentication (from Telegram bot)
            token = data.get("token")
            if token:
                try:
                    from Systems.web.auth.jwt_handler import get_jwt_handler
                    jwt_handler = get_jwt_handler()
                    payload = await jwt_handler.verify_token(token)
                    
                    if payload:
                        user_info = jwt_handler.get_user_info(payload)
                        # Роль уже нормализована в lowercase в jwt_handler
                        role = user_info["role"].lower() if user_info.get("role") else "user"
                        return {
                            "user": {
                                "username": user_info["username"],
                                "role": role
                            },
                            "token": token
                        }
                    else:
                        raise HTTPException(status_code=401, detail="Invalid or expired token")
                except Exception as e:
                    raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")
            
            # Username/password authentication removed - only token-based auth is supported
            raise HTTPException(status_code=400, detail="Username/password authentication is disabled. Please use token-based authentication via Telegram bot.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/auth/verify")
    async def verify_token(token: Optional[str] = None):
        """Verify JWT token from query parameter."""
        if not token:
            raise HTTPException(status_code=400, detail="Token parameter is required")
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            
            if payload:
                user_info = jwt_handler.get_user_info(payload)
                return {
                    "valid": True,
                    "user": {
                        "username": user_info["username"],
                        "role": user_info["role"]
                    }
                }
            else:
                return {"valid": False, "error": "Invalid or expired token"}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    @app.post("/api/auth/logout")
    async def logout():
        """Logout endpoint."""
        return {"success": True}
    
    # Cloud password endpoints
    @app.get("/api/auth/cloud-password/check")
    async def check_cloud_password_setup(request: Request):
        """Check if cloud password is setup for current user."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return {"isSetup": False}
        token = auth_header.replace("Bearer ", "")
        if not token:
            return {"isSetup": False}
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            
            if payload:
                user_info = jwt_handler.get_user_info(payload)
                user_id = user_info.get("user_id")
                
                # Check if cloud password exists (in real app, check database)
                # For demo, use localStorage-like approach
                cloud_password_file = Path(__file__).parent.parent.parent / "config" / f"cloud_password_{user_id}.txt"
                return {"isSetup": cloud_password_file.exists()}
        except Exception:
            pass
        
        return {"isSetup": False}
    
    @app.post("/api/auth/cloud-password/setup")
    async def setup_cloud_password(request: Request):
        """Setup cloud password for current user."""
        try:
            data = await request.json()
            password = data.get("password")
            
            if not password or len(password) < 8:
                raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
            
            # Get user from token
            auth_header = request.headers.get("Authorization", "")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Token required")
            token = auth_header.replace("Bearer ", "")
            if not token:
                raise HTTPException(status_code=401, detail="Token required")
            
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            
            if not payload:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            user_info = jwt_handler.get_user_info(payload)
            user_id = user_info.get("user_id")
            
            # Hash password (in real app, use proper hashing like bcrypt)
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Save cloud password (in real app, save to database)
            config_dir = Path(__file__).parent.parent.parent / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            cloud_password_file = config_dir / f"cloud_password_{user_id}.txt"
            
            with open(cloud_password_file, 'w') as f:
                f.write(password_hash)
            
            # Set secure permissions
            os.chmod(cloud_password_file, 0o600)
            
            return {"success": True}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/auth/cloud-password/verify")
    async def verify_cloud_password(request: Request):
        """Verify cloud password for current user."""
        try:
            data = await request.json()
            password = data.get("password")
            
            if not password:
                raise HTTPException(status_code=400, detail="Password required")
            
            # Get user from token
            auth_header = request.headers.get("Authorization", "")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Token required")
            token = auth_header.replace("Bearer ", "")
            if not token:
                raise HTTPException(status_code=401, detail="Token required")
            
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            
            if not payload:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            user_info = jwt_handler.get_user_info(payload)
            user_id = user_info.get("user_id")
            
            # Load cloud password hash
            cloud_password_file = Path(__file__).parent.parent.parent / "config" / f"cloud_password_{user_id}.txt"
            
            if not cloud_password_file.exists():
                raise HTTPException(status_code=404, detail="Cloud password not setup")
            
            with open(cloud_password_file, 'r') as f:
                saved_hash = f.read().strip()
            
            # Verify password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if password_hash != saved_hash:
                raise HTTPException(status_code=401, detail="Invalid password")
            
            return {"success": True}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Catch-all route for SPA - must be last
    @app.get("/{path:path}", response_class=HTMLResponse)
    async def catch_all(path: str):
        """Catch-all route for SPA routing."""
        # Don't catch API routes or static files
        if path.startswith("api/") or path.startswith("assets/"):
            raise HTTPException(status_code=404, detail="Not found")
        
        # Serve index.html for all other routes
        if dist_dir.exists():
            index_path = dist_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
        
        return HTMLResponse("<h1>SwiftDevBot Dashboard</h1><p>Please build the frontend: npm run build</p>")
    
    return app
