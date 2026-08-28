import streamlit as st
import pandas as pd
import os
import re
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_lightweight_charts import renderLightweightCharts

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Master Quant Engine", layout="wide", page_icon="📈")

# --- DATA LOADING FUNCTIONS ---
@st.cache_data(ttl=60)
def load_data(file_path):
    if os.path.exists(file_path):
        try: return pd.read_csv(file_path)
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def load_markdown(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f: return f.read()
    return "*AI Analysis is pending or no qualifying setups were found today.*"

# --- PORTFOLIO ACTION FUNCTIONS ---
def add_to_portfolio(raw_stock, df_source):
    if raw_stock is None or df_source.empty: return
    stock_row = df_source[df_source['RawStock'] == raw_stock].iloc[0]
    file_path = "portfolio.csv"
    pf = pd.read_csv(file_path) if os.path.exists(file_path) else pd.DataFrame(columns=['Stock', 'RawStock', 'Entry', 'Qty', 'Current_SL', 'T1', 'T2', 'T3', 'Status', 'Sector'])
    if not pf.empty and (pf['RawStock'] == stock_row['RawStock']).any():
        if 'Active' in pf.loc[pf['RawStock'] == stock_row['RawStock'], 'Status'].values:
            st.toast(f"⚠️ {stock_row['RawStock']} is already in your Active Portfolio!", icon="⚠️")
            return
    new_trade = pd.DataFrame([{'Stock': stock_row['Stock'], 'RawStock': stock_row['RawStock'], 'Entry': stock_row['Entry'], 'Qty': stock_row['Qty'], 'Current_SL': stock_row['EqSL'], 'T1': stock_row['EqT1'], 'T2': stock_row['EqT2'], 'T3': stock_row['EqT3'], 'Status': 'Active', 'Sector': 'Unknown'}])
    pf = pd.concat([pf, new_trade], ignore_index=True)
    pf.to_csv(file_path, index=False)
    st.toast(f"✅ Successfully added {stock_row['RawStock']} to your Portfolio Tracking Engine!", icon="✅")

def remove_from_portfolio(raw_stock):
    file_path = "portfolio.csv"
    if os.path.exists(file_path):
        pf = pd.read_csv(file_path)
        pf = pf[pf['RawStock'] != raw_stock]
        pf.to_csv(file_path, index=False)
        st.toast(f"🗑️ Removed {raw_stock} from Portfolio!", icon="✅")

def display_interactive_table(df, tab_name):
    if df.empty:
        st.info(f"No qualifying setups matched the criteria for {tab_name} today.")
        return
    df['Chart'] = "https://in.tradingview.com/chart/?symbol=NSE:" + df['RawStock']
    display_cols = ['Stock', 'Tag', 'Entry', 'EqSL', 'EqT1', 'EqT2', 'Score', 'Vol vs 50d', 'RSI', 'Chart', 'RawStock']
    display_df = df[[col for col in display_cols if col in df.columns]]
    column_config = {
        "Chart": st.column_config.LinkColumn("📊 Chart", display_text="📈 View", help="Open directly in TradingView"),
        "Score": st.column_config.NumberColumn("Score /10", help="Institutional Conviction Score", format="%d ⭐"),
        "Entry": st.column_config.NumberColumn("CMP (₹)", format="₹%.2f"),
        "EqSL": st.column_config.NumberColumn("Stop Loss", format="₹%.2f"),
        "Vol vs 50d": st.column_config.NumberColumn("Vol Spike", format="%.1fx"),
        "RawStock": None 
    }
    st.dataframe(display_df, use_container_width=True, hide_index=True, column_config=column_config)
    st.write("")
    col1, col2 = st.columns([3, 1])
    with col1: selected_stock = st.selectbox(f"Select stock to track from {tab_name}:", df['RawStock'].unique(), key=f"sel_{tab_name}")
    with col2:
        st.write(""); st.write("") 
        if st.button(f"➕ Add to Portfolio", key=f"btn_{tab_name}", use_container_width=True): add_to_portfolio(selected_stock, df)

# --- MAIN UI DASHBOARD LAYOUT ---
st.title("📈 Institutional Quant Dashboard")
st.markdown("Automated Multi-Timeframe Structural Breakout & Retest Scanner")

tabs = st.tabs(["💥 Pre-Breakout", "📈 Swing (1-2 Wk)", "🌙 Perfect BTST", "⚡ Intraday", "💰 Budget (<₹500)", "👑 Index Scalps", "💼 Active Portfolio", "🤖 AI Deep Dive", "📈 Advanced Charting"])

df_all = load_data("all_setups.csv")

# --- POPULATE TABLES ---
if not df_all.empty:
    with tabs[0]: st.header("💥 Pre-Breakout Coils"); display_interactive_table(df_all[df_all['Horizon'] == 'Pre-Breakout'], "Pre-Breakout")
    with tabs[1]: st.header("📈 Swing Trades"); display_interactive_table(df_all[df_all['Horizon'] == 'Swing'], "Swing Trades")
    with tabs[2]: st.header("🌙 Perfect BTST"); display_interactive_table(df_all[df_all['Horizon'] == 'BTST'], "BTST")
    with tabs[3]: st.header("⚡ Intraday Momentum"); display_interactive_table(df_all[df_all['Horizon'] == 'Intraday'], "Intraday")
    with tabs[4]: st.header("💰 Budget Picks (<₹500)"); display_interactive_table(df_all[df_all['Entry'] < 500], "Budget Stocks")
else:
    for i in range(5):
        with tabs[i]: st.info("No quantitative setups passed the institutional guardrails today. Capital protected.")

with tabs[5]:
    st.header("Index Options (5M Scalps)")
    df_index = load_data("index_setups.csv")
    if not df_index.empty: st.dataframe(df_index.drop(columns=['RawStock'], errors='ignore'), use_container_width=True, hide_index=True)
    else: st.info("No Index Scalp setups found.")

with tabs[6]:
    st.header("Active Trailing Portfolio")
    df_portfolio = load_data("portfolio.csv")
    if not df_portfolio.empty:
        active_pf = df_portfolio[df_portfolio['Status'] == 'Active']
        st.subheader(f"🟢 Active Trades ({len(active_pf)})")
        if not active_pf.empty:
            for index, row in active_pf.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{row['Stock']}** (Sector: {row.get('Sector', 'Unknown')}) | **Current SL: ₹{row['Current_SL']}**")
                        st.markdown(f"Entry: ₹{row['Entry']} | T1:₹{row['T1']} // T2:₹{row['T2']} // T3:₹{row['T3']}")
                    with col2:
                        if st.button("❌ Remove", key=f"remove_{row['RawStock']}_{index}"):
                            remove_from_portfolio(row['RawStock'])
                            st.rerun() 
        else: st.info("No active trades currently.")
    else: st.info("Your portfolio is currently empty.")

with tabs[7]:
    st.header("🔬 Institutional Fundamental Analysis")
    raw_ai_report = load_markdown("deep_dive_analysis.md")
    if "Pending Analysis" in raw_ai_report or "No qualifying setups" in raw_ai_report: st.info("AI Analysis is pending or no qualifying setups were found today.")
    else:
        reports = raw_ai_report.split("\n\n---\n\n")
        for report in reports:
            if not report.strip(): continue
            lines = report.strip().split('\n')
            title = lines[0].replace("# Detailed Stock Analysis:", "").strip() if lines else "Stock Analysis"
            scorecard_match = re.search(r'### 12\. Final Scorecard(.*?)(?=### 13\.|$)', report, re.DOTALL)
            summary_match = re.search(r'### 14\. Executive Summary(.*?)(?=###|$)', report, re.DOTALL)
            scorecard_text = scorecard_match.group(1).strip() if scorecard_match else "Data error."
            summary_text = summary_match.group(1).strip() if summary_match else "Data error."
            st.markdown(f"## {title}")
            col1, col2 = st.columns([1.2, 2]) 
            with col1:
                with st.container(border=True): st.markdown("#### 12. Final Scorecard"); st.markdown(scorecard_text)
            with col2:
                with st.container(border=True): st.markdown("#### 14. Executive Summary"); st.markdown(summary_text)
            with st.expander("🔍 Read Full 14-Pillar Fundamental Report"): st.markdown(report)
            st.divider()

# --- TAB 9: NATIVE QUANTITATIVE CHARTING ENGINE ---
with tabs[8]:
    st.header("📈 Interactive Native Charting")
    df_charts = load_data("chart_data.csv")
    
    if df_charts.empty or not df_all.empty == False:
        st.info("Chart data is currently building. Please wait for the next automated market scan to populate historical candlestick data.")
    else:
        chart_tickers = df_charts['Ticker'].unique().tolist()
        col1, col2 = st.columns([1, 2])
        with col1: selected_ticker = st.selectbox("Select Active Setup to Analyze:", chart_tickers)
        with col2: engine_choice = st.radio("Select Rendering Engine:", ["Lightweight Charts (Execution)", "Plotly (Deep Dive)"], horizontal=True)
        
        # Isolate the data
        stock_df = df_charts[df_charts['Ticker'] == selected_ticker].copy()
        stock_df['Date'] = pd.to_datetime(stock_df['Date'])
        
        # Calculate your specific EMAs
        stock_df['EMA9'] = stock_df['Close'].ewm(span=9, adjust=False).mean()
        stock_df['EMA21'] = stock_df['Close'].ewm(span=21, adjust=False).mean()
        stock_df['EMA50'] = stock_df['Close'].ewm(span=50, adjust=False).mean()
        
        if engine_choice == "Lightweight Charts (Execution)":
            st.markdown(f"### {selected_ticker} (Execution View)")
            
            # Format exactly for the JS lightweight charts wrapper
            lw_candles = json.loads(stock_df[['Date', 'Open', 'High', 'Low', 'Close']].rename(columns={'Date':'time'}).to_json(orient='records'))
            lw_vol = json.loads(stock_df[['Date', 'Volume']].rename(columns={'Date':'time', 'Volume':'value'}).to_json(orient='records'))
            lw_ema9 = json.loads(stock_df[['Date', 'EMA9']].rename(columns={'Date':'time', 'EMA9':'value'}).to_json(orient='records'))
            lw_ema21 = json.loads(stock_df[['Date', 'EMA21']].rename(columns={'Date':'time', 'EMA21':'value'}).to_json(orient='records'))
            lw_ema50 = json.loads(stock_df[['Date', 'EMA50']].rename(columns={'Date':'time', 'EMA50':'value'}).to_json(orient='records'))
            
            for i, v in enumerate(lw_vol): v['color'] = 'rgba(38, 166, 154, 0.5)' if stock_df['Close'].iloc[i] >= stock_df['Open'].iloc[i] else 'rgba(239, 83, 80, 0.5)'
            
            chartOptions = {
                "height": 500,
                "layout": {"background": {"type": "solid", "color": "#131722"}, "textColor": "#d1d4dc"},
                "grid": {"vertLines": {"color": "#1f2933"}, "horzLines": {"color": "#1f2933"}},
                "crosshair": {"mode": 0},
                "timeScale": {"timeVisible": False, "borderColor": "#2b2b43"},
            }
            
            series = [
                {"type": "Candlestick", "data": lw_candles, "options": {"upColor": "#26a69a", "downColor": "#ef5350", "borderVisible": False, "wickUpColor": "#26a69a", "wickDownColor": "#ef5350"}},
                {"type": "Line", "data": lw_ema9, "options": {"color": "green", "lineWidth": 2, "title": "9 EMA"}},
                {"type": "Line", "data": lw_ema21, "options": {"color": "orange", "lineWidth": 2, "title": "21 EMA"}},
                {"type": "Line", "data": lw_ema50, "options": {"color": "purple", "lineWidth": 2, "title": "50 EMA"}},
                {"type": "Histogram", "data": lw_vol, "options": {"priceFormat": {"type": "volume"}, "priceScaleId": "", "scaleMargins": {"top": 0.8, "bottom": 0}}}
            ]
            renderLightweightCharts([{"chartOptions": chartOptions, "series": series}], 'chart')
            
        elif engine_choice == "Plotly (Deep Dive)":
            st.markdown(f"### {selected_ticker} (Statistical View)")
            
            # Calculate RSI for sub-panel
            delta = stock_df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            stock_df['RSI'] = 100 - (100 / (1 + gain/loss))
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
            
            fig.add_trace(go.Candlestick(x=stock_df['Date'], open=stock_df['Open'], high=stock_df['High'], low=stock_df['Low'], close=stock_df['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=stock_df['Date'], y=stock_df['EMA9'], line=dict(color='green', width=1.5), name='9 EMA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=stock_df['Date'], y=stock_df['EMA21'], line=dict(color='orange', width=1.5), name='21 EMA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=stock_df['Date'], y=stock_df['EMA50'], line=dict(color='purple', width=1.5), name='50 EMA'), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=stock_df['Date'], y=stock_df['RSI'], line=dict(color='#00d1ff', width=1.5), name='RSI 14'), row=2, col=1)
            fig.add_hline(y=70, line_dash="dot", row=2, col=1, line_color="rgba(255, 82, 82, 0.5)")
            fig.add_hline(y=30, line_dash="dot", row=2, col=1, line_color="rgba(38, 166, 154, 0.5)")
            
            fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=650, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
