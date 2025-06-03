import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64

def generate_barcode(code):
    """Generate a Code128 barcode and return it as a base64 encoded string."""
    # Create barcode instance
    code128 = barcode.get_barcode_class('code128')
    
    # Generate the barcode
    rv = BytesIO()
    code128(code, writer=ImageWriter()).write(rv)
    
    # Convert to base64
    image_base64 = base64.b64encode(rv.getvalue()).decode()
    return f"data:image/png;base64,{image_base64}" 