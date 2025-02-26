import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import concurrent.futures
import time

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
        return False, None, None, None

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

        if trend_above:
            last_price = df['Close'].iloc[-1]
            last_volume = df['Volume'].iloc[-1]
            last_updated = df.index[-1]
            return trend_above, last_price, last_volume, last_updated
        
        return False, None, None, None
    except Exception as e:
        return False, None, None, None

def process_ticker(ticker):
    """
    Process a single ticker - for parallel execution
    """
    df = get_hourly_data(ticker)
    if df is not None:
        trend_above, last_price, last_volume, last_updated = calculate_ema_trend(df)
        if trend_above:
            return {
                'Ticker': ticker,
                'Last Price': round(last_price, 2),
                'Volume': int(last_volume),
                'Last Updated': last_updated.strftime('%Y-%m-%d %H:%M')
            }
    return None

def send_telegram_alert(bot_token, chat_ids, df_results):
    """
    Send results to multiple Telegram recipients
    """
    try:
        print("Initializing Telegram alert...")
        from telegram.ext import Application, CommandHandler
        import asyncio

        async def refresh_command(update, context):
            message = await update.message.reply_text("🔄 Refreshing stock analysis...")
            df = analyze_stocks(bot_token, chat_ids)
            
            if df.empty:
                await message.edit_text("No stocks found matching the trend criteria.")
            else:
                result_msg = "Stocks trending above EMA 20:\n\n"
                for _, row in df.iterrows():
                    result_msg += f"${row['Ticker']}: ${row['Last Price']:.2f}\n"
                await message.edit_text(result_msg)

        async def send_message():
            print(f"Setting up bot with token: {bot_token[:10]}...")
            application = Application.builder().token(bot_token).build()
            application.add_handler(CommandHandler('refresh', refresh_command))
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            print("Bot application initialized")
            if df_results.empty:
                message = "No stocks found matching the trend criteria."
            else:
                message = "Stocks trending above EMA 20:\n\n"
                for _, row in df_results.iterrows():
                    message += f"${row['Ticker']}: ${row['Last Price']:.2f}\n"
            
            for chat_id in chat_ids:
                try:
                    print(f"Attempting to send message to {chat_id}")
                    await application.bot.send_message(chat_id=chat_id, text=message)
                    print(f"Successfully sent message to {chat_id}")
                except Exception as chat_error:
                    print(f"Failed to send to {chat_id}: {str(chat_error)}")
            
        asyncio.run(send_message())
    except Exception as e:
        print(f"Failed to send Telegram alert: {str(e)}")
        import traceback
        print(traceback.format_exc())

def analyze_stocks(telegram_bot_token=None, telegram_chat_ids=None):
    """
    Analyze all S&P 500 stocks for EMA trend using parallel processing
    """
    try:
        # Get S&P 500 tickers
        tickers = get_sp500_tickers()
        results = []

        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            future_to_ticker = {executor.submit(process_ticker, ticker): ticker for ticker in tickers}
            
            # Process results as they complete
            for i, future in enumerate(concurrent.futures.as_completed(future_to_ticker)):
                result = future.result()
                if result:
                    results.append(result)

        # Create DataFrame from results
        df_results = pd.DataFrame(results)
        
        # Send Telegram alert if configured
        if telegram_bot_token and telegram_chat_ids and not df_results.empty:
            send_telegram_alert(telegram_bot_token, telegram_chat_ids, df_results)
            
        return df_results if not df_results.empty else pd.DataFrame()
    except Exception as e:
        raise Exception(f"Analysis failed: {str(e)}")
