from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import pickle

app = Flask(__name__)
CORS(app)  


try:
    with open('best_model.pkl', 'rb') as f:
        loaded_model = pickle.load(f)
    print("Model loaded successfully.")
except FileNotFoundError:
    print("Error: best_model.pkl not found. Make sure the model file is in the same directory.")
    loaded_model = None

@app.route('/predict', methods=['POST'])
def predict():
    if loaded_model is None:
        return jsonify({'error': 'Model not loaded.'}), 500

    try:
        data = request.get_json()
        expected_keys = ["Месяц", "Торговое наименование", "МНН / Действ. вещества", "Лек. форма",
                         "Страна производителя", "Фармако-терапевтическая группа", "ЖНВЛП", "ПККН",
                         "Характер", "flag", "monthID"]
        if not all(key in data for key in expected_keys):
             return jsonify({'error': f'Invalid input data. Missing keys. Expected: {expected_keys}, Received: {list(data.keys())}'}), 400


        input_df = pd.DataFrame([data])

        if 'ЖНВЛП' in input_df.columns and input_df['ЖНВЛП'].dtype == 'object':
             input_df['ЖНВЛП'] = input_df['ЖНВЛП'].apply(lambda x: 1 if str(x).lower() == 'да' else 0)
        if 'ПККН' in input_df.columns and input_df['ПККН'].dtype == 'object':
            input_df['ПККН'] = input_df['ПККН'].apply(lambda x: 1 if str(x).lower() == 'да' else 0)

        if 'Месяц' in input_df.columns:
             try:
                 input_df['Месяц'] = pd.to_datetime(input_df['Месяц'])
                 min_date = pd.to_datetime('2015-01-01') 
                 input_df['Месяц'] = (input_df['Месяц'].dt.year - min_date.year) * 12 + (input_df['Месяц'].dt.month - min_date.month)
             except Exception as e:
                 return jsonify({'error': f'Failed to process Месяц field: {e}'}), 400


        
        prediction = loaded_model.predict(input_df)

        
        return jsonify({'predicted_score': float(prediction[0])})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':

    app.run(host='0.0.0.0', port=8000)
