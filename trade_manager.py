import MetaTrader5 as mt5
import logging
import time

class TradeManager:
    def __init__(self, config, notifier=None):
        self.config = config
        self.notifier = notifier
        self.symbol = config['SYMBOL']
        self.magic = config['MAGIC_NUMBER']
        
        # Dictionary to track ticks for open positions
        # ticket -> {"ticks": int, "initial_sl": float, "initial_risk": float, "phase": int}
        self.trade_state = {}

    def update(self):
        """
        Called on every tick to update position states and apply time-decay logic.
        """
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return
            
        current_tickets = []
        for pos in positions:
            if pos.magic != self.magic:
                continue
                
            ticket = pos.ticket
            current_tickets.append(ticket)
            
            if ticket not in self.trade_state:
                self.trade_state[ticket] = {
                    "initial_sl": pos.sl,
                    "initial_price": pos.price_open,
                    "type": pos.type,
                    "phase": 1
                }
                
            state = self.trade_state[ticket]
            
            current_time_sec = int(time.time())
            ticks_array = mt5.copy_ticks_range(pos.symbol, pos.time, current_time_sec, mt5.COPY_TICKS_ALL)
            ticks = len(ticks_array) if ticks_array is not None else 0
            
            min_interval = self.config.get('MIN_HOLD_INTERVAL', 5000)
            max_interval = self.config.get('MAX_HOLD_INTERVAL', 60000)
            grace_period = self.config.get('GRACE_PERIOD_TICKS', 5000)
            max_hold_with_grace = max_interval + grace_period
            
            # Phase 1: The Noise Zone (< 5000 intervals) - Do nothing
            if ticks < min_interval:
                continue
                
            # Phase 2: The Breakout (5000 - 60000) - Adjust SL to -50% of original risk
            if min_interval <= ticks < max_interval and state["phase"] == 1:
                self.adjust_sl_to_half_risk(pos, state)
                state["phase"] = 2
                
            # Phase 3: The Decay Peak (>= 60000)
            if ticks >= max_interval and state["phase"] == 2:
                if pos.profit > 0:
                    self.close_position(pos, "Time-Decay Hard Exit")
                    state["phase"] = 3
                else:
                    state["phase"] = 2.5 # Grace Period
                    msg = f"Position {ticket} underwater at Alpha Peak. Entering Grace Period."
                    logging.info(msg)
                    if self.notifier:
                        self.notifier.send_message(f"⚠️ *Grace Period Activated*\n{msg}")
                    
            # Grace Period Exit
            if state["phase"] == 2.5:
                if pos.profit > 0 or ticks >= max_hold_with_grace:
                    self.close_position(pos, "Grace Period Hard Exit")
                    state["phase"] = 3

        # Cleanup closed trades
        closed_tickets = [t for t in self.trade_state.keys() if t not in current_tickets]
        for t in closed_tickets:
            del self.trade_state[t]

    def adjust_sl_to_half_risk(self, pos, state):
        """
        Adjusts the Stop Loss to -50% of the initial risk.
        """
        if state["initial_sl"] == 0.0:
            return # No initial SL set
            
        initial_risk_points = abs(state["initial_price"] - state["initial_sl"])
        new_risk_points = initial_risk_points * 0.5
        
        if pos.type == mt5.ORDER_TYPE_BUY:
            new_sl = state["initial_price"] - new_risk_points
            # Only move SL up
            if new_sl > pos.sl:
                self.modify_sl(pos, new_sl)
        else: # SELL
            new_sl = state["initial_price"] + new_risk_points
            # Only move SL down
            if new_sl < pos.sl or pos.sl == 0.0:
                self.modify_sl(pos, new_sl)

    def modify_sl(self, pos, new_sl):
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "sl": float(new_sl),
            "tp": float(pos.tp),
            "magic": self.magic
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"Failed to modify SL for {pos.ticket}: {result.comment}")

    def close_position(self, pos, comment="Closed by Manager"):
        tick = mt5.symbol_info_tick(pos.symbol)
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "price": tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask,
            "deviation": 20,
            "magic": self.magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"Failed to close position {pos.ticket}: {result.comment}")
        else:
            if self.notifier:
                self.notifier.send_message(f"🛑 *Position Closed* ({comment})\nTicket: {pos.ticket} | Symbol: {pos.symbol} | Vol: {pos.volume}")
            
    def check_drawdown_halt(self, start_balance):
        account_info = mt5.account_info()
        if account_info is None:
            return False
            
        current_equity = account_info.equity
        drawdown_pct = (start_balance - current_equity) / start_balance
        
        if drawdown_pct >= self.config.get('MAX_DRAWDOWN', 0.08):
            msg = "MAX DRAWDOWN REACHED! Halting trading."
            logging.critical(msg)
            if self.notifier:
                self.notifier.send_message(f"🚨 *CRITICAL:* {msg}")
            return True
        return False

    def close_all_positions(self):
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return
        for pos in positions:
            if pos.magic == self.magic:
                self.close_position(pos, "Friday Force Close")
