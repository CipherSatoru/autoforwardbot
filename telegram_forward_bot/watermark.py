"""
Telegram Forward Bot - Watermark Module
"""
from PIL import Image, ImageDraw, ImageFont
import io
from typing import Optional
import config

class WatermarkProcessor:
    def __init__(self):
        self.default_font_size = 24
    
    def add_text_watermark(self, image_data: bytes, text: str, 
                          position: str = 'bottom-right') -> bytes:
        """Add text watermark to image"""
        try:
            # Open image
            img = Image.open(io.BytesIO(image_data))
            
            # Convert to RGBA if necessary
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Create transparent overlay
            overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Try to use a font, fallback to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 
                                         self.default_font_size)
            except:
                font = ImageFont.load_default()
            
            # Calculate text size
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Calculate position
            padding = 20
            img_width, img_height = img.size
            
            if position == 'bottom-right':
                x = img_width - text_width - padding
                y = img_height - text_height - padding
            elif position == 'bottom-left':
                x = padding
                y = img_height - text_height - padding
            elif position == 'top-right':
                x = img_width - text_width - padding
                y = padding
            elif position == 'top-left':
                x = padding
                y = padding
            elif position == 'center':
                x = (img_width - text_width) // 2
                y = (img_height - text_height) // 2
            else:
                x = img_width - text_width - padding
                y = img_height - text_height - padding
            
            # Draw semi-transparent background
            bg_padding = 5
            draw.rectangle(
                [x - bg_padding, y - bg_padding, 
                 x + text_width + bg_padding, y + text_height + bg_padding],
                fill=(0, 0, 0, 128)
            )
            
            # Draw text
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
            
            # Composite images
            result = Image.alpha_composite(img, overlay)
            
            # Convert back to RGB for JPEG compatibility
            if result.mode == 'RGBA':
                # Create white background
                background = Image.new('RGB', result.size, (255, 255, 255))
                background.paste(result, mask=result.split()[3])  # Use alpha channel as mask
                result = background
            
            # Save to bytes
            output = io.BytesIO()
            result.save(output, format='JPEG', quality=95)
            output.seek(0)
            
            return output.getvalue()
            
        except Exception as e:
            print(f"Watermark error: {e}")
            return image_data  # Return original if error
    
    async def process_photo_with_watermark(self, bot, photo_file_id: str, 
                                           watermark_text: str, 
                                           position: str = 'bottom-right') -> bytes:
        """Download photo and add watermark"""
        try:
            # Download the photo
            file = await bot.get_file(photo_file_id)
            image_data = await file.download_as_bytearray()
            
            # Add watermark
            return self.add_text_watermark(bytes(image_data), watermark_text, position)
            
        except Exception as e:
            print(f"Photo watermark error: {e}")
            return None

# Global watermark processor
watermark_processor = WatermarkProcessor()
