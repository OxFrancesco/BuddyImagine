import os
import aioboto3
from typing import cast
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class R2Service:
    def __init__(self):
        self.access_key = os.getenv("R2_ACCESS_KEY_ID")
        self.secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("R2_BUCKET_NAME")
        self.endpoint_url = os.getenv("R2_ENDPOINT_URL")
        
        if not all([self.access_key, self.secret_key, self.bucket_name, self.endpoint_url]):
             logger.warning("R2 credentials missing. R2 service may not work.")

        self.session = aioboto3.Session()

    async def upload_file(self, file_data: bytes, filename: str, content_type: str = "image/jpeg") -> str:
        """
        Uploads a file to Cloudflare R2.
        
        Args:
            file_data: The binary content of the file.
            filename: The name to save the file as.
            content_type: The MIME type of the file.
            
        Returns:
            The filename of the uploaded file.
        """
        async with self.session.client("s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="auto" # R2 requires region to be 'auto'
        ) as s3:
            try:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=filename,
                    Body=file_data,
                    ContentType=content_type
                )
                logger.info(f"Successfully uploaded {filename} to R2")
                return filename
                
            except ClientError as e:
                logger.error(f"Failed to upload to R2: {e}")
                raise

    async def download_file(self, filename: str) -> bytes:
        """
        Downloads a file from Cloudflare R2.
        
        Args:
            filename: The name of the file to download.
            
        Returns:
            The binary content of the file.
        """
        async with self.session.client("s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="auto"
        ) as s3:
            try:
                response = await s3.get_object(Bucket=self.bucket_name, Key=filename)
                return cast(bytes, await response['Body'].read())
            except ClientError as e:
                logger.error(f"Failed to download {filename} from R2: {e}")
                raise

    async def get_presigned_url(self, filename: str, expires_in: int = 3600) -> str:
        """
        Generates a presigned URL for accessing a file in R2.
        
        Args:
            filename: The name of the file.
            expires_in: URL expiration time in seconds (default: 1 hour).
            
        Returns:
            A presigned URL that can be used to access the file.
        """
        async with self.session.client("s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="auto"
        ) as s3:
            try:
                url = await s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': filename},
                    ExpiresIn=expires_in
                )
                return str(url)
            except ClientError as e:
                logger.error(f"Failed to generate presigned URL for {filename}: {e}")
                raise