import os
from typing import Optional
import boto3
from botocore.client import Config
from src.runtime.config.settings import Settings

class StorageAdapter:
    def upload_file(self, file_path: str, key: str) -> bool:
        raise NotImplementedError

    def download_file(self, key: str, dest_path: str) -> bool:
        raise NotImplementedError

    def delete_file(self, key: str) -> bool:
        raise NotImplementedError

    def generate_signed_download_url(self, key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError

    def generate_signed_upload_url(self, key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError


class LocalFileStorageAdapter(StorageAdapter):
    """Fallback local filesystem storage adapter for local testing."""
    def __init__(self, base_dir: str = "data/storage"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def upload_file(self, file_path: str, key: str) -> bool:
        dest = os.path.join(self.base_dir, key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        import shutil
        shutil.copyfile(file_path, dest)
        return True

    def download_file(self, key: str, dest_path: str) -> bool:
        src = os.path.join(self.base_dir, key)
        if not os.path.exists(src):
            return False
        import shutil
        shutil.copyfile(src, dest_path)
        return True

    def delete_file(self, key: str) -> bool:
        src = os.path.join(self.base_dir, key)
        if os.path.exists(src):
            os.remove(src)
            return True
        return False

    def generate_signed_download_url(self, key: str, expires_in: int = 3600) -> str:
        return f"file://{os.path.abspath(os.path.join(self.base_dir, key))}"

    def generate_signed_upload_url(self, key: str, expires_in: int = 3600) -> str:
        return f"file://{os.path.abspath(os.path.join(self.base_dir, key))}"


class CloudflareR2Adapter(StorageAdapter):
    def __init__(self):
        self.bucket = Settings.R2_BUCKET
        self.client = boto3.client(
            service_name="s3",
            endpoint_url=Settings.R2_ENDPOINT,
            aws_access_key_id=Settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=Settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto"
        )

    def upload_file(self, file_path: str, key: str) -> bool:
        try:
            self.client.upload_file(file_path, self.bucket, key)
            return True
        except Exception as e:
            print(f"R2 Upload Error: {e}", flush=True)
            return False

    def download_file(self, key: str, dest_path: str) -> bool:
        try:
            dir_name = os.path.dirname(dest_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            self.client.download_file(self.bucket, key, dest_path)
            return True
        except Exception as e:
            print(f"R2 Download Error: {e}", flush=True)
            return False

    def delete_file(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as e:
            print(f"R2 Delete Error: {e}", flush=True)
            return False

    def generate_signed_download_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            return self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in
            )
        except Exception as e:
            print(f"R2 Presign Download Error: {e}", flush=True)
            return ""

    def generate_signed_upload_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            return self.client.generate_presigned_url(
                ClientMethod="put_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in
            )
        except Exception as e:
            print(f"R2 Presign Upload Error: {e}", flush=True)
            return ""
