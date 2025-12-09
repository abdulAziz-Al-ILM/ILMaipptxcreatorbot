import os
import io
import datetime
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from google import genai
from pptx import Presentation

# --- Konfiguratsiya va API Kalitlari ---
# *Almashtiring: Oʻz Telegram bot tokeningizni joylang*
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
# *Almashtiring: Oʻz Gemini API kalitingizni joylang*
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

ADMIN_USER_ID = YOUR_ADMIN_TELEGRAM_ID  # *Almashtiring: Sizning Telegram ID raqamingiz*

# Gemini API ni ishga tushirish
if GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
else:
    print("Xato: GEMINI_API_KEY sozlanmagan!")

# --- Global O'zgaruvchilar ---
user_states = {} # Foydalanuvchi holatini saqlash uchun lug'at

# --- Yordamchi Funksiyalar ---

def replace_text_in_slides(prs, new_texts_list):
    """
    Taqdimotdagi (PPTX) matn qutilaridagi matnni yangi matnlar bilan almashtiradi.
    Bu soddalashtirilgan yechim va har bir shablon uchun mos kelmasligi mumkin.
    """
    text_index = 0
    # Har bir slaydni aylanib chiqish
    for slide in prs.slides:
        # Har bir slayd ichidagi shakllarni (shapes) tekshirish
        for shape in slide.shapes:
            # Agar shakl matn qutisiga ega bo'lsa
            if shape.has_text_frame:
                text_frame = shape.text_frame
                # Barcha paragraflarni aylanib chiqish (sarlavhalar va matn)
                for paragraph in text_frame.paragraphs:
                    if text_index < len(new_texts_list):
                        # Matnni to'liq almashtirish
                        if paragraph.runs:
                            # Mavjud matnlarni tozalash
                            while len(paragraph.runs) > 0:
                                p = paragraph.runs.pop()

                            # Yangi matnni qo'shish
                            new_run = paragraph.add_run()
                            new_run.text = new_texts_list[text_index].strip()
                            text_index += 1
                        
                        if text_index >= len(new_texts_list):
                            return # Matnlar tugadi
    
    return # Agar matnlar tugamasa, barcha joylarga qo'yilgan bo'ladi

def generate_presentation_content(topic, num_slides):
    """
    Gemini API yordamida berilgan mavzu bo'yicha slaydlar uchun matn yaratadi.
    """
    prompt = f"""
    Siz Oʻzbek tilida ilmiy va rasmiy ohangda prezentatsiya slaydlarini tayyorlovchi mutaxassissiz.
    '{topic}' mavzusi bo'yicha {num_slides} ta alohida qisqa matnlar yarating.
    Har bir matn alohida qator yoki ajratuvchi belgi bilan bo'lsin.
    Matnlar 4-5 jumladan oshmasin va sarlavhalarni o'z ichiga olmasin.
    """
    try:
        response = gemini_model.generate_content(prompt)
        # Matnni qatorlarga ajratish va bo'sh qatorlarni olib tashlash
        return [text.strip() for text in response.text.split('\n') if text.strip()]
    except Exception as e:
        print(f"Gemini API xatosi: {e}")
        return None

