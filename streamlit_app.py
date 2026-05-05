import streamlit as st
import requests
from ics import Calendar, Event
from datetime import datetime
import io
import re

API_KEY = 'K81706642488957'

st.title("📅 Умный Календарь Смен")

surname = st.text_input("Введите фамилию", placeholder="Например: Москвичева")
uploaded_file = st.file_uploader("Загрузите фото (лучше скриншот)", type=["jpg", "jpeg", "png"])

if st.button("Создать календарь") and uploaded_file and surname:
    with st.spinner("Связываюсь с сервером распознавания..."):
        img_bytes = uploaded_file.getvalue()
        
        # Проверка размера (OCR.space Free любит файлы до 1-2мб)
        if len(img_bytes) > 1024 * 1024 * 5:
            st.error("⚠️ Файл слишком большой. Сделайте скриншот фото и загрузите его.")
        else:
            files = {"filename": ("image.jpg", img_bytes, "image/jpeg")}
            data = {
                "apikey": API_KEY,
                "language": "rus",
                "isTable": True,
                "OCREngine": 2 # Движок №2 лучше видит таблицы
            }
            
            try:
                res = requests.post("https://api.ocr.space/parse/image", files=files, data=data, timeout=60)
                result = res.json()

                if result.get("OCRExitCode") == 1:
                    text = result["ParsedResults"][0]["ParsedText"]
                    lines = text.split('\r\n')
                    
                    c = Calendar()
                    found_person = False
                    
                    for line in lines:
                        if surname.lower() in line.lower():
                            found_person = True
                            # Извлекаем все смены типа 11-22 или 09-21
                            shifts = re.findall(r'\d{1,2}[:.-]\d{2}', line)
                            
                            # ВАЖНО: Если OCR схлопнул пустые ячейки, 
                            # мы пока просто выводим их по порядку
                            for i, shift in enumerate(shifts):
                                try:
                                    t_start = shift.split('-')[0].split(':')[0].split('.')[0]
                                    if len(t_start) == 1: t_start = "0" + t_start
                                    
                                    e = Event(name=f"Смена: {surname}")
                                    # Временный костыль: ставим смену на i+1 день
                                    e.begin = datetime.strptime(f"2026-05-{i+1:02d} {t_start}:00", "%Y-%m-%d %H:%M")
                                    e.duration = {"hours": 11}
                                    c.events.add(e)
                                except: pass
                    
                    if found_person and len(c.events) > 0:
                        st.success(f"Найдено смен: {len(c.events)}")
                        st.download_button("📥 Скачать .ics", str(c), f"{surname}.ics")
                    else:
                        st.error(f"Фамилия '{surname}' не найдена или смены не считались.")
                        with st.expander("Посмотреть что прочитал робот"):
                            st.text(text)
                else:
                    # Выводим реальную причину ошибки от сервера
                    details = result.get("ErrorMessage", "Неизвестная ошибка")
                    st.error(f"Ошибка API: {details}")
                    if "Timed out" in str(details):
                        st.info("Попробуйте еще раз, сервер был перегружен.")

            except Exception as e:
                st.error(f"Ошибка соединения: {e}")

st.info("💡 Лайфхак: если даты сбиваются, обрежьте фото так, чтобы остались только шапка с числами и ваша фамилия.")
