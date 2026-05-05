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
st.title("Telegram Calendar Bot")

def create_calendar_visual(surname, days_data):
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
    
    # Мы ожидаем, что в days_data ровно 31 элемент
    for r_idx, week in enumerate(cal):
        for c_idx, day_num in enumerate(week):
            if day_num == 0: continue
            
            x = start_x + c_idx * cell_size
            y = start_y + r_idx * (cell_size + 15)
            
            # Логика цвета: по умолчанию ЗЕЛЕНЫЙ (выходной)
            bg_color = (60, 140, 85) 
            shift_info = ""

            # Проверяем данные конкретно для этого числа
            if day_num <= len(days_data):
                val = str(days_data[day_num-1]).strip().lower()
                if any(x in val for x in ["от", "отп"]):
                    bg_color = (180, 70, 70) # Красный
                    shift_info = "ОТПУСК"
                elif re.search(r'\d', val):
                    bg_color = (255, 140, 0) # ОРАНЖЕВЫЙ (работа)
                    # Чистим время от лишних букв, оставляем цифры и тире
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

async def process_ocr_table(image_bytes, surname):
    try:
        payload = {'apikey': OCR_API_KEY, 'language': 'rus', 'isTable': 'true', 'OCREngine': '2'}
        files = {'file': ('img.jpg', image_bytes, 'image/jpeg')}
        r = requests.post('https://api.ocr.space/parse/image', files=files, data=payload, timeout=60).json()
        
        if r.get('OCRExitCode') != 1: return "Ошибка чтения таблицы."

        # Разбор таблицы по ячейкам
        lines = r['ParsedResults'][0]['ParsedText'].split('\r\n')
        target = surname.lower().strip()
        
        for line in lines:
            # Разбиваем строку по табуляции (так OCR отдает ячейки таблицы)
            cells = line.split('\t')
            if any(target in c.lower() for c in cells):
                # Нашли строку! Теперь берем всё, что идет после фамилии
                # Мы ищем только те ячейки, где есть данные (смены)
                schedule_cells = cells[1:] # Пропускаем ячейку с фамилией
                return create_calendar_visual(surname, schedule_cells)

        return f"Сотрудник {surname} не найден."
    except Exception as e:
        return f"Ошибка: {e}"

# --- БОТ ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🗓 Пришли фото и фамилию!")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    if not message.caption:
        await message.answer("⚠️ Напиши фамилию!")
        return
    
    surname = message.caption.strip()
    wait_msg = await message.answer(f"⏳ Читаю таблицу для {surname}...")
    
    file = await bot.get_file(message.photo[-1].file_id)
    photo_file = await bot.download_file(file.file_path)
    
    result = await process_ocr_table(photo_file.read(), surname)
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
