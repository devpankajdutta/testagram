from fastapi import FastAPI
from contextlib import asynccontextmanager
import aioboto3
from app.config import settings, fetch_ssm_params
from app.routers import images
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Starting up...")
    
    # 1. Fetch SSM Params
    await fetch_ssm_params()

    # 2. Bootstrap LocalStack (Ensure Bucket and Table exist)
    # Only do this if we are in dev/local environment
    if settings.ENV == "dev" or settings.ENV == "local":
        session = aioboto3.Session()
        
        # S3 Bootstrap
        try:
            async with session.client("s3", 
                                      region_name=settings.AWS_REGION, 
                                      endpoint_url=settings.aws_endpoint,
                                      aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as s3:
                try:
                    await s3.head_bucket(Bucket=settings.BUCKET_NAME)
                    print(f"Bucket {settings.BUCKET_NAME} exists.")
                except:
                    print(f"Creating bucket {settings.BUCKET_NAME}...")
                    await s3.create_bucket(Bucket=settings.BUCKET_NAME)
        except Exception as e:
            print(f"Failed to bootstrap S3: {e}")

        # DynamoDB Bootstrap
        try:
            async with session.resource("dynamodb",
                                        region_name=settings.AWS_REGION, 
                                        endpoint_url=settings.aws_endpoint,
                                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as dynamo:
                table = await dynamo.Table(settings.TABLE_NAME)
                try:
                    await table.load()
                    print(f"Table {settings.TABLE_NAME} exists.")
                except:
                    print(f"Creating table {settings.TABLE_NAME}...")
                    await dynamo.create_table(
                        TableName=settings.TABLE_NAME,
                        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
                        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
                        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    )
        except Exception as e:
            print(f"Failed to bootstrap DynamoDB: {e}")

    yield
    print("Shutting down...")

import os
root_path = os.environ.get("ROOT_PATH", "")
app = FastAPI(title="Testagram Image Service", lifespan=lifespan, root_path=root_path)

app.include_router(images.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Testagram Image Service"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, env_file="dev.env")

# Adapter for AWS Lambda
from mangum import Mangum
handler = Mangum(app)
