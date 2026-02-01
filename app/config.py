import os
from contextlib import asynccontextmanager
from typing import Optional

from pydantic_settings import BaseSettings
from botocore.exceptions import ClientError
import aioboto3

class Settings(BaseSettings):
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = "test"
    AWS_SECRET_ACCESS_KEY: str = "test"
    AWS_ENDPOINT_URL: Optional[str] = None
    ENV: str = "dev"
    
    # These will be populated from SSM or defaults
    BUCKET_NAME: str = "testagram-images"
    TABLE_NAME: str = "testagram-metadata"

    @property
    def aws_endpoint(self) -> Optional[str]:
        if self.AWS_ENDPOINT_URL:
            return self.AWS_ENDPOINT_URL
        localstack_host = os.environ.get("LOCALSTACK_HOSTNAME")
        if localstack_host:
            return f"http://{localstack_host}:4566"
        return None

    model_config = {
        "env_file": "dev.env",
        "extra": "ignore"
    }

settings = Settings()

async def fetch_ssm_params():
    """
    Fetches configuration from SSM Parameter Store.
    Updates the global settings object.
    """
    session = aioboto3.Session()
    print(f"DEBUG: Session created. Connecting to SSM at {settings.AWS_ENDPOINT_URL}", flush=True)
    try:
        async with session.client("ssm", 
                                  region_name=settings.AWS_REGION,
                                  endpoint_url=settings.aws_endpoint,
                                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as ssm:
            print("DEBUG: SSM Client created. Fetching parameters...", flush=True)
            # Example: Fetching /testagram/bucket_name and /testagram/table_name
            response = await ssm.get_parameters(
                Names=["/testagram/bucket_name", "/testagram/table_name"],
                WithDecryption=True
            )
            print("DEBUG: SSM Response received.", flush=True)
            
            for param in response.get("Parameters", []):
                if param["Name"] == "/testagram/bucket_name":
                    settings.BUCKET_NAME = param["Value"]
                elif param["Name"] == "/testagram/table_name":
                    settings.TABLE_NAME = param["Value"]
                    
            print(f"Loaded config from SSM: Bucket={settings.BUCKET_NAME}, Table={settings.TABLE_NAME}")
            
    except ClientError as e:
        print(f"Failed to fetch parameters from SSM: {e}")
        print("Using default values or env vars.")

