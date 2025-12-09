# Python asosiy imidjini olish
FROM python:3.11-slim

# Ishchi katalog yaratish
WORKDIR /app

# Kutubxonalarni yuklab olish uchun requirements.txt faylini nusxalash
COPY requirements.txt .

# Kutubxonalarni o'rnatish
RUN pip install --no-cache-dir -r requirements.txt

# Asosiy kod faylini nusxalash
COPY main.py .

# PORT sozlamasini olib tashlaymiz, chunki polling ishlatilgan.
# Botni ishga tushirish buyrug'i
CMD ["python", "main.py"]
