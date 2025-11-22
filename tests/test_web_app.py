import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from Systems.web.app import BlockUserRequest, ModuleToggleRequest, create_app


class DummyUser:
    def __init__(self, id_: int, telegram_id: int, username: str):
        self.id = id_
        self.telegram_id = telegram_id
        self.username = username
        self.is_bot_blocked = False


class DummySession:
    def __init__(self, user: DummyUser):
        self._user = user

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def get(self, model, id_):
        return self._user if self._user.id == id_ else None


class DummyDB:
    def __init__(self, user: DummyUser):
        self._user = user

    def get_session(self):
        return DummySession(self._user)


class DummyUserService:
    def __init__(self):
        self.last_change = None

    async def set_user_bot_blocked_status(self, user: DummyUser, block: bool, session):
        self.last_change = (user.id, block)
        user.is_bot_blocked = block
        return True


class DummyManifest:
    def __init__(self, description: str, display_name: str, version: str):
        self.description = description
        self.display_name = display_name
        self.version = version


class DummyModuleInfo:
    def __init__(self, name: str, is_enabled: bool, manifest: DummyManifest, is_system_module: bool = False):
        self.name = name
        self.is_enabled = is_enabled
        self.manifest = manifest
        self.is_system_module = is_system_module


class DummyModules:
    def __init__(self, modules_info, enabled_module_names):
        self._modules_info = modules_info
        self.enabled_plugin_names = enabled_module_names[:]  # keep own copy

    def get_all_modules_info(self):
        return list(self._modules_info)

    def get_module_info(self, module_name):
        for info in self._modules_info:
            if info.name == module_name:
                return info
        return None


class DummyServices:
    def __init__(self, tmp_path: Path, user: DummyUser):
        core_config = SimpleNamespace(
            super_admins=[999],
            enabled_modules_config_path=tmp_path / "enabled_modules.json",
            project_data_path=tmp_path,
        )
        self.config = SimpleNamespace(core=core_config)
        self.db = DummyDB(user)
        self.user_service = DummyUserService()
        manifest = DummyManifest(
            description="Demo plugin",
            display_name="Demo Plugin",
            version="2.0.0",
        )
        self.modules = DummyModules([DummyModuleInfo("demo", True, manifest)], enabled_module_names=["demo"])


@pytest.fixture
def dummy_services(tmp_path):
    return DummyServices(tmp_path, DummyUser(id_=1, telegram_id=123, username="tester"))


def test_get_modules_fallback_and_custom(dummy_services):
    client = TestClient(create_app(dummy_services))

    # When services are provided, expect actual modules info
    resp = client.get("/api/modules")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["name"] == "demo" for item in data)

    # Without services fall back to mock data
    client = TestClient(create_app())
    resp = client.get("/api/modules")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "sys_status"


def test_block_user_and_module_toggle(dummy_services):
    client = TestClient(create_app(dummy_services))

    block_resp = client.post("/api/users/1/block", json=BlockUserRequest(block=True).dict())
    assert block_resp.status_code == 200
    assert block_resp.json()["is_blocked"] is True
    assert dummy_services.user_service.last_change == (1, True)

    toggle_resp = client.post(
        "/api/modules/demo/toggle",
        json=ModuleToggleRequest(enable=False).dict(),
    )
    assert toggle_resp.status_code == 200
    module_data = toggle_resp.json()["module"]
    assert module_data["status"] == "inactive"
    assert dummy_services.modules.enabled_plugin_names == []

    # Ensure enabled modules file was persisted
    with open(dummy_services.config.core.enabled_modules_config_path, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert "demo" not in saved["active_modules"]

    # Re-enable module
    resp = client.post(
        "/api/modules/demo/toggle",
        json=ModuleToggleRequest(enable=True).dict(),
    )
    assert resp.status_code == 200
    assert resp.json()["module"]["status"] == "active"
    assert dummy_services.modules.enabled_plugin_names == ["demo"]

