import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# 網頁配置 (保持不變)
st.set_page_config(page_title="改良版 SAR 趨勢追蹤系統 (K線版)", layout="wide")

# --- [新增] 改良版 SAR 核心計算法 (依照 Word 版邏輯) ---
def calculate_modified_sar(df, af_start=0.02, af_max=0.2):
    data = df.copy()
    data['SAR'] = np.nan
    data['Trend'] = 0  # 1: 多頭, -1: 空頭
    
    # 初始設定
    initial_trend = 1 if data['Close'].iloc[0] > data['Open'].iloc[0] else -1
    current_trend = initial_trend
    current_af = af_start
    
    if initial_trend == 1:
        current_sar = data['Low'].iloc[0]
        ep = data['High'].iloc[0]
    else:
        current_sar = data['High'].iloc[0]
        ep = data['Low'].iloc[0]

    for i in range(len(data)):
        curr_high = data['High'].iloc[i]
        curr_low = data['Low'].iloc[i]
        curr_close = data['Close'].iloc[i]
        
        data.iat[i, data.columns.get_loc('SAR')] = current_sar
        data.iat[i, data.columns.get_loc('Trend')] = current_trend
        
        next_trend = current_trend
        next_af = current_af
        
        if current_trend == 1: # 上升趨勢
            if curr_high > ep:
                ep = curr_high
                next_af = min(current_af + af_start, af_max)
            
            if curr_low <= current_sar: # 觸碰 SAR
                if curr_close > current_sar: # [改良邏輯] 收盤守住
                    next_trend = 1
                    next_af = af_start 
                    ep = curr_high
                    next_sar = curr_low 
                else: # 沒守住，標準反轉
                    next_trend = -1
                    next_af = af_start
                    next_sar = ep
                    ep = curr_low
            else: # 沒觸碰
                next_sar = current_sar + current_af * (ep - current_sar)
                if i > 0: next_sar = min(next_sar, curr_low, data['Low'].iloc[i-1])
        
        else: # 下降趨勢
            if curr_low < ep:
                ep = curr_low
                next_af = min(current_af + af_start, af_max)
            
            if curr_high >= current_sar: # 觸碰 SAR
                if curr_close < current_sar: # [改良邏輯] 收盤壓住
                    next_trend = -1
                    next_af = af_start
                    ep = curr_low
                    next_sar = curr_high
                else: # 沒守住，標準反轉
                    next_trend = 1
                    next_af = af_start
                    next_sar = ep
                    ep = curr_high
            else: # 沒觸碰
                next_sar = current_sar + current_af * (ep - current_sar)
                if i > 0: next_sar = max(next_sar, curr_high, data['High'].iloc[i-1])

        current_sar = next_sar
        current_trend = next_trend
        current_af = next_af

    return data

# --- 側邊欄：參數設定 ---
st.sidebar.header("參數設定")
stock_id = st.sidebar.text_input("股票代號(如2330.TW或AAPL)", "2330.TW")
start_date = st.sidebar.date_input("起始日期(YYYY/MM/DD)", datetime(2022, 10, 3))
end_date = st.sidebar.date_input("結束日期(YYYY/MM/DD)", datetime.now())
theme_choice = st.sidebar.radio("圖表主題(對應網頁背景)", ["亮色(白色背景)", "深色(深色背景)"])

