import os
import aioboto3
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
            content_type: The MIME type of the file. Defaults to "image/jpeg".
            
        Returns:
            The filename (key) of the uploaded file.
        """
        async with self.session.client("s3",
                                       endpoint_url=self.endpoint_url,
                                       aws_access_key_id=self.access_key,
                                       aws_secret_access_key=self.secret_key) as s3:
            try:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=filename,
                    Body=file_data,
                    ContentType=content_type
                )
                logger.info(f"Successfully uploaded {filename} to R2")
                
                # Return a theoretical public URL. 
                # Note: You need to configure a custom domain or public bucket access in Cloudflare for this to be directly accessible via HTTP.
                # If using the R2.dev subdomain, it would look like https://pub-<hash>.r2.dev/<filename>
                # For now, we'll return the filename/key.
                return filename
                
            except ClientError as e:
                logger.error(f"Failed to upload to R2: {e}")
                raise
