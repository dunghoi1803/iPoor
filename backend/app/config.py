from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = Field("development", alias="APP_ENV")
    app_host: str = Field("0.0.0.0", alias="APP_HOST")
    app_port: int = Field(8000, alias="APP_PORT")
    allowed_origins: str = Field("*", alias="ALLOWED_ORIGINS")

    db_host: str = Field(..., alias="DB_HOST")
    db_port: int = Field(3306, alias="DB_PORT")
    db_user: str = Field(..., alias="DB_USER")
    db_password: str = Field(..., alias="DB_PASSWORD")
    db_name: str = Field("ipoor", alias="DB_NAME")

    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(60, alias="JWT_EXPIRE_MINUTES")

    admin_email: str = Field(..., alias="ADMIN_EMAIL")
    admin_password: str = Field(..., alias="ADMIN_PASSWORD")
    admin_full_name: str = Field("System Admin", alias="ADMIN_FULL_NAME")

    upload_dir: str = Field("uploads", alias="UPLOAD_DIR")

    s3_bucket: str | None = Field(None, alias="AWS_S3_BUCKET")
    s3_region: str | None = Field(None, alias="AWS_REGION")
    s3_access_key_id: str | None = Field(None, alias="AWS_ACCESS_KEY_ID")
    s3_secret_access_key: str | None = Field(None, alias="AWS_SECRET_ACCESS_KEY")
    s3_endpoint_url: str | None = Field(None, alias="AWS_S3_ENDPOINT_URL")
    s3_public_base_url: str | None = Field(None, alias="AWS_S3_PUBLIC_BASE_URL")
    s3_presign_expires: int = Field(900, alias="AWS_S3_PRESIGN_EXPIRES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origins(self) -> list[str]:
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
