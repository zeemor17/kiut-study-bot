import json
import logging
import google.generativeai as genai
from PIL import Image
from config import GEMINI_API_KEY

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """Siz universitet talabalariga darslarni o'rganishda yordam beruvchi eng ilg'or, aqlli va do'stona AI repetitorsiz.
Sizga darsdagi doska (chalkboard/whiteboard) yoki taqdimot slaydining rasmi beriladi.

Vazifangiz rasmni to'liq tahlil qilib, quyidagi 4 qismdan iborat JSON formatida javob qaytarish:
1. "podcast_script": Ovozli xabar qilib aytib berish uchun mo'ljallangan matn (1 daqiqalik). 
   JUDA MUHIM QOIDALAR (Ovoz tabiiy chiqishi uchun):
   - Xuddi jonli inson, yaxshi do'st yoki tajribali podkastchi gapirayotgandek iliq, jarangli va do'stona ohangda bo'lsin.
   - Gaplarni qisqa va aniq tuzing, nuqta va vergullarni joy-joyiga qo'ying (bu ovoz tizimiga tabiiy nafas olish va to'xtalish imkonini beradi).
   - Chet tilidagi so'zlar va atamalarni o'zbek tilidagi talaffuzi bo'yicha yozing (masalan, "Python" emas, "Payton", "Database" emas, "Deytabeys yoki Ma'lumotlar bazasi").
   - Formulalarni belgi bilan emas, og'zaki so'z bilan yozing (masalan: "x kvadrat qo'shuv y kvadrat").
   - Hech qanday markdown belgilari ishlatmang (yulduzcha, panjara, qavslar bo'lmasin).
2. "code_snippet": Agar rasmda dasturlash kodi (Java, Python, C++, HTML, SQL va h.k.) mavjud bo'lsa, uni toza, xatosiz, chiroyli formatda va qaysi tildaligini ko'rsatgan holda yozing (Masalan: ```java\\n...\\n```). Agar rasmda kod bo'lmasa, bo'sh qator "" qoldiring.
3. "clean_notes": Doskadagi ma'lumotlarning tartibli, chiroyli formatlangan konspekti (Markdown formatida, asosiy atamalar, ta'riflar va qisqacha tushuntirishlar bilan).
4. "flashcards": Talaba o'zini sinashi uchun 3-4 ta eng muhim savol va javoblar ro'yxati (har biri "question" va "answer" kalitiga ega).

Qat'iy qoida: Faqat to'g'ri JSON formatida javob bering, boshqa hech qanday ortiqcha matn yoki ```json blokisiz.
Format:
{
  "podcast_script": "...",
  "code_snippet": "```java\\n...\\n```",
  "clean_notes": "...",
  "flashcards": [
    {"question": "...", "answer": "..."}
  ]
}
"""

CANDIDATE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash"
]

def analyze_board_image(image_path: str) -> dict:
    """Doska yoki slayd rasmini tahlil qilib, konspekt, audio matn va flashcardlarni qaytaradi."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY sozlanmagan! Iltimos, .env fayliga kalitni kiriting.")

    image = Image.open(image_path)
    last_error = None

    for model_name in CANDIDATE_MODELS:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config={"response_mime_type": "application/json"}
            )
            response = model.generate_content([
                SYSTEM_PROMPT,
                image,
                "Iltimos, ushbu doska/slayd rasmidagi dars mavzusini tahlil qilib bering."
            ])
            text = response.text.strip()
            
            # JSON formatidan tozalash
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)
            return data
        except Exception as e:
            logging.warning(f"{model_name} xatosi: {e}. Keyingi model sinab ko'rilmoqda...")
            last_error = e

    # Agar barcha modellar xato bersa
    raise RuntimeError(f"AI modellari javob bera olmadi: {last_error}")
