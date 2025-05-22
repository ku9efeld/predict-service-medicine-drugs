import streamlit as st
import requests
from requests.exceptions import ConnectionError
from io import BytesIO

ip_api = "127.0.0.1"
port_api = "8000"

st.title("Прогноз закупки лекарств")

# Поле ввода месяца прогнозирования
month = st.selectbox(
    "Выберите месяц для прогнозирования закупки:",
    options=[
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ],
    index=0
)

# Поле загрузки Excel-файла с данными
uploaded_file = st.file_uploader(
    "Загрузите файл с перечнем закупаемых лекарств (Excel)",
    type=["xlsx", "xls"]
)

if st.button("Рассчитать прогноз"):
    if uploaded_file is not None:
        try:
            # Отправка файла на сервер
            files = {
                "month": (None, month),
                "file": (uploaded_file.name, uploaded_file.getvalue())
            }
            
            response = requests.post(
                f"http://{ip_api}:{port_api}/predict",
                files=files
            )
            
            if response.status_code == 200:
                st.success("Прогноз успешно рассчитан!")
                
                # Создаем кнопку для скачивания полученного файла
                st.download_button(
                    label="Скачать прогноз в Excel",
                    data=response.content,
                    file_name=f"прогноз_закупок_{month.lower()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
                st.write(f"Размер файла: {len(response.content)/1024:.2f} KB")
                
            else:
                st.error(f"Ошибка при расчете прогноза. Код статуса: {response.status_code}")
                st.text(response.text)
                
        except ConnectionError:
            st.error("Ошибка соединения с сервером прогнозирования")
        except Exception as e:
            st.error(f"Произошла непредвиденная ошибка: {str(e)}")
    else:
        st.warning("Пожалуйста, загрузите файл с данными о лекарствах")