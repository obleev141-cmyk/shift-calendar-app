import streamlit as st
import requests
from ics import Calendar, Event
from datetime import datetime
import io

# Твой API ключ
API_KEY = 'K81706642488957'

st.title("📅 Генератор Календаря Смен")

surname = st.text_input("Введите фамилию для поиска")
uploaded_file = st.file_uploader("Загрузите фото графика", type=["jpg", "jpeg", "png"])

if st.button("Создать календарь") and uploaded_file and surname:
    with st.spinner("Распознаю таблицу..."):
        # Отправка в OCR.space
        files = {"filename": uploaded_file.getvalue()}
        data = {
            "apikey": API_KEY,
            "language": "rus",
            "isTable": True,
            "OCREngine": 2
        }
        res = requests.post("https://api.ocr.space/parse/image", files=files, data=data)
        result = res.json()

        if result.get("OCRExitCode") == 1:
            text = result["ParsedResults"][0]["ParsedText"]
            lines = text.split("\r\n")
            
            c = Calendar()
            found = False
            for line in lines:
                if surname.lower() in line.lower():
                    found = True
                    parts = line.split()
                    day = 1
                    for p in parts:
                        if "-" in p and any(c.isdigit() for c in p):
                            try:
                                t_start = p.split("-")[0].replace(".", ":")
                                if ":" not in t_start: t_start += ":00"
                                e = Event(name=f"Смена: {surname}")
                                e.begin = datetime.strptime(f"2026-05-{day:02d} {t_start}", "%Y-%m-%d %H:%M")
                                e.duration = {"hours": 12}
                                c.events.add(e)
                            except: pass
                            day += 1
            
            if found and len(c.events) > 0:
                st.success(f"Найдено смен: {len(c.events)}")
                st.download_button("📥 Скачать .ics файл", str(c), f"{surname}.ics")
            else:
                st.error("Не нашли смены. Попробуйте другое фото.")
