from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
import pandas as pd
import pickle
from io import BytesIO
from datetime import datetime
import logging
import calendar

from urllib.parse import quote

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pharmacy Prediction API")

# Модель загружается при старте приложения
try:
    logger.info("Загрузка модели...")
    with open('best_model.pkl', 'rb') as f:
        model = pickle.load(f)
    logger.info("Модель успешно загружена")

except Exception as e:
    logger.error(f"Ошибка загрузки модели: {str(e)}")
    raise RuntimeError("Невозможно загрузить модель")


def convert_month(month_name):
    months = {
        "Январь": 1, "Февраль": 2, "Март": 3,
        "Апрель": 4, "Май": 5, "Июнь": 6,
        "Июль": 7, "Август": 8, "Сентябрь": 9,
        "Октябрь": 10, "Ноябрь": 11, "Декабрь": 12
    }
    return months.get(month_name, 1)

def get_proc_date(selected_month, current_date):
    try:
        last_day = calendar.monthrange(current_date.year, selected_month)[1]
        adjusted_day = min(current_date.day, last_day)
        processing_date = datetime( year=current_date.year,
                                    month=selected_month,
                                    day=adjusted_day).strftime("%Y-%m-%d")
        
    except Exception as e:
        processing_date = current_date.strftime("%Y-%m-%d")
    
    return processing_date


def encode(df, flag):
    if flag == True:
        if 'ЖНВЛП' in df.columns and df['ЖНВЛП'].dtype == 'object':
            df['ЖНВЛП'] = df['ЖНВЛП'].apply(lambda x: 1 if str(x).lower() == 'да' else 0)
        if 'ПККН' in df.columns and df['ПККН'].dtype == 'object':
            df['ПККН'] = df['ПККН'].apply(lambda x: 1 if str(x).lower() == 'да' else 0)

    elif flag == False:
        if 'ЖНВЛП' in df.columns and df['ЖНВЛП'].dtype == 'int':
            df['ЖНВЛП'] = df['ЖНВЛП'].apply(lambda x: 'Да' if x == 1 else 'Нет')
        if 'ПККН' in df.columns and df['ПККН'].dtype == 'int':
            df['ПККН'] = df['ПККН'].apply(lambda x: 'Да' if x == 1 else 'Нет')

    return df


@app.post("/predict")
async def predict(
    month: str = Form(...),
    file: UploadFile = File(...)
):  
    
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "Допускаются только Excel файлы")

    try:

        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))

        required_columns = ["Торговое наименование", "МНН / Действ. вещества", "Лек. форма",
                    "Страна производителя", "Фармако-терапевтическая группа", "ЖНВЛП", "ПККН",
                    "Характер", "flag"]
        
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise HTTPException(400, f"Отсутствуют колонки: {missing}")
        
        df = encode(df, True)
        
        selected_month = convert_month(month)
        current_date = datetime.now()

        processing_date = get_proc_date(selected_month, current_date)

        df.insert(0, 'Месяц', processing_date)
        
        df['monthID'] = pd.to_datetime(df['Месяц']).dt.month - 1

        if 'Месяц' in df.columns:
             try:
                 df['Месяц'] = pd.to_datetime(df['Месяц'])
                 min_date = pd.to_datetime('2015-01-01') 
                 df['Месяц'] = (df['Месяц'].dt.year - min_date.year) * 12 + (df['Месяц'].dt.month - min_date.month)
             except Exception as e:
                 raise HTTPException(400, f'Failed to process Месяц field: {e}')


        prediction = model.predict(df)
        prediction = list(map(int, prediction))

        df['Прогноз'] = prediction

        # Преобразуем данные к исходному виду
        df = df.drop(columns = ['Месяц', 'monthID'])
        df = encode(df, False)

        # Сохранение в временный файл
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0) 

        # Формирование имени файла
        filename = f"прогноз_закупок_{month.lower()}.xlsx"

        safe_filename = quote(filename, safe='')  

        # Формирование заголовков
        headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"}
        
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )


    except HTTPException as he:
        raise he
    
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        raise HTTPException(500, f"Внутренняя ошибка сервера: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)