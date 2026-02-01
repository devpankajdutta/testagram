import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app
from app.config import settings
import aioboto3

# Verify we are in test environment (e.g. check standard env vars or override keys)
# For this setup, we'll assume LocalStack is running and we can use it.
# We might want to use a different bucket/table for tests.
TEST_BUCKET = "test-images-bucket"
TEST_TABLE = "test-images-table"

@pytest_asyncio.fixture(scope="session") # Create once per session or function
async def aws_setup():
    # Override settings for tests
    settings.BUCKET_NAME = TEST_BUCKET
    settings.TABLE_NAME = TEST_TABLE
    
    session = aioboto3.Session()
    
    # 1. Create Bucket
    async with session.client("s3", 
                              region_name=settings.AWS_REGION, 
                              endpoint_url=settings.AWS_ENDPOINT_URL,
                              aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as s3:
        try:
            await s3.create_bucket(Bucket=TEST_BUCKET)
        except:
            pass # Bucket might exist

    # 2. Create Table
    async with session.resource("dynamodb",
                                region_name=settings.AWS_REGION, 
                                endpoint_url=settings.AWS_ENDPOINT_URL,
                                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as dynamo:
        try:
            await dynamo.create_table(
                TableName=TEST_TABLE,
                KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
        except:
            pass # Table might exist

    yield

    # Teardown (Optional: Clear bucket/table)
    # For now, we leave them dirty or rely on logic to clean specific items if needed

@pytest_asyncio.fixture
async def client(aws_setup):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
