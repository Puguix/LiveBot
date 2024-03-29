# - - import used by the bot - -

import sys
sys.path.append("./LiveBot")
import ta
import pandas as pd
from utilities.perp_bitget import PerpBitget
from utilities.custom_indicators import get_n_columns
from datetime import datetime
from pytz import timezone
import json
import discord


# - - print execution starting time - -

now = datetime.now(timezone("Europe/Paris"))
current_time = now.strftime("%d/%m/%Y %H:%M:%S")
print("--- Start Execution Time :", current_time, "---")


# - - get secret data - -

f = open(
    "./LiveBot/secret.json",
)
secret = json.load(f)
f.close()

print(1)

account_to_select = "bot crypto"
production = True
checkConditions = False
tradeClosed = False

# - - Define time frames and trading pair - -

pair = "ETH/USDT:USDT"
timeframe = "1h"
leverage = 2


# - - Define parameters for the strategy - -

risque = 0.05
risqueWithLeverage = risque / leverage
type = ["long", "short"]
trixLength = 8
trixSignal = 21
RSIWindow = 16
top = 0.87
bottom = 0.27


# - - Define rules of the strategy - -

def open_long(row):
    return row['TRIX_HISTO'] > 0 and row['STOCH_RSI'] < top

def close_long(row):
    return row['TRIX_HISTO'] < 0 and row['STOCH_RSI'] > bottom

def open_short(row):
    return row['TRIX_HISTO'] < 0 and row['STOCH_RSI'] > bottom

def close_short(row):
    return row['TRIX_HISTO'] > 0 and row['STOCH_RSI'] < top

print(1.5)

# - - Get bitget API - -

bitget = PerpBitget(
    apiKey=secret[account_to_select]["apiKey"],
    secret=secret[account_to_select]["secret"],
    password=secret[account_to_select]["password"],
)

print(2)

# Get data
df = bitget.get_more_last_historical_async(pair, timeframe, 1000)

# Populate indicator
df.drop(columns=df.columns.difference(['open','high','low','close','volume']), inplace=True)

# - - Trix Indicator - -
df['TRIX'] = ta.trend.ema_indicator(ta.trend.ema_indicator(ta.trend.ema_indicator(close=df['close'], window=trixLength), window=trixLength), window=trixLength)
df['TRIX_PCT'] = df["TRIX"].pct_change()*100
df['TRIX_SIGNAL'] = ta.trend.sma_indicator(df['TRIX_PCT'],trixSignal)
df['TRIX_HISTO'] = df['TRIX_PCT'] - df['TRIX_SIGNAL']

# - - Stochastic RSI - -
df['STOCH_RSI'] = ta.momentum.stochrsi(close=df['close'], window=RSIWindow, smooth1=3, smooth2=3)

print(3)

# - - Get balance - -

usd_balance = float(bitget.get_usdt_equity())
message = f" - - - - - - - - - {now.strftime('%d/%m %H h')}- - - - - - - - - \nCurrent USD balance : {round(usd_balance, 2)} $"


# - - Get open positions - -

positions_data = bitget.get_open_position()
position = [
 {"side": d["side"], "size": float(d["contracts"]) * float(d["contractSize"]), "market_price":d["info"]["marketPrice"], "usd_size": float(d["contracts"]) * float(d["contractSize"]) * float(d["info"]["marketPrice"]), "open_price": d["entryPrice"]} for d in positions_data if d["symbol"] == pair]

row = df.iloc[-2]

print(4)

histo = row['TRIX_HISTO']
rsi = row['STOCH_RSI']

message += f"\nTrix histo: {histo} et RSI: {rsi}"

# - - Check if we have to close positions - -

