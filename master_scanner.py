import os
import requests
import json
import time
import threading
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import math
import warnings
warnings.filterwarnings('ignore')

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BASE_CAPITAL_PER_TRADE = 50000  
HIGH_CONVICTION_MULTIPLIER = 2  

# --- INSTITUTIONAL THREAD-SAFE RATE LIMITER ---
class RateLimitedSession(requests.Session):
    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self._last_call = 0.0

    def request(self, *args, **kwargs):
        with self._lock:
            now = time.time()
            elapsed = now - self._last_call
            if elapsed < 0.35:
                time.sleep(0.35 - elapsed)
            self._last_call = time.time()
        return super().request(*args, **kwargs)

session = RateLimitedSession()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive'
})

SECTOR_INDICES = {
    "^CNXAUTO": "Consumer Cyclical",
    "^CNXIT": "Technology",
    "^CNXMETAL": "Basic Materials",
    "^CNXREALTY": "Real Estate",
    "^CNXENERGY": "Energy",
    "^CNXPHARMA": "Healthcare",
    "^CNXFMCG": "Consumer Defensive",
    "^CNXINFRA": "Industrials",
    "^NSEBANK": "Financial Services"
}

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    message_chunks = [message[i:i+3800] for i in range(0, len(message), 3800)] if len(message) > 3800 else [message]
    for chunk in message_chunks:
        try: 
            res = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": "Markdown", "disable_web_page_preview": True})
            if res.status_code != 200:
                clean_text = chunk.replace("*", "").replace("`", "")
                requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": clean_text, "disable_web_page_preview": True})
        except: pass

def maintenance_purge():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    if now_ist.weekday() >= 5 and os.path.exists("sent_alerts.json"): 
        try: os.remove("sent_alerts.json")
        except: pass

def is_market_open():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    if now_ist.weekday() >= 5: return False 
    nse_holidays = ["01-26", "03-24", "04-14", "05-01", "08-15", "10-02", "12-25"]
    return False if now_ist.strftime("%m-%d") in nse_holidays else True

STATIC_FNO = [
    "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ACCELYA", "ACTIONCONST", "ADANIENSOL", "ADANIENT", 
    "ADANIGREEN", "ADANIPORTS", "ADANIPOWER", "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", 
    "ASTRAL", "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", 
    "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", 
    "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", 
    "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", 
    "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", 
    "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", 
    "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", 
    "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", 
    "INDUSINDBK", "INFY", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", 
    "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", 
    "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", 
    "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PETRONET", 
    "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", 
    "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", 
    "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", 
    "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"
]
EXTENDED_FALLBACK = list(set(("360ONE 3IINFOTECH 3MINDIA 5PAISA 63MOONS AARTIIND ACC ADANIENT ADANIPORTS APOLLOHOSP ASIANPAINT AXISBANK BAJAJ-AUTO BAJFINANCE BEL BHARTIARTL COALINDIA HDFCBANK INFY ITC LT MARUTI RELIANCE SBIN TCS TITAN TRENT WIPRO").split()))

def get_complete_nse_universe():
    headers = {'User-Agent': 'Mozilla/5.0'}
    symbols = set()
    urls = [
        "https://archives.nseindia.com/content/indices/ind_niftytotalmarket_list.csv",
        "https://archives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv"
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                for line in r.text.splitlines()[1:]:
                    parts = line.split(',')
                    if parts and parts[0].strip():
                        sym = parts[0].strip().replace('"', '')
                        if sym.isalnum() and not any(sub in sym for sub in ["BEES", "ETF", "LIQUID", "GSEC", "SGB", "INFRA"]):
                            symbols.add(sym)
        except: continue
        
    symbols.update(STATIC_FNO)
    symbols.update(EXTENDED_FALLBACK)
    return sorted(list(symbols))

def calculate_leading_sectors(nifty_return_20d):
    leading_sectors = set()
    try:
        data = yf.download(list(SECTOR_INDICES.keys()), period="3mo", interval="1d", progress=False, threads=True, session=session)
        if not data.empty:
            closes = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data
            sector_scores = {}
            for ticker, yf_sec_name in SECTOR_INDICES.items():
                if ticker in closes.columns:
                    s_series = closes[ticker].dropna()
                    if len(s_series) >= 25:
                        s_ret_20d = float(s_series.iloc[-1] / s_series.iloc[-20] - 1)
                        s_ema20 = float(s_series.ewm(span=20).mean().iloc[-1])
                        s_close = float(s_series.iloc[-1])
                        rs_vs_nifty = s_ret_20d - nifty_return_20d
                        if rs_vs_nifty > 0 and s_close >= s_ema20: sector_scores[yf_sec_name] = rs_vs_nifty
            leading_sectors = {s[0] for s in sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)[:4]}
    except: pass
    return leading_sectors

