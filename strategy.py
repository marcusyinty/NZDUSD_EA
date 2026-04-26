import MetaTrader5 as mt5

class Strategy:
    def __init__(self, config):
        self.config = config

    def check_entry_signal(self, df, asian_high, asian_low):
        """
        Checks for Breakout of Asian Range OR M15 High/Low sweep.
        Filters: EMA 50 (Trend) and RSI > 50 (Momentum)
        """
        if df is None or len(df) < 3:
            return None
            
        last_closed = df.iloc[-2]
        current = df.iloc[-1]
        
        # Indicator columns created by pandas_ta: 'EMA_50', 'RSI_14'
        if 'EMA_50' not in df.columns or 'RSI_14' not in df.columns:
            return None
            
        ema50 = last_closed['EMA_50']
        rsi = last_closed['RSI_14']
        
        # Current tick data vs last closed
        close = current['close']
        
        # Trend and Momentum filters
        uptrend = close > ema50 and rsi > 50
        downtrend = close < ema50 and rsi < 50
        
        signal = None
        
        # 1. Asian Session Breakout
        if asian_high is not None and asian_low is not None:
            if close > asian_high:
                if uptrend:
                    signal = "BUY"
                else:
                    import logging
                    logging.info(f"Asian Breakout (High) detected but filters failed: EMA 50={ema50:.5f}, RSI={rsi:.1f} (Need close > EMA and RSI > 50)")
            elif close < asian_low:
                if downtrend:
                    signal = "SELL"
                else:
                    import logging
                    logging.info(f"Asian Breakout (Low) detected but filters failed: EMA 50={ema50:.5f}, RSI={rsi:.1f} (Need close < EMA and RSI < 50)")
                 
        # 2. 15-Minute Sweep (Previous candle's high/low broken)
        if signal is None:
            prev_high = df.iloc[-3]['high']
            prev_low = df.iloc[-3]['low']
            
            # Check if last closed candle swept the previous high/low
            # and current price confirms it
            if last_closed['high'] > prev_high:
                if uptrend:
                    signal = "BUY"
                else:
                    import logging
                    logging.info(f"15m Sweep (High) detected but filters failed: EMA 50={ema50:.5f}, RSI={rsi:.1f} (Need close > EMA and RSI > 50)")
            elif last_closed['low'] < prev_low:
                if downtrend:
                    signal = "SELL"
                else:
                    import logging
                    logging.info(f"15m Sweep (Low) detected but filters failed: EMA 50={ema50:.5f}, RSI={rsi:.1f} (Need close < EMA and RSI < 50)")
                
        return signal

    def calculate_position_size(self, balance, win_rate=0.98):
        """
        Kelly-Inspired Sizing.
        Ensures risk is between 0.25% and 1.0%.
        """
        min_risk = self.config.get('MIN_RISK', 0.0025)
        max_risk = self.config.get('MAX_RISK', 0.010)
        
        # Simplified Kelly: K = W - ((1 - W) / R) where R = Reward/Risk Ratio
        # Assuming R = 1 for this calculation
        r = 1.0 
        kelly = win_rate - ((1 - win_rate) / r)
        
        # Scale down Kelly (e.g., fractional Kelly)
        fractional_kelly = kelly * 0.1 
        
        # Bound the risk
        risk_pct = max(min_risk, min(max_risk, fractional_kelly))
        risk_amount = balance * risk_pct
        
        # Lot sizing based on NZDUSD
        # Approximate: 1 Lot = $10 per pip. 
        sl_pips = self.config.get('SL_PIPS', 20)
        pip_value_per_lot = 10.0 # Approximate for NZDUSD
        
        lot_size = risk_amount / (sl_pips * pip_value_per_lot)
        
        # Ensure lot size fits broker bounds
        symbol_info = mt5.symbol_info(self.config['SYMBOL'])
        if symbol_info is None:
            return 0.01
            
        lot_size = max(symbol_info.volume_min, min(symbol_info.volume_max, lot_size))
        
        # Round to volume step
        vol_step = symbol_info.volume_step
        lot_size = round(lot_size / vol_step) * vol_step
        
        return lot_size
