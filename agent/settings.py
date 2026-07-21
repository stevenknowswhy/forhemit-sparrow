"""
User settings persistence for Sparrow.

Stores rubric preference and custom weights as a JSON file
alongside the agent code. Loaded at server start, editable via API.
"""
import json
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent / "user_settings.json"

DEFAULT_SETTINGS = {
    "rubric": "consumer",
    "custom_weights": None,
}


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        raw = SETTINGS_FILE.read_text()
        if not raw.strip():
            return DEFAULT_SETTINGS.copy()
        data = json.loads(raw)
        result = DEFAULT_SETTINGS.copy()
        result.update(data)
        return result
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> dict:
    current = load_settings()
    current.update(settings)
    if "rubric" in settings:
        from scorer import RUBRIC_PRESETS
        if current["rubric"] not in RUBRIC_PRESETS:
            raise ValueError(
                f"Invalid rubric '{current['rubric']}'. "
                f"Available: {list(RUBRIC_PRESETS.keys())}"
            )
    SETTINGS_FILE.write_text(json.dumps(current, indent=2) + "\n")
    return current


def get_active_rubric() -> str:
    return load_settings().get("rubric", "consumer")


def get_custom_weights() -> dict | None:
    return load_settings().get("custom_weights")