# --- 強制背景色切換邏輯 (保持與五線譜一致) ---
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
        [data-testid="stSidebar"], .stApp, header { background-color: #FFFFFF !important; color: black !important; }
        .stMarkdown, p, h1, h2, h3, span { color: black !important; }
        div[data-baseweb="input"], div[data-baseweb="input"] > div, div[data-baseweb="input"] input {
            background-color: white !important;
            border-color: #dcdcdc !important;
            box-shadow: none !important;
        }
        div.stButton > button {
            background-color: #000000 !important;
            border: 1px solid #000000 !important;
            font-weight: bold !important;
        }
        div.stButton > button * { color: #FFFFFF !important; }
        [data-testid="stSidebar"] { border-right: 1px solid #f0f2f6; }
        input { color: black !important; background-color: white !important; }
        </style>
        """, unsafe_allow_html=True)

st.sidebar.markdown("---")
af_start_val = st.sidebar.slider("AF 起始值", min_value=0.01, max_value=0.10, value=0.02, step=0.01)
af_max_val = st.sidebar.slider("AF 極限值", min_value=0.10, max_value=0.50, value=0.20, step=0.01)

analyze_btn = st.sidebar.button("開始分析")
search_id = f"{stock_id}.TW" if stock_id.isdigit() else stock_id
st.title("🚀 改良版 SAR 趨勢追蹤系統 (K線版)")

if not analyze_btn:
    st.info("💡 請設定參數後按「開始分析」。")
else:
    data = yf.download(search_id, start=start_date, end=end_date, auto_adjust=True)
    
    if not data.empty:
        df = data.copy().reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 1. 計算改良版 SAR
        df_result = calculate_modified_sar(df, af_start=af_start_val, af_max=af_max_val)
        
        # 2. 將結果分配給繪圖欄位
        df['SAR_Long'] = df_result.apply(lambda x: x['SAR'] if x['Trend'] == 1 else np.nan, axis=1)
        df['SAR_Short'] = df_result.apply(lambda x: x['SAR'] if x['Trend'] == -1 else np.nan, axis=1)
        df['Trend'] = df_result['Trend']

        # 3. 繪製圖表 (保持原有配置)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                     name='K線', increasing_line_color='#FF4136', decreasing_line_color='#2ECC40'))
        fig.add_trace(go.Scatter(x=df['Date'], y=df['SAR_Long'], name='多頭支撐', mode='markers',
                                 marker=dict(size=4, color='#FF4136', symbol='circle')))
        fig.add_trace(go.Scatter(x=df['Date'], y=df['SAR_Short'], name='空頭壓力', mode='markers',
                                 marker=dict(size=4, color='#2ECC40', symbol='circle')))

        fig.update_layout(height=700, template=chart_template, xaxis_rangeslider_visible=False,
                          yaxis_title='價格', hovermode='x unified', font=dict(color=font_color),
                          paper_bgcolor=bg_color, plot_bgcolor=bg_color,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
        st.plotly_chart(fig, use_container_width=True)

        # 4. 數據摘要 (完整恢復並適配新數據)
        st.header("📊 最新狀態")
        last_row = df.iloc[-1]
        last_price = last_row['Close']
        is_long = last_row['Trend'] == 1
        
        trend_text = "看漲 (多頭)" if is_long else "看跌 (空頭)"
        trend_icon = "📈" if is_long else "📉"
        sar_val = last_row['SAR_Long'] if is_long else last_row['SAR_Short']
        sar_label = "SAR 支撐位置" if is_long else "SAR 壓力位置"

        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("目前趨勢")
            st.markdown(f"### {trend_icon} {trend_text}")
        with col2:
            st.subheader("最新收盤價")
            st.markdown(f"### {last_price:.2f}")
        with col3:
            st.subheader(sar_label)
            st.markdown(f"### {sar_val:.2f}")
    else:
        st.error("找不到股票資料，請檢查代號是否正確。")



# 修改重點備註
# 1.更換計算法核心：移除原本依賴 pandas_ta 的寫法，改用 calculate_modified_sar 函數 。這能確保當下影線穿過紅點但收盤守住時，紅點不會像傳統 SAR 那樣瞬間反轉變綠 。
# 2.重置機制實作：
# 上升趨勢觸碰：若 Low <= SAR 但 Close > SAR，趨勢標記維持 1，加速因子 (AF) 重置回 0.02，且明日 SAR 起點重置為今日 Low 。
# 下降趨勢觸碰：若 High >= SAR 但 Close < SAR，趨勢標記維持 -1，AF 重置，且明日 SAR 起點重置為今日 High 。
# 3.版面配置凍結：我完全沒有更動側邊欄 (Sidebar)、CSS 樣式區塊、按鈕位置以及 Plotly 的佈局設定 。
# 4.數據銜接：手動算法產出的 SAR 與 Trend 會被拆解回 SAR_Long 與 SAR_Short ，確保您原本的紅、綠點繪圖邏輯能完美承接，不需改動 Plotly 程式碼。
# 這樣修改後，您的 SAR 系統將會比傳統版本更能過濾掉盤中的波動（假跌破/假突破） 。

