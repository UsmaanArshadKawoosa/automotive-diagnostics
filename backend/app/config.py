from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Automotive AI Diagnostic Engine"
    app_env: str = "development"
    debug: bool = True

    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_server: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "automotive_diagnostic"

    database_url: str | None = None

    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        return (
            f"postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}"
            f"/{self.postgres_db}"
        )


settings = Settings()