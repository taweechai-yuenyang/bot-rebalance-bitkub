import pandas as pd


def get_klines_iter(symbol, interval, start, end, limit=5000):
    df = pd.DataFrame()
    startDate = end
    while startDate > start:
        url = 'https://api.binance.com/api/v3/klines?symbol=' + \
            symbol + '&interval=' + interval + '&limit=' + str(iteration)
        if startDate is not None:
            url += '&endTime=' + str(startDate)

        df2 = pd.read_json(url)
        df2.columns = ['Opentime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Closetime',
                       'Quote asset volume', 'Number of trades', 'Taker by base', 'Taker buy quote', 'Ignore']
        df = pd.concat([df2, df], axis=0, ignore_index=True, keys=None)
        startDate = df.Opentime[0]
    df.reset_index(drop=True, inplace=True)
    return df