def download_in_chunks(tickers, chunk_size=150):
    opens_list, closes_list, highs_list, lows_list, vols_list = [], [], [], [], []
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i+chunk_size]
        print(f"📡 Downloading chunk {i//chunk_size + 1}/{math.ceil(len(tickers)/chunk_size)}...")
        d = yf.download(chunk, period="1y", interval="1d", progress=False, threads=True, session=session)
        if not d.empty:
            if isinstance(d.columns, pd.MultiIndex):
                if 'Open' in d.columns.levels[0]: opens_list.append(d['Open'])
                if 'Close' in d.columns.levels[0]: closes_list.append(d['Close'])
                if 'High' in d.columns.levels[0]: highs_list.append(d['High'])
                if 'Low' in d.columns.levels[0]: lows_list.append(d['Low'])
                if 'Volume' in d.columns.levels[0]: vols_list.append(d['Volume'])
            else: 
                sym = chunk[0]
                opens_list.append(d[['Open']].rename(columns={'Open': sym}))
                closes_list.append(d[['Close']].rename(columns={'Close': sym}))
                highs_list.append(d[['High']].rename(columns={'High': sym}))
                lows_list.append(d[['Low']].rename(columns={'Low': sym}))
                vols_list.append(d[['Volume']].rename(columns={'Volume': sym}))
        
    opens = pd.concat(opens_list, axis=1) if opens_list else pd.DataFrame()
    closes = pd.concat(closes_list, axis=1) if closes_list else pd.DataFrame()
    highs = pd.concat(highs_list, axis=1) if highs_list else pd.DataFrame()
    lows = pd.concat(lows_list, axis=1) if lows_list else pd.DataFrame()
    volumes = pd.concat(vols_list, axis=1) if vols_list else pd.DataFrame()
    
    opens = opens.loc[:, ~opens.columns.duplicated()]
    closes = closes.loc[:, ~closes.columns.duplicated()]
    highs = highs.loc[:, ~highs.columns.duplicated()]
    lows = lows.loc[:, ~lows.columns.duplicated()]
    volumes = volumes.loc[:, ~volumes.columns.duplicated()]
    return opens, closes, highs, lows, volumes

def get_new_alerts(df, category_name):
    if df.empty: return df
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    alert_file = "sent_alerts.json"
    try:
        with open(alert_file, "r") as f: alerts_db = json.load(f) if os.path.exists(alert_file) else {}
    except: alerts_db = {}
    if alerts_db.get("date") != today_str: alerts_db = {"date": today_str, "sent": []}
    new_rows = []
    for idx, row in df.iterrows():
        alert_id = f"{row['Stock']}_{row['Tag']}_{category_name}"
        if alert_id not in alerts_db["sent"]:
            new_rows.append(row)
            alerts_db["sent"].append(alert_id)
    with open(alert_file, "w") as f: json.dump(alerts_db, f)
    return pd.DataFrame(new_rows)

def calculate_dynamic_targets(close_p, atr, df_h, df_l):
    diff = max(2.0, float(df_h.tail(20).max()) - float(df_l.tail(20).min()))
    t1 = round((close_p + 1.2 * atr + close_p + diff * 0.236) / 2, 1)
    t2 = round((close_p + 2.2 * atr + close_p + diff * 0.382) / 2, 1)
    t3 = round((close_p + 3.5 * atr + close_p + diff * 0.618) / 2, 1)
    return t1, t2, t3

def check_structure_hh_hl(df_h, df_l):
    if len(df_h) < 20: return True
    return (df_h.iloc[-10:].max() >= df_h.iloc[-20:-10].max()) and (df_l.iloc[-10:].min() >= df_l.iloc[-20:-10].min())

