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

stock_id = st.sidebar.text_input("股票代號(如2330.TW或AAPL)", "2330")
start_date = st.sidebar.date_input("起始日期(YYYY/MM/DD)", datetime(2022, 10, 3))
end_date = st.sidebar.date_input("結束日期(YYYY/MM/DD)", datetime.now())

# 增加圖表主題選擇
theme_choice = st.sidebar.radio("圖表主題(對應網頁背景)", ["亮色(白色背景)", "深色(深色背景)"])

# --- 強制背景色切換邏輯 (CSS 優化) ---
if theme_choice == "深色(深色背景)":
    chart_template = "plotly_dark"
    font_color = "white"
    bg_color = "#0E1117"
    st.markdown("""
        <style>
        /* 強制側邊欄、主背景、文字顏色為深色 */
        [data-testid="stSidebar"], .stApp, header { background-color: #0E1117 !important; color: white !important; }
        .stMarkdown, p, h1, h2, h3, span { color: white !important; }
        /* 調整輸入框文字顏色 */
        input { color: white !important; background-color: #262730 !important; }
        </style>
        """, unsafe_allow_html=True)
else:
    chart_template = "plotly_white"
    font_color = "black"
    bg_color = "#FFFFFF"
    st.markdown("""
        <style>
        /* 強制側邊欄、主背景、文字顏色為純白 */
        [data-testid="stSidebar"], .stApp, header { background-color: #FFFFFF !important; color: black !important; }
        .stMarkdown, p, h1, h2, h3, span { color: black !important; }
        /* 調整輸入框與按鈕邊框 */
        [data-testid="stSidebar"] { border-right: 1px solid #f0f2f6; }
        input { color: black !important; background-color: white !important; border: 1px solid #dcdcdc !important; }
        </style>
        """, unsafe_allow_html=True)

st.sidebar.markdown("---")
af_start = st.sidebar.slider("AF 起始值", min_value=0.01, max_value=0.10, value=0.02, step=0.01)
af_max = st.sidebar.slider("AF 極限值", min_value=0.10, max_value=0.50, value=0.20, step=0.01)

analyze_btn = st.sidebar.button("開始分析")

search_id = f"{stock_id}.TW" if stock_id.isdigit() else stock_id

st.title("🚀 改良版 SAR 趨勢追蹤系統 (K線版)")

if not analyze_btn:
    st.info("💡 請設定參數後按「開始分析」。")
else:
    data = yf.download(search_id, start=start_date, end=end_date, auto_adjust=True)
    
    if not data.empty:
        df = data.copy().reset_index()
        
        # 解決 Multi-index 與 1D 資料轉換問題
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df['Close_1D'] = df['Close'].values.flatten()
        df['High_1D'] = df['High'].values.flatten()
        df['Low_1D'] = df['Low'].values.flatten()
        df['Open_1D'] = df['Open'].values.flatten()
        
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
            x=df['Date'], open=df['Open_1D'], high=df['High_1D'], low=df['Low_1D'], close=df['Close_1D'],
            name='K線', increasing_line_color='#FF4136', decreasing_line_color='#2ECC40'
        ))

        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['SAR_Long'], name='多頭支撐', mode='markers',
            marker=dict(size=4, color='#FF4136', symbol='circle')
        ))

        fig.add_trace(go.Scatter(
            x=df['Date'], y=df['SAR_Short'], name='空頭壓力', mode='markers',
            marker=dict(size=4, color='#2ECC40', symbol='circle')
        ))

        fig.update_layout(
            height=700,
            template=chart_template,
            xaxis_rangeslider_visible=False,
            yaxis_title='價格',
            hovermode='x unified',
            font=dict(color=font_color), # 同步 Plotly 字體顏色
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict, color=font_color),
            paper_bgcolor=bg_color,
            plot_bgcolor=bg_color 
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # 數據摘要 (修正 nan 問題)
        st.header("📊 最新狀態")
        valid_df = df.dropna(subset=['Close_1D'])
        
        if not valid_df.empty:
            last_price = valid_df['Close_1D'].iloc[-1]
            col1, col2, col3 = st.columns(3)
            
            # 判斷趨勢
            is_long = not pd.isna(df['SAR_Long'].iloc[-1])
            trend_text = "看漲 (多頭)" if is_long else "看跌 (空頭)"
            trend_icon = "📈" if is_long else "📉"
            sar_val = df['SAR_Long'].iloc[-1] if is_long else df['SAR_Short'].iloc[-1]
            sar_label = "SAR 支撐位置" if is_long else "SAR 壓力位置"

            with col1:
                st.subheader("目前趨勢")
                st.markdown(f"### {trend_icon} {trend_text}")
            with col2:
                st.subheader("收盤價")
                st.markdown(f"### {last_price:.2f}")
            with col3:
                st.subheader(sar_label)
                st.markdown(f"### {sar_val:.2f}")
                
    else:
        st.error("找不到股票資料，請檢查代號是否正確。")