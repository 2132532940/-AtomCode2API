import os
import time
import toml
import httpx
from pathlib import Path
from typing import Optional

ATOMCODE_CONFIG_DIR = Path.home() / ".atomcode"
ATOMCODE_CONFIG_PATH = ATOMCODE_CONFIG_DIR / "config.toml"
ATOMCODE_AUTH_PATH = ATOMCODE_CONFIG_DIR / "auth.toml"

API_BASE_URL = "https://api-ai.gitcode.com/v1"
GITCODE_API_BASE = "https://api.gitcode.com/api/v5"
ATOMCODE_USER_AGENT = "atomcode/4.22.0"

_cached_token: Optional[str] = None
_token_expires_at: float = 0.0
_cached_models: Optional[list] = None
_models_cached_at: float = 0.0
MODELS_CACHE_TTL = 300.0


def load_atomcode_config() -> dict:
    if ATOMCODE_CONFIG_PATH.exists():
        return toml.load(str(ATOMCODE_CONFIG_PATH))
    return {}


def load_atomcode_auth() -> dict:
    if ATOMCODE_AUTH_PATH.exists():
        return toml.load(str(ATOMCODE_AUTH_PATH))
    return {}


def get_access_token() -> Optional[str]:
    global _cached_token, _token_expires_at

    env_key = os.environ.get("ATOMCODE_API_KEY")
    if env_key:
        return env_key

    if _cached_token and time.time() < _token_expires_at:
        return _cached_token

    auth_config = load_atomcode_auth()
    access_token = auth_config.get("access_token")
    refresh_token = auth_config.get("refresh_token")

    if refresh_token:
        try:
            resp = httpx.post(
                f"https://acs.atomgit.com/oauth/refresh",
                json={"refresh_token": refresh_token},
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                new_access = data.get("access_token")
                new_refresh = data.get("refresh_token", refresh_token)
                if new_access:
                    _cached_token = new_access
                    _token_expires_at = time.time() + 86400 * 6
                    _save_auth(new_access, new_refresh, data)
                    return new_access
        except Exception:
            pass

    if access_token:
        return access_token

    return None


def _save_auth(access_token: str, refresh_token: str, data: dict):
    auth_config = load_atomcode_auth()
    auth_config["access_token"] = access_token
    auth_config["refresh_token"] = refresh_token
    auth_config["token_type"] = data.get("token_type", "Bearer")
    auth_config["expires_in"] = data.get("expires_in", 604800)
    auth_config["created_at"] = int(time.time())
    if "user" in data:
        auth_config["user"] = data["user"]

    try:
        ATOMCODE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(str(ATOMCODE_AUTH_PATH), "w") as f:
            for key, value in auth_config.items():
                if isinstance(value, dict):
                    f.write(f"[{key}]\n")
                    for k, v in value.items():
                        f.write(f'{k} = "{v}"\n')
                else:
                    f.write(f'{key} = "{value}"\n')
    except Exception:
        pass


async def fetch_codingplan_models() -> list:
    global _cached_models, _models_cached_at

    if _cached_models and (time.time() - _models_cached_at) < MODELS_CACHE_TTL:
        return _cached_models

    token = get_access_token()
    if not token:
        return []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GITCODE_API_BASE}/coding-plan/models",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    _cached_models = data
                    _models_cached_at = time.time()
                    return data
    except Exception:
        pass

    return _cached_models or []


def get_model_list() -> list[str]:
    if _cached_models:
        return [m.get("display_model_name", "") for m in _cached_models if m.get("display_model_name")]
    return []


def get_all_model_ids() -> list[str]:
    from model_list import AVAILABLE_MODELS
    return list(AVAILABLE_MODELS.keys())


SERVER_HOST = os.environ.get("PROXY_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("PROXY_PORT", "8000"))
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "deepseek-v4-flash")
