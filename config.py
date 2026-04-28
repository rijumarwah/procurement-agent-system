import os
from autogen import config_list_from_json

os.environ["AUTOGEN_USE_DOCKER"] = "False"

_model_config = None


def get_model_config() -> dict:
    """Load and cache the LLM config from config_list.json."""
    global _model_config
    if _model_config is None:
        config_list = config_list_from_json("config_list.json")
        _model_config = {
            "config_list": config_list,
            "temperature": 0,
        }
    return _model_config
