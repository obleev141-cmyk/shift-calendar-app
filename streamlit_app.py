import asyncio
import io
import requests
import re
import calendar
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from PIL import Image, ImageDraw

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8646138607:AAFSSiamq4LQ3TWBOnxw5izNRDZkjgFusCY"
OCR_API_KEY = "K81706642488957"

bot = Bot(token=TOKEN)
dp = Dispatcher()

def create_calendar_visual(surname, raw_line):
    year, month = 2026, 5
    img_w, img_h = 1000, 1100
    img = Image.new('RGB', (img_w, img_h), color=(33, 37, 43))
    d = ImageDraw.Draw(img)
    
    d.text((430, 40), "МАЙ 2026", fill=(255, 255, 255))
    d.text((60, 90), f"СОТРУДНИК: {surname.upper()}", fill=(200, 200, 200))

    days_ru = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    cell_size = 125
    start_x, start_y = 65, 200

    for i, day in enumerate(days_ru):
        d.text((start_x + i * cell_size + 40, start_y - 50), day, fill=(150, 150, 150))

    # Извлекаем данные (время или "ОТ")
    parts = re.findall(r'(\d{1,2}[:\-\s]*\d{0,2}|ОТ)', raw_line[len(surname):])
    clean_data = [x.strip() for x in parts if x.strip()]

    cal_structure = calendar.monthcalendar(year, month)
    
    for r_idx, week in enumerate(cal_structure):
        for c_idx, day_num in enumerate(week):
            if day_num == 0: continue
            
            x = start_x + c_idx * cell_size
            y = start_y + r_idx * (cell_size + 15)
            
            # --- НОВАЯ ЛОГИКА ЦВЕТОВ ---
            # По умолчанию выходной - ЗЕЛЕНЫЙ
            bg_color = (60, 140, 85) 
            shift_info = ""

            if (day_num - 1) < len(clean_data):
                val = clean_data[day_num - 1]
                if "ОТ" in val.upper():
                    bg_color = (180, 70, 70) # Красный для отпуска
                    shift_info = "ОТПУСК"
                elif re.search(r'\d', val):
                    # Рабочий день - ОРАНЖЕВЫЙ
                    bg_color = (255, 140, 0) 
                    shift_info = val.replace(" ", "")

            # Рисуем ячейку
            d.rectangle([x, y, x + cell_size - 12, y + cell_size - 12], fill=bg_color)
            d.text((x + 10, y + 10), str(day_num), fill=(255, 255, 255))
            
            # Текст смены (жирный шрифт наложением)
            if shift_info:
                txt = f"с {shift_info}" if len(shift_info) < 6 else shift_info
                tx, ty = x + 15, y + 55
                for off_x in range(2):
                    for off_y in range(2):
                        d.text((tx + off_x, ty + off_y), txt, fill=(255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

def get_schedule_from_cloud(image_bytes, surname):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        img.thumbnail((2000, 2000))
        c_buf = io.BytesIO()
        img.save(c_buf, format='JPEG', quality=95)

        payload = {'apikey': OCR_API_KEY, 'language': 'rus', 'isTable': 'true', 'OCREngine': '2'}
        files = {'file': ('img.jpg', c_buf.getvalue(), 'image/jpeg')}
        r = requests.post('https://api.ocr.space/parse/image', files=files, data=payload, timeout=60).json()
        
        if r.get('OCRExitCode') != 1:
            return f"Ошибка OCR: {r.get('ErrorMessage')}"

        parsed_text = r['ParsedResults'][0]['ParsedText']
        lines = parsed_text.split('\r\n')
        
        target = surname.strip().lower()
        for line in lines:
            if target in line.lower():
                return create_calendar_visual(surname, line)
