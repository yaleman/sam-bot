from pathlib import Path
from typing import Dict, Self
import logging
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MISPConfig(BaseSettings):
    url: str
    key: str
    ssl: bool = Field(True)


class SlackConfig(BaseSettings):
    SLACK_BOT_OAUTH_TOKEN: str = Field()
    SLACK_SIGNING_SECRET: str = Field()

    model_config = SettingsConfigDict(env_prefix="")

    @model_validator(mode="before")
    def validate_slack_config(cls, values: Dict[str, str]) -> Dict[str, str]:
        if not values.get("SLACK_BOT_OAUTH_TOKEN"):
            raise ValueError("SLACK_BOT_OAUTH_TOKEN is required")
        if not values.get("SLACK_SIGNING_SECRET"):
            raise ValueError("SLACK_SIGNING_SECRET is required")
        return values


class LoggingConfig(BaseSettings):
    output_file: str = Field("./logs/sambot.log")
    output_error_file: str = Field("./logs/sambot_error.log")

    @classmethod
    def default(cls) -> Self:
        return cls.model_validate({})


class SamBotConfig(BaseSettings):
    slack: SlackConfig
    misp: MISPConfig
    testing: bool = False
    logging: LoggingConfig = Field(default_factory=LoggingConfig.default)

    @classmethod
    def load(cls) -> Self:
        if Path("config.json").exists():
            return cls.model_validate_json(Path("config.json").read_text())
        else:
            logger = logging.getLogger("sam_bot")
            logger.warning("No config file found, using default settings.")
            return cls.model_validate({})
