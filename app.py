import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.title("🥇 COMEX Gold Daily Bias Checker")
st.write("This app analyzes institutional volume, trend alignment, and open interest proxies to give a daily trading bias for XAUUSD.")

if st.button("Run Daily Analysis"):
    with st.spinner("Fetching data from COMEX futures..."):
        gold = yf.Ticker("GC=F")
        df = gold.history(period="3mo")

        if df.empty:
            st.error("Could not retrieve data.")
        else:
            df['EMA_Fast'] = df['Close'].ewm(span=9, adjust=False).mean()
            df['EMA_Slow'] = df['Close'].ewm(span=21, adjust=False).mean()
            df['Vol_SMA'] = df['Volume'].rolling(window=20).mean()

            last = df.iloc[-1]
            prev = df.iloc[-2]

            price_up = last['Close'] > prev['Close']
            price_down = last['Close'] < prev['Close']
            trend_bullish = last['EMA_Fast'] > last['EMA_Slow']
            trend_bearish = last['EMA_Fast'] < last['EMA_Slow']
            volume_expanding = last['Volume'] > last['Vol_SMA']

            bias = "NEUTRAL (Waiting for structural confirmation)"
            if trend_bullish and price_up and volume_expanding:
                bias = "STRONG BULLISH BIAS 🟢 (Look for buy setups)"
            elif trend_bearish and price_down and volume_expanding:
                bias = "STRONG BEARISH BIAS 🔴 (Look for sell setups)"

            st.metric(label="Latest COMEX Gold Close", value=f"${round(last['Close'], 2)}")
            st.subheader(f"Directional Bias: {bias}")

            st.write("### Raw Data Table")
            st.dataframe(df[['Close', 'Volume']].tail(5))