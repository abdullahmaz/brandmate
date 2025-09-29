import base64
import io
from PIL import Image
from typing import Optional
import os
from diffusers import StableDiffusionPipeline
import torch
import gc

class ImageGenerator:
    def __init__(self):
        # Using local Stable Diffusion model
        model_name = "runwayml/stable-diffusion-v1-5"
        print(f"Loading local image generation model: {model_name}")
        
        try:
            # Load the pipeline with optimizations
            self.pipe = StableDiffusionPipeline.from_pretrained(
                model_name,
                dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                safety_checker=None,
                requires_safety_checker=False,
                use_safetensors=True,  # Faster loading
            )
            
            # Move to GPU if available
            if torch.cuda.is_available():
                self.pipe = self.pipe.to("cuda")
                print(f"Using GPU for image generation: {torch.cuda.get_device_name(0)}")
                print(f"CUDA Version: {torch.version.cuda}")
            else:
                print("Using CPU for image generation")
                
            print("Image generation model loaded successfully!")
            
            # Enable memory optimization
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print(f"GPU memory cleared. Available: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
                
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
        """
        style_enhancements = {
            "eastern_clothing": "Eastern clothing, Pakistani/Indian fashion, traditional and modern fusion, vibrant colors, elegant designs",
            "summer_collection": "Summer lawn collection, light fabrics, floral patterns, pastel colors, breathable materials",
            "winter_collection": "Winter khaddar collection, warm fabrics, rich colors, traditional patterns, cozy designs",
            "formal_wear": "Formal Eastern wear, elegant cuts, sophisticated designs, professional attire",
            "casual_wear": "Casual Eastern clothing, comfortable fits, everyday wear, modern styles"
        }
        
        enhancement = style_enhancements.get(style, style_enhancements["eastern_clothing"])
        
        return f"{prompt}, {enhancement}, high quality, professional photography, marketing poster, clean background, brand showcase"
    
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
