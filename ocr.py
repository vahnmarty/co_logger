
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

print("Tesseract version:")
print(pytesseract.get_tesseract_version())

# Create a simple test image
image = Image.new("RGB", (500, 100), "white")

from PIL import ImageDraw

draw = ImageDraw.Draw(image)
draw.text((10, 30), "Talk Hello", fill="black")

# Run OCR
text = pytesseract.image_to_string(image)

print("\nRecognized text:")
print(text)
