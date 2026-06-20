"""Runtime LLM settings route: read masked settings, update provider/key.

The full API key is never returned to the client. Reads expose only a masked
hint (last four characters); writes persist server-side and take effect live.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from examsolver.api.schemas import SettingsBody, UpdateSettingsBody
from examsolver.runtime_settings import describe_settings, update_settings

router = APIRouter(tags=["settings"])


@router.get("/config", response_model=SettingsBody)
def get_config() -> SettingsBody:
    """Return the provider list with masked keys; full keys stay server-side."""

    return SettingsBody.model_validate(describe_settings())


@router.put("/config", response_model=SettingsBody)
def update_config(body: UpdateSettingsBody) -> SettingsBody:
    """Persist and live-apply a provider/key change, then echo masked settings."""

    try:
        update_settings(provider=body.provider, api_key=body.api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SettingsBody.model_validate(describe_settings())
