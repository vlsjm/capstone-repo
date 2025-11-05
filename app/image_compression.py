from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


def compress_and_convert_to_binary(image_file, quality=85, max_dimension=1920):
    """
    Compress image and convert to binary data for PostgreSQL storage.
    
    Args:
        image_file: Django ImageField or UploadedFile object
        quality: JPEG quality (1-100, default 85 for good balance)
        max_dimension: Maximum width or height in pixels (default 1920)
    
    Returns:
        Tuple of (binary_data: bytes, size: int) or (None, 0) if compression fails
    """
    try:
        # Open the image
        img = Image.open(image_file)
        
        # Convert RGBA to RGB if necessary (for PNG with transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Calculate new dimensions while maintaining aspect ratio
        width, height = img.size
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int((max_dimension / width) * height)
            else:
                new_height = max_dimension
                new_width = int((max_dimension / height) * width)
            
            # Resize with high-quality resampling
            img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Save to BytesIO with compression
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        
        # Get binary data
        binary_data = output.getvalue()
        size = len(binary_data)
        
        return binary_data, size
        
    except Exception as e:
        # Log the error and return None
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Image compression to binary failed: {str(e)}")
        return None, 0


def compress_damage_report_image(image_file, quality=85, max_dimension=1920):
    """
    DEPRECATED: Legacy function for file-based storage.
    Use compress_and_convert_to_binary() for database storage instead.
    
    Compress and resize damage report images for efficient storage.
    
    Args:
        image_file: Django ImageField or UploadedFile object
        quality: JPEG quality (1-100, default 85 for good balance)
        max_dimension: Maximum width or height in pixels (default 1920)
    
    Returns:
        Compressed InMemoryUploadedFile or None if compression fails
    """
    try:
        # Open the image
        img = Image.open(image_file)
        
        # Convert RGBA to RGB if necessary (for PNG with transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Calculate new dimensions while maintaining aspect ratio
        width, height = img.size
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int((max_dimension / width) * height)
            else:
                new_height = max_dimension
                new_width = int((max_dimension / height) * width)
            
            # Resize with high-quality resampling
            img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Save to BytesIO with compression
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        # Create a new InMemoryUploadedFile
        compressed_file = InMemoryUploadedFile(
            output,
            'ImageField',
            f"{image_file.name.split('.')[0]}_compressed.jpg",
            'image/jpeg',
            sys.getsizeof(output),
            None
        )
        
        return compressed_file
        
    except Exception as e:
        # Log the error and return None to fall back to original image
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Image compression failed: {str(e)}")
        return None
