import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gold Intraday Engine", layout="centered")

st.title("🥇 COMEX Gold Intraday & Institutional Engine")
st.write("Macro Daily Bias Filter combined with 4-Hour Intraday Execution, Data Auditing, and Multi-Panel Visuals.")

if st.button("Run Full Analysis"):
    with st.spinner("Fetching data, resampling to 4-hour candles, and calculating levels..."):
        gold = yf.Ticker("GC=F")
        
        # 1. Fetch Daily Data for Macro Bias Filter
        df_daily = gold.history(period="3mo")
        
        # 2. Fetch Hourly Data and Resample to 4-Hour for Intraday Execution
        df_1h = gold.history(period="60d", interval="1h")
        
        if df_daily.empty or df_1h.empty:
            st.error("Could not retrieve market data.")
        else:
            # Resample 1h to 4h candles (fixed lowercase '4h' for Pandas compatibility)
            df_4h = df_1h.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()

            # --- MACRO DAILY BIAS FILTER ---
            df_daily['EMA_Fast'] = df_daily['Close'].ewm(span=9, adjust=False).mean()
            df_daily['EMA_Slow'] = df_daily['Close'].ewm(span=21, adjust=False).mean()
            df_daily['Vol_SMA'] = df_daily['Volume'].rolling(window=20).mean()
            
            daily_last = df_daily.iloc[-1]
            daily_trend_bullish = daily_last['EMA_Fast'] > daily_last['EMA_Slow']
            daily_trend_bearish = daily_last['EMA_Fast'] < daily_last['EMA_Slow']
            daily_vol_expanding = daily_last['Volume'] > daily_last['Vol_SMA']

            # --- 4-HOUR INTRADAY EXECUTION CALCULATIONS ---
            df_4h['EMA_Fast'] = df_4h['Close'].ewm(span=9, adjust=False).mean()
            df_4h['EMA_Slow'] = df_4h['Close'].ewm(span=21, adjust=False).mean()
            df_4h['Vol_SMA'] = df_4h['Volume'].rolling(window=20).mean()
            
            # 4-Hour ATR (14 period)
            df_4h['H-L'] = df_4h['High'] - df_4h['Low']
            df_4h['H-PC'] = abs(df_4h['High'] - df_4h['Close'].shift(1))
            df_4h['L-PC'] = abs(df_4h['Low'] - df_4h['Close'].shift(1))
            df_4h['TR'] = df_4h[['H-L', 'H-PC', 'L-PC']].max(axis=1)
            df_4h['ATR'] = df_4h['TR'].rolling(window=14).mean()
            
            # Open Interest Proxy Change
            df_4h['OI_Change'] = (df_4h['Close'].diff() * df_4h['Volume'] / 1000000).fillna(0)

            last_4h = df_4h.iloc[-1]
            current_price = round(last_4h['Close'], 2)
            current_4h_atr = round(last_4h['ATR'], 2)
            
            # 4-Hour Liquidity / Volume Node Proxy
            df_4h['Price_Bin'] = df_4h['Close'].round(0)
            hvn_4h = df_4h.groupby('Price_Bin')['Volume'].sum().idxmax()

            # Core Logic Gates (Macro Filter + 4H Intraday confirmation)
            bias = "NEUTRAL / NO TRADE (Choppy Conditions)"
            entry_price, stop_loss, take_profit = 0.0, 0.0, 0.0

            if daily_trend_bullish and daily_vol_expanding:
                bias = "STRONG BULLISH BIAS 🟢 (4H Pullback Setup)"
                entry_price = round(min(current_price, float(hvn_4h)), 2)
                stop_loss = round(entry_price - (1.5 * current_4h_atr), 2)
                risk = entry_price - stop_loss
                take_profit = round(entry_price + (2 * risk), 2)
                
            elif daily_trend_bearish and daily_vol_expanding:
                bias = "STRONG BEARISH BIAS 🔴 (4H Rally Setup)"
                entry_price = round(max(current_price, float(hvn_4h)), 2)
                stop_loss = round(entry_price + (1.5 * current_4h_atr), 2)
                risk = stop_loss - entry_price
                take_profit = round(entry_price - (2 * risk), 2)

            # --- TOP SECTION: METRICS & STATUS ---
            st.metric(label="Latest COMEX Gold Price", value=f"${current_price}")
            st.subheader(f"Status: {bias}")
            
            if "BULLISH" in bias or "BEARISH" in bias:
                st.markdown("### 📊 4-Hour Intraday Execution Levels")
                col1, col2, col3 = st.columns(3)
                col1.metric("Suggested Entry", f"${entry_price}")
                col2.metric("4H ATR Stop Loss (SL)", f"${stop_loss}")
                col3.metric("Target Take Profit (TP)", f"${take_profit}")

            # --- MIDDLE PANEL: RAW DATA TABLE ---
            st.write("### 📋 Middle Panel: Raw 4-Hour Data Audit")
            st.write("Recent 4-hour candles, closing prices, volume, calculated ATR volatility, and open interest capital proxy:")
            st.dataframe(df_4h[['Open', 'High', 'Low', 'Close', 'Volume', 'ATR', 'OI_Change']].tail(6), use_container_width=True)

            # --- BOTTOM PANEL: MULTI-ROW PLOTLY CHART ---
            st.write("### 📉 Bottom Panel: Multi-Panel Institutional Chart")
            
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.08, 
                row_heights=[0.7, 0.3],
                subplot_titles=("4-Hour COMEX Gold Price & Execution Levels", "Open Interest Change (Capital Flow)")
            )

            # Row 1: 4H Candlesticks
            fig.add_trace(go.Candlestick(
                x=df_4h.index, open=df_4h['Open'], high=df_4h['High'],
                low=df_4h['Low'], close=df_4h['Close'], name='4H GC=F'
            ), row=1, col=1)

            # Row 1: 4H EMAs
            fig.add_trace(go.Scatter(x=df_4h.index, y=df_4h['EMA_Fast'], mode='lines', name='4H 9 EMA', line=dict(color='orange', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_4h.index, y=df_4h['EMA_Slow'], mode='lines', name='4H 21 EMA', line=dict(color='blue', width=1.5)), row=1, col=1)

            # Row 1: Trade Levels (if active)
            if entry_price > 0:
                fig.add_hline(y=entry_price, line_dash="dash", line_color="green", annotation_text=f"Entry: ${entry_price}", row=1, col=1)
                fig.add_hline(y=stop_loss, line_dash="dot", line_color="red", annotation_text=f"SL: ${stop_loss}", row=1, col=1)
                fig.add_hline(y=take_profit, line_dash="dash", line_color="blue", annotation_text=f"TP: ${take_profit}", row=1, col=1)

            # Row 2: Open Interest Change Bars
            colors = ['green' if val >= 0 else 'red' for val in df_4h['OI_Change']]
            fig.add_trace(go.Bar(
                x=df_4h.index, y=df_4h['OI_Change'], name='OI Change', marker_color=colors
            ), row=2, col=1)

            fig.update_layout(
                xaxis_rangeslider_visible=False,
                height=650,
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)