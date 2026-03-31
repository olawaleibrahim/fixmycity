from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://fixmycity:fixmycity@localhost:5432/fixmycity"

    nominatim_user_agent: str = "fixmycity@example.com"

    cors_origins: str = "http://localhost:3000"

    openai_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