# --- Telegram Bot Handlerlari ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start buyrug'ini qabul qiladi."""
    user = update.effective_user
    today = datetime.date.today()
    target_date = datetime.date(2025, 1, 1)

    if user.id != ADMIN_USER_ID:
        # Foydalanuvchilar uchun reklama
        if today < target_date:
            await update.message.reply_text(
                f"Assalomu alaykum, {user.full_name}! 👋\n\n"
                f"Men hali to'liq ishga tushmadim. Men WPS Office shablonlari asosida ilmiy prezentatsiyalarni AI yordamida avtomatik to'ldirib beruvchi botman!\n\n"
                f"Rasmiy ishga tushish: **2025 yil 1 yanvar!** Qolib ketmang! 😉"
            )
        else:
            await update.message.reply_text(
                f"Assalomu alaykum, {user.full_name}! Bot ishga tushdi!\n\n"
                f"Menga kerakli mavzuni yozing, so'ngra WPS Officedan tanlagan PPTX shabloningizni yuboring. Men uni avtomatik to'ldiraman."
            )
    else:
        # Admin uchun vazifani bajarish
        await update.message.reply_text(
            f"Salom, Admin! 😊\n\n"
            f"Siz botning barcha funksiyalaridan foydalanishingiz mumkin.\n"
            f"1. Birinchi navbatda, prezentatsiya mavzusini yozing."
        )
        user_states[user.id] = 'awaiting_topic'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Matn yoki fayllarni qabul qiladi."""
    user = update.effective_user
    
    # Faqat Adminning xabarlarini qayta ishlash (1-yanvardan keyin /start bosgan foydalanuvchilarniki ham)
    today = datetime.date.today()
    target_date = datetime.date(2025, 1, 1)
    
    if user.id != ADMIN_USER_ID and today < target_date:
        # Reklamadan keyin boshqa foydalanuvchilarning matnini e'tiborsiz qoldirish
        return

    # 1-yanvardan keyin barcha foydalanuvchilar ishlashi mumkin.
    
    state = user_states.get(user.id)

    if state == 'awaiting_topic' and update.message.text:
        # 1-holat: Mavzuni qabul qilish
        context.user_data['topic'] = update.message.text
        user_states[user.id] = 'awaiting_pptx'
        await update.message.reply_text(
            f"Mavzu qabul qilindi: **{update.message.text}**.\n\n"
            f"Endi iltimos, WPS Office/PowerPoint'dan tanlagan **PPTX shabloningizni** (eng kamida 15 slaydli) fayl sifatida yuboring."
        )
    
    elif state == 'awaiting_pptx' and update.message.document and update.message.document.file_name.endswith('.pptx'):
        # 2-holat: PPTX faylini qabul qilish
        await update.message.reply_text("Fayl qabul qilindi. Iltimos kuting, AI matnni yaratmoqda va joylamoqda...")

        pptx_file = await update.message.document.get_file()
        file_data = io.BytesIO()
        await pptx_file.download_to_memory(file_data)
        file_data.seek(0)

        # 1. Taqdimot obyektini yuklash
        try:
            prs = Presentation(file_data)
        except Exception as e:
            await update.message.reply_text(f"PPTX faylini yuklashda xato yuz berdi: {e}")
            user_states[user.id] = None
            return

        # 2. Slaydlar sonini aniqlash
        num_slides = len(prs.slides)
        topic = context.user_data.get('topic', 'Umumiy prezentatsiya mavzusi')
        
        # 3. AI kontentni yaratish
        new_texts = generate_presentation_content(topic, num_slides * 2) # Har bir slayd uchun 2ta matn joyini taxmin qilib ko'ramiz
        
        if not new_texts:
            await update.message.reply_text("AI kontent yaratishda xato yuz berdi. Iltimos, boshqa mavzu bilan urinib ko'ring.")
            user_states[user.id] = None
            return

        # 4. Matnni joylashtirish
        replace_text_in_slides(prs, new_texts)

        # 5. Yangi faylni saqlash va yuborish
        output_buffer = io.BytesIO()
        prs.save(output_buffer)
        output_buffer.seek(0)

        await update.message.reply_document(
            document=output_buffer,
            filename=f"To'ldirilgan_{update.message.document.file_name}",
            caption=f"Tayyor prezentatsiya:\n\n**Mavzu:** {topic}\n**Slaydlar soni:** {num_slides}"
        )
        
        user_states[user.id] = None
        context.user_data.clear()

    else:
        # Boshqa holatlar uchun javob
        if user.id == ADMIN_USER_ID:
             await update.message.reply_text("Noto'g'ri qadam. Iltimos, /start buyrug'ini qaytadan bosing yoki PPTX faylini yuboring.")
        # Boshqa foydalanuvchilar e'tiborsiz qoldiriladi.


def main() -> None:
    """Botni ishga tushiradi."""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_message))

    # Botni ishga tushirish (Webhook yoki Polling)
    # Railway uchun Webhook sozlamalari odatda Dockerfile orqali boshqariladi, Polling oddiyroq
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
