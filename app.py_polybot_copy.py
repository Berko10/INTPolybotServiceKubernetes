import flask
from flask import request
import os
import boto3
import json
from pymongo import MongoClient
from bot import ObjectDetectionBot

app = flask.Flask(__name__)


# פונקציה לטעינת סוד מ-AWS Secrets Manager
def get_secret(secret_name):
    # סשן Boto3 שמתחבר ל- Secrets Manager
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name='eu-central-1')

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve secret {secret_name}: {str(e)}")

    # תוצאת secret_value יכולה להיות JSON או string
    secret = get_secret_value_response['SecretString']
    return json.loads(secret)


# טוען את ה-TELEGRAM_TOKEN מ-Secret Manager
secrets = get_secret("Berko-telegram-bot-token")
TELEGRAM_TOKEN = secrets['TELEGRAM_TOKEN']
TELEGRAM_APP_URL = os.environ['TELEGRAM_APP_URL']
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")


@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


@app.route(f'/results', methods=['POST'])
def results():
    prediction_id = request.args.get('predictionId')

    # השתמש ב-prediction_id כדי לשלוף את התוצאות מ-MongoDB
    result = get_prediction_results(prediction_id)
    if not result:
        return "Prediction not found", 404

    chat_id = result['chat_id']  # נניח שהתוצאה מכילה את ה-chat_id של המשתמש
    text_results = f"Prediction Results: {result['text_results']}"  # נניח שהתוצאה מכילה את תוצאת החיזוי

    bot.send_text(chat_id, text_results)
    return 'Ok'


@app.route(f'/loadTest/', methods=['POST'])
def load_test():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


def get_prediction_results(prediction_id):
    # חיבור ל-MongoDB (הנח כאן את פרטי החיבור שלך)
    client = MongoClient('mongodb://localhost:27017')  # דוגמה לחיבור מקומי
    db = client['object_detection_db']  # שם המסד
    predictions = db['predictions']  # אוסף התוצאות

    result = predictions.find_one({"prediction_id": prediction_id})  # חיפוש תוצאה לפי prediction_id
    return result  # מחזיר את התוצאה אם נמצאה


if __name__ == "__main__":
    bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL, S3_BUCKET_NAME, SQS_QUEUE_URL)

    app.run(host='0.0.0.0', port=8443)
