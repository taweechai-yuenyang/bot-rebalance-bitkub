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


def create_log(msg):
    f = open("rebalance-log.txt", 'w+')
    f.write(msg + "\n")
    f.close()


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
    response = requests.get(f'{API_HOST}/api/servertime')
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
        'typ': 'limit',  # market or limit
        'ts': ts,
    }

    signature = sign(data)
    data['sig'] = signature

    # print('Payload with signature: ' + json_encode(data))
    response = requests.post(f'{API_HOST}/api/market/place-bid',
                             headers=header, data=json_encode(data))

    obj = response.json()["result"]
    id = obj["id"]  # "id": 1, // order id
    hash = obj["hash"]  # "hash": "fwQ6dnQWQPs4cbatFGc9LPnpqyu", // order hash
    typ = obj["typ"]  # "typ": "limit", // order type
    amt = obj["amt"]  # "amt": 1.00000000, // selling amount
    rat = obj["rat"]  # "rat": 15000, // rate
    fee = obj["fee"]  # "fee": 37.5, // fee
    cre = obj["cre"]  # "cre": 37.5, // fee credit used
    rec = obj["rec"]  # "rec": 15000, // amount to receive
    ts = obj["ts"]  # "ts": 1533834844 // timestamp
    msg = f"Buy id: {id} hash: {hash} typ: {typ} amt: {amt} rat: {rat} fee: {fee} cre: {cre} rec: {rec} ts: {ts}"
    create_log(msg)

    print('Buy Response: ' + response.text)
    return response.status_code


def sell(symbol, amount, rate):
    ts = server_time()
    data = {
        'sym': f'THB_{symbol}',
        'amt': amount,  # THB amount you want to spend
        'rat': rate,
        'typ': 'limit',  # market or limit
        'ts': ts,
    }

    signature = sign(data)
    data['sig'] = signature

    # print('Payload with signature: ' + json_encode(data))
    response = requests.post(f'{API_HOST}/api/market/place-ask',
                             headers=header, data=json_encode(data))

    obj = response.json()["result"]
    id = obj["id"]  # "id": 1, // order id
    hash = obj["hash"]  # "hash": "fwQ6dnQWQPs4cbatFGc9LPnpqyu", // order hash
    typ = obj["typ"]  # "typ": "limit", // order type
    amt = obj["amt"]  # "amt": 1.00000000, // selling amount
    rat = obj["rat"]  # "rat": 15000, // rate
    fee = obj["fee"]  # "fee": 37.5, // fee
    cre = obj["cre"]  # "cre": 37.5, // fee credit used
    rec = obj["rec"]  # "rec": 15000, // amount to receive
    ts = obj["ts"]  # "ts": 1533834844 // timestamp
    msg = f"Sell id: {id} hash: {hash} typ: {typ} amt: {amt} rat: {rat} fee: {fee} cre: {cre} rec: {rec} ts: {ts}"
    create_log(msg)
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
    if len(obj["result"]) > 0:
        return False

    return True


def check_balance():
    ts = server_time()
    data = {
        'ts': ts,
    }

    signature = sign(data)
    data['sig'] = signature

    #print('Payload with signature: ' + json_encode(data))
    response = requests.post(f'{API_HOST}/api/market/balances',
                             headers=header, data=json_encode(data))

    data = response.json()
    data = data['result']

    # Start Bot
    percentDivided = 0
    sym = ['MATIC']
    # Check Order Hold
    isOpenOrSell = f"Hold {str(sym)}"
    isHold = False
    for s in sym:
        isHold = check_order_hold(s)

    if isHold:
        baseTotal = float(data["THB"]['available'])
        print('THB คงเหลือ: {}'.format(baseTotal))
        divided = baseTotal/(len(sym) + 1)
        for s in sym:
            lastPrice = get_price(s)
            price = float(data[s]['available'])
            if price == 0:
                isCode = buy(s, divided, lastPrice[1])
                print(f"Open Order {s} is: {isCode}")
                isOpenOrSell = "Buy"

            else:
                percentDivided = round(
                    (((price*lastPrice[0])-baseTotal)*100/baseTotal), 2)
                if percentDivided >= 3 or percentDivided <= -3:
                    # sell
                    isCode = sell(s, float(data[s]['available']), lastPrice[2])
                    print(f"Sell Order {s} is: {isCode}")
                    isOpenOrSell = "Sell"

            print('{} คงเหลือ: {} ราคาล่าสุด: {} ราคาซื้อ: {} ราคาขาย: {} ส่วนต่างจากต้นทุน: {}% สถานะ: {}'.format(
                s, round((price*lastPrice[0]), 2), lastPrice[0], lastPrice[1], lastPrice[2], percentDivided, isOpenOrSell))

    return isOpenOrSell


def main():
    txtStatus = check_balance()
    if txtStatus == "Sell":
        check_balance()

    print(f"Order Is: {txtStatus}")


if __name__ == '__main__':
    main()
    sys.exit(0)
