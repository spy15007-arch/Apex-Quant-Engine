import streamlit as st
import pandas as pd
import os
import re

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Master Quant Engine", layout="wide", page_icon="📈")

# --- DATA LOADING FUNCTIONS ---
def load_data(file_path):
    if os.path.exists(file_path):
        try:
            return pd.read_csv(file_path)
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def load_markdown(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "*AI Analysis is pending or no qualifying setups were found today.*"

# --- PORTFOLIO ACTION FUNCTIONS ---
def add_to_portfolio(raw_stock, df_source):
    if raw_stock is None or df_source.empty: return
    stock_row = df_source[df_source['RawStock'] == raw_stock].iloc[0]
    file_path = "portfolio.csv"
    
    if os.path.exists(file_path):
        pf = pd.read_csv(file_path)
    else:
        pf = pd.DataFrame(columns=['Stock', 'RawStock', 'Entry', 'Qty', 'Current_SL', 'T1', 'T2', 'T3', 'Status', 'Sector'])
    
    if not pf.empty and (pf['RawStock'] == stock_row['RawStock']).any():
        if 'Active' in pf.loc[pf['RawStock'] == stock_row['RawStock'], 'Status'].values:
            st.toast(f"⚠️ {stock_row['RawStock']} is already in your Active Portfolio!", icon="⚠️")
            return
            
    new_trade = pd.DataFrame([{
        'Stock': stock_row['Stock'],
        'RawStock': stock_row['RawStock'],
        'Entry': stock_row['Entry'],
        'Qty': stock_row['Qty'],
        'Current_SL': stock_row['EqSL'],
        'T1': stock_row['EqT1'],
        'T2': stock_row['EqT2'],
        'T3': stock_row['EqT3'],
        'Status': 'Active',
        'Sector': 'Unknown' 
    }])
    
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

# --- INTERACTIVE TABLE RENDERER ---
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
    with col1:
        selected_stock = st.selectbox(f"Select stock to track from {tab_name}:", df['RawStock'].unique(), key=f"sel_{tab_name}")
    with col2:
        st.write("")
        st.write("") 
        if st.button(f"➕ Add to Portfolio", key=f"btn_{tab_name}", use_container_width=True):
            add_to_portfolio(selected_stock, df)

# --- MAIN UI DASHBOARD LAYOUT ---
st.title("📈 Institutional Quant Dashboard")
st.markdown("Automated Multi-Timeframe Structural Breakout & Retest Scanner")

tabs = st.tabs(["💥 Pre-Breakout", "📈 Swing (1-2 Wk)", "🌙 Perfect BTST", "⚡ Intraday", "💰 Budget (<₹500)", "👑 Index Scalps", "💼 Active Portfolio", "🤖 AI Deep Dive"])

df_all = load_data("all_setups.csv")

# --- POPULATE TABS ---
if not df_all.empty:
    with tabs[0]:
        st.header("💥 Pre-Breakout Coils & Ignitions")
        display_interactive_table(df_all[df_all['Horizon'] == 'Pre-Breakout'], "Pre-Breakout")
    with tabs[1]:
        st.header("📈 Swing Trades (Retest & Rising Support)")
        display_interactive_table(df_all[df_all['Horizon'] == 'Swing'], "Swing Trades")
    with tabs[2]:
        st.header("🌙 Perfect BTST (Buy Today, Sell Tomorrow)")
        display_interactive_table(df_all[df_all['Horizon'] == 'BTST'], "BTST")
    with tabs[3]:
        st.header("⚡ Intraday Momentum & Breakouts")
        display_interactive_table(df_all[df_all['Horizon'] == 'Intraday'], "Intraday")
    with tabs[4]:
        st.header("💰 Budget Picks (CMP under ₹500)")
        display_interactive_table(df_all[df_all['Entry'] < 500], "Budget Stocks")
else:
    for i in range(5):
        with tabs[i]:
            st.info("No quantitative setups passed the institutional guardrails today. Capital protected.")

with tabs[5]:
    st.header("Index Options (5M Scalps)")
    df_index = load_data("index_setups.csv")
    if not df_index.empty:
        st.dataframe(df_index.drop(columns=['RawStock'], errors='ignore'), use_container_width=True, hide_index=True)
    else:
        st.info("No Index Scalp setups found. Waiting for live market momentum.")

with tabs[6]:
    st.header("Active Trailing Portfolio")
    df_portfolio = load_data("portfolio.csv")
    if not df_portfolio.empty:
        active_pf = df_portfolio[df_portfolio['Status'] == 'Active']
        closed_pf = df_portfolio[df_portfolio['Status'] == 'Closed']
        
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
        else:
            st.info("No active trades currently.")
            
        with st.expander("View Closed / Stopped Out Trades"):
            if not closed_pf.empty:
                st.dataframe(closed_pf.drop(columns=['RawStock'], errors='ignore'), use_container_width=True, hide_index=True)
    else:
        st.info("Your portfolio is currently empty.")

# --- TAB 8: AI DEEP DIVE (NEW PARSING ENGINE) ---
with tabs[7]:
    st.header("🔬 Institutional Fundamental Analysis")
    raw_ai_report = load_markdown("deep_dive_analysis.md")
    
    if "Pending Analysis" in raw_ai_report or "No qualifying setups" in raw_ai_report:
        st.info("AI Analysis is pending or no qualifying setups were found today.")
    else:
        # Split the markdown into individual stock reports based on the '---' divider
        reports = raw_ai_report.split("\n\n---\n\n")
        
        for report in reports:
            if not report.strip(): continue
            
            # Extract Stock Title
            lines = report.strip().split('\n')
            title = lines[0].replace("# Detailed Stock Analysis:", "").strip() if lines else "Stock Analysis"
            
            # Regex extraction for exactly Section 12 and Section 14
            scorecard_match = re.search(r'### 12\. Final Scorecard(.*?)(?=### 13\.|$)', report, re.DOTALL)
            summary_match = re.search(r'### 14\. Executive Summary(.*?)(?=###|$)', report, re.DOTALL)
            
            scorecard_text = scorecard_match.group(1).strip() if scorecard_match else "Scorecard data formatting error."
            summary_text = summary_match.group(1).strip() if summary_match else "Summary data formatting error."
            
            st.markdown(f"## {title}")
            
            # Render side-by-side containers just like the TradingView image overlays
            col1, col2 = st.columns([1.2, 2]) # Ratio to give summary more reading space
            
            with col1:
                with st.container(border=True):
                    st.markdown("#### 12. Final Scorecard")
                    st.markdown(scorecard_text)
                    
            with col2:
                with st.container(border=True):
                    st.markdown("#### 14. Executive Summary")
                    st.markdown(summary_text)
                    
            # Hide the rest of the 14-pillar report in an expander below the beautiful overlay
            with st.expander("🔍 Read Full 14-Pillar Fundamental Report"):
                st.markdown(report)
                
            st.divider()
