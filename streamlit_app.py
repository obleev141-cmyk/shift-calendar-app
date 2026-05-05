import streamlit as st
import requests
from ics import Calendar, Event
from datetime import datetime
import io

# Настройки
API_KEY = 'K81706642488957'

st.set_page_config(page_title="Shift Calendar", page_icon="📅")
st.title("📅 Генератор Календаря Смен")

surname = st.text_input("Введите фамилию (точно как в таблице)", placeholder="Например: Москвичева")
uploaded_file = st.file_uploader("Загрузите фото графика", type=["jpg", "jpeg", "png"])

if st.button("Создать календарь"):
    if not uploaded_file or not surname:
        st.warning("⚠️ Пожалуйста, загрузите фото и введите фамилию.")
    else:
        status = st.empty() # Место для статуса
        status.info("📡 Отправка фото на сервер распознавания...")
        
        try:
            # Подготовка данных
            img_data = uploaded_file.getvalue()
            files = {"filename": ("chart.jpg", img_data, "image/jpeg")}
            data = {
                "apikey": API_KEY,
                "language": "rus",
                "isTable": True,
                "OCREngine": 2
            }
            
            # Запрос с тайм-аутом 60 секунд
            response = requests.post("https://api.ocr.space/parse/image", files=files, data=data, timeout=60)
            result = response.json()

            if result.get("OCRExitCode") == 1:
                status.info("🔍 Ищу вашу фамилию в тексте...")
                text = result["ParsedResults"][0]["ParsedText"]
                lines = text.split('\r\n')
                
                c = Calendar()
                found_person = False
                
                for line in lines:
                    if surname.lower() in line.lower():
                        found_person = True
                        parts = line.split()
                        day = 1
                        for p in parts:
                            if "-" in p and any(char.isdigit() for char in p):
                                try:
                                    t_start = p.split("-")[0].replace(".", ":")
                                    if ":" not in t_start: t_start += ":00"
                                    
                                    e = Event(name=f"Смена: {surname}")
                                    e.begin = datetime.strptime(f"2026-05-{day:02d} {t_start}", "%Y-%m-%d %H:%M")
                                    e.duration = {"hours": 12}
                                    c.events.add(e)
                                except: pass
                                day += 1
                
                if found_person and len(c.events) > 0:
                    status.success(f"✅ Найдено смен: {len(c.events)}")
                    st.download_button(
                        label="📥 Скачать файл (.ics)",
                        data=str(c),
                        file_name=f"{surname}_calendar.ics",
                        mime="text/calendar"
                    )
                elif not found_person:
                    status.error(f"❌ Фамилия '{surname}' не найдена в тексте таблицы.")
                    with st.expander("Посмотреть распознанный текст"):
                        st.text(text) # Показываем, что именно увидел робот
                else:
                    status.error("❌ Фамилия найдена, но смены (формата 00-00) не распознаны.")
            else:
                error_msg = result.get("ErrorMessage", "Неизвестная ошибка API")
                status.error(f"❌ Ошибка распознавания: {error_msg}")

        except requests.exceptions.Timeout:
            status.error("❌ Сервер распознавания не ответил вовремя (Тайм-аут). Попробуйте фото меньшего размера.")
        except Exception as e:
            status.error(f"❌ Произошла ошибка: {e}")

st.divider()
st.caption("Совет: Делайте фото при хорошем освещении и максимально ровно.")
