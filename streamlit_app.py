import streamlit as st
import requests
import re
from datetime import date
import calendar

# Настройки
API_KEY = 'K81706642488957'

# Стилизация под мобильное приложение (Dark Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #1c1c1e;
        color: white;
        font-family: 'Roboto', sans-serif;
    }
    .stTextInput input, .stFileUploader section {
        background-color: #2c2c2e !important;
        border-radius: 15px !important;
        color: white !important;
        border: none !important;
    }
    .calendar-header {
        font-size: 24px;
        font-weight: 700;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .grid-container {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 8px;
        text-align: center;
    }
    .weekday-label {
        color: #8e8e93;
        font-size: 12px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .day-cell {
        background-color: #2c2c2e;
        border-radius: 12px;
        padding: 8px 4px;
        min-height: 70px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        font-size: 14px;
        position: relative;
    }
    .day-num { font-weight: 500; text-align: left; margin-left: 5px; }
    
    /* Твой запрос: зеленый для выходных */
    .weekend { background-color: #2e4d2e !important; }
    
    /* Цвета для смен */
    .shift-9 { background-color: #f8b08e !important; color: #1c1c1e !important; }
    .shift-12 { background-color: #a8e0a8 !important; color: #1c1c1e !important; }
    .shift-10 { background-color: #f8a0a0 !important; color: #1c1c1e !important; }
    .shift-11 { background-color: #d1d1d6 !important; color: #1c1c1e !important; }
    
    .shift-info {
        font-size: 10px;
        font-weight: 700;
        background: rgba(0,0,0,0.1);
        border-radius: 4px;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.write('<div class="calendar-header">май 2026 г. <span>+</span></div>', unsafe_allow_html=True)

surname = st.text_input("Фамилия", placeholder="Введите для поиска...")
uploaded_file = st.file_uploader("Загрузить график", type=["jpg", "png", "jpeg"])

if uploaded_file and surname:
    with st.spinner("Анализирую таблицу..."):
        # OCR запрос
        files = {"f": uploaded_file.getvalue()}
        data = {"apikey": API_KEY, "language": "rus", "isTable": True, "OCREngine": 2}
        res = requests.post("https://api.ocr.space/parse/image", files=files, data=data)
        result = res.json()

        shifts_found = {}
        if result.get("OCRExitCode") == 1:
            text = result["ParsedResults"][0]["ParsedText"]
            lines = text.split('\r\n')
            for line in lines:
                if surname.lower() in line.lower():
                    # Ищем смены типа 09-22
                    all_shifts = re.findall(r'\d{1,2}-\d{2}', line)
                    for i, s in enumerate(all_shifts):
                        shifts_found[i+1] = s # Привязка к дням
        
        # Рисуем календарь
        st.write('<div class="grid-container">', unsafe_allow_html=True)
        for wd in ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]:
            st.write(f'<div class="weekday-label">{wd}</div>', unsafe_allow_html=True)
        
        # Май 2026 начинается с пятницы (индекс 4)
        month_cal = calendar.monthcalendar(2026, 5)
        
        for week in month_cal:
            for i, day in enumerate(week):
                if day == 0:
                    st.write('<div></div>', unsafe_allow_html=True)
                else:
                    is_weekend = i >= 5
                    shift = shifts_found.get(day, "")
                    
                    # Определяем класс цвета
                    style_class = "day-cell"
                    if is_weekend: style_class += " weekend"
                    
                    shift_text = ""
                    if shift:
                        start_time = shift.split('-')[0]
                        shift_text = f'<div class="shift-info">с {start_time}</div>'
                        if "09" in start_time: style_class += " shift-9"
                        elif "12" in start_time: style_class += " shift-12"
                        elif "10" in start_time: style_class += " shift-10"
                        elif "11" in start_time: style_class += " shift-11"

                    html = f'''
                    <div class="{style_class}">
                        <div class="day-num">{day}</div>
                        {shift_text}
                    </div>
                    '''
                    st.write(html, unsafe_allow_html=True)
        st.write('</div>', unsafe_allow_html=True)
else:
    st.info("Загрузите фото, чтобы увидеть ваш персональный график.")

st.markdown('<br><div style="text-align:center; color:#8e8e93; font-size:12px;">Poco X5 Pro Edition</div>', unsafe_allow_html=True)
