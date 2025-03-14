import flask
from flask import request
import os
import boto3
import json
from pymongo import MongoClient
from bot import ObjectDetectionBot
from loguru import logger


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
mongodb_uri = os.environ['MONGODB_URI']


@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


@app.route('/results', methods=['POST'])
def results():
    data = request.get_json()  # קבל את כל ה-body של הבקשה כ-json
    prediction_id = data.get('predictionId')  # שלוף את ה-predictionId מתוך ה-body

    if not prediction_id:
        return "predictionId is missing", 400  # אם ה-predictionId לא נמצא, מחזירים שגיאה

    # השתמש ב-prediction_id כדי לשלוף את התוצאות מ-MongoDB
    logger.info(f"prediction_id is : {prediction_id}")
    result = get_prediction_results(prediction_id)
    logger.info(f"result is : {result}")
    if not result:
        return "Prediction not found", 404

    logger.info(f"result from DB: {result}")
    if result is None:
        logger.error(f"No prediction found for ID: {prediction_id}")
        return "Prediction not found", 404

    if 'chat_id' in result:
        chat_id = result['chat_id']
    else:
        logger.error(f"chat_id not found in the result: {result}")
        return "chat_id not found", 400

    logger.info(f"Result: {result}")
    # בודק אם קיימים תוצאות זיהוי (labels)
    if 'labels' in result:
        message = "Prediction Results:\n\n"

        # מעבד את כל האובייקטים שנמצאו בתמונה
        for label in result['labels']:
            message += f"Object: {label['class']}\n"
            message += f"Coordinates: cx={label['cx']}, cy={label['cy']}, width={label['width']}, height={label['height']}\n\n"
    else:
        message = "No objects found in the image."

    bot.send_text(chat_id, message)  # שולח את התוצאה למשתמש בטלגרם
    return 'Ok'



@app.route(f'/loadTest/', methods=['POST'])
def load_test():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


def get_prediction_results(prediction_id):
    # חיבור ל-MongoDB (הנח כאן את פרטי החיבור שלך)
    mongo_client = MongoClient(mongodb_uri)
    logger.info(f"mongo_client is : {mongo_client}")
    db = mongo_client['yolo5_db']  # שם המסד
    logger.info(f"db is : {prediction_id}")
    predictions = db['predictions']  # אוסף התוצאות
    logger.info(f"prediction is : {predictions}")

    db.predictions.find({"prediction_id": "68908143-5b66-4f41-a02a-62773609ec4a"})
    result = predictions.find_one({"prediction_id": prediction_id})  # חיפוש תוצאה לפי prediction_id
    if result:
        logger.info(f"Found prediction: {result}")
    else:
        logger.error(f"Prediction with ID {prediction_id} not found.")
    return result  # מחזיר את התוצאה אם נמצאה


if __name__ == "__main__":
    bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL, S3_BUCKET_NAME, SQS_QUEUE_URL)

    app.run(host='0.0.0.0', port=8443)
