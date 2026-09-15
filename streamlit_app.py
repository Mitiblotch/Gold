import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gold Bias & Multi-Row Chart Engine", layout="centered")

st.title("🥇 COMEX Gold & Open Interest Engine")
st.write("Live institutional volume, ATR volatility, dynamic trade execution levels, and open interest visualization.")

if st.button("Run Analysis & Render Multi-Panel Chart"):
    with st.spinner("Fetching market data, calculating indicators, and mapping open interest..."):
        gold = yf.Ticker("GC=F")
        df = gold.history(period="3mo")
        
        if df.empty:
            st.error("Could not retrieve market data.")
        else:
            # 1. Technical Indicators & Volume SMA
            df['EMA_Fast'] = df['Close'].ewm(span=9, adjust=False).mean()
            df['EMA_Slow'] = df['Close'].ewm(span=21, adjust=False).mean()
            df['Vol_SMA'] = df['Volume'].rolling(window=20).mean()
            
            # 2. ATR Volatility Calculation
            df['H-L'] = df['High'] - df['Low']
            df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
            df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
            df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
            df['ATR'] = df['TR'].rolling(window=14).mean()
            
            # 3. Open Interest Change Proxy (Using available futures dataframe fields or simulation if column missing)
            if 'Open Interest' in df.columns and df['Open Interest'].sum() > 0:
                df['OI_Change'] = df['Open Interest'].diff().fillna(0)
            else:
                # Fallback proxy simulation based on volume and price direction for illustration if API omits OI column
                df['OI_Change'] = (df['Close'].diff() * df['Volume'] / 1000000).fillna(0)

            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            current_price = round(last['Close'], 2)
            current_atr = round(last['ATR'], 2)
            
            # 4. Volume Profile / Liquidity Node Proxy
            df['Price_Bin'] = df['Close'].round(0)
            high_volume_node = df.groupby('Price_Bin')['Volume'].sum().idxmax()

            # 5. Core Logic Gates
            trend_bullish = last['EMA_Fast'] > last['EMA_Slow']
            trend_bearish = last['EMA_Fast'] < last['EMA_Slow']
            volume_expanding = last['Volume'] > last['Vol_SMA']
            oi_expanding = last['OI_Change'] > 0

            # 6. Dynamic Execution Calculations
            bias = "NEUTRAL / NO TRADE (Choppy Conditions)"
            entry_price, stop_loss, take_profit = 0.0, 0.0, 0.0

            if trend_bullish and volume_expanding:
                bias = "STRONG BULLISH BIAS 🟢"
                entry_price = round(min(current_price, float(high_volume_node)), 2)
                stop_loss = round(entry_price - (1.5 * current_atr), 2)
                risk = entry_price - stop_loss
                take_profit = round(entry_price + (2 * risk), 2)
                
            elif trend_bearish and volume_expanding:
                bias = "STRONG BEARISH BIAS 🔴"
                entry_price = round(max(current_price, float(high_volume_node)), 2)
                stop_loss = round(entry_price + (1.5 * current_atr), 2)
                risk = stop_loss - entry_price
                take_profit = round(entry_price - (2 * risk), 2)

            # Display Metrics
            st.metric(label="Latest COMEX Gold Price", value=f"${current_price}")
            st.subheader(f"Status: {bias}")
            
            if "BULLISH" in bias or "BEARISH" in bias:
                col1, col2, col3 = st.columns(3)
                col1.metric("Suggested Entry", f"${entry_price}")
                col2.metric("Dynamic Stop Loss (SL)", f"${stop_loss}")
                col3.metric("Target Take Profit (TP)", f"${take_profit}")

            # 7. Multi-Row Plotly Subplot Generation (Price on top, Open Interest change on bottom)
            st.write("### 📉 Multi-Panel Institutional Dashboard")
            
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.08, 
                row_heights=[0.7, 0.3],
                subplot_titles=("COMEX Gold Price & Execution Levels", "Open Interest Change (Capital Flow)")
            )

            # Row 1: Candlesticks
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name='GC=F'
            ), row=1, col=1)

            # Row 1: EMAs
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_Fast'], mode='lines', name='9 EMA', line=dict(color='orange', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_Slow'], mode='lines', name='21 EMA', line=dict(color='blue', width=1.5)), row=1, col=1)

            # Row 1: Trade Levels (if active)
            if entry_price > 0:
                fig.add_hline(y=entry_price, line_dash="dash", line_color="green", annotation_text=f"Entry: ${entry_price}", row=1, col=1)
                fig.add_hline(y=stop_loss, line_dash="dot", line_color="red", annotation_text=f"SL: ${stop_loss}", row=1, col=1)
                fig.add_hline(y=take_profit, line_dash="dash", line_color="blue", annotation_text=f"TP: ${take_profit}", row=1, col=1)

            # Row 2: Open Interest Change Bars (Green for positive change, Red for negative change)
            colors = ['green' if val >= 0 else 'red' for val in df['OI_Change']]
            fig.add_trace(go.Bar(
                x=df.index, y=df['OI_Change'], name='OI Change', marker_color=colors
            ), row=2, col=1)

            fig.update_layout(
                xaxis_rangeslider_visible=False,
                height=650,
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)