if len(position) > 0:
    position = position[0]
    message += f"\nCurrent position : {position['side']}, Diff since opening: {round((float(position['market_price']) - float(position['open_price']))/float(position['open_price'])*leverage*100, 2)}%, Open Price: {float(position['open_price'])}"
    print(4.5)

    # - - Long - - 
    if position["side"] == "long" and close_long(row):
        close_long_market_price = float(df.iloc[-1]["close"])
        close_long_quantity = float(
            bitget.convert_amount_to_precision(pair, position["size"])
        )
        exchange_close_long_quantity = close_long_quantity * close_long_market_price
        message += f"\nPlace Close Long Market Order: {close_long_quantity} {pair[:-5]} at the price of {close_long_market_price}$ ~{round(exchange_close_long_quantity, 2)}$"
        tradeClosed = True
        tradeResult = f"{position['side']}: {round((float(close_long_market_price) - float(position['open_price']))/float(position['open_price'])*leverage*100,2)}%"
        if production:
            bitget.place_market_order(pair, "sell", close_long_quantity, reduce=True)
        checkConditions = True

    # - - Short - -
    elif position["side"] == "short" and close_short(row):
        close_short_market_price = float(df.iloc[-1]["close"])
        close_short_quantity = float(
            bitget.convert_amount_to_precision(pair, position["size"])
        )
        exchange_close_short_quantity = close_short_quantity * close_short_market_price
        message += f"\nPlace Close Short Market Order: {close_short_quantity} {pair[:-5]} at the price of {close_short_market_price}$ ~{round(exchange_close_short_quantity, 2)}$"
        tradeClosed = True
        tradeResult = f"{position['side']}: {-round((float(close_short_market_price) - float(position['open_price']))/float(position['open_price'])*leverage*100,2)}%"
        if production:
            bitget.place_market_order(pair, "buy", close_short_quantity, reduce=True)
        checkConditions = True
    
    else:
        message += "\nHolding the position"

print(5)

# - - Check if we have to open a position - -

if len(position) == 0 or checkConditions:
    message += "\nLooking to open a position ..."
    print(5.1)

    # - - Look for a long - -
    if open_long(row) and "long" in type:
        print(5.2)
        long_market_price = float(df.iloc[-1]["close"])
        long_quantity_in_usd = usd_balance * leverage
        long_quantity = float(bitget.convert_amount_to_precision(pair, float(
            bitget.convert_amount_to_precision(pair, long_quantity_in_usd / long_market_price - 0.01)
        )))
        exchange_long_quantity = long_quantity * long_market_price
        print(exchange_long_quantity, usd_balance)
        message += f"\nPlace Open Long Market Order: {long_quantity} {pair[:-5]} at the price of {long_market_price}$ ~{round(exchange_long_quantity, 2)}$"
        if production:
            bitget.place_market_order(pair, "buy", long_quantity)
            bitget.place_market_stop_loss(pair, "buy", long_quantity, long_market_price * (1 - risqueWithLeverage))
        print(5.3)

    # - - Look for a short - -
    elif open_short(row) and "short" in type:
        print(5.5)
        short_market_price = float(df.iloc[-1]["close"])
        short_quantity_in_usd = usd_balance * leverage
        short_quantity = float(bitget.convert_amount_to_precision(pair, float(
            bitget.convert_amount_to_precision(pair, short_quantity_in_usd / short_market_price - 0.01)
        )))
        exchange_short_quantity = short_quantity * short_market_price
        message += f"\nPlace Open Short Market Order: {short_quantity} {pair[:-5]} at the price of {short_market_price}$ ~{round(exchange_short_quantity, 2)}$"
        if production:
            bitget.place_market_order(pair, "sell", short_quantity)
            bitget.place_market_stop_loss(pair, "sell", short_quantity, short_market_price * (1 + risqueWithLeverage))
        print(5.6)

    # - - No position to be opened - -
    else:
        message += "\nNo interesting position found"
        print(5.9)

print(message)

# Discord part to get updates on what the bot is doing

TOKEN = secret["discordToken"]
ID = secret["myDiscordId"]
TRADEID = secret["tradeHistoryId"]

client = discord.Client(intents=discord.Intents.all())


@client.event
async def on_ready():
    print(f'{client.user} has successfully connected to Discord!')
    
    botChannel = client.get_channel(ID)
    await botChannel.send(message)

    if (tradeClosed):
        tradeChannel = client.get_channel(TRADEID)
        await tradeChannel.send(tradeResult)

    await client.close()

client.run(TOKEN)


now = datetime.now(timezone("Europe/Paris"))
current_time = now.strftime("%d/%m/%Y %H:%M:%S")
print("--- End Execution Time :", current_time, "---")
