import MetaTrader5 as mt5
import json
import time
import logging
from datetime import datetime
from data_loader import DataLoader
from strategy import Strategy
from trade_manager import TradeManager
from notifier import TelegramNotifier
import sys
import os
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(path="config.json"):
    if not os.path.exists(path):
        sample_path = path + ".sample"
        if os.path.exists(sample_path):
            logging.info(f"Configuration file {path} not found. Copying from {sample_path}")
            shutil.copy(sample_path, path)
        else:
            logging.warning(f"Neither {path} nor {sample_path} was found!")
            
    with open(path, "r") as f:
        return json.load(f)

def execute_trade(signal, config, strategy, current_price, notifier=None):
    account_info = mt5.account_info()
    if account_info is None:
        logging.error("Failed to get account info")
        return
        
    balance = account_info.balance
    lot_size = strategy.calculate_position_size(balance)
    
    symbol = config['SYMBOL']
    sl_pips = config.get('SL_PIPS', 20)
    magic = config['MAGIC_NUMBER']
    
    symbol_info = mt5.symbol_info(symbol)
    point = symbol_info.point
    
    # 1 pip = 10 points usually for 5 digit brokers. Assume NZDUSD is 5 digits.
    # We'll use a standard point multiplier or assume 1 pip = 0.0001
    pip_size = 0.0001
    
    if signal == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).ask
        sl = price - (sl_pips * pip_size)
        tp = price + (sl_pips * config.get('RISK_REWARD_RATIO', 1.5) * pip_size)
    elif signal == "SELL":
        order_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).bid
        sl = price + (sl_pips * pip_size)
        tp = price - (sl_pips * config.get('RISK_REWARD_RATIO', 1.5) * pip_size)
    else:
        return

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": magic,
        "comment": "NZD-Alpha Entry",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Order failed, retcode={result.retcode}")
    else:
        msg = f"Order placed successfully: {signal} {lot_size} lots at {price:.5f}"
        logging.info(msg)
        if notifier:
            notifier.send_message(f"🚀 *NZD-Alpha Entry*\n{msg}\nSL: {sl:.5f} | TP: {tp:.5f}")


def main():
    try:
        config = load_config()
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        sys.exit(1)
        
    if not mt5.initialize():
        logging.error("mt5.initialize() failed")
        mt5.shutdown()
        sys.exit(1)
        
    symbol = config['SYMBOL']
    if not mt5.symbol_select(symbol, True):
        logging.error(f"Failed to select symbol {symbol}")
        mt5.shutdown()
        sys.exit(1)
        
    msg = f"NZD-Alpha EA initialized for {symbol}"
    logging.info(msg)
    
    notifier = TelegramNotifier(config)
    notifier.send_message(f"✅ *NZD-Alpha EA Initialized*\n{msg}")
    
    data_loader = DataLoader(config)
    strategy = Strategy(config)
    trade_manager = TradeManager(config, notifier)
    
    start_balance = mt5.account_info().balance
    
    # Simple rate limiting for M15 processing to avoid redundant calculations
    last_processed_candle_time = None
    
    try:
        while True:
            # Friday Close Check
            now = datetime.now()
            if now.weekday() == 4 and now.hour >= config.get('FRIDAY_CLOSE_HOUR', 20):
                positions = mt5.positions_get(symbol=symbol)
                if positions is not None and len(positions) > 0:
                    msg = "Friday Close Time reached. Closing all positions."
                    logging.info(msg)
                    notifier.send_message(f"🛑 *Friday Close*\n{msg}")
                    trade_manager.close_all_positions()
                time.sleep(60)
                continue

            # Check Circuit Breaker
            if trade_manager.check_drawdown_halt(start_balance):
                break
                
            # Update active positions (Time-Decay logic on every tick/loop)
            trade_manager.update()
            
            # Check for new entries only once per tick
            df = data_loader.get_data(num_bars=3)
            if df is not None and not df.empty:
                current_candle_time = df.iloc[-1]['time']
                
                # We can check entry on every tick since the breakout could happen mid-candle
                asian_high, asian_low = data_loader.get_asian_session_range()
                
                # Check if we already have a position to avoid pyramiding if not allowed
                positions = mt5.positions_get(symbol=symbol)
                has_open_position = positions is not None and len(positions) > 0
                
                if not has_open_position:
                    # Spread Filter
                    tick = mt5.symbol_info_tick(symbol)
                    pip_size = 0.0001
                    current_spread = (tick.ask - tick.bid) / pip_size
                    
                    if current_spread <= config.get('MAX_SPREAD_PIPS', 3.0):
                        signal = strategy.check_entry_signal(df, asian_high, asian_low)
                        if signal:
                            current_price = tick.ask if signal == "BUY" else tick.bid
                            execute_trade(signal, config, strategy, current_price, notifier)
                    else:
                        logging.debug(f"Spread {current_spread:.1f} > Max ({config.get('MAX_SPREAD_PIPS', 3.0)}). Blocking entry.")
            
            time.sleep(1) # Sleep to prevent 100% CPU usage
            
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()
