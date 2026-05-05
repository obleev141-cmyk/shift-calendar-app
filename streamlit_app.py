import streamlit as st
import requests
from ics import Calendar, Event
from datetime import datetime
import io
import re

API_KEY = 'K81706642488957'

st.title("📅 Умный Календарь Смен")

surname = st.text_input("Введите фамилию", placeholder="Например: Москвичева")
uploaded_file = st.file_uploader("Загрузите фото графика", type=["jpg", "jpeg", "png"])

if st.button("Создать календарь") and uploaded_file and surname:
    with st.spinner("Анализирую структуру таблицы..."):
        files = {"filename": uploaded_file.getvalue()}
        data = {"apikey": API_KEY, "language": "rus", "isTable": True, "OCREngine": 2}
        
        try:
            res = requests.post("https://api.ocr.space/parse/image", files=files, data=data, timeout=60)
            result = res.json()

            if result.get("OCRExitCode") == 1:
                text = result["ParsedResults"][0]["ParsedText"]
                lines = text.split('\r\n')
                
                # 1. Пытаемся найти строку с датами (1 2 3 ... 31)
                days_row = []
                for line in lines:
                    nums = re.findall(r'\b\d{1,2}\b', line)
                    if len(nums) > 20: # Если в строке больше 20 чисел, это шапка дат
                        days_row = nums
                        break

                c = Calendar()
                found_person = False
                
                for line in lines:
                    if surname.lower() in line.lower():
                        found_person = True
                        # Разбиваем строку по табуляции или двойным пробелам (как делает OCR для таблиц)
                        parts = re.split(r'\t| {2,}', line)
                        
                        # Убираем фамилию из списка данных
                        data_parts = [p for p in parts if surname.lower() not in p.lower() and not p.isalpha()]
                        
                        # Сопоставляем данные с днями месяца
                        # Мы идем по строке и ищем смены типа "11-22"
                        current_day = 1
                        for part in data_parts:
                            # Если это смена (содержит дефис)
                            if '-' in part and any(char.isdigit() for char in part):
                                try:
                                    t_start = part.split('-')[0].strip().replace('.', ':')
                                    if ':' not in t_start: t_start += ":00"
                                    
                                    e = Event(name=f"Смена: {surname}")
                                    # Пытаемся понять, в какой "колонке" мы находимся
                                    # Если OCR пропустил ячейку, это слабое место, но мы ориентируемся на порядковый номер
                                    e.begin = datetime.strptime(f"2026-05-{current_day:02d} {t_start}", "%Y-%m-%d %H:%M")
                                    e.duration = {"hours": 12}
                                    c.events.add(e)
                                except: pass
                            
                            # Важный момент: если в ячейке просто пробел или "ОТ", мы все равно считаем день
                            current_day += 1
                
                if found_person and len(c.events) > 0:
                    st.success(f"Готово! Найдено смен: {len(c.events)}")
                    st.download_button("📥 Скачать .ics", str(c), f"{surname}.ics")
                else:
                    st.error("Не удалось точно сопоставить смены. Попробуйте обрезать фото, оставив только шапку с числами и вашу строку.")
                    with st.expander("Что увидел робот:"):
                        st.text(text)
            else:
                st.error("Ошибка API. Попробуйте еще раз.")
        except Exception as e:
            st.error(f"Ошибка: {e}")
