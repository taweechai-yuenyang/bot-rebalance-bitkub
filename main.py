import json
import hashlib
import hmac
import os
import sys
import requests

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env.local"))

API_HOST = "https://api.bitkub.com"
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# check balances
header = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-BTK-APIKEY': API_KEY,
}


# encode
def json_encode(data):
    return json.dumps(data, separators=(',', ':'), sort_keys=True)


# create signature
def sign(data):
    j = json_encode(data)
    h = hmac.new(bytes(API_SECRET, "utf-8"),
                 msg=j.encode(), digestmod=hashlib.sha256)
    return h.hexdigest()


# check server time
def server_time():
    response = requests.get(API_HOST + '/api/servertime')
    ts = int(response.text)
    #print('Server time: ' + response.text)
    return ts


def get_price(symbol):
    pair = f"THB_{symbol}"
    response = requests.request(
        "GET", f"{API_HOST}/api/market/ticker?sym={pair}")
    lastPrice = [0, 0, 0]
    if response.status_code == 200:
        obj = response.json()
        if len(obj) > 0:
            # last ราคาล่าสุด
            # highestBid รายคาซื้อ
            # lowestAsk ราคาขาย
            lastPrice = [
                float(obj[pair]["last"]),
                float(obj[pair]["highestBid"]),
                float(obj[pair]["lowestAsk"])
            ]
    # print(response.text)
    return lastPrice


def buy(symbol, amount, rate):
    ts = server_time()
    data = {
        'sym': f'THB_{symbol}',
        'amt': amount,  # THB amount you want to spend
        'rat': rate,
        'typ': 'limit',
        'ts': ts,
    }

    signature = sign(data)
    data['sig'] = signature

    # print('Payload with signature: ' + json_encode(data))
    response = requests.post(f'{API_HOST}/api/market/place-bid',
                             headers=header, data=json_encode(data))
    print('Buy Response: ' + response.text)
    return response.status_code


def sell(symbol, amount, rate):
    ts = server_time()
    data = {
        'sym': f'THB_{symbol}',
        'amt': amount,  # THB amount you want to spend
        'rat': rate,
        'typ': 'limit',
        'ts': ts,
    }

    signature = sign(data)
    data['sig'] = signature

    # print('Payload with signature: ' + json_encode(data))
    response = requests.post(f'{API_HOST}/api/market/place-ask',
                             headers=header, data=json_encode(data))
    print('Sell Response: ' + response.text)
    return response.status_code

def check_order_hold(symbol):
    ts = server_time()
    data = {
        'sym': f'THB_{symbol}',
        'ts': ts,
    }

    signature = sign(data)
    data['sig'] = signature

    # print('Payload with signature: ' + json_encode(data))
    response = requests.post(f'{API_HOST}/api/market/my-open-orders',
                             headers=header, data=json_encode(data))
    obj = response.json()
    print('Sell Response: ' + response.text)
    if len(obj["result"]) > 0:
        return False
    
    return True


def check_balance(s, data, baseTotal, divided):
    lastPrice = get_price(s)
    price = float(data[s]['available'])
    if price > 0:
        price = price*lastPrice[0]
    percentDivided = round(((price-baseTotal)*100/baseTotal), 2)

    isOpenOrSell = "-"
    if price == 0:
        isCode = buy(s, divided, lastPrice[1])
        print(f"Open Order {s} is: {isCode}")
        isOpenOrSell = "Buy"

    if percentDivided > 1:
        isCode = sell(s, float(data[s]['available']), lastPrice[2])
        print(f"Sell Order {s} is: {isCode}")
        isOpenOrSell = "Sell"

    print('{} คงเหลือ: {} ราคาล่าสุด: {} ราคาซื้อ: {} ราคาขาย: {} ส่วนต่างจากต้นทุน: {}%'.format(
        s, round(price, 2), lastPrice[0], lastPrice[1], lastPrice[2], percentDivided))

    return isOpenOrSell


def main():
    ts = server_time()
    data = {
        'ts': ts,
    }

    signature = sign(data)
    data['sig'] = signature

    #print('Payload with signature: ' + json_encode(data))
    response = requests.post(API_HOST + '/api/market/balances',
                             headers=header, data=json_encode(data))

    #print('Balances: ' + response.text)
    data = response.json()
    data = data['result']

    sym = ['JFIN']
    ### Check Order Hold
    isHold = False
    for s in sym:
        isHold = check_order_hold(s)

    if isHold:
        baseTotal = float(data["THB"]['available'])
        print('THB คงเหลือ: {}'.format(baseTotal))
        divided = baseTotal/(len(sym) + 1)
        for s in sym:
            if float(data[s]['available']) == 0:
                baseTotal = divided

            check_balance(s, data, baseTotal, divided)


if __name__ == '__main__':
    main()
    sys.exit(0)
