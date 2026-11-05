
from PIL import Image
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Load captured game screenshot
image = Image.open("wgc_capture.png")

width, height = image.size

print("Screenshot:", width, "x", height)

# Bottom-left quarter
chat = image.crop((
    0,
    height // 2,
    width // 2,
    height
))

# Save cropped chat
chat.save("chat_crop.png")

# Enlarge image for better OCR
chat = chat.resize(
    (chat.width * 2, chat.height * 2)
)

# OCR
text = pytesseract.image_to_string(
    chat,
    config="--psm 6"
)

print("\nRecognized chat:")
print(text)
