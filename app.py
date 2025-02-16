import streamlit as st
import pandas as pd
from utils import analyze_stocks
import time

# Page config
st.set_page_config(
    page_title="S&P 500 EMA Trend Scanner",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
        .stProgress > div > div > div > div {
            background-color: #1f77b4;
        }
        .stDataFrame {
            font-size: 14px;
        }
        .title-container {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# Title and description
st.markdown("""
    <div class="title-container">
        <h1>S&P 500 EMA Trend Scanner 📈</h1>
        <p>This app scans all S&P 500 stocks and filters those trending above their EMA 20 line for the last 18 hourly candles.</p>
    </div>
""", unsafe_allow_html=True)

# Add refresh button
if st.button("🔄 Refresh Analysis"):
    # Telegram configuration
    telegram_bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN", None)
    telegram_chat_ids = st.secrets.get("TELEGRAM_CHAT_IDS", [])
    
    try:
        with st.spinner("Analyzing S&P 500 stocks... This may take a few minutes..."):
            # Create a progress bar
            progress_bar = st.progress(0)
            
            # Perform analysis
            df_results = analyze_stocks(telegram_bot_token, telegram_chat_id)
            
            # Update progress bar to complete
            progress_bar.progress(100)
            time.sleep(0.5)  # Small delay for visual feedback
            progress_bar.empty()  # Remove progress bar
            
            if df_results.empty:
                st.warning("No stocks found matching the trend criteria.")
            else:
                # Display results
                st.success(f"Found {len(df_results)} stocks trending above EMA 20! 🎯")
                
                # Format the dataframe
                st.dataframe(
                    df_results.style.format({
                        'Last Price': '${:.2f}',
                        'Volume': '{:,.0f}'
                    }),
                    use_container_width=True
                )
                
                # Add download button
                csv = df_results.to_csv(index=False)
                st.download_button(
                    label="📥 Download Results",
                    data=csv,
                    file_name="sp500_ema_trends.csv",
                    mime="text/csv"
                )
                
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
else:
    st.info("👆 Click the refresh button to start the analysis")

# Add footer with information
st.markdown("""
    ---
    ### About this Scanner
    - Analyzes hourly timeframe data for all S&P 500 stocks
    - Filters stocks where price is trending above the 20-period EMA
    - Confirms trend by checking the last 18 hourly candles
    - Updates data in real-time when refreshed
    
    ⚠️ **Disclaimer**: This tool is for informational purposes only and should not be considered as financial advice.
""")
