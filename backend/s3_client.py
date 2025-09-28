import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import uuid
from datetime import datetime

load_dotenv()

class S3Client:
    def __init__(self):
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region_name = os.getenv("AWS_REGION", "us-east-1")
        self.bucket_name = os.getenv("S3_BUCKET_NAME")
        self.s3_client = None
        
        if not all([self.aws_access_key_id, self.aws_secret_access_key, self.bucket_name]):
            print("WARNING: AWS credentials and S3_BUCKET_NAME not set. File storage features will be disabled.")
            print(f"DEBUG: AWS_ACCESS_KEY_ID: {'SET' if self.aws_access_key_id else 'NOT SET'}")
            print(f"DEBUG: AWS_SECRET_ACCESS_KEY: {'SET' if self.aws_secret_access_key else 'NOT SET'}")
            print(f"DEBUG: S3_BUCKET_NAME: {'SET' if self.bucket_name else 'NOT SET'}")
            return
        
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name
            )
            print("S3 client initialized successfully")
        except Exception as e:
            print(f"Error initializing S3 client: {e}")
            self.s3_client = None
    
    async def upload_file(self, file_content: bytes, file_extension: str, folder: str = "generated") -> str:
        """Upload file to S3 and return the URL"""
        if not self.s3_client:
            raise Exception("S3 client not available. Please check your AWS credentials.")
            
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{folder}/{timestamp}_{unique_id}.{file_extension}"
            
            # Upload file with public read access
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=file_content,
                ContentType=self._get_content_type(file_extension),
                ACL='public-read'  # Make the object publicly readable
            )
            
            # Return public URL
            url = f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{filename}"
            return url
            
        except ClientError as e:
            print(f"Error uploading file to S3: {e}")
            raise Exception(f"Failed to upload file: {str(e)}")
    
    async def upload_image(self, image_content: bytes, folder: str = "images") -> str:
        """Upload image to S3 and return the URL"""
        print(f"DEBUG: Uploading image to S3 folder: {folder}")
        print(f"DEBUG: Image content size: {len(image_content)} bytes")
        return await self.upload_file(image_content, "png", folder)
    
    def _get_content_type(self, file_extension: str) -> str:
        """Get content type based on file extension"""
        content_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "mp4": "video/mp4",
            "webm": "video/webm",
            "html": "text/html",
            "css": "text/css",
            "js": "application/javascript",
            "json": "application/json"
        }
        return content_types.get(file_extension.lower(), "application/octet-stream")

# Global instance
s3_client = S3Client()
