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
from scipy.stats import norm
import warnings

warnings.filterwarnings('ignore')

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BASE_CAPITAL_PER_TRADE = 50000  
HIGH_CONVICTION_MULTIPLIER = 2  

# --- YAHOO FINANCE CONCURRENT RATE-LIMIT BYPASS ---
# Enables fast threads=True downloading while safely throttling 
# the request initialization to 5 per second, completely avoiding the GitHub Actions IP ban.
class ConcurrencySafeSession(requests.Session):
    def __init__(self, req_per_sec=5):
        super().__init__()
        self.lock = threading.Lock()
        self.interval = 1.0 / req_per_sec
        self.last_call = 0.0

    def request(self, *args, **kwargs):
        with self.lock:
            elapsed = time.time() - self.last_call
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
            self.last_call = time.time()
        return super().request(*args, **kwargs)

session = ConcurrencySafeSession(req_per_sec=5)
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive'
})

SECTOR_INDICES = {
    "^CNXAUTO": "Consumer Cyclical", "^CNXIT": "Technology", "^CNXMETAL": "Basic Materials",
    "^CNXREALTY": "Real Estate", "^CNXENERGY": "Energy", "^CNXPHARMA": "Healthcare",
    "^CNXFMCG": "Consumer Defensive", "^CNXINFRA": "Industrials", "^NSEBANK": "Financial Services"
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
    if now_ist.weekday() >= 5 and os.path.exists("sent_alerts.json"): os.remove("sent_alerts.json")

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
    "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "](#)**

