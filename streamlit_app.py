import streamlit as st
import asyncio, io, requests, re, calendar, threading
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from PIL import Image, ImageDraw

TOKEN = "8646138607:AAFSSiamq4LQ3TWBOnxw5izNRDZkjgFusCY"
OCR_URL = "https://api.ocr.space/parse/image"
API_KEY = "K81706642488957"

st.title("Shift Bot")

def get_calendar_img(surname, days_dict):
    now = datetime.now()
    year, month = now.year, now.month
    img = Image.new('RGB', (1000, 1100), (33, 37, 43))
    d = ImageDraw.Draw(img)
    
    d.text((400, 40), f"{calendar.month_name[month].upper()} {year}", (255, 255, 255))
    d.text((60, 100), f"СОТРУДНИК: {surname.upper()}", (200, 200, 200))
    
    for i, day in enumerate(["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]):
        d.text((105 + i * 125, 150), day, (150, 150, 150))

    for r_idx, week in enumerate(calendar.monthcalendar(year, month)):
        for c_idx, day_num in enumerate(week):
            if day_num:
                x, y = 65 + c_idx * 125, 200 + r_idx * 140
                val = days_dict.get(day_num, "").lower()
                
                color = (60, 140, 85) # Выходной (Зеленый)
                info = ""
                
                if "от" in val: color, info = (180, 70, 70), "ОТПУСК"
                elif re.search(r'\d', val):
                    color = (255, 140, 0) # Работа (Оранжевый)
                    nums = "".join(re.findall(r'\d+', val))
                    info = f"{nums[:2]}-{nums[-2:]}" if len(nums) >= 4 else nums

                d.rectangle([x, y, x + 113, y + 113], fill=color)
                d.text((x + 10, y + 10), str(day_num), (255, 255, 255))
                if info: d.text((x + 15, y + 55), info, (255, 255, 255))

    buf = io.BytesIO(); img.save(buf, 'PNG'); buf.seek(0)
    return buf

async def process_photo(photo_bytes, surname):
    payload = {'apikey': API_KEY, 'language': 'rus', 'isOverlayRequired': 'true', 'OCREngine': '2'}
    r = requests.post(OCR_URL, files={'file': photo_bytes}, data=payload).json()
    if r.get('OCRExitCode') != 1: return "Ошибка OCR"

    lines = r['ParsedResults'][0]['TextOverlay']['Lines']
    anchors = {w['Left']+w['Width']//2: int(w['WordText']) for l in lines for w in l['Words'] if w['WordText'].isdigit() and 1<=int(w['WordText'])<=31 and w['Top']<600}
    
    for line in lines:
        if surname.lower() in " ".join(w['WordText'] for w in line['Words']).lower():
            y = line['Words'][0]['Top']
            row_words = [w for l in lines for w in l['Words'] if abs(w['Top']-y) < 40]
            data = {}
            for w in row_words:
                if surname.lower() not in w['WordText'].lower():
                    mid_x = w['Left'] + w['Width']//2
                    best_day = min(anchors.items(), key=lambda x: abs(x[0]-mid_x), default=(0,0))
                    if abs(best_day[0]-mid_x) < 60: data[best_day[1]] = w['WordText']
            return get_calendar_img(surname, data)
    return "Сотрудник не найден"

bot = Bot(TOKEN); dp = Dispatcher()

@dp.message(F.photo)
async def on_photo(m: types.Message):
    if not m.caption: return await m.answer("Укажите фамилию!")
    wait = await m.answer("⌛ Обработка...")
    file = await bot.get_file(m.photo[-1].file_id)
    res = await process_photo((await bot.download_file(file.file_path)).read(), m.caption.strip())
    await wait.delete()
    if isinstance(res, io.BytesIO): await m.answer_photo(types.BufferedInputFile(res.read(), "res.png"))
    else: await m.answer(res)

def run():
    asyncio.run(dp.start_polling(bot, skip_updates=True, handle_signals=False))

if "started" not in st.session_state:
    st.session_state.started = True
    threading.Thread(target=run, daemon=True).start()