def check_bullish_divergence(closes, rsi):
    try:
        if len(closes) < 30: return False
        w1_c, w2_c = closes.iloc[-25:-10], closes.iloc[-10:]
        p1, p2 = w1_c.min(), w2_c.min()
        r1, r2 = rsi.loc[w1_c.idxmin()], rsi.loc[w2_c.idxmin()]
        if (p2 < p1 and r2 > r1) or (p2 > p1 and r2 < r1): return True
    except: pass
    return False

def check_ascending_trendline_support(df_w_c, df_w_l, df_w_h, lookback_weeks=40):
    try:
        if len(df_w_c) < lookback_weeks: return False, 0.0, None, None
        lows = df_w_l.tail(lookback_weeks).values
        dates = df_w_l.tail(lookback_weeks).index
        n = len(lows)
        
        idx1 = int(np.argmin(lows[: int(n * 0.55)]))
        l1 = lows[idx1]
        d1 = dates[idx1].strftime('%Y-%m-%d')
        
        idx2_search = lows[idx1 + 4 : n - 1]
        if len(idx2_search) < 3: return False, 0.0, None, None
        idx2 = idx1 + 4 + int(np.argmin(idx2_search))
        l2 = lows[idx2]
        
        if l2 <= l1 or (idx2 - idx1) < 5: return False, 0.0, None, None
        slope = (l2 - l1) / (idx2 - idx1)
        curr_idx = n - 1
        projected_tl = l2 + slope * (curr_idx - idx2)
        curr_close, curr_low = float(df_w_c.iloc[-1]), float(df_w_l.iloc[-1])
        
        is_testing = (curr_low <= projected_tl * 1.025) and (curr_close >= projected_tl * 0.985)
        violations = np.sum(lows[idx1:curr_idx] < (l1 + slope * (np.arange(idx1, curr_idx) - idx1)) * 0.97)
        
        if is_testing and violations <= 1: 
            return True, round(projected_tl, 2), d1, round(l1, 2)
    except: pass
    return False, 0.0, None, None

def format_telegram_text(df_stocks, title, regime="Neutral"):
    msg = f"🚨 *{title}* 🚨\n🧭 Macro Regime: *{regime}*\n\n"
    if not df_stocks.empty:
        msg += "📊 *TOP CONVICTION SETUPS*\n\n"
        for idx, r in df_stocks.head(20).reset_index().iterrows():
            stock_clean = r['Stock'].replace(" (↑)", "")
            msg += f"{idx+1}. *{stock_clean}* | *{r['Tag']}*\n"
            msg += f"   🏆 Score: *{r['Score']}/100* | RS vs Nifty: *{r['RS_Rating']}*\n"
            msg += f"   ⚡ *Entry Zone: {r.get('EntryZone', '₹'+str(r['Entry']))}* | SL: ₹{r['EqSL']}\n"
            msg += f"   🎯 TGTs: T1: ₹{r['EqT1']} | T2: ₹{r['EqT2']} | T3: ₹{r['EqT3']}\n"
            msg += f"   🔗 [TradingView](https://in.tradingview.com/chart/?symbol=NSE:{r['RawStock']})\n\n"
    return msg

