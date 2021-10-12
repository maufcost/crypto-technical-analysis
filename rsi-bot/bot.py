import websocket, json, numpy, talib, config, pprint
import config
from binance.enums import *
from binance.client import Client

# Bot configuration
# RSI is a momentum indicator (remember the ball-thrown-in-the-air metaphor) that
# measures the relative internal strength of a stock or market against ITSELF,
# instead of comparing one asset with another, or a stock with a market.
#
# To calculate RSI 14, we need 15 data points (in our case, 15 closing ETH prices)
RSI_PERIOD = 14
RSI_OVERSOLD_THRESHOLD = 30
RSI_OVERBOUGHT_TRESHOLD = 70
# if ETH is $3000, we will trade TRADE_QUANTITY * 3000
TRADE_QUANTITY = 0.05
TRADE_SYMBOL = "ETHUSD"
# Streaming candlesticks every minute.
SOCKET = "wss://stream.binance.com:9943/ws/ethusdt@kline_1m"

# Initial program setup
closing_prices = []

# Flag so that when we buy ETH (when ETH is oversold), we don't keep buying it
# if it keeps going down. The flag will be back to True when we sell our
# previously bought ETH.
in_position = False
client = Client(config.API_KEY, config.API_SECRET, tld="us")

# side: buy or sell
def order(side, quantity, symbol, order_type=ORDER_TYPE_MARKET):
    try:
        print("Sending order")
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
        print(order)
    except Exception as e:
        print("Failed to create order")
        return False
    return True

def on_open(ws):
    print("Opened websocket connection")

def on_message(ws, message):
    global closing_prices

    print("Message detected")
    json_message = json.loads(message)
    # Candlestick data is under the 'k' property
    pprint.pprint(json_message)
    candlestick = json_message['k']
    # The 'x' boolean property says if it's the order is the last tick of the candlestick
    # i.e. if the candlestick closed.

    # Because we are using the RSI indicator, we are only interested in the
    # closing value.
    is_candlestick_closed = candlestick['x']

    # Closing price
    closing_price = candlestick['c']

    if is_candlestick_closed:
        print("Candlestick closed at ${}".format(closing_price))

        # Building a series of closing prices
        closing_prices.append(float(closing_price))

        if len(closing_prices) > RSI_PERIOD:
            # We need to have at least 15 closing prices since our RSI_PERIOD is 14.
            np_closing_prices = np.array(closing_prices)
            rsi = talib.RSI(np_closing_prices, RSI_PERIOD)
            print("All RSIs calculated so far:")
            print(rsi)

            # The last rsi is the one we use to make our trading decisions.
            last_rsi = rsi[-1]
            print("The current RSI is: {}".format(last_rsi))

            if last_rsi > RSI_OVERBOUGHT_TRESHOLD:
                if in_position:
                    print("Selling...")

                    # Binance sell order logic starts here
                    order_succeeded = order(SIDE_SELL, TRADE_QUANTITY, TRADE_SYMBOL)
                    if order_succeeded:
                        # We managed to sell. Now, we can buy again.
                        in_position = False
                else:
                    print("We don't own anything. Nothing to do, son.")

            if last_rsi < RSI_OVERSOLD_THRESHOLD:
                if in_position:
                    print("It is oversold, but you already own it. Nothing to do for now.")
                else:
                    print("Buying...")

                    # Binance buy order logic starts here
                    order_succeeded = order(SIDE_BUY, TRADE_QUANTITY, TRADE_SYMBOL)
                    if (order_succeeded):
                        # We managed to buy. So, we're in position now.
                        in_position = True

def on_close(ws):
    print("Just closed websocket connection")

ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_message=on_message, on_close=on_close)
ws.run_forever()
