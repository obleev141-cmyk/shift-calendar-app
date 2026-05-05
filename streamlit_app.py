import streamlit as st
import asyncio
import io
import requests
import re
import calendar
import threading
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from PIL import Image, ImageDraw

# --- НАСТРОЙКИ ---
TOKEN = "8646138607:AAFSSiamq4LQ3TWBOnxw5izNRDZkjgFusCY"
OCR_API_KEY = "K81706642488957"

st.set_page_config(page_title="Shift Bot", page_icon="🗓")
st.title("Telegram Calendar Bot v3.0")

def create_calendar_visual(surname, days_dict):
    year, month = 2026, 5
    img_w, img_h = 1000, 1100
    img = Image.new('RGB', (img_w, img_h), color=(33, 37, 43))
    d = ImageDraw.Draw(img)
    
    # Шапка
    d.text((430, 40), "МАЙ 2026", fill=(255, 255, 255))
    d.text((60, 100), f"СОТРУДНИК: {surname.upper()}", fill=(200, 200, 200))

    days_ru = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    cell_size, start_x, start_y = 125, 65, 200

    for i, day in enumerate(days_ru):
        d.text((start_x + i * cell_size + 40, start_y - 50), day, fill=(150, 150, 150))

    cal = calendar.monthcalendar(year, month)
    
    for r_idx, week in enumerate(cal):
        for c_idx, day_num in enumerate(week):
            if day_num == 0: continue
            
            x = start_x + c_idx * cell_size
            y = start_y + r_idx * (cell_size + 15)
            
            # По умолчанию ЗЕЛЕНЫЙ (выходной)
            bg_color = (60, 140, 85) 
            shift_info = ""

            # Если для этого числа (день месяца) мы нашли текст в строке
            if day_num in days_dict:
                val = days_dict[day_num].lower()
                if any(k in val for k in ["от", "отп"]):
                    bg_color = (180, 70, 70)
                    shift_info = "ОТПУСК"
                elif re.search(r'\d', val):
                    bg_color = (255, 140, 0) # ОРАНЖЕВЫЙ
                    shift_info = "".join(re.findall(r'[\d\-\:]+', val))

            d.rectangle([x, y, x + cell_size - 12, y + cell_size - 12], fill=bg_color)
            d.text((x + 10, y + 10), str(day_num), fill=(255, 255, 255))
            
            if shift_info:
                txt = f"с {shift_info}" if len(shift_info) < 7 else shift_info
                tx, ty = x + 15, y + 55
                for ox in range(2): 
                    for oy in range(2):
                        d.text((tx + ox, ty + oy), txt, fill=(255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

async def process_advanced_ocr(image_bytes, surname):
    try:
        # Включаем overlay, чтобы получить координаты слов
        payload = {
            'apikey': OCR_API_KEY, 
            'language': 'rus', 
            'isTable': 'true', 
            'isOverlayRequired': 'true',
            'OCREngine': '2'
        }
        files = {'file': ('img.jpg', image_bytes, 'image/jpeg')}
        r = requests.post('https://api.ocr.space/parse/image', files=files, data=payload, timeout=60).json()
        
        if r.get('OCRExitCode') != 1: return "Ошибка OCR."

        results = r['ParsedResults'][0]
        lines = results['TextOverlay']['Lines']
        
        target_line = None
        target_surname = surname.lower().strip()

        # 1. Ищем строку, где есть фамилия
        for line in lines:
            line_text = "".join([w['WordText'] for w in line['Words']]).lower()
            if target_surname in line_text:
                target_line = line
                break
        
        if not target_line:
            return f"Сотрудник {surname} не найден."

        # 2. Анализируем координаты ячеек
        # Определяем границы таблицы по заголовку (датам 1-31)
        # Но для простоты: распределяем слова по X-координате
        words = target_line['Words']
        
        # Находим самую левую координату (после фамилии) и самую правую
        # Считаем, что в таблице 32 колонки (Фамилия + 31 день)
        # Это грубый расчет, но он лучше, чем просто список слов
        
        days_dict = {}
        # Находим координаты самой фамилии, чтобы начать считать ПОСЛЕ неё
        surname_end_x = 0
        for w in words:
            if target_surname in w['WordText'].lower():
                surname_end_x = w['Left'] + w['Width']
        
        # Ширина всей области дней (примерно)
        max_x = max([w['Left'] + w['Width'] for w in words])
        table_width = max_x - surname_end_x
        col_width = table_width / 31 if table_width > 0 else 1

        for w in words:
            word_text = w['WordText']
            if target_surname in word_text.lower(): continue
            
            # Определяем номер дня по позиции X
            relative_x = w['Left'] - surname_end_x
            day_index = int(relative_x / col_width) + 1
            if 1 <= day_index <= 31:
                days_dict[day_index] = word_text

        return create_calendar_visual(surname, days_dict)

    except Exception as e:
        return f"Ошибка: {e}"

# --- БОТ ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    if not message.caption:
        await message.answer("⚠️ Напиши фамилию!")
        return
    
    surname = message.caption.strip()
    wait_msg = await message.answer(f"⏳ Точный анализ таблицы для {surname}...")
    
    file = await bot.get_file(message.photo[-1].file_id)
    photo_file = await bot.download_file(file.file_path)
    
    result = await process_advanced_ocr(photo_file.read(), surname)
    await wait_msg.delete()

    if isinstance(result, io.BytesIO):
        await message.answer_photo(types.BufferedInputFile(result.read(), filename="res.png"))
    else:
        await message.answer(result)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(dp.start_polling(bot, skip_updates=True, handle_signals=False))

if "started" not in st.session_state:
    st.session_state.started = True
    threading.Thread(target=run_bot, daemon=True).start()
