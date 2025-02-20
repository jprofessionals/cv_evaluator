from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    PROJECT_NAME: str = "CV Evaluator"
    DEBUG: bool = False

    CV_PARTNER_API_KEY: str = "a"

    # Token to OpenAI service
    OPENAI_API_KEY: str = "b"

    # Tokens to slack service
    SLACK_BOT_TOKEN: str = "c"
    SLACK_CLIENT_ID: str = "d"
    SLACK_CLIENT_SECRET: str = "e"
    SLACK_SIGNING_SECRET: str = "f"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()

