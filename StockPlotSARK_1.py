import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pandas_ta as ta
from datetime import datetime

# 網頁配置
st.set_page_config(page_title="改良版 SAR 趨勢追蹤系統 (K線版)", layout="wide")

# --- 側邊欄：參數設定 ---
st.sidebar.header("參數設定")

# 1. 股票代號標籤
stock_id = st.sidebar.text_input("股票代號(如2330.TW或AAPL)", "2330")

# 2. 起始日期標籤與預設值
start_date = st.sidebar.date_input("起始日期(YYYY/MM/DD)", datetime(2022, 10, 3))

# 3. 結束日期標籤
end_date = st.sidebar.date_input("結束日期(YYYY/MM/DD)", datetime.now())

# 增加圖表主題選擇
theme_choice = st.sidebar.radio("圖表主題(對應網頁背景)", ["亮色(白色背景)", "深色(深色背景)"])

# 修正背景顏色切換邏輯
if theme_choice == "深色(深色背景)":
    chart_template = "plotly_dark"
    # 使用 CSS 強制切換 Streamlit 背景
    st.markdown("""
        <style>
        .stApp { background-color: #0E1117; color: white; }
        </style>
        """, unsafe_allow_html=True)
else:
    chart_template = "plotly_white"
    st.markdown("""
        <style>
        .stApp { background-color: white; color: black; }
        </style>
        """, unsafe_allow_html=True)

st.sidebar.markdown("---")
af_start = st.sidebar.slider("AF 起始值", min_value=0.01, max_value=0.10, value=0.02, step=0.01)
af_max = st.sidebar.slider("AF 極限值", min_value=0.10, max_value=0.50, value=0.20, step=0.01)

analyze_btn = st.sidebar.button("開始分析")

# 處理台股代號
search_id = f"{stock_id}.TW" if stock_id.isdigit() else stock_id

st.title("🚀 改良版 SAR 趨勢追蹤系統 (K線版)")

# --- 修正邏輯：點選連結首頁顯示提醒文字 ---
# 只有在按下按鈕後才會執行分析，否則顯示提示
if not analyze_btn:
    st.info("💡 請設定參數後按「開始分析」。")
else:
    # 抓取資料
    data = yf.download(search_id, start=start_date, end=end_date, auto_adjust=True)
    
    if not data.empty:
        df = data.copy().reset_index()
        
        # --- 解決 KeyError：強制轉換欄位名稱並壓平 ---
        # 處理 yfinance 可能產生的 Multi-index 或多餘維度
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df['Close_1D'] = df['Close'].values.flatten()
        df['High_1D'] = df['High'].values.flatten()
        df['Low_1D'] = df['Low'].values.flatten()
        df['Open_1D'] = df['Open'].values.flatten()
        
        # 計算 SAR
        psar = df.ta.psar(high='High_1D', low='Low_1D', close='Close_1D', 
                          af0=af_start, af=af_start, max_af=af_max)
        
        if psar is not None:
            df['SAR_Long'] = psar.iloc[:, 0]
            df['SAR_Short'] = psar.iloc[:, 1]
        else:
            df['SAR_Long'] = np.nan
            df['SAR_Short'] = np.nan

        # 繪圖
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df['Date'],
            open=df['Open_1D'],
            high=df['High_1D'],
            low=df['Low_1D'],
            close=df['Close_1D'],
            name='K線',
            increasing_line_color='#FF4136',
            decreasing_line_color='#2ECC40'
        ))

        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['SAR_Long'],
            name='多頭支撐',
            mode='markers',
            marker=dict(size=4, color='#FF4136', symbol='circle')
        ))

        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['SAR_Short'],
            name='空頭壓力',
            mode='markers',
            marker=dict(size=4, color='#2ECC40', symbol='circle')
        ))

        fig.update_layout(
            height=700,
            template=chart_template,
            xaxis_rangeslider_visible=False,
            yaxis_title='價格',
            hovermode='x unified',
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="center", 
                x=0.5
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # 數據摘要
        st.header("📊 數據摘要")
        # 修正 KeyError 的地方：確保使用正確的欄位名稱過濾空值
        valid_df = df.dropna(subset=['Close_1D'])
        
        if not valid_df.empty:
            last_price = valid_df['Close_1D'].iloc[-1]
            col1, col2, col3 = st.columns(3)
            col1.metric("最後收盤價", f"{last_price:.2f}")
            
            # 趨勢判斷
            if not pd.isna(df['SAR_Long'].iloc[-1]):
                col2.metric("支撐價", f"{df['SAR_Long'].iloc[-1]:.2f}")
                col3.success("🔥 目前趨勢：多頭")
            elif not pd.isna(df['SAR_Short'].iloc[-1]):
                col2.metric("壓力價", f"{df['SAR_Short'].iloc[-1]:.2f}")
                col3.warning("❄️ 目前趨勢：空頭")
    else:
        st.error("找不到股票資料，請檢查代號是否正確。")