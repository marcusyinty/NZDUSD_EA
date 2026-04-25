import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
from datetime import datetime

class DataLoader:
    def __init__(self, config):
        self.config = config
        self.symbol = config['SYMBOL']
        self.timeframe_str = config['TIMEFRAME']
        
        self.tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1
        }
        self.tf = self.tf_map.get(self.timeframe_str, mt5.TIMEFRAME_M15)

    def get_data(self, num_bars=200):
        rates = mt5.copy_rates_from_pos(self.symbol, self.tf, 0, num_bars)
        if rates is None or len(rates) == 0:
            return None
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Calculate Indicators
        # Using pandas_ta for EMA and RSI
        df.ta.ema(length=50, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.atr(length=14, append=True)
        
        return df

    def get_asian_session_range(self):
        # We fetch the last 100 bars of M15 which covers more than a day
        rates = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M15, 0, 100)
        if rates is None or len(rates) == 0:
            return None, None
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        current_date = datetime.now().date()
        start_hour = self.config.get('ASIAN_SESSION_START', 0)
        end_hour = self.config.get('ASIAN_SESSION_END', 8)
        
        # Filter for today's asian session
        df_asian = df[(df['time'].dt.date == current_date) & 
                      (df['time'].dt.hour >= start_hour) & 
                      (df['time'].dt.hour < end_hour)]
        
        if df_asian.empty:
            return None, None
            
        return df_asian['high'].max(), df_asian['low'].min()
