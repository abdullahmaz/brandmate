import base64
import io
from PIL import Image
from typing import Optional
import os
from diffusers import DiffusionPipeline
import torch
import gc

class ImageGenerator:
    def __init__(self):
        # Using Openjourney model (fine-tuned on Midjourney images)
        model_name = "prompthero/openjourney"
        print(f"Loading Openjourney image generation model: {model_name}")
        
        try:
            # Load the pipeline with optimizations
            self.pipe = DiffusionPipeline.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                use_safetensors=True,  # Faster loading
            )
            
            print("Image generation model loaded successfully!")
            
                
        except Exception as e:
            print(f"Error loading image model: {e}")
            self.pipe = None
    
    async def generate_image(self, prompt: str, style: str = "eastern_clothing") -> Optional[str]:
        """
        Generate an image using local Stable Diffusion
        """
        if self.pipe is None:
            print("Image generation model not loaded, returning placeholder")
            return self._create_placeholder_image(prompt)
        
        try:
            # Enhance prompt for Eastern clothing
            enhanced_prompt = self._enhance_prompt_for_eastern_clothing(prompt, style)
            
            print(f"Generating image with prompt: {enhanced_prompt}")
            
            # Generate image
            with torch.no_grad():
                image = self.pipe(
                    enhanced_prompt,
                    num_inference_steps=20,
                    guidance_scale=7.5,
                    width=512,
                    height=512
                ).images[0]
            
            # Convert to base64 for web display
            buffer = io.BytesIO()
            image.save(buffer, format='PNG', optimize=True)  # Optimize PNG compression
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
                
        except Exception as e:
            print(f"Error generating image: {e}")
            return self._create_placeholder_image(prompt)
    
    def _enhance_prompt_for_eastern_clothing(self, prompt: str, style: str) -> str:
        """
        Enhance the prompt to be more specific for Eastern clothing brands
        Note: Openjourney requires 'mdjrny-v4 style' prefix for best results
        """
        return f"mdjrny-v4 style, {prompt}, {style}, high quality, professional photography, marketing poster, clean background, brand showcase"
    
    def _create_placeholder_image(self, prompt: str) -> str:
        """
        Create a placeholder image for demo purposes
        """
        # Create a simple placeholder image
        img = Image.new('RGB', (512, 512), color='#f0f0f0')
        
        # Convert to base64 for web display
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def _save_generated_image(self, image_data: bytes, filename: str) -> str:
        """
        Save generated image to file system
        """
        # In production, you'd save to a proper file storage system
        # For now, we'll just return the base64 data
        return base64.b64encode(image_data).decode()
