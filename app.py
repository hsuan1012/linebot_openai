from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os
import openai
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
import time

# Initialize Flask app
app = Flask(__name__)

# Initialize LINE API
line_bot_api = LineBotApi(os.getenv('tsGykdGQN1KnwwQWwkkmq7JM0ji0RnYXFa0DBN3sfLVJ4wgcXudGmWpUZst3ZDBHXCL7xp2NhVrR1eDJKdExozjb6DInsSdHeSw1rtrjmz9Bi3Tx/YiI1g4/yGU95a0Jg15MyGM9QFCNdrM2SfU+XQdB04t89/1O/w1cDnyilFU='))
handler = WebhookHandler(os.getenv('0584d0fc476d78024afcd7cbbf8096b4'))

# Initialize OpenAI API
openai.api_key = os.getenv('OPENAI_API_KEY')

# Selenium setup
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
service = ChromeService(executable_path="/usr/local/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

def scrape_transit_info():
    try:
        driver.get("https://transit.navitime.com/zh-tw/tw/transfer?start=00016389&goal=00022583") 
        driver.refresh()
        time.sleep(3) 

        transit_info = "捷運士林站(中正)-東吳大學:\n"

        table_element = driver.find_element(By.ID, "transit-1")
        table_text = table_element.text
        transit_info += table_text + "\n\n"

        table_element = driver.find_element(By.ID, "transit-2")
        table_text = table_element.text
        transit_info += table_text

        return transit_info

    except Exception as e:
        print("發生錯誤:", str(e))
        return "無法抓取捷運資訊。"

# Function to get GPT response
def GPT_response(text):
    try:
        response = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=text,
            temperature=0.5,
            max_tokens=500
        )
        answer = response['choices'][0]['text'].strip()
        return answer
    except Exception as e:
        print(f"Error in GPT_response: {e}")
        return "Error generating response from GPT"

# Webhook callback route
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# Handle text messages
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    if "交通" in msg:
        transit_info = scrape_transit_info()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(transit_info))
    else:
        try:
            GPT_answer = GPT_response(msg)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
        except Exception as e:
            print(traceback.format_exc())
            error_message = 'Error with OpenAI API key or exceeding usage limits. Check logs for more details.'
            line_bot_api.reply_message(event.reply_token, TextSendMessage(error_message))

# Handle postback events
@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    if data == "交通":
        transit_info = scrape_transit_info()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(transit_info))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage("未知的 postback 事件"))

# Welcome new members
@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    welcome_message = TextSendMessage(text=f'{name} 歡迎加入')
    line_bot_api.reply_message(event.reply_token, welcome_message)

# Run the Flask app
if __name__ == "__main__":
    try:
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port)
    finally:
        driver.quit()
