from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os

import requests
from bs4 import BeautifulSoup, Comment
import re
from prettytable import PrettyTable

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])

def get_tables():
    url = "https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?a=9200&b=9268&c=E&d=1"
    headers = {
        "content-type": "text/html; charset=UTF-8",
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36'
    }
    res = requests.get(url, headers =  headers) 
    soup = BeautifulSoup(res.text,'html.parser') 

    return soup.select('table')

def get_volume(code):
    url_tmp = f"https://fubon-ebrokerdj.fbs.com.tw/Z/ZC/ZCX/ZCX_{code}.djhtm"
    headers = {
        "content-type": "text/html; charset=UTF-8",
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36'
    }
    res_tmp = requests.get(url_tmp, headers =  headers) 
    soup_tmp = BeautifulSoup(res_tmp.text,'html.parser') 
    inform = soup_tmp.select('table')[3].select('tr')[3]
    for i, row in enumerate(inform.select('.t3n0')):
        if(row.text == '成交量'):
            return inform.select('.t3n1')[i].text
        
def get_stock_info():
    tables = get_tables()
    pattern = re.compile(r"[(](.*?)[)]", re.S)
    stock_table = PrettyTable(['代碼', '券商名稱', '買進張數', '賣出張數', '差額', '成交比例'])

    for i, tr in enumerate(tables[3].select('tr')):
        if i==0:
            if tr.text != '買超':
                break
            else:
                continue
        if i==1:
            continue

        if tr.find('script'):
            code_name = re.findall(pattern, tr.select('script')[0].text)[0].split(',')
            code = code_name[0].replace("'", "").replace("AS", "")
            name = code_name[1].replace("'", "")
            price = tr.select('.t3n1')
            volume = int(get_volume(code).replace(",", ""))
            buy = int(price[2].text.replace(",", ""))
            ratio = round(buy/volume*100, 2)
            stock_table.add_row([code, name, price[0].text, price[1].text, price[2].text, ratio])

    return stock_table.get_string(sortby="成交比例", reversesort=True)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message = TextSendMessage(text=get_stock_info())
    line_bot_api.reply_message(event.reply_token, message)

import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
