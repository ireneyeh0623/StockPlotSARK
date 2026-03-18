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

stock_id = st.sidebar.text_input("股票代號(如2330.TW或AAPL)", "2330.TW")
start_date = st.sidebar.date_input("起始日期(YYYY/MM/DD)", datetime(2022, 10, 3))
end_date = st.sidebar.date_input("結束日期(YYYY/MM/DD)", datetime.now())

# 增加圖表主題選擇
theme_choice = st.sidebar.radio("圖表主題(對應網頁背景)", ["亮色(白色背景)", "深色(深色背景)"])

# --- 強制背景色切換邏輯 (與五線譜邏輯一致) ---
if theme_choice == "深色(深色背景)":
    chart_template = "plotly_dark"
    font_color = "white"
    bg_color = "#0E1117"
    st.markdown("""
        <style>
        [data-testid="stSidebar"], .stApp, header { background-color: #0E1117 !important; color: white !important; }
        .stMarkdown, p, h1, h2, h3, span { color: white !important; }
        input { color: white !important; background-color: #262730 !important; }
        </style>
        """, unsafe_allow_html=True)
else:
    chart_template = "plotly_white"
    font_color = "black"
    bg_color = "#FFFFFF"
    st.markdown("""
        <style>
        /* 1. 強制背景與文字顏色 */
        [data-testid="stSidebar"], .stApp, header { background-color: #FFFFFF !important; color: black !important; }
        .stMarkdown, p, h1, h2, h3, span { color: black !important; }
        
        /* 2. 徹底消除輸入框右側陰影與淡淡格線 */
        div[data-baseweb="input"], div[data-baseweb="input"] > div, div[data-baseweb="input"] input {
            background-color: white !important;
            border-color: #dcdcdc !important;
            box-shadow: none !important;
        }

        /* 3. 修正按鈕：黑底白字 */
        div.stButton > button {
            background-color: #000000 !important;
            border: 1px solid #000000 !important;
            font-weight: bold !important;
        }
        div.stButton > button * {
            color: #FFFFFF !important;
        }
        div.stButton > button:hover {
            background-color: #333333 !important;
        }

        /* 4. 側邊欄邊框調整 */
        [data-testid="stSidebar"] { border-right: 1px solid #f0f2f6; }
        input { color: black !important; background-color: white !important; }
        </style>
        """, unsafe_allow_html=True)

st.sidebar.markdown("---")
af_start = st.sidebar.slider("AF 起始值", min_value=0.01, max_value=0.10, value=0.02, step=0.01)
af_max = st.sidebar.slider("AF 極限值", min_value=0.10, max_value=0.50, value=0.20, step=0.01)

# 先定義分析按鈕
analyze_btn = st.sidebar.button("開始分析")

search_id = f"{stock_id}.TW" if stock_id.isdigit() else stock_id

st.title("🚀 改良版 SAR 趨勢追蹤系統 (K線版)")

# --- 啟動邏輯：點擊按鈕後才計算 ---
if not analyze_btn:
    st.info("💡 請設定參數後按「開始分析」。")
else:
    data = yf.download(search_id, start=start_date, end=end_date, auto_adjust=True)
    
    if not data.empty:
        df = data.copy().reset_index()
        
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
        # --- 修改此處：新增 rangebreaks 或將 xaxis 類型改為 category 以消除缺口 ---
        fig.update_layout(
            height=700,
            template=chart_template,
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
            font=dict(color=font_color),
            # 關鍵修正：將 xaxis 類型設為 category，忽略非交易日
            xaxis=dict(
                type='category', 
                color=font_color, 
                tickfont=dict(color=font_color),
                # 設定日期顯示格式為：月(縮寫) 日 年
                tickformat='%b %d %Y',
                # 自動控制標籤數量，避免 Nov 2 2025 等字串重疊
                nticks=8  # 限制顯示的座標標籤數量，避免字體重疊
            ),
            yaxis=dict(color=font_color, tickfont=dict(color=font_color)),
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="center", 
                x=0.5,
                font=dict(color=font_color)
            ),
            paper_bgcolor=bg_color,
            plot_bgcolor=bg_color 
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # 數據摘要
        st.header("📊 最新狀態")
        valid_df = df.dropna(subset=['Close_1D'])
        
        if not valid_df.empty:
            last_price = valid_df['Close_1D'].iloc[-1]
            col1, col2, col3 = st.columns(3)
            
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

# 要解決線圖中出現「缺口」的問題，是因為 Plotly 預設會在 X 軸（日期軸）上保留所有日曆天數，包含週末與國定假日。
# 我們需要將 X 軸的類型從預設的日期格式改為**「類別格式 (Category)」**，這樣圖表就會僅按照資料中存在的日期進行連續排列，自動忽略沒有交易數據的日期。
# 1.type='category'：這是最關鍵的設定。它告訴 Plotly 不要把 X 軸當作時間線，而是當作一串「標籤」。這樣一來，中間缺失的日期（休市日）就不會佔用任何空間。
# 2.nticks=10：當 X 軸變成類別格式時，每個日期都會被視為獨立標籤。如果資料量很大，日期字體會重疊。設定 nticks 可以讓系統自動選取合適的間隔來顯示日期標籤。