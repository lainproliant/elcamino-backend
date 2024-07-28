# --------------------------------------------------------------------
# config.py
#
# Author: Lain Musgrove (lain.proliant@gmail.com)
# Date: Thursday July 25, 2024
# --------------------------------------------------------------------

import os
from dataclasses import dataclass, field
from typing import cast

from dataclass_wizard import YAMLWizard


# --------------------------------------------------------------------
def class_field(cls):
    return field(default_factory=cls)


# --------------------------------------------------------------------
@dataclass
class MememoConfig(YAMLWizard):
    hostname: str
    port: int
    auth_token: str


# --------------------------------------------------------------------
@dataclass
class WeatherConfig(YAMLWizard):
    latitude: float
    longitude: float
    openmeteo_url: str
    openmeteo_key: str


# --------------------------------------------------------------------
@dataclass
class Config(YAMLWizard):
    mememo: MememoConfig
    weather: WeatherConfig
    env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls):
        cls.INSTANCE = cls.from_yaml_file("/opt/elcamino/config.yaml")
        for key, value in cls.INSTANCE.env.items():
            os.environ[key] = value

    @classmethod
    def get(cls) -> "Config":
        if cls.INSTANCE is None:
            cls.load()
        return cast("Config", cls.INSTANCE)


Config.INSTANCE = None
