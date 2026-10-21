import re
import edge_tts
from config import TTS_VOICE

def clean_text_for_speech(text: str) -> str:
    """Markdown belgilari va keraksiz simvollarni tozalab, sof nutq matniga aylantiradi."""
    # Sarlavhalar va keraksiz belgilarni tozalash
    cleaned = re.sub(r'[*_#`~>\[\]\(\)\{\}\\\/]', ' ', text)
    # Ortiqcha chiziqcha va belgilarni to'g'rilash
    cleaned = re.sub(r'[-–—]', ', ', cleaned)
    # Ko'p bo'shliqlarni bitta bo'shliqqa keltirish
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

async def generate_speech(text: str, output_file_path: str, voice: str = TTS_VOICE) -> str:
    """Matnni dona-dona, jarangli va insondek tabiiy ovozga aylantiradi."""
    cleaned_text = clean_text_for_speech(text)
    
    if not cleaned_text:
        cleaned_text = "Dars mazmuni tushunarli bo'ldi."

    # rate='-6%': nutq shoshilmasdan, har bir so'z dona-dona eshitilishi uchun
    # pitch='+1Hz': ovoz jarangli va jonli chiqishi uchun
    communicate = edge_tts.Communicate(
        cleaned_text,
        voice=voice,
        rate="-6%",
        pitch="+1Hz"
    )
    await communicate.save(output_file_path)
    return output_file_path
