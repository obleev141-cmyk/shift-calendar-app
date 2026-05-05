import streamlit as st
import asyncio, io, requests, re, calendar, threading
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from PIL import Image, ImageDraw

TOKEN = "8646138607:AAFSSiamq4LQ3TWBOnxw5izNRDZkjgFusCY"
API_KEY = "K81706642488957"

st.title("Shift Bot v6.0")

def get_calendar_img(surname, days_dict):
    now = datetime.now()
    y, m = now.year, now.month
    img = Image.new('RGB', (1000, 1100), (33, 37, 43))
    d = ImageDraw.Draw(img)
    
    # Заголовки
    d.text((400, 40), f"{calendar.month_name[m].upper()} {y}", (255, 255, 255))
    d.text((60, 100), f"СОТРУДНИК: {surname.upper()}", (200, 200, 200))
    
    for i, day in enumerate(["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]):
        d.text((105 + i * 125, 150), day, (150, 150, 150))

    for r_idx, week in enumerate(calendar.monthcalendar(y, m)):
        for c_idx, day_num in enumerate(week):
            if day_num:
                x, y_pos = 65 + c_idx * 125, 200 + r_idx * 140
                val = days_dict.get(day_num, "").lower()
                
                # Логика цвета: выходной (зеленый), работа (оранжевый)
                color, info = (60, 140, 85), ""
                if "от" in val: color, info = (180, 70, 70), "ОТПУСК"
                elif re.search(r'\d', val):
                    color = (255, 140, 0)
                    nums = "".join(re.findall(r'\d+', val))
                    info = f"{nums[:2]}-{nums[-2:]}" if len(nums) >= 4 else nums

                d.rectangle([x, y_pos, x + 113, y_pos + 113], fill=color)
                d.text((x + 10, y_pos + 10), str(day_num), (255, 255, 255))
                if info: d.text((x + 15, y_pos + 55), info, (255, 255, 255))

    buf = io.BytesIO(); img.save(buf, 'PNG'); buf.seek(0)
    return buf

async def process_photo(photo_bytes, surname):
    p = {'apikey': API_KEY, 'language': 'rus', 'isOverlayRequired': 'true', 'OCREngine': '2'}
    try:
        r = requests.post("https://api.ocr.space/parse/image", files={'file': photo_bytes}, data=p).json()
        if r.get('OCRExitCode') != 1: return "Ошибка OCR"
        
        lines = r['ParsedResults'][0]['TextOverlay']['Lines']
        # Поиск "якорей" дат
        anchors = {w['Left']+w['Width']//2: int(w['WordText']) for l in lines for w in l['Words'] if w['WordText'].isdigit() and 1<=int(w['WordText'])<=31 and w['Top']<600}
        
        for line in lines:
            if surname.lower() in " ".join(w['WordText'] for w in line['Words']).lower():
                y_coord = line['Words'][0]['Top']
                row_words = [w for l in lines for w in l['Words'] if abs(w['Top']-y_coord) < 40]
                data = {}
                for w in row_words:
                    if surname.lower() not in w['WordText'].lower():
                        mid_x = w['Left'] + w['Width']//2
                        best = min(anchors.items(), key=lambda x: abs(x[0]-mid_x), default=(None, None))
                        if best[0] and abs(best[0]-mid_x) < 60: data[best[1]] = w['WordText']
                return get_calendar_img(surname, data)
        return "Сотрудник не найден"
    except: return "Ошибка сервера"

bot, dp = Bot(TOKEN), Dispatcher()

@dp.message(F.photo)
async def on_photo(m: types.Message):
    if not m.caption: return await m.answer("Укажите фамилию!")
    wait = await m.answer("⌛ Обработка...")
    try:
        f = await bot.get_file(m.photo[-1].file_id)
        b = await bot.download_file(f.file_path)
        res = await process_photo(b.read(), m.caption.strip())
        await wait.delete()
        if isinstance(res, io.BytesIO): await m.answer_photo(types.BufferedInputFile(res.read(), "res.png"))
        else: await m.answer(res)
    except: await m.answer("Ошибка бота")

def run():
    asyncio.run(dp.start_polling(bot, skip_updates=True, handle_signals=False))

if "started" not in st.session_state:
    st.session_state.started = True
    threading.Thread(target=run, daemon=True).start()
