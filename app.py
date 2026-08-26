import streamlit as st
import pandas as pd
import os

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
    """Finds the stock in the dataframe and adds it to the tracking portfolio."""
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
    """Deletes an active trade from the portfolio."""
    file_path = "portfolio.csv"
    if os.path.exists(file_path):
        pf = pd.read_csv(file_path)
        pf = pf[pf['RawStock'] != raw_stock]
        pf.to_csv(file_path, index=False)
        st.toast(f"🗑️ Removed {raw_stock} from Portfolio!", icon="✅")

# --- INTERACTIVE TABLE RENDERER ---
def display_interactive_table(df, tab_name):
    """Renders a highly interactive dataframe with TradingView links and a quick-add tool."""
    if df.empty:
        st.info(f"No qualifying setups matched the criteria for {tab_name} today.")
        return

    # Generate Direct TradingView URL for the interactive column
    df['Chart'] = "https://in.tradingview.com/chart/?symbol=NSE:" + df['RawStock']
    
    # Reorder and filter columns for a pristine tabular view
    display_cols = ['Stock', 'Tag', 'Entry', 'EqSL', 'EqT1', 'EqT2', 'Score', 'Vol vs 50d', 'RSI', 'Chart', 'RawStock']
    display_df = df[[col for col in display_cols if col in df.columns]]

    # Map Streamlit Column Configs (Links, Number Formatting)
    column_config = {
        "Chart": st.column_config.LinkColumn(
            "📊 Chart", 
            display_text="📈 View", 
            help="Open directly in TradingView"
        ),
        "Score": st.column_config.NumberColumn(
            "Score /10", 
            help="Institutional Conviction Score", 
            format="%d ⭐"
        ),
        "Entry": st.column_config.NumberColumn(
            "CMP (₹)", 
            format="₹%.2f"
        ),
        "EqSL": st.column_config.NumberColumn(
            "Stop Loss", 
            format="₹%.2f"
        ),
        "Vol vs 50d": st.column_config.NumberColumn(
            "Vol Spike", 
            format="%.1fx"
        ),
        "RawStock": None # Hides the raw ID from the user view but keeps it for the backend
    }

    # Render the interactive Data Grid
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )

    # 1-Click Track to Portfolio tool beneath the table
    st.write("")
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_stock = st.selectbox(f"Select stock to track from {tab_name}:", df['RawStock'].unique(), key=f"sel_{tab_name}")
    with col2:
        st.write("")
        st.write("") # Visual alignment spacer
        if st.button(f"➕ Add to Portfolio", key=f"btn_{tab_name}", use_container_width=True):
            add_to_portfolio(selected_stock, df)


# --- MAIN UI DASHBOARD LAYOUT ---
st.title("📈 Institutional Quant Dashboard")
st.markdown("Automated Multi-Timeframe Structural Breakout & Retest Scanner")

# Top Navigation Tabs
tabs = st.tabs([
    "💥 Pre-Breakout", 
    "📈 Swing (1-2 Wk)", 
    "🌙 Perfect BTST", 
    "⚡ Intraday", 
    "💰 Budget (<₹500)", 
    "👑 Index Scalps", 
    "💼 Active Portfolio", 
    "🤖 AI Deep Dive"
])

df_all = load_data("all_setups.csv")

# --- POPULATE TABS ---
if not df_all.empty:
    with tabs[0]:
        st.header("💥 Pre-Breakout Coils & Ignitions")
        st.markdown("> *Volatility contraction patterns preparing for expansion.*")
        display_interactive_table(df_all[df_all['Horizon'] == 'Pre-Breakout'], "Pre-Breakout")

    with tabs[1]:
        st.header("📈 Swing Trades (Retest & Rising Support)")
        st.markdown("> *Multi-day/week holds bouncing off dynamic institutional support.*")
        display_interactive_table(df_all[df_all['Horizon'] == 'Swing'], "Swing Trades")

    with tabs[2]:
        st.header("🌙 Perfect BTST (Buy Today, Sell Tomorrow)")
        st.markdown("> *Extremely strong daily close indicating morning gap-up probability.*")
        display_interactive_table(df_all[df_all['Horizon'] == 'BTST'], "BTST")

    with tabs[3]:
        st.header("⚡ Intraday Momentum & Breakouts")
        st.markdown("> *High volume relative strength intraday breakouts.*")
        display_interactive_table(df_all[df_all['Horizon'] == 'Intraday'], "Intraday")

    with tabs[4]:
        st.header("💰 Budget Picks (CMP under ₹500)")
        st.markdown("> *High-conviction quantitative setups across all timeframes priced under ₹500.*")
        budget_df = df_all[df_all['Entry'] < 500]
        display_interactive_table(budget_df, "Budget Stocks")
else:
    for i in range(5):
        with tabs[i]:
            st.info("No quantitative setups passed the institutional guardrails today. Capital protected.")

# Index Options Scalps
with tabs[5]:
    st.header("Index Options (5M Scalps)")
    df_index = load_data("index_setups.csv")
    if not df_index.empty:
        st.dataframe(df_index.drop(columns=['RawStock'], errors='ignore'), use_container_width=True, hide_index=True)
    else:
        st.info("No Index Scalp setups found. Waiting for live market momentum.")

# Active Portfolio Management
with tabs[6]:
    st.header("Active Trailing Portfolio")
    df_portfolio = load_data("portfolio.csv")
    
    if not df_portfolio.empty:
        active_pf = df_portfolio[df_portfolio['Status'] == 'Active']
        closed_pf = df_portfolio[df_portfolio['Status'] == 'Closed']
        
        st.subheader(f"🟢 Active Trades ({len(active_pf)})")
        if not active_pf.empty:
            for index, row in active_pf.iterrows():
                # Utilizing cards here for easy "Delete/Remove" button access
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{row['Stock']}** (Sector: {row.get('Sector', 'Unknown')}) | **Current SL: ₹{row['Current_SL']}**")
                        st.markdown(f"Entry: ₹{row['Entry']} | T1:₹{row['T1']} // T2:₹{row['T2']} // T3:₹{row['T3']}")
                    with col2:
                        if st.button("❌ Remove", key=f"remove_{row['RawStock']}_{index}"):
                            remove_from_portfolio(row['RawStock'])
                            st.rerun() 
                    st.divider()
        else:
            st.info("No active trades currently.")
            
        with st.expander("View Closed / Stopped Out Trades"):
            if not closed_pf.empty:
                st.dataframe(closed_pf.drop(columns=['RawStock'], errors='ignore'), use_container_width=True, hide_index=True)
    else:
        st.info("Your portfolio is currently empty.")

# AI Deep Dive
with tabs[7]:
    st.header("🔬 Institutional Fundamental Analysis")
    ai_report = load_markdown("deep_dive_analysis.md")
    st.markdown(ai_report)
