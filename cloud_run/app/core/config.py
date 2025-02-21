from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    PROJECT_NAME: str = "CV Evaluator"
    DEBUG: bool = True

    CV_PARTNER_API_KEY: str

    # Token to OpenAI service
    OPENAI_API_KEY: str

    # Tokens to slack service
    SLACK_BOT_TOKEN: str
    SLACK_CLIENT_ID: str
    SLACK_CLIENT_SECRET: str
    SLACK_SIGNING_SECRET: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()

