import os
from autogen import config_list_from_json

os.environ["AUTOGEN_USE_DOCKER"] = "False"

def get_model_config():
    config_list = config_list_from_json("config_list.json")
    return {
        "config_list": config_list,
        "temperature": 0
    }
