import base64
import io
from typing import Optional
from s3_client import s3_client
from database_models import MessageType

class StorageService:
    def __init__(self):
        self.s3 = s3_client
    
    async def store_generated_image(self, image_data_url: str, prompt: str) -> str:
        """Store generated image in S3 and return URL"""
        try:
            # Handle both data URL and plain base64
            if image_data_url.startswith('data:image/'):
                # Extract base64 part from data URL
                image_base64 = image_data_url.split(',')[1]
            else:
                # Assume it's already base64
                image_base64 = image_data_url
            
            # Decode base64 image
            image_data = base64.b64decode(image_base64)
            
            # Upload to S3
            s3_url = await self.s3.upload_image(image_data, "generated_images")
            
            print(f"Successfully uploaded image to S3: {s3_url}")
            return s3_url
            
        except Exception as e:
            print(f"Error storing generated image: {e}")
            raise Exception(f"Failed to store image: {str(e)}")
    
    async def store_generated_content(self, content: str, content_type: str, filename: str) -> str:
        """Store generated content (text, HTML, etc.) in S3 and return URL"""
        try:
            # Determine file extension based on content type
            file_extension = self._get_extension_for_content_type(content_type)
            
            # Convert content to bytes
            content_bytes = content.encode('utf-8')
            
            # Upload to S3
            s3_url = await self.s3.upload_file(content_bytes, file_extension, "generated_content")
            
            return s3_url
            
        except Exception as e:
            print(f"Error storing generated content: {e}")
            raise Exception(f"Failed to store content: {str(e)}")
    
    def _get_extension_for_content_type(self, content_type: str) -> str:
        """Get file extension based on content type"""
        extensions = {
            "text": "txt",
            "html": "html",
            "css": "css",
            "javascript": "js",
            "json": "json",
            "markdown": "md"
        }
        return extensions.get(content_type.lower(), "txt")
    
    def get_message_type_from_tool(self, tool_name: str) -> MessageType:
        """Get message type based on tool used"""
        tool_to_type = {
            "image_generation": MessageType.IMAGE,
            "text_generation": MessageType.TEXT,
            "video_generation": MessageType.VIDEO,
            "website_generation": MessageType.WEBSITE
        }
        return tool_to_type.get(tool_name, MessageType.TEXT)

# Global instance
storage_service = StorageService()
