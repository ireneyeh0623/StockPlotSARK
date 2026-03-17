import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pandas_ta as ta
from datetime import datetime

# 網頁配置
st.set_page_config(page_title="股票分析系統 - SARX 版", layout="wide")

# 側邊欄：查詢設定
st.sidebar.header("查詢設定")
stock_id = st.sidebar.text_input("股票代號(如2330.TW或AAPL)", "2330.TW")
start_date = st.sidebar.date_input("起始日期(YYYY/MM/DD)", datetime(2022, 10, 3))
end_date = st.sidebar.date_input("結束日期(YYYY/MM/DD)", datetime.now())

# 主題與顏色設定
theme_choice = st.sidebar.radio("圖表主題 (對應網頁背景)", ["亮色 (白色背景)", "深色 (深色背景)"])
main_line_color = "white" if theme_choice == "深色 (深色背景)" else "black"
chart_template = "plotly_dark" if theme_choice == "深色 (深色背景)" else "plotly_white"

# 功能開關
show_sar = st.sidebar.checkbox("顯示 Parabolic SAR (轉折點)", value=True)

calculate_btn = st.sidebar.button("開始計算")

# 處理台股代號
search_id = stock_id
if stock_id.isdigit():
    search_id = f"{stock_id}.TW"

st.title("📈 股票分析系統 (五線譜 + SARX)")
st.subheader(f"📊 目前分析標的: {search_id}")

if calculate_btn or stock_id:
    # 抓取資料 (確保 auto_adjust=True)
    data = yf.download(search_id, start=start_date, end=end_date, auto_adjust=True)
    
    if not data.empty:
        # 資料整理：確保 Close 是一維數值
        df = data.copy()
        df = df.reset_index()
        
        # 關鍵修正：確保所有核心欄位都是 1D Array
        df['Close_1D'] = df['Close'].values.flatten()
        df['High_1D'] = df['High'].values.flatten()
        df['Low_1D'] = df['Low'].values.flatten()
        df['Time_Idx'] = np.arange(len(df)) 
        
        # --- 1. 計算樂活五線譜 (線性回歸) ---
        z = np.polyfit(df['Time_Idx'], df['Close_1D'], 1)
        p = np.poly1d(z)
        df['Trend_Line'] = p(df['Time_Idx'])
        std_dev = (df['Close_1D'] - df['Trend_Line']).std()
        df['Upper_2'] = df['Trend_Line'] + 2 * std_dev
        df['Upper_1'] = df['Trend_Line'] + 1 * std_dev
        df['Lower_1'] = df['Trend_Line'] - 1 * std_dev
        df['Lower_2'] = df['Trend_Line'] - 2 * std_dev

        # --- 2. 計算 SAR 指標 ---
        # 使用 pandas_ta 計算，並確保欄位正確
        psar = df.ta.psar(high='High_1D', low='Low_1D', close='Close_1D')
        
        # PSAR 會回傳多個欄位 (PSARl, PSARs 等)，我們將它們合併成一欄顯示
        if psar is not None:
            # 取第一欄和第二欄的非空值 (SAR 點位)
            df['SAR'] = psar.iloc[:, 0].fillna(psar.iloc[:, 1])
        else:
            df['SAR'] = np.nan

        # --- 3. 繪製圖表 ---
        fig = go.Figure()
        
        # 收盤價
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Close_1D'], name='收盤價', 
                                 line=dict(color=main_line_color, width=1.5)))
        
        # 五線譜線段
        colors = ['#FF4136', '#FF851B', '#0074D9', '#2ECC40', '#3D9970']
        names = ['極端樂觀', '樂觀', '趨勢中線', '悲觀', '極端悲觀']
        bands = ['Upper_2', 'Upper_1', 'Trend_Line', 'Lower_1', 'Lower_2']
        
        for idx, band in enumerate(bands):
            fig.add_trace(go.Scatter(x=df['Date'], y=df[band], name=names[idx], 
                                     line=dict(dash='dash' if 'Trend' not in band else 'solid', 
                                               color=colors[idx], width=1)))

        # 拋物線 SAR
        if show_sar and 'SAR' in df:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SAR'], name='Parabolic SAR',
                                     mode='markers', marker=dict(size=4, color='purple', symbol='circle')))

        fig.update_layout(height=600, template=chart_template, hovermode='x unified',
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        # 數據摘要
        st.header("📊 數據摘要")
        last_price = df['Close_1D'].iloc[-1]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("最後收盤價", f"{last_price:.2f}")
        
        if 'SAR' in df and not pd.isna(df['SAR'].iloc[-1]):
            last_sar = df['SAR'].iloc[-1]
            col2.metric("SAR 轉折價", f"{last_sar:.2f}")
            if last_price > last_sar:
                col3.success("🔥 目前趨勢：看多 (SAR 位於價下)")
            else:
                col3.warning("❄️ 目前趨勢：看空 (SAR 位於價上)")
        else:
            col2.write("SAR 計算中...")
            
    else:
        st.error("找不到資料，請檢查代號是否正確。")