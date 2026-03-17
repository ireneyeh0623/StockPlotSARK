import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pandas_ta as ta
from datetime import datetime

# 網頁配置
st.set_page_config(page_title="改良版 SAR 趨勢追蹤系統 (K線版)", layout="wide")

# 側邊欄：參數設定
st.sidebar.header("參數設定")
stock_id = st.sidebar.text_input("股票代號", "2330")
start_date = st.sidebar.date_input("起始日期", datetime(2025, 8, 29))
end_date = st.sidebar.date_input("結束日期", datetime.now())

st.sidebar.markdown("---")
# 加入 AF 移動軸
af_start = st.sidebar.slider("AF 起始值", min_value=0.01, max_value=0.10, value=0.02, step=0.01)
af_max = st.sidebar.slider("AF 極限值", min_value=0.10, max_value=0.50, value=0.20, step=0.01)

analyze_btn = st.sidebar.button("開始分析")

# 處理台股代號
search_id = f"{stock_id}.TW" if stock_id.isdigit() else stock_id

st.title("🚀 改良版 SAR 趨勢追蹤系統 (K線版)")

if not analyze_btn:
    st.info("💡 請設定參數後按「開始分析」。")

if analyze_btn:
    # 抓取資料
    data = yf.download(search_id, start=start_date, end=end_date, auto_adjust=True)
    
    if not data.empty:
        df = data.copy().reset_index()
        # 確保資料格式
        df['Close_1D'] = df['Close'].values.flatten()
        df['High_1D'] = df['High'].values.flatten()
        df['Low_1D'] = df['Low'].values.flatten()
        df['Open_1D'] = df['Open'].values.flatten()
        
        # 使用自定義的 AF 參數計算 SAR
        # pandas_ta 的 psar 參數: af0=起始值, af=增量(通常同起始值), max_af=極限值
        psar = df.ta.psar(high='High_1D', low='Low_1D', close='Close_1D', 
                          af0=af_start, af=af_start, max_af=af_max)
        
        # 取得 PSARl (多頭支撐) 與 PSARs (空頭壓力)
        df['SAR_Long'] = psar.iloc[:, 0]  # 多頭點位
        df['SAR_Short'] = psar.iloc[:, 1] # 空頭點位

        # 繪圖
        fig = go.Figure()

        # 1. 繪製 K 線圖 (Candlestick)
        fig.add_trace(go.Candlestick(
            x=df['Date'],
            open=df['Open_1D'],
            high=df['High_1D'],
            low=df['Low_1D'],
            close=df['Close_1D'],
            name='K線',
            increasing_line_color='#FF4136', # 紅漲
            decreasing_line_color='#2ECC40'  # 綠跌
        ))

        # 2. 繪製多頭支撐 SAR (紅色點)
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['SAR_Long'],
            name='多頭支撐',
            mode='markers',
            marker=dict(size=4, color='#FF4136', symbol='circle')
        ))

        # 3. 繪製空頭壓力 SAR (綠色點)
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['SAR_Short'],
            name='空頭壓力',
            mode='markers',
            marker=dict(size=4, color='#2ECC40', symbol='circle')
        ))

        # 圖表佈局調整
        fig.update_layout(
            height=700,
            template='plotly_dark',
            xaxis_rangeslider_visible=False, # 隱藏下方的範圍滑桿，讓畫面更簡潔
            yaxis_title='價格',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # 數據摘要
        col1, col2 = st.columns(2)
        last_price = df['Close_1D'].iloc[-1]
        
        with col1:
            st.metric("最新收盤價", f"{last_price:.2f}")
        with col2:
            if not pd.isna(df['SAR_Long'].iloc[-1]):
                st.success(f"🔥 目前趨勢：多頭 (支撐價: {df['SAR_Long'].iloc[-1]:.2f})")
            elif not pd.isna(df['SAR_Short'].iloc[-1]):
                st.warning(f"❄️ 目前趨勢：空頭 (壓力價: {df['SAR_Short'].iloc[-1]:.2f})")
    else:
        st.error("找不到股票資料，請檢查代號是否正確。")