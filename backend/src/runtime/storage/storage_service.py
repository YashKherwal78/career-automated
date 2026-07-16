from src.runtime.config.settings import Settings
from src.runtime.storage.storage_adapter import (
    StorageAdapter,
    LocalFileStorageAdapter,
    CloudflareR2Adapter
)

class StorageService:
    _adapter: StorageAdapter = None

    @classmethod
    def get_adapter(cls) -> StorageAdapter:
        if cls._adapter is None:
            if not Settings.R2_ENDPOINT or not Settings.R2_ACCESS_KEY_ID:
                if Settings.ENABLE_LOCAL_FALLBACKS or Settings.APP_ENV == "development":
                    print("WARNING: R2 credentials not configured. Falling back to LocalFileStorageAdapter.", flush=True)
                    cls._adapter = LocalFileStorageAdapter()
                else:
                    raise ValueError("Cloudflare R2 credentials (R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY) must be configured in production mode.")
            else:
                cls._adapter = CloudflareR2Adapter()
        return cls._adapter

    @classmethod
    def upload_file(cls, file_path: str, key: str) -> bool:
        return cls.get_adapter().upload_file(file_path, key)

    @classmethod
    def download_file(cls, key: str, dest_path: str) -> bool:
        return cls.get_adapter().download_file(key, dest_path)

    @classmethod
    def delete_file(cls, key: str) -> bool:
        return cls.get_adapter().delete_file(key)

    @classmethod
    def generate_signed_download_url(cls, key: str, expires_in: int = 3600) -> str:
        return cls.get_adapter().generate_signed_download_url(key, expires_in)

    @classmethod
    def generate_signed_upload_url(cls, key: str, expires_in: int = 3600) -> str:
        return cls.get_adapter().generate_signed_upload_url(key, expires_in)
