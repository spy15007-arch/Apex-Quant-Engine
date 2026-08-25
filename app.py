import streamlit as st
import pandas as pd
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Master Quant Engine", layout="wide", page_icon="📈")

# --- DATA LOADING FUNCTIONS ---
def load_data(file_path):
    """Safely loads CSV files, returning an empty DataFrame if it doesn't exist yet."""
    if os.path.exists(file_path):
        try:
            return pd.read_csv(file_path)
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def load_markdown(file_path):
    """Safely loads the AI markdown report."""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "*AI Analysis is pending or no qualifying setups were found today.*"

# --- PORTFOLIO ACTION FUNCTION ---
def add_to_portfolio(stock_row):
    file_path = "portfolio.csv"
    if os.path.exists(file_path):
        pf = pd.read_csv(file_path)
    else:
        # Create it if it doesn't exist
        pf = pd.DataFrame(columns=['Stock', 'RawStock', 'Entry', 'Qty', 'Current_SL', 'T1', 'T2', 'T3', 'Status', 'Sector'])
    
    # Safety Check: Is it already active in the portfolio?
    if not pf.empty and (pf['RawStock'] == stock_row['RawStock']).any():
        if 'Active' in pf.loc[pf['RawStock'] == stock_row['RawStock'], 'Status'].values:
            st.toast(f"⚠️ {stock_row['RawStock']} is already in your Active Portfolio!", icon="⚠️")
            return
            
    # Create the new trade entry
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
        'Sector': 'Unknown' # The background scanner will populate this on the next run
    }])
    
    # Save back to CSV
    pf = pd.concat([pf, new_trade], ignore_index=True)
    pf.to_csv(file_path, index=False)
    st.toast(f"✅ Successfully added {stock_row['RawStock']} to your Portfolio Tracking Engine!", icon="✅")

# --- UI LAYOUT & DESIGN ---
st.title("📈 Institutional Quant Dashboard")
st.markdown("Automated Multi-Timeframe Structural Breakout & Retest Scanner")

# Create sleek navigation tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Market Scans", "👑 Index Scalps", "💼 Active Portfolio", "🤖 AI Deep Dive"])

# --- TAB 1: MARKET SCANS ---
with tab1:
    st.header("Validated Equity Setups")
    df_setups = load_data("all_setups.csv")
    
    if not df_setups.empty:
        # Allow filtering by Horizon (Swing, BTST, Intraday, Pre-Breakout)
        horizons = df_setups['Horizon'].unique().tolist()
        selected_horizons = st.multiselect("Filter by Timeframe/Horizon:", horizons, default=horizons)
        
        filtered_df = df_setups[df_setups['Horizon'].isin(selected_horizons)]
        
        if not filtered_df.empty:
            for index, row in filtered_df.iterrows():
                # Wrap each setup in a clean container
                with st.container():
                    col1, col2 = st.columns([8, 1]) # Ratio to give the table more space
                    with col1:
                        # Clean up the display (Hide 'RawStock' backend ID)
                        display_df = pd.DataFrame([row]).drop(columns=['RawStock'], errors='ignore')
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                    with col2:
                        st.write("") # Visual spacing to align the button
                        # 1-Click Interactive Button
                        if st.button(f"➕ Track", key=f"add_{row.get('RawStock', index)}_{index}"):
                            add_to_portfolio(row)
                    st.divider()
        else:
            st.info("No setups match the selected timeframe filters.")
    else:
        st.success("No quantitative setups passed the institutional guardrails today. Capital protected.")

# --- TAB 2: INDEX SCALPS ---
with tab2:
    st.header("Index Options (5M Scalps)")
    df_index = load_data("index_setups.csv")
    
    if not df_index.empty:
        st.dataframe(df_index.drop(columns=['RawStock'], errors='ignore'), use_container_width=True, hide_index=True)
    else:
        st.info("No Index Scalp setups found. Waiting for live market hours and momentum.")

# --- TAB 3: ACTIVE PORTFOLIO ---
with tab3:
    st.header("Active Trailing Portfolio")
    st.markdown("> *These trades are monitored by the backend ATR Trailing Stop Engine.*")
    df_portfolio = load_data("portfolio.csv")
    
    if not df_portfolio.empty:
        active_pf = df_portfolio[df_portfolio['Status'] == 'Active']
        closed_pf = df_portfolio[df_portfolio['Status'] == 'Closed']
        
        st.subheader(f"🟢 Active Trades ({len(active_pf)})")
        if not active_pf.empty:
            # Display cleanly without the backend RawStock column
            st.dataframe(active_pf.drop(columns=['RawStock'], errors='ignore'), use_container_width=True, hide_index=True)
        else:
            st.info("No active trades currently.")
            
        with st.expander("View Closed / Stopped Out Trades"):
            if not closed_pf.empty:
                st.dataframe(closed_pf.drop(columns=['RawStock'], errors='ignore'), use_container_width=True, hide_index=True)
            else:
                st.write("No closed trades yet.")
    else:
        st.info("Your portfolio is currently empty. Click '+ Track' on a setup in the Market Scans tab to add one!")

# --- TAB 4: AI DEEP DIVE ---
with tab4:
    st.header("🔬 Institutional Fundamental Analysis")
    st.markdown("> *Powered by Gemini 1.5 Pro Quantitative AI*")
    ai_report = load_markdown("deep_dive_analysis.md")
    st.markdown(ai_report)
