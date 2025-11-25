import base64
import io
from PIL import Image
from typing import Optional
import os
from pathlib import Path
from diffusers import DiffusionPipeline
import torch
import gc

class ImageGenerator:
    def __init__(self, lora_path: Optional[str] = None):
        # Using Openjourney model (fine-tuned on Midjourney images)
        model_name = "prompthero/openjourney"

        print(f"Loading Openjourney image generation model: {model_name}")
        
        # Initialize LoRA loaded flag
        self.lora_loaded = False
        
        try:
            # Determine device and dtype
            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            
            # Load the pipeline with optimizations
            self.pipe = DiffusionPipeline.from_pretrained(
                model_name,
                torch_dtype=dtype,
                use_safetensors=True,  # Faster loading
            )
            
            # Move pipeline to device
            if torch.cuda.is_available():
                self.pipe = self.pipe.to(device)
            
            # Load fine-tuned LoRA weights if provided
            if lora_path:
                self._load_lora_weights(lora_path)
            else:
                # Try to load from default location
                default_lora_path = self._get_default_lora_path()
                if default_lora_path and os.path.exists(default_lora_path):
                    print(f"Found LoRA weights at default location: {default_lora_path}")
                    self._load_lora_weights(default_lora_path)
            
            if self.lora_loaded:
                print("✅ Image generation model loaded with fine-tuned LoRA weights!")
            else:
                print("✅ Image generation model loaded successfully! (using base model)")
            
                
        except Exception as e:
            print(f"Error loading image model: {e}")
            self.pipe = None
    
    def _get_default_lora_path(self) -> Optional[str]:
        """Get the default path to the fine-tuned LoRA model"""
        # Get the backend directory (current file location)
        backend_dir = Path(__file__).parent
        project_root = backend_dir.parent
        
        # Path to the fine-tuned LoRA checkpoint
        lora_path = project_root / "fine_tuning" / "models" / "fashion_lora" / "checkpoint-final"
        
        return str(lora_path) if lora_path.exists() else None
    
    def _load_lora_weights(self, lora_path: str):
        """
        Load LoRA weights from the fine-tuned model.
        Supports PEFT format (separate unet_lora and text_encoder_lora folders).
        """
        lora_path = Path(lora_path)
        
        if not lora_path.exists():
            print(f"Warning: LoRA path does not exist: {lora_path}")
            return
        
        try:
            unet_lora_path = lora_path / "unet_lora"
            text_encoder_lora_path = lora_path / "text_encoder_lora"
            
            if unet_lora_path.exists() and text_encoder_lora_path.exists():
                # Use PEFT to load and merge LoRA weights (PEFT format from training)
                try:
                    from peft import PeftModel
                    
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
                    
                    # Load UNet LoRA adapter
                    print(f"Loading UNet LoRA from: {unet_lora_path}")
                    unet_peft = PeftModel.from_pretrained(
                        self.pipe.unet,
                        str(unet_lora_path),
                        torch_dtype=dtype,
                    )
                    
                    # Merge LoRA weights into base UNet model
                    print("Merging UNet LoRA weights into base model...")
                    merged_unet = unet_peft.merge_and_unload()
                    
                    # Replace pipeline UNet with merged model and ensure correct device/dtype
                    self.pipe.unet = merged_unet.to(device=device, dtype=dtype)
                    self.pipe.unet.eval()
                    print("✅ UNet LoRA weights merged successfully")
                    
                    # Load Text Encoder LoRA adapter
                    print(f"Loading Text Encoder LoRA from: {text_encoder_lora_path}")
                    text_encoder_peft = PeftModel.from_pretrained(
                        self.pipe.text_encoder,
                        str(text_encoder_lora_path),
                        torch_dtype=dtype,
                    )
                    
                    # Merge LoRA weights into base Text Encoder model
                    print("Merging Text Encoder LoRA weights into base model...")
                    merged_text_encoder = text_encoder_peft.merge_and_unload()
                    
                    # Replace pipeline Text Encoder with merged model and ensure correct device/dtype
                    self.pipe.text_encoder = merged_text_encoder.to(device=device, dtype=dtype)
                    self.pipe.text_encoder.eval()
                    print("✅ Text Encoder LoRA weights merged successfully")
                    
                    # Ensure VAE is also on correct device (it should be, but double-check)
                    self.pipe.vae = self.pipe.vae.to(device=device, dtype=dtype)
                    self.pipe.vae.eval()
                    
                    # Clear memory from PEFT models (no longer needed)
                    del unet_peft, text_encoder_peft
                    torch.cuda.empty_cache() if torch.cuda.is_available() else None
                    
                    # Enable memory optimizations for inference
                    try:
                        if hasattr(self.pipe, 'enable_attention_slicing'):
                            self.pipe.enable_attention_slicing(1)
                        if hasattr(self.pipe, 'enable_vae_slicing'):
                            self.pipe.enable_vae_slicing()
                    except Exception as e:
                        print(f"Note: Could not enable memory optimizations: {e}")
                    
                    print("✅ Successfully merged fine-tuned LoRA weights into base model!")
                    print(f"✅ All pipeline components on device: {device}")
                    self.lora_loaded = True
                    
                except ImportError:
                    print("⚠️  PEFT library not found. Install it with: pip install peft")
                    print("⚠️  LoRA weights will not be loaded. Using base model only.")
                    self.lora_loaded = False
                except Exception as e:
                    print(f"⚠️  Error loading LoRA weights with PEFT: {e}")
                    import traceback
                    traceback.print_exc()
                    print("⚠️  Continuing with base model only.")
                    self.lora_loaded = False
            else:
                print(f"⚠️  LoRA directories not found at: {lora_path}")
                print(f"   Looking for: {unet_lora_path} and {text_encoder_lora_path}")
                self.lora_loaded = False
                
        except Exception as e:
            print(f"⚠️  Error loading LoRA weights: {e}")
            import traceback
            traceback.print_exc()
            print("⚠️  Continuing with base model only.")
            self.lora_loaded = False
    
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
            
            # Ensure pipeline is ready for inference
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Verify all components are on correct device
            if torch.cuda.is_available():
                self.pipe.unet = self.pipe.unet.to(device)
                self.pipe.text_encoder = self.pipe.text_encoder.to(device)
                self.pipe.vae = self.pipe.vae.to(device)
            
            # Ensure models are in eval mode
            self.pipe.unet.eval()
            self.pipe.text_encoder.eval()
            self.pipe.vae.eval()
            
            # Generate image
            print(f"Starting generation on device: {device}...")
            print(f"UNet device: {next(self.pipe.unet.parameters()).device}")
            print(f"Text Encoder device: {next(self.pipe.text_encoder.parameters()).device}")
            print(f"VAE device: {next(self.pipe.vae.parameters()).device}")
            
            # Get negative prompt to avoid weird faces and artifacts
            negative_prompt = self._get_negative_prompt()
            
            with torch.no_grad():
                try:
                    image = self.pipe(
                        enhanced_prompt,
                        negative_prompt=negative_prompt,
                        num_inference_steps=50,  # Reduced from 80 for faster generation with similar quality
                        guidance_scale=7.5,  # Lowered from 15 - too high can cause artifacts
                        width=512,
                        height=512,
                        output_type="pil"  # Explicitly request PIL image
                    ).images[0]
                except RuntimeError as e:
                    if "device" in str(e).lower() or "dtype" in str(e).lower():
                        print(f"Device/dtype error detected. Attempting to fix...")
                        # Force all components to same device
                        if torch.cuda.is_available():
                            self.pipe.unet = self.pipe.unet.cuda()
                            self.pipe.text_encoder = self.pipe.text_encoder.cuda()
                            self.pipe.vae = self.pipe.vae.cuda()
                        # Retry
                        image = self.pipe(
                            enhanced_prompt,
                            negative_prompt=negative_prompt,
                            num_inference_steps=50,
                            guidance_scale=7.5,
                            width=512,
                            height=512,
                            output_type="pil"
                        ).images[0]
                    else:
                        raise
            
            print(f"✅ Image generated successfully!")
            
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
        Enhance the prompt to be more specific for Eastern clothing brands.
        If LoRA is loaded, we can use simpler prompts since the model is already trained on fashion data.
        """
        # Face quality terms to prevent weird faces
        face_quality = "realistic face, natural facial features, proper facial proportions, detailed eyes, natural skin texture"
        
        # Check if LoRA is loaded (use simpler prompts)
        if hasattr(self, 'lora_loaded') and self.lora_loaded:
            # With fine-tuned model, add face quality terms
            return f"{prompt}, {style}, {face_quality}, high quality, professional photography, clean background"
        else:
            # Base model needs more specific instructions
            return f"mdjrny-v4 style, {prompt}, {style}, {face_quality}, high quality, professional photography, marketing poster, clean background, brand showcase"
    
    def _get_negative_prompt(self) -> str:
        """
        Get negative prompt to avoid common generation issues, especially weird faces.
        """
        return (
            "distorted face, deformed face, disfigured face, ugly face, weird face, "
            "blurry face, asymmetrical face, cartoon face, painting face, "
            "extra limbs, extra fingers, missing fingers, bad anatomy, "
            "bad proportions, gross proportions, malformed hands, "
            "mutated, mutation, distorted, bad art, low quality, "
            "blurry, bad eyes, cross eyed, uncanny valley, "
            "double face, multiple faces, cloned face, warped features"
        )
    
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