def generate_ai_deep_dive(top_candidates):
    if not GEMINI_API_KEY or not top_candidates:
        with open("deep_dive_analysis.md", "w", encoding="utf-8") as f: 
            f.write("# 🔬 Institutional Deep Dive Analysis\n\n*Pending Analysis: Waiting for active market setups.*")
        return
    print("🤖 Generating AI 14-Pillar Fundamental Analysis...")
    all_dossiers = []
    for candidate in top_candidates[:2]:
        sym, entry, eq_sl, t1, tag, score = candidate['RawStock'], candidate['Entry'], candidate['EqSL'], candidate['EqT1'], candidate['Tag'], candidate['Score']
        try:
            info = yf.Ticker(f"{sym}.NS", session=session).info
            pe, sector = info.get('trailingPE', 'N/A'), info.get('sector', 'N/A')
        except: pe, sector = "N/A", "N/A"
        prompt = f"""You are an Elite Institutional Equity Research Analyst. Write a rigorous 14-section research dossier on **{sym} (NSE: {sym})**. Setup Context: Category: {tag} (Score: {score}/100) | Buy: ₹{entry} | SL: ₹{eq_sl} | Target 1: ₹{t1} | Sector: {sector} | P/E: {pe}. Format EXACTLY as:
# Detailed Stock Analysis: {sym} (NSE: {sym})
---
### 1. Technical Analysis
### 2. Why Did the Stock Fall Earlier?
### 3. Has the Company Recovered?
### 4. Latest News & Business Developments
### 5. Fundamental Analysis
### 6. Shareholding Pattern
### 7. Quarterly & Annual Financial Performance
### 8. Five-Year Financial Trend
### 9. Valuation Summary
### 10. Key Risks
### 11. Key Growth Triggers
### 12. Final Scorecard
### 13. Final Investment View
### 14. Executive Summary"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
            if res.status_code == 200: 
                all_dossiers.append(res.json()['candidates'][0]['content']['parts'][0]['text'])
            else:
                all_dossiers.append(f"# Detailed Stock Analysis: API ERROR\n\n### 12. Final Scorecard\nError: {res.status_code}\n### 14. Executive Summary\nGoogle API error.")
        except Exception as e:
            all_dossiers.append(f"# Detailed Stock Analysis: SYSTEM ERROR\n\n### 12. Final Scorecard\nError: {str(e)}\n### 14. Executive Summary\nAPI connection failure.")
            
    with open("deep_dive_analysis.md", "w", encoding="utf-8") as f:
        f.write("\n\n---\n\n".join(all_dossiers) if all_dossiers else "# 🔬 Analysis Completed.")

def run():
    print("🚀 Starting Automated Daily/Weekly Quant Scanner...")
    maintenance_purge()
    if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch" and not is_market_open(): 
        print("Market closed. Skipping execution.")
        return

    nifty_df = yf.download("^NSEI", period="1y", interval="1d", progress=False, session=session)
    nifty_return_20d, nifty_return_60d = 0.0, 0.0
    if not nifty_df.empty:
        if isinstance(nifty_df.columns, pd.MultiIndex): nifty_df.columns = nifty_df.columns.get_level_values(0)
        n_close = nifty_df['Close'].dropna()
        if len(n_close) >= 65:
            nifty_return_20d = float(n_close.iloc[-1] / n_close.iloc[-20] - 1)
            nifty_return_60d = float(n_close.iloc[-1] / n_close.iloc[-60] - 1)

    leading_sectors = calculate_leading_sectors(nifty_return_20d)
    universe = get_complete_nse_universe()
    
    opens, closes, highs, lows, volumes = download_in_chunks([f"{s}.NS" for s in universe], chunk_size=150)
    if closes.empty: return

    # --- MARKET BREADTH & REGIME ---
    ema_50_daily = closes.ewm(span=50).mean()
    total_stocks = len(closes.columns)
    stocks_above_50ema = (closes.iloc[-1] > ema_50_daily.iloc[-1]).sum()
    breadth_50_pct = stocks_above_50ema / total_stocks if total_stocks > 0 else 0
    breadth_str = f"Breadth: {breadth_50_pct*100:.1f}% > 50EMA"
    if breadth_50_pct > 0.60: nifty_regime = f"🟢 Bullish Market Trend ({breadth_str})"
    elif breadth_50_pct < 0.40: nifty_regime = f"🔴 Bearish - Capital Protection Mode ({breadth_str})"
    else: nifty_regime = f"🟡 Neutral Consolidation ({breadth_str})"

    # --- ATR TRAILING STOP ENGINE ---
    portfolio_file = "portfolio.csv"
    if os.path.exists(portfolio_file): 
        pf = pd.read_csv(portfolio_file)
        if 'Sector' not in pf.columns: pf['Sector'] = 'Unknown'
    else: 
        pf = pd.DataFrame(columns=['Stock', 'RawStock', 'Entry', 'Qty', 'Current_SL', 'T1', 'T2', 'T3', 'Status', 'Sector'])
        
    active_sectors_count, trail_alerts = {}, []
    if not pf.empty:
        for i, row in pf.iterrows():
            if row['Status'] != 'Active': continue
            sym, sec = row['RawStock'], row.get('Sector', 'Unknown')
            if sec == 'Unknown' or pd.isna(sec):
                try: 
                    sec = yf.Ticker(f"{sym}.NS", session=session).info.get('sector', 'Unknown')
                    pf.at[i, 'Sector'] = sec
                except: sec = 'Unknown'
            active_sectors_count[sec] = active_sectors_count.get(sec, 0) + 1
            ticker = f"{sym}.NS"
            if ticker in closes.columns:
                latest_p, curr_sl, entry_p, t1, t2 = float(closes[ticker].iloc[-1]), float(row['Current_SL']), float(row['Entry']), float(row['T1']), float(row['T2'])
                if latest_p < curr_sl: 
                    pf.at[i, 'Status'] = 'Closed'
                    trail_alerts.append(f"🔴 *STOP OUT:* {sym} closed below SL (₹{curr_sl}).")
                elif latest_p >= t2 and curr_sl < t1: 
                    pf.at[i, 'Current_SL'] = t1
                    trail_alerts.append(f"🟢 *PROFIT LOCK:* {sym} hit T2! SL moved to T1 (₹{t1}).")
                elif latest_p >= t1 and curr_sl < entry_p: 
                    pf.at[i, 'Current_SL'] = entry_p
                    trail_alerts.append(f"🟡 *BREAKEVEN:* {sym} hit T1! SL moved to Cost (₹{entry_p}).")
        pf.to_csv(portfolio_file, index=False)
        if trail_alerts: send_telegram_message("🔔 *TRAILING STOP PORTFOLIO ENGINE*\n\n" + "\n".join(trail_alerts))

    # --- TECHNICAL PRE-COMPUTATIONS ---
    closes_weekly = closes.resample('W').last().dropna(how='all')
    highs_weekly = highs.resample('W').max().dropna(how='all')
    lows_weekly = lows.resample('W').min().dropna(how='all')
    
    ema_20_daily = closes.ewm(span=20).mean()
    ema_200_daily = closes.ewm(span=200).mean()
    vol_50d_avg_daily = volumes.rolling(50).mean()
    
    delta = closes.diff()
    gain, loss = (delta.where(delta > 0, 0)).rolling(14).mean(), (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_daily = 100 - (100 / (1 + (gain / loss)))
    
    macd_daily = closes.ewm(span=12, adjust=False).mean() - closes.ewm(span=26, adjust=False).mean()
    macd_signal_daily = macd_daily.ewm(span=9, adjust=False).mean()
    
    atr_daily = pd.DataFrame(
        np.maximum((highs - lows).values, np.maximum((highs - closes.shift(1)).abs().values, (lows - closes.shift(1)).abs().values)),
        index=highs.index, columns=highs.columns
    ).ewm(alpha=1/14).mean()
    
    ema_30_weekly = closes_weekly.ewm(span=30).mean()
    obv = (np.sign(delta) * volumes).fillna(0).cumsum()
    obv_ema20 = obv.ewm(span=20).mean()

    valid_setups = []

    for ticker in closes.columns:
        symbol = ticker.replace(".NS", "")
        if any(sub in symbol for sub in ["BEES", "ETF", "LIQUID", "GSEC", "SGB", "INFRA"]): continue

        try:
            df_c = closes[ticker].dropna()
            df_h = highs[ticker].dropna()
            df_l = lows[ticker].dropna()
            df_v = volumes[ticker].dropna()
            if len(df_c) < 130: continue

            close_p = float(df_c.iloc[-1])
            prev_close = float(df_c.iloc[-2])
            vol_today = float(df_v.iloc[-1])
            vol_50_avg = float(vol_50d_avg_daily.iloc[-1][ticker])
            
            # Liquidity Filters: Absolute Minimum Requirements
            turnover_avg = close_p * vol_50_avg
            if close_p < 25 or turnover_avg < 20000000 or vol_50_avg < 50000: continue
            
            vol_vs = round(vol_today / vol_50_avg, 2) if vol_50_avg > 0 else 1.0
            daily_high, daily_low = float(df_h.iloc[-1]), float(df_l.iloc[-1])
            daily_range = daily_high - daily_low

            # Reject High-Volume Distribution Candles
            if daily_range > 0 and ((daily_high - max(close_p, prev_close)) / daily_range) > 0.55 and vol_vs > 2.0 and close_p < prev_close:
                continue

            # Key Moving Averages
            d_ema20 = float(ema_20_daily.iloc[-1][ticker])
            d_ema50 = float(ema_50_daily.iloc[-1][ticker])
            d_ema200 = float(ema_200_daily.iloc[-1][ticker]) if not pd.isna(ema_200_daily.iloc[-1][ticker]) else 0.0
            d_ema200_20d_ago = float(ema_200_daily.iloc[-20][ticker]) if len(ema_200_daily) >= 20 and not pd.isna(ema_200_daily.iloc[-20][ticker]) else d_ema200
            
            w_ema30 = float(ema_30_weekly.iloc[-1][ticker]) if ticker in ema_30_weekly.columns and not pd.isna(ema_30_weekly.iloc[-1][ticker]) else d_ema200
            
            atr = float(atr_daily.iloc[-1][ticker])
            rsi_val = float(rsi_daily.iloc[-1][ticker])
            macd_val = float(macd_daily.iloc[-1][ticker])
            macd_sig = float(macd_signal_daily.iloc[-1][ticker])
            prev_macd_val = float(macd_daily.iloc[-2][ticker])
            prev_macd_sig = float(macd_signal_daily.iloc[-2][ticker])

            # 52-Week Range Metrics
            high_52w = float(df_h.tail(250).max())
            low_52w = float(df_l.tail(250).min())

            # --- MARK MINERVINI STAGE 2 TREND TEMPLATE ---
            is_stage_2 = (
                close_p > d_ema50 and
                d_ema50 > d_ema200 and
                d_ema200 >= d_ema200_20d_ago and      # 200 EMA trending upward
                close_p >= low_52w * 1.25 and         # At least 25% above 52w low
                close_p >= high_52w * 0.75 and        # Within 25% of 52w high
                close_p > w_ema30                     # Above weekly 30-week base
            )

            # --- RELATIVE STRENGTH (RS) CALCULATION ---
            stock_ret_20d = float(df_c.iloc[-1] / df_c.iloc[-20] - 1)
            stock_ret_60d = float(df_c.iloc[-1] / df_c.iloc[-60] - 1)
            rs_score_composite = (stock_ret_20d - nifty_return_20d) * 0.5 + (stock_ret_60d - nifty_return_60d) * 0.5
            is_rs_outperformer = rs_score_composite > 0

            # --- VOLATILITY CONTRACTION PATTERN (VCP) ---
            atr_3d_avg = float((df_h.tail(3) - df_l.tail(3)).mean())
            atr_20d_avg = float((df_h.tail(20) - df_l.tail(20)).mean())
            is_range_contracted = atr_3d_avg <= (atr_20d_avg * 0.68)
            is_volume_dryup = vol_today <= (vol_50_avg * 0.75)
            is_vcp = is_range_contracted and is_volume_dryup and (close_p >= d_ema20)

            # --- MACD BULLISH ZERO-CROSS ---
            is_macd_bullish_cross = (prev_macd_val <= prev_macd_sig) and (macd_val > macd_sig) and (macd_val > 0)

            # --- PRE-BREAKOUT COIL ---
            recent_20d_high = float(df_h.tail(20).max())
            dist_to_pivot = (recent_20d_high - close_p) / close_p
            is_pre_breakout = (0.002 <= dist_to_pivot <= 0.035) and (close_p >= d_ema20) and (vol_vs <= 1.2)

            # --- HIGH-TIGHT BTST (INSTITUTIONAL CLOSE) ---
            close_position = ((close_p - daily_low) / daily_range) if daily_range > 0 else 1.0
            is_btst = (
                close_position >= 0.82 and 
                close_p > prev_close and 
                close_p >= (recent_20d_high * 0.985) and 
                vol_vs >= 1.25 and 
                (55 <= rsi_val <= 78)
            )

            # --- STRUCTURAL PULLBACK / RETEST ---
            is_trendline_retest, tl_val, tl_d1, tl_v1 = check_ascending_trendline_support(
                closes_weekly[ticker].dropna(), lows_weekly[ticker].dropna(), highs_weekly[ticker].dropna()
            )
            is_ema_retest = (
                abs(close_p - d_ema20) / d_ema20 <= 0.015 or 
                (daily_low <= d_ema20 and close_p > d_ema20)
            ) and (vol_vs <= 0.95)

            # Filter Categorization
            horizon, sl_multiplier, tag = "", 1.0, ""
            if is_btst:
                horizon, sl_multiplier, tag = "BTST", 1.0, "🌙 High-Tight BTST"
            elif is_vcp:
                horizon, sl_multiplier, tag = "Pre-Breakout", 0.8, "🗜️ VCP Contraction Dry-Up"
            elif is_macd_bullish_cross:
                horizon, sl_multiplier, tag = "MACD", 1.2, "🌊 MACD Bullish Zero-Cross"
            elif is_pre_breakout:
                horizon, sl_multiplier, tag = "Pre-Breakout", 0.9, "💥 Pre-Breakout Coil"
            elif is_trendline_retest:
                horizon, sl_multiplier, tag = "Swing", 1.2, "📈 Rising Support Retest"
            elif is_ema_retest and is_stage_2:
                horizon, sl_multiplier, tag = "Swing", 1.0, "🔄 20-EMA Pullback Retest"
            else:
                continue

            # Trend and divergence checks
            is_rsi_div = check_bullish_divergence(df_c, rsi_daily[ticker].dropna())
            if is_rsi_div: tag += " (+RSI Div)"

            # Targets & Stop Loss (ATR-driven)
            t1, t2, t3 = calculate_dynamic_targets(close_p, atr, df_h, df_l)
            eq_sl = round(close_p - sl_multiplier * atr, 1)
            if (close_p - eq_sl) <= 0: continue

            # --- 100-POINT INSTITUTIONAL COMPOSITE SCORING MATRIX ---
            score = 0
            # 1. Stage 2 Trend Template (Max 25 pts)
            if is_stage_2: score += 15
            if d_ema20 > d_ema50: score += 5
            if check_structure_hh_hl(df_h, df_l): score += 5

            # 2. Relative Strength vs. Nifty (Max 25 pts)
            if rs_score_composite > 0.10: score += 25
            elif rs_score_composite > 0.04: score += 18
            elif rs_score_composite > 0: score += 12

            # 3. Base Contraction & Volatility (Max 20 pts)
            if is_vcp or is_range_contracted: score += 12
            if is_volume_dryup or vol_vs <= 1.0: score += 8

            # 4. Volume Accumulation / OBV (Max 15 pts)
            curr_obv = float(obv[ticker].iloc[-1])
            curr_obv_ema = float(obv_ema20[ticker].iloc[-1])
            if curr_obv > curr_obv_ema: score += 10
            if vol_vs >= 1.5 and close_p > prev_close: score += 5

            # 5. Momentum Health (Max 15 pts)
            if 55 <= rsi_val <= 70: score += 8
            elif 48 <= rsi_val <= 75: score += 4
            if macd_val > macd_sig and macd_val > 0: score += 7

            # Sector Bonus
            try:
                stock_sec = yf.Ticker(ticker, session=session).info.get('sector', 'Unknown')
                if stock_sec in leading_sectors: score = min(100, score + 5)
            except: pass

            # Institutional Quality Cutoff: Minimum 65 Points
            if score < 65: continue

            # Capital Sizing
            cash_qty = int(BASE_CAPITAL_PER_TRADE / close_p)
            if score >= 85: cash_qty = int((BASE_CAPITAL_PER_TRADE * HIGH_CONVICTION_MULTIPLIER) / close_p)

            # Entry Zones
            if "BTST" in tag:
                ez_low, ez_high, best_entry = round(close_p - 0.2 * atr, 1), round(close_p + 0.1 * atr, 1), round(close_p, 1)
            elif "Pullback" in tag or "Support" in tag:
                ez_low, ez_high, best_entry = round(d_ema20 - 0.2 * atr, 1), round(close_p, 1), round(d_ema20, 1)
            else:
                ez_low, ez_high, best_entry = round(close_p - 0.15 * atr, 1), round(close_p + 0.3 * atr, 1), round(close_p + 0.05 * atr, 1)

            entry_zone_str = f"₹{ez_low} - ₹{ez_high} (🎯 ₹{best_entry})"
            rs_rating_display = f"+{round(rs_score_composite*100, 1)}%" if rs_score_composite > 0 else f"{round(rs_score_composite*100, 1)}%"

            valid_setups.append({
                'Stock': f"{symbol} (↑)",
                'RawStock': symbol,
                'Horizon': horizon,
                'Tag': tag,
                'Entry': round(close_p, 2),
                'EntryZone': entry_zone_str,
                'Qty': cash_qty,
                'Risk': round(cash_qty * (close_p - eq_sl), 2),
                'RSI': round(rsi_val, 1),
                'RS_Rating': rs_rating_display,
                'Vol vs 50d': vol_vs,
                'EqSL': eq_sl,
                'EqT1': t1,
                'EqT2': t2,
                'EqT3': t3,
                'Score': score,
                'TL_D1': tl_d1,
                'TL_V1': tl_v1,
                'TL_V2': tl_val
            })
        except: continue

    # --- SAVE CLEAN CSV EXPORTS ---
    df_all = pd.DataFrame(valid_setups).drop_duplicates(subset=['Stock']).sort_values(by=['Score', 'Vol vs 50d'], ascending=[False, False]) if valid_setups else pd.DataFrame()
    df_all.to_csv("all_setups.csv", index=False) if not df_all.empty else pd.DataFrame(columns=['Stock', 'RawStock', 'Horizon', 'Tag', 'Entry', 'EntryZone', 'Qty', 'Risk', 'RSI', 'RS_Rating', 'Vol vs 50d', 'EqSL', 'EqT1', 'EqT2', 'EqT3', 'Score']).to_csv("all_setups.csv", index=False)

    # Chart Data Extraction
    chart_data_list = []
    if valid_setups:
        for r in valid_setups:
            sym = r['RawStock']
            t = f"{sym}.NS"
            try:
                if t in opens.columns:
                    temp = pd.DataFrame({
                        'Date': opens.index.strftime('%Y-%m-%d'),
                        'Ticker': sym,
                        'Open': opens[t],
                        'High': highs[t],
                        'Low': lows[t],
                        'Close': closes[t],
                        'Volume': volumes[t]
                    }).dropna().tail(150)
                    chart_data_list.append(temp)
            except: pass
    if chart_data_list: pd.concat(chart_data_list).to_csv("chart_data.csv", index=False)
    else: pd.DataFrame(columns=['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume']).to_csv("chart_data.csv", index=False)

    # Segmented Buckets
    df_vcp = df_all[df_all['Horizon'] == 'Pre-Breakout'].head(20) if not df_all.empty else pd.DataFrame()
    df_macd = df_all[df_all['Horizon'] == 'MACD'].head(20) if not df_all.empty else pd.DataFrame()
    df_swing = df_all[df_all['Horizon'] == 'Swing'].head(20) if not df_all.empty else pd.DataFrame()
    df_btst = df_all[df_all['Horizon'] == 'BTST'].head(20) if not df_all.empty else pd.DataFrame()

    # AI Deep Dive on Top 2 Stocks
    if not df_all.empty: 
        generate_ai_deep_dive(df_all.to_dict('records'))
    else:
        with open("deep_dive_analysis.md", "w", encoding="utf-8") as f: 
            f.write("# 🔬 Institutional Deep Dive Analysis\n\n*No qualifying setups met the institutional 65-point cutoff today.*")

    # --- TELEGRAM DISPATCH ---
    if not df_btst.empty:
        new_btst = get_new_alerts(df_btst, "BTST")
        if not new_btst.empty: send_telegram_message(format_telegram_text(new_btst, "🌙 Institutional BTST Alerts", nifty_regime))
        
    if not df_vcp.empty:
        new_vcp = get_new_alerts(df_vcp, "PreBreakout")
        if not new_vcp.empty: send_telegram_message(format_telegram_text(new_vcp, "🗜️ Pre-Breakout / VCP Coils", nifty_regime))
        
    if not df_macd.empty:
        new_macd = get_new_alerts(df_macd, "MACD")
        if not new_macd.empty: send_telegram_message(format_telegram_text(new_macd, "🌊 MACD Bullish Zero-Cross", nifty_regime))

    if not df_swing.empty:
        new_swing = get_new_alerts(df_swing, "Swing")
        if not new_swing.empty: send_telegram_message(format_telegram_text(new_swing, "📈 Structural Swing Trades", nifty_regime))

    if df_all.empty:
        send_telegram_message(f"🛡️ *Quant Scan Complete*\n\nZero stocks passed the Minervini Stage 2 / VCP quality filters today. Capital protected in 100% Cash.\n🧭 {nifty_regime}")

if __name__ == "__main__":
    run()
