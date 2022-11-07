from datetime import datetime
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
    d = datetime.now()
    fileName = f"rebalance-{d.strftime('%Y-%m-%d')}-log.txt"
    with open(fileName, "a") as f:
        # Append 'hello' at the end of file
        f.write(f"{d.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
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


def buy(symbol, amount, rate, market='limit'):
    if amount > 50:
        data = {
            'sym': f'THB_{symbol}',
            'amt': amount,  # THB amount you want to spend
            'rat': rate,
            'typ': market,  # market or limit
            'ts': server_time(),
        }

        signature = sign(data)
        data['sig'] = signature

        # print('Payload with signature: ' + json_encode(data))
        response = requests.post(f'{API_HOST}/api/market/place-bid',
                                 headers=header, data=json_encode(data))

        obj = response.json()["result"]
        id = obj["id"]  # "id": 1, // order id
        # "hash": "fwQ6dnQWQPs4cbatFGc9LPnpqyu", // order hash
        hash = obj["hash"]
        typ = obj["typ"]  # "typ": "limit", // order type
        amt = obj["amt"]  # "amt": 1.00000000, // selling amount
        rat = obj["rat"]  # "rat": 15000, // rate
        fee = obj["fee"]  # "fee": 37.5, // fee
        cre = obj["cre"]  # "cre": 37.5, // fee credit used
        rec = obj["rec"]  # "rec": 15000, // amount to receive
        ts = obj["ts"]  # "ts": 1533834844 // timestamp
        msg = f"Buy id: {id} hash: {hash} typ: {typ} amt: {amt} rat: {rat} fee: {fee}"
        create_log(msg)

        print('Buy Response: ' + response.text)
        return response.status_code

    return 500


def sell(symbol, amount, rate, market='limit'):
    data = {
        'sym': f'THB_{symbol}',
        'amt': amount,  # THB amount you want to spend
        'rat': rate,
        'typ': market,  # market or limit
        'ts': server_time(),
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
    msg = f"Sell id: {id} hash: {hash} typ: {typ} amt: {amt} rat: {rat} fee: {fee}"
    create_log(msg)
    print('Sell Response: ' + response.text)
    return response.status_code


def cancel(symbol, order_id, sd, txt_hash):
    data = {
        'sym': f'THB_{symbol}',
        'id': order_id,
        'sd': sd,
        'hash': txt_hash,
        'ts': server_time(),
    }

    signature = sign(data)
    data['sig'] = signature

    # print('Payload with signature: ' + json_encode(data))
    response = requests.post(f'{API_HOST}/api/market/cancel-order',
                             headers=header, data=json_encode(data))
    # obj = response.json()
    msg = f"Cancel id: {id} hash: {hash} sts: {response.status_code}"
    create_log(msg)
    return response.status_code


def check_order_hold(symbol):
    try:
        data = {
            'sym': f'THB_{symbol}',
            'ts': server_time(),
        }

        signature = sign(data)
        data['sig'] = signature

        # print('Payload with signature: ' + json_encode(data))
        response = requests.post(f'{API_HOST}/api/market/my-open-orders',
                                 headers=header, data=json_encode(data))
        return response.json()["result"]

    except Exception as e:
        pass

    return []


def fetch_balance():
    data = {
        'ts': server_time(),
    }
    signature = sign(data)
    data['sig'] = signature
    #print('Payload with signature: ' + json_encode(data))
    response = requests.post(f'{API_HOST}/api/market/balances',
                             headers=header, data=json_encode(data))
    data = response.json()
    data = data['result']
    return data


def main():
    sym = ['XRP', 'TRX']
    data = fetch_balance()
    # Start Bot
    cost = 300
    baseTotal = 0  # float(data["THB"]['available'])
    for s in sym:
        fetchPrice = get_price(s)
        baseTotal += (float(fetchPrice[0]) * float(data[s]['available']))

    for i in range(0, len(sym)):
        symbol = sym[i]
        fetchPrice = get_price(symbol)
        baseAsset = float(data[symbol]['available'])
        assetPrice = fetchPrice[0] * baseAsset
        assetBidPrice = fetchPrice[1]
        assetAskPrice = fetchPrice[2]

        costDivided = int(baseTotal)
        if costDivided <= (cost/len(sym)):
            costDivided = cost/len(sym)

        else:
            if baseTotal >= cost:
                costDivided = int(baseTotal)/len(sym)

        # ตรวจสอบ Asset
        if int(assetPrice) == 0:
            # ตรวจสอบรายการ Hold
            isHold = check_order_hold(symbol)
            if len(isHold) == 0:
                isStatus = buy(symbol, costDivided, assetBidPrice)
                print(f"Open Order {symbol} Status: {isStatus}")

            else:
                msg = f"Hold {isHold[0]['side']} Order {symbol} ID: {isHold[0]['id']}"
                create_log(msg)

        else:
            percentDivided = round(((assetPrice-costDivided)*100)/costDivided, 2)
            print(f"{symbol} Asset: {baseAsset} Price: {assetPrice} Profit: {(assetPrice-costDivided)} Percent: {percentDivided}%")
            if percentDivided > 5 and percentDivided < -3:
                isHold = check_order_hold(symbol)
                if len(isHold) == 0:
                    isStatus = sell(symbol, baseAsset, assetAskPrice)
                    print(f"Sell Order {symbol} Status: {isStatus}")
                else:
                    msg = f"Hold {isHold[0]['side']} Order {symbol} ID: {isHold[0]['id']}"
                    create_log(msg)


if __name__ == '__main__':
    main()
    sys.exit(0)
