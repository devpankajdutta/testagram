import aioboto3
from fastapi import UploadFile, HTTPException
from app.config import settings
from app.models import ImageMetadata, ImageFilter
import uuid
import time
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

class StorageService:
    def __init__(self):
        self.session = aioboto3.Session()

    async def upload_file(self, file: UploadFile, filename: str) -> str:
        async with self.session.client("s3",
                                       region_name=settings.AWS_REGION,
                                       endpoint_url=settings.AWS_ENDPOINT_URL,
                                       aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                       aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as s3:
            try:
                # Upload file
                await s3.upload_fileobj(file.file, settings.BUCKET_NAME, filename)
                return filename
            except ClientError as e:
                raise HTTPException(status_code=500, detail=f"S3 Upload Failed: {e}")

    async def delete_file(self, filename: str):
        async with self.session.client("s3",
                                       region_name=settings.AWS_REGION,
                                       endpoint_url=settings.AWS_ENDPOINT_URL,
                                       aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                       aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as s3:
            try:
                await s3.delete_object(Bucket=settings.BUCKET_NAME, Key=filename)
            except ClientError as e:
                raise HTTPException(status_code=500, detail=f"S3 Delete Failed: {e}")

    async def generate_presigned_url(self, filename: str) -> str:
        async with self.session.client("s3",
                                       region_name=settings.AWS_REGION,
                                       endpoint_url=settings.AWS_ENDPOINT_URL,
                                       aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                       aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as s3:
            try:
                url = await s3.generate_presigned_url('get_object',
                                                      Params={'Bucket': settings.BUCKET_NAME,
                                                              'Key': filename},
                                                      ExpiresIn=3600)
                return url
            except ClientError as e:
                print(f"Error generating presigned URL: {e}")
                return ""

class DatabaseService:
    def __init__(self):
        self.session = aioboto3.Session()

    async def save_metadata(self, metadata: ImageMetadata):
        async with self.session.resource("dynamodb",
                                         region_name=settings.AWS_REGION,
                                         endpoint_url=settings.AWS_ENDPOINT_URL,
                                         aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                         aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as dynamo:
            table = await dynamo.Table(settings.TABLE_NAME)
            await table.put_item(Item=metadata.model_dump())

    async def get_metadata(self, image_id: str) -> ImageMetadata:
        async with self.session.resource("dynamodb",
                                         region_name=settings.AWS_REGION,
                                         endpoint_url=settings.AWS_ENDPOINT_URL,
                                         aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                         aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as dynamo:
            table = await dynamo.Table(settings.TABLE_NAME)
            response = await table.get_item(Key={'id': image_id})
            item = response.get('Item')
            if not item:
                return None
            return ImageMetadata(**item)

    async def delete_metadata(self, image_id: str):
        async with self.session.resource("dynamodb",
                                         region_name=settings.AWS_REGION,
                                         endpoint_url=settings.AWS_ENDPOINT_URL,
                                         aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                         aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as dynamo:
            table = await dynamo.Table(settings.TABLE_NAME)
            await table.delete_item(Key={'id': image_id})

    async def list_images(self, filter_params: ImageFilter) -> list[ImageMetadata]:
        async with self.session.resource("dynamodb",
                                         region_name=settings.AWS_REGION,
                                         endpoint_url=settings.AWS_ENDPOINT_URL,
                                         aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                         aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as dynamo:
            table = await dynamo.Table(settings.TABLE_NAME)
            
            # Simple scan with filter expression
            # Use FilterExpression for attributes
            scan_kwargs = {}
            filter_expression = None
            
            if filter_params.filename:
                # Use 'contains' for partial match
                condition = Attr('filename').contains(filter_params.filename)
                filter_expression = condition if filter_expression is None else filter_expression & condition
            
            if filter_params.tag:
                 # Check if tag is in tags list
                condition = Attr('tags').contains(filter_params.tag)
                filter_expression = condition if filter_expression is None else filter_expression & condition

            # Add more filters if needed (date logic needs ISO string comparison)
            
            if filter_expression:
                scan_kwargs['FilterExpression'] = filter_expression

            response = await table.scan(**scan_kwargs)
            items = response.get('Items', [])
            return [ImageMetadata(**item) for item in items]
