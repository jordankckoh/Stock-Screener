import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_sp500_tickers():
    """
    Fetch S&P 500 tickers using yfinance
    """
    try:
        sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(sp500_url)
        sp500_table = tables[0]
        tickers = sp500_table['Symbol'].tolist()
        return tickers
    except Exception as e:
        raise Exception(f"Failed to fetch S&P 500 tickers: {str(e)}")

def get_hourly_data(ticker):
    """
    Fetch hourly data for a given ticker
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)  # Get 5 days of hourly data

        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date, interval='1h')

        if df.empty:
            return None

        return df
    except Exception as e:
        return None

def calculate_ema(data, period=20):
    """
    Calculate EMA using pandas
    """
    return data.ewm(span=period, adjust=False).mean()

def calculate_ema_trend(df):
    """
    Calculate EMA 20 and check if all price components (Open, High, Low, Close) 
    of last 18 candles are above it
    """
    if df is None or len(df) < 20:
        return False

    try:
        # Calculate EMA 20 using pandas built-in function
        df['EMA20'] = calculate_ema(df['Close'], period=20)

        # Get last 18 candles
        last_18 = df.tail(18)

        # Check if all price components are above EMA20
        open_above = all(last_18['Open'] > last_18['EMA20'])
        high_above = all(last_18['High'] > last_18['EMA20'])
        low_above = all(last_18['Low'] > last_18['EMA20'])
        close_above = all(last_18['Close'] > last_18['EMA20'])

        # All conditions must be true
        trend_above = all([open_above, high_above, low_above, close_above])

        return trend_above
    except Exception as e:
        return False

def send_telegram_alert(bot_token, chat_ids, df_results):
    """
    Send results to multiple Telegram recipients
    """
    try:
        from telegram import Bot
        import asyncio
        
        async def send_message():
            bot = Bot(token=bot_token)
            if df_results.empty:
                message = "No stocks found matching the trend criteria."
            else:
                message = "Stocks trending above EMA 20:\n\n"
                for _, row in df_results.iterrows():
                    message += f"${row['Ticker']}: ${row['Last Price']:.2f}\n"
            
            for chat_id in chat_ids:
                await bot.send_message(chat_id=chat_id, text=message)
            
        asyncio.run(send_message())
    except Exception as e:
        print(f"Failed to send Telegram alert: {str(e)}")

def analyze_stocks(telegram_bot_token=None, telegram_chat_ids=None):
    """
    Analyze all S&P 500 stocks for EMA trend
    """
    try:
        tickers = get_sp500_tickers()
        results = []

        for ticker in tickers:
            df = get_hourly_data(ticker)
            if df is not None:
                trend_above = calculate_ema_trend(df)
                if trend_above:
                    last_price = df['Close'].iloc[-1]
                    last_volume = df['Volume'].iloc[-1]
                    results.append({
                        'Ticker': ticker,
                        'Last Price': round(last_price, 2),
                        'Volume': int(last_volume),
                        'Last Updated': df.index[-1].strftime('%Y-%m-%d %H:%M')
                    })

        df_results = pd.DataFrame(results)
        
        # Send Telegram alert if configured
        if telegram_bot_token and telegram_chat_ids:
            send_telegram_alert(telegram_bot_token, telegram_chat_ids, df_results)
            
        return df_results
    except Exception as e:
        raise Exception(f"Analysis failed: {str(e)}")