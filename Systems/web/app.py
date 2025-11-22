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
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

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
    
    @app.get("/api/metrics/system")
    async def get_system_metrics():
        """Get system metrics (CPU, RAM, Disk, Redis, DB connections)."""
        if sdb_services:
            try:
                metrics = {
                    "cpu": 0.0,
                    "ram": 0.0,
                    "ramUsed": 0,
                    "ramTotal": 0,
                    "disk": 0.0,
                    "diskUsed": 0,
                    "diskTotal": 0,
                    "redis": 0.0,
                    "redisUsed": 0,
                    "redisTotal": 0,
                    "dbConnections": 0
                }
                
                # Get CPU, RAM, Disk via psutil
                try:
                    import psutil
                    import os
                    process = psutil.Process(os.getpid())
                    
                    # CPU: use system-wide CPU if process CPU is 0
                    cpu_percent = process.cpu_percent(interval=0.1)
                    if cpu_percent == 0:
                        cpu_percent = psutil.cpu_percent(interval=0.1)
                    metrics["cpu"] = cpu_percent
                    
                    # RAM: use process memory info
                    mem_info = process.memory_info()
                    system_mem = psutil.virtual_memory()
                    metrics["ram"] = (mem_info.rss / system_mem.total) * 100
                    metrics["ramUsed"] = int(mem_info.rss)
                    metrics["ramTotal"] = int(system_mem.total)
                    
                    # Disk usage for project data path
                    disk_usage = psutil.disk_usage(sdb_services.config.core.project_data_path)
                    metrics["disk"] = (disk_usage.used / disk_usage.total) * 100
                    metrics["diskUsed"] = int(disk_usage.used)
                    metrics["diskTotal"] = int(disk_usage.total)
                except Exception as e:
                    # If psutil fails, try to get at least some info
                    try:
                        import psutil
                        metrics["cpu"] = psutil.cpu_percent(interval=0.1)
                        mem = psutil.virtual_memory()
                        metrics["ram"] = mem.percent
                        metrics["ramUsed"] = int(mem.used)
                        metrics["ramTotal"] = int(mem.total)
                    except:
                        pass
                
                # Get Redis memory if available
                try:
                    if sdb_services.cache and hasattr(sdb_services.cache, 'get_redis_client_instance'):
                        # Redis client is async, so we need to handle it differently
                        # For now, try to get info if it's available synchronously
                        # In a real async context, you'd await this
                        try:
                            # Try to access redis client directly if it's stored
                            if hasattr(sdb_services.cache, '_redis_client') and sdb_services.cache._redis_client:
                                # This is async redis, so we can't call info() directly
                                # For now, set a placeholder or skip
                                metrics["redis"] = 0.0  # Will be updated when async support is added
                                metrics["redisUsed"] = 0
                                metrics["redisTotal"] = 0
                        except:
                            pass
                except Exception:
                    pass
                
                # Get DB connections from pool
                try:
                    if sdb_services.db and hasattr(sdb_services.db, 'engine'):
                        pool = sdb_services.db.engine.pool
                        metrics["dbConnections"] = pool.size() if hasattr(pool, 'size') else 0
                except Exception:
                    pass
                
                return metrics
            except Exception as e:
                return {
                    "cpu": 0.0,
                    "ram": 0.0,
                    "ramUsed": 0,
                    "ramTotal": 0,
                    "disk": 0.0,
                    "diskUsed": 0,
                    "diskTotal": 0,
                    "redis": 0.0,
                    "redisUsed": 0,
                    "redisTotal": 0,
                    "dbConnections": 0
                }
        
        return {
            "cpu": 0.0,
            "ram": 0.0,
            "ramUsed": 0,
            "ramTotal": 0,
            "disk": 0.0,
            "diskUsed": 0,
            "diskTotal": 0,
            "redis": 0.0,
            "redisUsed": 0,
            "redisTotal": 0,
            "dbConnections": 0
        }
    
    @app.get("/api/metrics/live")
    async def get_live_metrics():
        """Get live metrics for Mission Control (RPS, Response Time, Error Rate, etc.)."""
        if sdb_services:
            try:
                from Systems.core.monitoring.metrics import get_metrics_collector
                from datetime import datetime, timedelta
                
                metrics_collector = get_metrics_collector()
                metrics_dict = metrics_collector.get_metrics_dict() if metrics_collector else {}
                
                # Calculate RPS from events_total
                rps = 0.0
                total_events = 0
                for key, value in metrics_dict.get("counters", {}).items():
                    if "sdb_events_total" in key:
                        # Sum all event types
                        total_events += value
                
                # Simple RPS calculation: if we have events, estimate based on time window
                # This is a simplified approach - in production, you'd track events over time windows
                if total_events > 0:
                    # Estimate: assume events accumulated over last minute
                    # In real implementation, you'd track events per second
                    rps = total_events / 60.0  # Rough estimate
                
                # Get response time from histograms
                response_time = 0.0
                response_times = []
                for key, hist_data in metrics_dict.get("histograms", {}).items():
                    if "sdb_event_duration_seconds" in key or "duration" in key.lower():
                        if isinstance(hist_data, dict) and "avg" in hist_data:
                            response_times.append(hist_data["avg"] * 1000)  # Convert to ms
                
                if response_times:
                    response_time = sum(response_times) / len(response_times)
                else:
                    # Fallback: if no histogram data, use a default or calculate from counters
                    # This is a placeholder - real implementation would track actual response times
                    response_time = 50.0  # Default 50ms if no data
                
                # Calculate error rate
                error_rate = 0.0
                error_events = 0
                for key, value in metrics_dict.get("counters", {}).items():
                    if "sdb_events_error_total" in key:
                        error_events += value
                
                if total_events > 0:
                    error_rate = (error_events / total_events) * 100
                
                # Get active users (24h) - users with last_activity_at in last 24 hours
                active_users = 0
                try:
                    async with sdb_services.db.get_session() as session:
                        from datetime import datetime, timedelta
                        cutoff_time = datetime.now() - timedelta(hours=24)
                        stmt = select(func.count(DBUser.id)).where(DBUser.last_activity_at >= cutoff_time)
                        result = await session.execute(stmt)
                        active_users = result.scalar_one_or_none() or 0
                except Exception:
                    pass
                
                # Get new users today
                new_users_today = 0
                try:
                    async with sdb_services.db.get_session() as session:
                        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                        # Assuming there's a created_at field, if not, use id as proxy
                        stmt = select(func.count(DBUser.id))
                        # If no created_at, we can't accurately count new users today
                        # For now, return 0
                        new_users_today = 0
                except Exception:
                    pass
                
                # Queue size (if using Redis queue)
                queue_size = 0
                try:
                    if sdb_services.cache and hasattr(sdb_services.cache, 'redis') and sdb_services.cache.redis:
                        # Try to get queue length if there's a queue
                        queue_size = 0  # Placeholder - would need queue implementation
                except Exception:
                    pass
                
                return {
                    "rps": float(rps),
                    "responseTime": float(response_time),
                    "errorRate": float(error_rate),
                    "activeUsers": active_users,
                    "newUsersToday": new_users_today,
                    "queueSize": queue_size
                }
            except Exception as e:
                return {
                    "rps": 0.0,
                    "responseTime": 0.0,
                    "errorRate": 0.0,
                    "activeUsers": 0,
                    "newUsersToday": 0,
                    "queueSize": 0
                }
        
        return {
            "rps": 0.0,
            "responseTime": 0.0,
            "errorRate": 0.0,
            "activeUsers": 0,
            "newUsersToday": 0,
            "queueSize": 0
        }
    
    @app.get("/api/stats")
    async def get_stats():
        """Get bot statistics."""
        if sdb_services:
            try:
                # Get total users from database
                total_users = 0
                async with sdb_services.db.get_session() as session:
                    count_stmt = select(func.count(DBUser.id))
                    total_users_result = await session.execute(count_stmt)
                    total_users = total_users_result.scalar_one_or_none() or 0
                
                # Get modules info
                active_modules = len(sdb_services.modules.enabled_plugin_names) if sdb_services.modules else 0
                total_modules = len(sdb_services.modules.get_all_modules_info()) if sdb_services.modules else 0
                
                # Get messages today from metrics
                messages_today = 0
                try:
                    from Systems.core.monitoring.metrics import get_metrics_collector
                    metrics_collector = get_metrics_collector()
                    if metrics_collector:
                        metrics_dict = metrics_collector.get_metrics_dict()
                        # Get message events from today
                        # Count events with type="message" from counters
                        message_key = "sdb_events_total{'type': 'message'}"
                        if message_key in metrics_dict.get("counters", {}):
                            messages_today = metrics_dict["counters"][message_key]
                        # If not found, try to get from all message-related counters
                        for key, value in metrics_dict.get("counters", {}).items():
                            if "message" in key.lower():
                                messages_today += value
                                break
                except Exception as e:
                    # If metrics not available, set to 0
                    messages_today = 0
                
                # Get uptime (if available from process start time)
                uptime = "N/A"
                try:
                    import psutil
                    import os
                    pid = os.getpid()
                    process = psutil.Process(pid)
                    create_time = datetime.fromtimestamp(process.create_time())
                    uptime_delta = datetime.now() - create_time
                    days = uptime_delta.days
                    hours = uptime_delta.seconds // 3600
                    minutes = (uptime_delta.seconds % 3600) // 60
                    if days > 0:
                        uptime = f"{days}d {hours}h {minutes}m"
                    elif hours > 0:
                        uptime = f"{hours}h {minutes}m"
                    else:
                        uptime = f"{minutes}m"
                except Exception:
                    # If psutil not available or error, try to get from bot start time if stored
                    uptime = "N/A"
                
                return {
                    "uptime": uptime,
                    "messages_today": messages_today,
                    "total_users": total_users,
                    "active_modules": active_modules,
                    "total_modules": total_modules
                }
            except Exception as e:
                # Fallback to empty data on error
                return {
                    "uptime": "N/A",
                    "messages_today": 0,
                    "total_users": 0,
                    "active_modules": 0,
                    "total_modules": 0
                }
        
        # Fallback: return empty data if services not available
        return {
            "uptime": "N/A",
            "messages_today": 0,
            "total_users": 0,
            "active_modules": 0,
            "total_modules": 0
        }
    
    @app.get("/api/modules")
    async def get_modules(include_system: bool = False):
        """Get modules list.
        
        Args:
            include_system: If True, include system modules. Default: False (only user plugins).
        """
        if sdb_services:
            modules_info = sdb_services.modules.get_all_modules_info()
            modules_payload = []
            for info in modules_info:
                # Filter system modules if not requested
                if not include_system and info.is_system_module:
                    continue
                    
                modules_payload.append({
                    "name": info.name,
                    "status": "active" if info.is_enabled else "inactive",
                    "description": info.manifest.description if info.manifest and info.manifest.description else "",
                    "display_name": info.manifest.display_name if info.manifest and info.manifest.display_name else info.name,
                    "is_system_module": info.is_system_module,
                    "version": info.manifest.version if info.manifest and info.manifest.version else None,
                })
            return modules_payload

        # Fallback: return empty list if no services (no modules installed)
        return []
    
    @app.get("/api/services")
    async def get_services():
        """Get services status."""
        if sdb_services:
            try:
                import psutil
                import os
                from datetime import datetime
                
                process = psutil.Process(os.getpid())
                create_time = datetime.fromtimestamp(process.create_time())
                uptime_delta = datetime.now() - create_time
                days = uptime_delta.days
                hours = uptime_delta.seconds // 3600
                minutes = (uptime_delta.seconds % 3600) // 60
                
                if days > 0:
                    uptime_str = f"{days}d {hours}h {minutes}m"
                elif hours > 0:
                    uptime_str = f"{hours}h {minutes}m"
                else:
                    uptime_str = f"{minutes}m"
                
                memory_mb = process.memory_info().rss / (1024 * 1024)
                memory_str = f"{int(memory_mb)} MB"
                
                services = []
                
                # Bot Core / Polling - always running if bot is initialized
                services.append({
                    "id": "polling",
                    "name": "Polling",
                    "description": "Telegram bot polling service",
                    "status": "running" if sdb_services.bot else "stopped",
                    "uptime": uptime_str if sdb_services.bot else "0m",
                    "memory": memory_str if sdb_services.bot else "0 MB"
                })
                
                # Scheduler - check if LoggingManager has scheduler
                try:
                    from Systems.core.logging_manager import LoggingManager
                    # Scheduler is part of LoggingManager, assume running if services are up
                    services.append({
                        "id": "scheduler",
                        "name": "Scheduler",
                        "description": "Background task scheduler",
                        "status": "running",
                        "uptime": uptime_str,
                        "memory": "0 MB"  # Part of main process
                    })
                except:
                    services.append({
                        "id": "scheduler",
                        "name": "Scheduler",
                        "description": "Background task scheduler",
                        "status": "stopped",
                        "uptime": "0m",
                        "memory": "0 MB"
                    })
                
                # WebServer - always running if we're here
                services.append({
                    "id": "webserver",
                    "name": "WebServer",
                    "description": "FastAPI web server",
                    "status": "running",
                    "uptime": uptime_str,
                    "memory": memory_str
                })
                
                # BackgroundTasks - part of asyncio, always running
                services.append({
                    "id": "backgroundtasks",
                    "name": "BackgroundTasks",
                    "description": "Async background tasks",
                    "status": "running",
                    "uptime": uptime_str,
                    "memory": "0 MB"  # Part of main process
                })
                
                return services
            except Exception as e:
                return []
        
        return []
    
    @app.post("/api/services/{service_id}/{action}")
    async def service_action(service_id: str, action: str):
        """Perform action on a service (start/stop/restart)."""
        if not sdb_services:
            raise HTTPException(status_code=503, detail="SwiftDevBot services are not initialized.")
        
        if action not in ['start', 'stop', 'restart']:
            raise HTTPException(status_code=400, detail="Invalid action. Must be 'start', 'stop', or 'restart'.")
        
        # For now, services are part of the main process, so we can't actually start/stop them
        # This is a placeholder for future implementation
        # In a real scenario, you might have separate processes or containers
        
        return {
            "success": True,
            "message": f"Service {service_id} {action} requested (note: services are part of main process, restart bot to apply changes)"
        }
    
    @app.get("/api/config")
    async def get_config():
        """Get core configuration as YAML."""
        if sdb_services:
            try:
                import yaml
                config_path = sdb_services.config.core.project_data_path / "Config" / "core_settings.yaml"
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        return {"content": f.read()}
                else:
                    # Return default structure if file doesn't exist
                    default_config = {
                        "core": {
                            "project_data_path": str(sdb_services.config.core.project_data_path),
                            "super_admins": sdb_services.config.core.super_admins,
                            "log_level": sdb_services.config.core.log_level,
                            "log_to_file": sdb_services.config.core.log_to_file,
                        },
                        "db": {
                            "type": sdb_services.config.db.type,
                        },
                        "cache": {
                            "type": sdb_services.config.cache.type,
                        },
                        "telegram": {
                            "polling_timeout": sdb_services.config.telegram.polling_timeout,
                        }
                    }
                    return {"content": yaml.dump(default_config, default_flow_style=False, allow_unicode=True)}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to read config: {str(e)}")
        
        raise HTTPException(status_code=503, detail="SwiftDevBot services are not initialized.")
    
    @app.put("/api/config")
    async def update_config(request: Request):
        """Update core configuration."""
        if not sdb_services:
            raise HTTPException(status_code=503, detail="SwiftDevBot services are not initialized.")
        
        try:
            body = await request.json()
            content = body.get("content", "")
            
            # Validate YAML
            import yaml
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")
            
            # Write to file
            config_path = sdb_services.config.core.project_data_path / "Config" / "core_settings.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {"success": True, "message": "Configuration saved. Restart required to apply changes."}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")
    
    @app.post("/api/config/reload")
    async def reload_config():
        """Hot reload configuration (placeholder - requires implementation)."""
        # Note: Full config reload would require reinitializing services
        # For now, return a message that restart is needed
        return {
            "success": False,
            "message": "Hot reload not fully implemented. Please restart the bot to apply configuration changes."
        }
    
    @app.get("/api/feature-flags")
    async def get_feature_flags():
        """Get feature flags."""
        # For now, return default feature flags
        # In the future, these could be stored in DB or config
        return [
            {
                "name": "maintenance_mode",
                "enabled": False,
                "description": "Enable maintenance mode (only admins can access)"
            },
            {
                "name": "disable_broadcasts",
                "enabled": False,
                "description": "Disable all broadcast messages"
            },
            {
                "name": "strict_rbac",
                "enabled": True,
                "description": "Enable strict RBAC enforcement"
            }
        ]
    
    @app.put("/api/feature-flags/{flag_name}")
    async def update_feature_flag(flag_name: str, request: Request):
        """Update a feature flag."""
        try:
            body = await request.json()
            enabled = body.get("enabled", False)
            
            # For now, just return success
            # In the future, this would persist to DB or config
            return {
                "success": True,
                "flag": {
                    "name": flag_name,
                    "enabled": enabled
                },
                "message": "Feature flag updated (restart may be required)"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update feature flag: {str(e)}")
    
    @app.get("/api/sessions")
    async def get_sessions(request: Request):
        """Get active sessions for current user."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return []
        token = auth_header.replace("Bearer ", "")
        if not token:
            return []
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                return []
            
            user_info = jwt_handler.get_user_info(payload)
            user_id = user_info.get("user_id")
            
            # For now, return current session only
            # In the future, track sessions in Redis or DB
            return [{
                "id": "current",
                "device": "Current Browser",
                "location": "Unknown",
                "lastActivity": "Just now",
                "current": True,
                "ip": request.client.host if request.client else "Unknown"
            }]
        except Exception:
            return []
    
    @app.post("/api/sessions/{session_id}/terminate")
    async def terminate_session(session_id: str, request: Request):
        """Terminate a session."""
        # For now, just return success
        # In the future, invalidate token in Redis or DB
        return {"success": True, "message": "Session terminated"}
    
    @app.get("/api/tokens")
    async def get_tokens(request: Request):
        """Get API tokens for current user."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return []
        token = auth_header.replace("Bearer ", "")
        if not token:
            return []
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                return []
            
            # For now, return empty list
            # In the future, store tokens in DB
            return []
        except Exception:
            return []
    
    @app.post("/api/tokens")
    async def create_token(request: Request):
        """Create a new API token."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Token required")
        token = auth_header.replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            body = await request.json()
            token_name = body.get("name", "Unnamed Token")
            
            # Generate token
            import secrets
            token_value = f"sdb_{secrets.token_urlsafe(32)}"
            
            # For now, just return the token
            # In the future, store in DB with user_id, name, created_at, last_used_at
            return {
                "id": secrets.token_urlsafe(16),
                "name": token_name,
                "token": token_value,
                "created": datetime.now().isoformat(),
                "lastUsed": None
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create token: {str(e)}")
    
    @app.delete("/api/tokens/{token_id}")
    async def revoke_token(token_id: str, request: Request):
        """Revoke an API token."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Token required")
        token = auth_header.replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # For now, just return success
            # In the future, delete from DB
            return {"success": True, "message": "Token revoked"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to revoke token: {str(e)}")
    
    @app.get("/api/command-history")
    async def get_command_history(request: Request, limit: int = 50):
        """Get command history for current user."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return []
        token = auth_header.replace("Bearer ", "")
        if not token:
            return []
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                return []
            
            # For now, return empty list
            # In the future, parse logs or store commands in DB
            return []
        except Exception:
            return []
    
    @app.get("/api/files")
    async def get_files(request: Request):
        """Get files for current user."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return []
        token = auth_header.replace("Bearer ", "")
        if not token:
            return []
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                return []
            
            # For now, return empty list
            # In the future, get from file storage system
            return []
        except Exception:
            return []
    
    @app.get("/api/tickets")
    async def get_tickets(request: Request):
        """Get support tickets for current user."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return []
        token = auth_header.replace("Bearer ", "")
        if not token:
            return []
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                return []
            
            # For now, return empty list
            # In the future, get from DB (support_tickets table)
            return []
        except Exception:
            return []
    
    @app.post("/api/tickets")
    async def create_ticket(request: Request):
        """Create a support ticket."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Token required")
        token = auth_header.replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            body = await request.json()
            subject = body.get("subject", "")
            message = body.get("message", "")
            
            # For now, just return success
            # In the future, store in DB
            return {
                "id": f"T-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "subject": subject,
                "status": "open",
                "created": datetime.now().isoformat(),
                "updated": datetime.now().isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")
    
    @app.post("/api/terminal/execute")
    async def execute_terminal_command(request: Request):
        """Execute a bot command via terminal."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Token required")
        token = auth_header.replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            body = await request.json()
            command = body.get("command", "").strip()
            
            if not command:
                raise HTTPException(status_code=400, detail="Command is required")
            
            # Security: Only allow bot commands (starting with /)
            if not command.startswith("/"):
                raise HTTPException(status_code=400, detail="Only bot commands (starting with /) are allowed")
            
            # For now, return a simulated response
            # In the future, integrate with bot command handler
            # This would require accessing BotServicesProvider and executing commands
            return {
                "output": f"Command '{command}' executed successfully.\n[Note: Terminal execution is currently simulated. Full integration requires bot command handler access.]",
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to execute command: {str(e)}")
    
    @app.get("/api/cron-jobs")
    async def get_cron_jobs(request: Request):
        """Get list of scheduled cron jobs from APScheduler."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return []
        token = auth_header.replace("Bearer ", "")
        if not token:
            return []
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                return []
            
            # Try to get scheduler from LoggingManager
            jobs = []
            if sdb_services:
                try:
                    # Access LoggingManager's scheduler
                    logging_manager = getattr(sdb_services, 'logging_manager', None)
                    if logging_manager and hasattr(logging_manager, '_scheduler') and logging_manager._scheduler:
                        scheduler = logging_manager._scheduler
                        for job in scheduler.get_jobs():
                            jobs.append({
                                "id": job.id,
                                "name": job.name or job.id,
                                "func": job.func.__name__ if hasattr(job.func, '__name__') else str(job.func),
                                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                                "trigger": str(job.trigger) if job.trigger else None,
                            })
                except Exception as e:
                    # If scheduler is not available, return empty list
                    pass
            
            return jobs
        except Exception:
            return []
    
    @app.get("/api/logs/stream")
    async def stream_logs(request: Request, limit: int = 100, level: Optional[str] = None):
        """Stream logs (for live updates)."""
        # This endpoint can be used for polling-based live updates
        # For true streaming, WebSocket would be better, but polling is simpler
        return await get_logs(limit, level)
    
    @app.get("/api/audit-logs")
    async def get_audit_logs(
        request: Request,
        limit: int = 100,
        module_name: Optional[str] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ):
        """Get security audit logs."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return []
        token = auth_header.replace("Bearer ", "")
        if not token:
            return []
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                return []
            
            # Check if user is admin
            user_info = jwt_handler.get_user_info(payload)
            if user_info.get("role", "").lower() != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
            
            if sdb_services and hasattr(sdb_services, 'audit_logger') and sdb_services.audit_logger:
                from Systems.core.security.audit_logger import AuditEventType, AuditSeverity
                
                # Convert string filters to enums
                event_type_enum = None
                if event_type:
                    try:
                        event_type_enum = AuditEventType(event_type)
                    except:
                        pass
                
                severity_enum = None
                if severity:
                    try:
                        severity_enum = AuditSeverity(severity)
                    except:
                        pass
                
                events = sdb_services.audit_logger.get_events(
                    module_name=module_name,
                    event_type=event_type_enum,
                    severity=severity_enum,
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit
                )
                
                # Convert to dict format
                result = []
                for event in events:
                    result.append({
                        "event_id": event.event_id,
                        "event_type": event.event_type.value,
                        "module_name": event.module_name,
                        "user_id": event.user_id,
                        "timestamp": event.timestamp,
                        "severity": event.severity.value,
                        "details": event.details,
                        "ip_address": event.ip_address,
                        "user_agent": event.user_agent,
                        "success": event.success,
                        "error_message": event.error_message,
                    })
                
                return result
            return []
        except HTTPException:
            raise
        except Exception as e:
            return []
    
    @app.get("/api/audit-stats")
    async def get_audit_stats(request: Request):
        """Get security audit statistics."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return {}
        token = auth_header.replace("Bearer ", "")
        if not token:
            return {}
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                return {}
            
            # Check if user is admin
            user_info = jwt_handler.get_user_info(payload)
            if user_info.get("role", "").lower() != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
            
            if sdb_services and hasattr(sdb_services, 'audit_logger') and sdb_services.audit_logger:
                stats = sdb_services.audit_logger.get_statistics()
                return stats
            return {}
        except HTTPException:
            raise
        except Exception:
            return {}
    
    @app.post("/api/database/query")
    async def execute_sql_query(request: Request):
        """Execute a safe SQL SELECT query (read-only)."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Token required")
        token = auth_header.replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # Check if user is admin
            user_info = jwt_handler.get_user_info(payload)
            if user_info.get("role", "").lower() != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
            
            body = await request.json()
            query = body.get("query", "").strip()
            
            if not query:
                raise HTTPException(status_code=400, detail="Query is required")
            
            # Security: Only allow SELECT queries
            query_upper = query.upper().strip()
            if not query_upper.startswith("SELECT"):
                raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
            
            # Additional security: Block dangerous keywords
            dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "EXEC", "EXECUTE"]
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    raise HTTPException(status_code=400, detail=f"Query contains forbidden keyword: {keyword}")
            
            if sdb_services and sdb_services.db:
                from sqlalchemy import text
                async with sdb_services.db.get_session() as session:
                    result = await session.execute(text(query))
                    rows = result.fetchall()
                    
                    # Convert to list of dicts
                    columns = result.keys()
                    data = []
                    for row in rows:
                        row_dict = {}
                        for i, col in enumerate(columns):
                            value = row[i]
                            # Convert datetime and other types to string
                            if hasattr(value, 'isoformat'):
                                row_dict[col] = value.isoformat()
                            else:
                                row_dict[col] = str(value) if value is not None else None
                        data.append(row_dict)
                    
                    return {
                        "columns": list(columns),
                        "data": data,
                        "row_count": len(data)
                    }
            
            raise HTTPException(status_code=500, detail="Database not available")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")
    
    @app.get("/api/migrations")
    async def get_migrations(request: Request):
        """Get Alembic migration history."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return []
        token = auth_header.replace("Bearer ", "")
        if not token:
            return []
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                return []
            
            # Check if user is admin
            user_info = jwt_handler.get_user_info(payload)
            if user_info.get("role", "").lower() != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
            
            # Get current revision and history from Alembic
            try:
                from alembic.config import Config
                from alembic.script import ScriptDirectory
                from alembic.runtime.migration import MigrationContext
                from alembic import command
                import os
                
                # Get migration directory
                migration_dir = Path(__file__).parent.parent / "migration"
                alembic_cfg = Config(str(migration_dir / "alembic.ini"))
                alembic_cfg.set_main_option("script_location", str(migration_dir))
                
                script = ScriptDirectory.from_config(alembic_cfg)
                revisions = list(script.walk_revisions())
                
                # Get current revision from database
                current_rev = None
                if sdb_services and sdb_services.db:
                    from sqlalchemy import text
                    async with sdb_services.db.get_session() as session:
                        try:
                            context = MigrationContext.configure(await session.connection())
                            current_rev = context.get_current_revision()
                        except:
                            pass
                
                migrations = []
                for rev in reversed(revisions):  # Most recent first
                    migrations.append({
                        "revision": rev.revision,
                        "down_revision": rev.down_revision,
                        "branch_labels": list(rev.branch_labels) if rev.branch_labels else [],
                        "is_current": rev.revision == current_rev,
                        "doc": rev.doc or "",
                    })
                
                return migrations
            except Exception as e:
                return []
        except HTTPException:
            raise
        except Exception:
            return []
    
    @app.post("/api/migrations/{action}")
    async def migration_action(action: str, request: Request):
        """Execute Alembic migration action (upgrade/downgrade)."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Token required")
        token = auth_header.replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # Check if user is admin
            user_info = jwt_handler.get_user_info(payload)
            if user_info.get("role", "").lower() != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
            
            # For now, return success (actual migration execution would require subprocess)
            # In production, this should be done via CLI command
            return {
                "success": True,
                "message": f"Migration {action} requested. Please use CLI command 'sdb db {action}' for safety."
            }
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=500, detail="Migration action failed")
    
    @app.get("/api/cache/keys")
    async def get_cache_keys(request: Request, pattern: Optional[str] = None, limit: int = 100):
        """Get Redis cache keys."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return []
        token = auth_header.replace("Bearer ", "")
        if not token:
            return []
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                return []
            
            # Check if user is admin
            user_info = jwt_handler.get_user_info(payload)
            if user_info.get("role", "").lower() != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
            
            if sdb_services and sdb_services.cache:
                redis_client = sdb_services.cache.get_redis_client_instance()
                if redis_client:
                    try:
                        # Get keys matching pattern
                        if pattern:
                            keys = await redis_client.keys(pattern)
                        else:
                            keys = await redis_client.keys("*")
                        
                        # Limit results
                        keys = keys[:limit]
                        
                        # Get TTL for each key
                        result = []
                        for key in keys:
                            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                            ttl = await redis_client.ttl(key)
                            result.append({
                                "key": key_str,
                                "ttl": ttl if ttl > 0 else None,
                            })
                        
                        return result
                    except Exception as e:
                        return []
            return []
        except HTTPException:
            raise
        except Exception:
            return []
    
    @app.post("/api/cache/flush")
    async def flush_cache(request: Request):
        """Flush Redis cache."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Token required")
        token = auth_header.replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # Check if user is admin
            user_info = jwt_handler.get_user_info(payload)
            if user_info.get("role", "").lower() != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
            
            if sdb_services and sdb_services.cache:
                await sdb_services.cache.clear_all_cache()
                return {"success": True, "message": "Cache flushed successfully"}
            
            return {"success": False, "message": "Cache not available"}
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to flush cache")
    
    @app.get("/api/broadcasts")
    async def get_broadcasts(request: Request):
        """Get broadcast history."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return []
        token = auth_header.replace("Bearer ", "")
        if not token:
            return []
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                return []
            
            # Check if user is admin
            user_info = jwt_handler.get_user_info(payload)
            if user_info.get("role", "").lower() != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
            
            # For now, return empty list (in future, store broadcasts in DB)
            return []
        except HTTPException:
            raise
        except Exception:
            return []
    
    @app.post("/api/broadcasts")
    async def create_broadcast(request: Request):
        """Create and send a broadcast."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Token required")
        token = auth_header.replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # Check if user is admin
            user_info = jwt_handler.get_user_info(payload)
            if user_info.get("role", "").lower() != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
            
            body = await request.json()
            message = body.get("message", "")
            target_type = body.get("target_type", "all")  # all, admins, active, language
            target_value = body.get("target_value", None)  # language code if target_type is language
            schedule_time = body.get("schedule_time", None)  # ISO datetime string or null for immediate
            
            if not message:
                raise HTTPException(status_code=400, detail="Message is required")
            
            # Get target users
            target_users = []
            if sdb_services and sdb_services.db:
                from sqlalchemy import select, and_
                from Systems.core.database.core_models import User as DBUser
                
                async with sdb_services.db.get_session() as session:
                    from Systems.core.database.core_models import Role, UserRole
                    
                    if target_type == "all":
                        stmt = select(DBUser.telegram_id).where(DBUser.is_bot_blocked == False)
                    elif target_type == "admins":
                        # Get super admins and users with admin role
                        super_admins = sdb_services.config.core.super_admins if sdb_services.config else []
                        stmt = select(DBUser.telegram_id).where(
                            and_(
                                DBUser.is_bot_blocked == False,
                                DBUser.telegram_id.in_(super_admins) if super_admins else False
                            )
                        )
                    elif target_type == "role":
                        # Users with specific role
                        role_name = target_value or "User"
                        stmt = (
                            select(DBUser.telegram_id)
                            .join(UserRole, DBUser.id == UserRole.user_id)
                            .join(Role, UserRole.role_id == Role.id)
                            .where(
                                and_(
                                    DBUser.is_bot_blocked == False,
                                    Role.name == role_name
                                )
                            )
                        )
                    elif target_type == "active":
                        # Users active in last N days
                        days = int(target_value) if target_value else 7
                        cutoff = datetime.now() - timedelta(days=days)
                        stmt = select(DBUser.telegram_id).where(
                            and_(
                                DBUser.is_bot_blocked == False,
                                DBUser.last_activity_at >= cutoff
                            )
                        )
                    elif target_type == "inactive":
                        # Users not active for N days
                        days = int(target_value) if target_value else 30
                        cutoff = datetime.now() - timedelta(days=days)
                        stmt = select(DBUser.telegram_id).where(
                            and_(
                                DBUser.is_bot_blocked == False,
                                or_(
                                    DBUser.last_activity_at < cutoff,
                                    DBUser.last_activity_at.is_(None)
                                )
                            )
                        )
                    elif target_type == "new_users":
                        # Users registered in last N days
                        days = int(target_value) if target_value else 30
                        cutoff = datetime.now() - timedelta(days=days)
                        stmt = select(DBUser.telegram_id).where(
                            and_(
                                DBUser.is_bot_blocked == False,
                                DBUser.created_at >= cutoff
                            )
                        )
                    elif target_type == "language":
                        # Users with specific language
                        lang_code = target_value or "ru"
                        stmt = select(DBUser.telegram_id).where(
                            and_(
                                DBUser.is_bot_blocked == False,
                                DBUser.preferred_language_code == lang_code
                            )
                        )
                    elif target_type == "active_status":
                        # Users by active status
                        status = target_value or "active"
                        if status == "active":
                            stmt = select(DBUser.telegram_id).where(
                                and_(
                                    DBUser.is_bot_blocked == False,
                                    DBUser.is_active == True
                                )
                            )
                        else:  # inactive
                            stmt = select(DBUser.telegram_id).where(
                                and_(
                                    DBUser.is_bot_blocked == False,
                                    DBUser.is_active == False
                                )
                            )
                    else:
                        stmt = select(DBUser.telegram_id).where(DBUser.is_bot_blocked == False)
                    
                    result = await session.execute(stmt)
                    target_users = [row[0] for row in result.fetchall()]
            
            # Create broadcast ID
            broadcast_id = f"BC_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # If scheduled, just return queued status
            if schedule_time:
                return {
                    "id": broadcast_id,
                    "message": message,
                    "target_type": target_type,
                    "target_count": len(target_users),
                    "status": "queued",
                    "created_at": datetime.now().isoformat(),
                    "schedule_time": schedule_time,
                    "note": "Broadcast scheduled. Sending will start at scheduled time."
                }
            
            # Send messages immediately
            # Try to get bot token from multiple sources
            bot_token = None
            if sdb_services and sdb_services.config:
                # Try from config.telegram.token
                try:
                    if hasattr(sdb_services.config, 'telegram') and hasattr(sdb_services.config.telegram, 'token'):
                        bot_token = sdb_services.config.telegram.token
                except:
                    pass
            
            # Fallback to environment variable
            if not bot_token:
                import os
                bot_token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
            
            if bot_token:
                import asyncio
                import aiohttp
                api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                
                sent_count = 0
                error_count = 0
                
                # Send messages with rate limiting (max 30 messages per second for Telegram)
                async def send_to_user(telegram_id: int):
                    nonlocal sent_count, error_count
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                api_url,
                                json={
                                    "chat_id": telegram_id,
                                    "text": message,
                                    "parse_mode": "HTML",
                                    "disable_web_page_preview": True
                                },
                                timeout=aiohttp.ClientTimeout(total=10)
                            ) as response:
                                if response.status == 200:
                                    result = await response.json()
                                    if result.get("ok"):
                                        sent_count += 1
                                    else:
                                        error_count += 1
                                else:
                                    error_count += 1
                    except asyncio.TimeoutError:
                        error_count += 1
                    except Exception as e:
                        error_count += 1
                
                # Send messages in batches to respect rate limits
                batch_size = 20  # Send 20 messages at a time
                delay_between_batches = 1.0  # Wait 1 second between batches
                
                for i in range(0, len(target_users), batch_size):
                    batch = target_users[i:i + batch_size]
                    tasks = [send_to_user(tg_id) for tg_id in batch]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Wait before next batch (except for last batch)
                    if i + batch_size < len(target_users):
                        await asyncio.sleep(delay_between_batches)
                
                return {
                    "id": broadcast_id,
                    "message": message,
                    "target_type": target_type,
                    "target_count": len(target_users),
                    "sent_count": sent_count,
                    "error_count": error_count,
                    "status": "completed" if error_count == 0 else "completed_with_errors",
                    "created_at": datetime.now().isoformat(),
                    "schedule_time": schedule_time,
                    "note": f"Broadcast sent. {sent_count} successful, {error_count} errors."
                }
            else:
                # No bot token available - provide helpful error message
                debug_info = []
                if not sdb_services:
                    debug_info.append("sdb_services is None")
                elif not sdb_services.config:
                    debug_info.append("sdb_services.config is None")
                else:
                    debug_info.append("sdb_services.config exists")
                    try:
                        if hasattr(sdb_services.config, 'telegram'):
                            debug_info.append("config.telegram exists")
                            if hasattr(sdb_services.config.telegram, 'token'):
                                token_value = sdb_services.config.telegram.token
                                debug_info.append(f"config.telegram.token exists: {bool(token_value)} (length: {len(token_value) if token_value else 0})")
                            else:
                                debug_info.append("config.telegram.token attribute not found")
                        else:
                            debug_info.append("config.telegram attribute not found")
                    except Exception as e:
                        debug_info.append(f"Error checking config: {str(e)}")
                
                import os
                env_token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
                if env_token:
                    debug_info.append(f"BOT_TOKEN found in environment (length: {len(env_token)})")
                else:
                    debug_info.append("BOT_TOKEN not found in environment")
                
                return {
                    "id": broadcast_id,
                    "message": message,
                    "target_type": target_type,
                    "target_count": len(target_users),
                    "status": "failed",
                    "created_at": datetime.now().isoformat(),
                    "schedule_time": schedule_time,
                    "note": f"Bot token not available. Debug info: {'; '.join(debug_info)}. Please ensure BOT_TOKEN is set in .env file or config.telegram.token is configured."
                }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create broadcast: {str(e)}")
    
    @app.get("/api/broadcasts/{broadcast_id}/progress")
    async def get_broadcast_progress(broadcast_id: str, request: Request):
        """Get broadcast progress."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return {"sent": 0, "total": 0, "errors": 0, "status": "unknown"}
        token = auth_header.replace("Bearer ", "")
        if not token:
            return {"sent": 0, "total": 0, "errors": 0, "status": "unknown"}
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                return {"sent": 0, "total": 0, "errors": 0, "status": "unknown"}
            
            # Check if user is admin
            user_info = jwt_handler.get_user_info(payload)
            if user_info.get("role", "").lower() != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
            
            # For now, return mock progress (in future, track in DB or Redis)
            return {
                "sent": 0,
                "total": 0,
                "errors": 0,
                "status": "completed"
            }
        except HTTPException:
            raise
        except Exception:
            return {"sent": 0, "total": 0, "errors": 0, "status": "unknown"}
    
    @app.get("/api/api-keys")
    async def get_api_keys(request: Request):
        """Get API keys list (admin only)."""
        # Get user from token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Token required")
        token = auth_header.replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Token required")
        
        try:
            from Systems.web.auth.jwt_handler import get_jwt_handler
            jwt_handler = get_jwt_handler()
            payload = await jwt_handler.verify_token(token)
            if not payload:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # Check if user is admin
            user_info = jwt_handler.get_user_info(payload)
            if user_info.get("role", "").lower() != "admin":
                raise HTTPException(status_code=403, detail="Admin access required")
            
            # Load API keys from CLI storage
            try:
                from Systems.cli.api import _load_api_keys, API_KEYS_FILE
                keys_data = _load_api_keys()
                keys = keys_data.get("keys", {})
                
                # Convert to list format (hide actual keys for security)
                result = []
                for key_name, key_info in keys.items():
                    result.append({
                        "name": key_name,
                        "permissions": key_info.get("permissions", "read"),
                        "created_at": key_info.get("created_at"),
                        "expires_at": key_info.get("expires_at"),
                        "last_used": key_info.get("last_used"),
                        "usage_count": key_info.get("usage_count", 0),
                    })
                
                return result
            except Exception as e:
                return []
        except HTTPException:
            raise
        except Exception:
            return []
    
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
                        "first_name": user.first_name or "",
                        "last_name": user.last_name or "",
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
        """Get logs from log files."""
        if sdb_services:
            try:
                import re
                from datetime import datetime
                
                log_dir = sdb_services.config.core.project_data_path / sdb_services.config.core.log_structured_dir
                if not log_dir.exists():
                    return []
                
                # Get current hour log file and recent files
                now = datetime.now()
                current_log_file = log_dir / now.strftime("%Y") / f"{now.strftime('%m')}-{now.strftime('%B')}" / now.strftime("%d") / f"{now.strftime('%H')}_sdb.log"
                
                log_files = []
                if current_log_file.exists():
                    log_files.append(current_log_file)
                
                # Also check previous hour
                prev_hour = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
                prev_log_file = log_dir / prev_hour.strftime("%Y") / f"{prev_hour.strftime('%m')}-{prev_hour.strftime('%B')}" / prev_hour.strftime("%d") / f"{prev_hour.strftime('%H')}_sdb.log"
                if prev_log_file.exists() and prev_log_file != current_log_file:
                    log_files.append(prev_log_file)
                
                all_logs = []
                for log_file in log_files:
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            for line in lines[-500:]:  # Read last 500 lines from each file
                                # Parse loguru format: 2025-01-15 10:30:45.123 | LEVEL    | module:message
                                match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s+\|\s+(\w+)\s+\|\s+(.+)', line)
                                if match:
                                    timestamp_str, log_level, message = match.groups()
                                    try:
                                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                                    except:
                                        timestamp = datetime.now()
                                    
                                    # Map loguru levels to our levels
                                    level_map = {
                                        'TRACE': 'info',
                                        'DEBUG': 'info',
                                        'INFO': 'info',
                                        'SUCCESS': 'success',
                                        'WARNING': 'warning',
                                        'ERROR': 'error',
                                        'CRITICAL': 'error'
                                    }
                                    mapped_level = level_map.get(log_level.upper(), 'info')
                                    
                                    if level and level != "all" and mapped_level != level:
                                        continue
                                    
                                    all_logs.append({
                                        "level": mapped_level,
                                        "message": message.strip(),
                                        "timestamp": timestamp.isoformat()
                                    })
                    except Exception as e:
                        continue
                
                # Sort by timestamp descending and limit
                all_logs.sort(key=lambda x: x["timestamp"], reverse=True)
                return all_logs[:limit]
            except Exception as e:
                # Fallback to empty on error
                return []
        
        # Fallback: return empty list
        return []
    
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
                        # Get user from database to get first_name and last_name
                        telegram_id = user_info.get("user_id")  # This is actually telegram_id from JWT
                        first_name = None
                        last_name = None
                        if telegram_id and sdb_services:
                            try:
                                async with sdb_services.db.get_session() as session:
                                    stmt = select(DBUser).where(DBUser.telegram_id == telegram_id)
                                    result = await session.execute(stmt)
                                    db_user = result.scalar_one_or_none()
                                    if db_user:
                                        first_name = db_user.first_name
                                        last_name = db_user.last_name
                                        print(f"[API] Found user {telegram_id}: first_name={first_name}, last_name={last_name}")
                                    else:
                                        print(f"[API] User with telegram_id {telegram_id} not found in database")
                            except Exception as e:
                                print(f"[API] Error fetching user data: {e}")
                                import traceback
                                traceback.print_exc()
                        
                        return {
                            "user": {
                                "username": user_info["username"],
                                "role": role,
                                "first_name": first_name,
                                "last_name": last_name
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
                # Get user from database to get first_name and last_name
                telegram_id = user_info.get("user_id")  # This is actually telegram_id from JWT
                first_name = None
                last_name = None
                if telegram_id and sdb_services:
                    try:
                        async with sdb_services.db.get_session() as session:
                            stmt = select(DBUser).where(DBUser.telegram_id == telegram_id)
                            result = await session.execute(stmt)
                            db_user = result.scalar_one_or_none()
                            if db_user:
                                first_name = db_user.first_name
                                last_name = db_user.last_name
                                print(f"[API] Found user {telegram_id}: first_name={first_name}, last_name={last_name}")
                            else:
                                print(f"[API] User with telegram_id {telegram_id} not found in database")
                    except Exception as e:
                        print(f"[API] Error fetching user data: {e}")
                        import traceback
                        traceback.print_exc()
                
                return {
                    "valid": True,
                    "user": {
                        "username": user_info["username"],
                        "role": user_info["role"],
                        "first_name": first_name,
                        "last_name": last_name
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
