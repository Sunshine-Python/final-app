import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover
from data_handler import fetch_data
from utils import run_backtest, plot_strat_perf, display_metrics

def ema(data, period):
    alpha = 2 / (period + 1)
    result = np.zeros_like(data)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
    return result

class MACDStrategy(Strategy):
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    stop_loss_pct = 2.0
    take_profit_pct = 5.0
    enable_shorting = True
    enable_stop_loss = True
    enable_take_profit = True

    def init(self):
        close = self.data.Close
        def macd(macd_fast, macd_slow, macd_signal):
            fast_ema = ema(close, macd_fast)
            slow_ema = ema(close, macd_slow)
            macd_line = fast_ema - slow_ema
            signal_line = ema(macd_line, macd_signal)
            return macd_line, signal_line
        self.macd_line, self.signal_line = self.I(macd, self.macd_fast, self.macd_slow, self.macd_signal)
        self.entry_price = None
        self.position_type = None  # 'long' or 'short'

    def next(self):
        if self.position:
            if self.position_type == 'long':
                if self.enable_stop_loss and self.data.Close[-1] <= self.entry_price * (1 - self.stop_loss_pct / 100):
                    self.position.close()
                    self.position_type = None
                elif self.enable_take_profit and self.data.Close[-1] >= self.entry_price * (1 + self.take_profit_pct / 100):
                    self.position.close()
                    self.position_type = None
            elif self.position_type == 'short':
                if self.enable_stop_loss and self.data.Close[-1] >= self.entry_price * (1 + self.stop_loss_pct / 100):
                    self.position.close()
                    self.position_type = None
                elif self.enable_take_profit and self.data.Close[-1] <= self.entry_price * (1 - self.take_profit_pct / 100):
                    self.position.close()
                    self.position_type = None
        if not self.position:
            if crossover(self.macd_line, self.signal_line):
                self.buy()
                self.entry_price = self.data.Close[-1]
                self.position_type = 'long'
            elif crossover(self.signal_line, self.macd_line) and self.enable_shorting:
                self.sell()
                self.entry_price = self.data.Close[-1]
                self.position_type = 'short'

def macd_viz(data, macd_fast=12, macd_slow=26, macd_signal=9):
    data = data[data['Volume'] > 0].copy()
    data.reset_index(inplace=True)
    
    if 'Datetime' not in data.columns:
        data['Datetime'] = data.index
    
    data['ema_fast'] = data['Close'].ewm(span=macd_fast, adjust=False).mean()
    data['ema_slow'] = data['Close'].ewm(span=macd_slow, adjust=False).mean()
    data['macd'] = data['ema_fast'] - data['ema_slow']
    data['signal'] = data['macd'].ewm(span=macd_signal, adjust=False).mean()
    data['histogram'] = data['macd'] - data['signal']
    data['Date'] = pd.to_datetime(data['Datetime']).dt.date
    daily_indices = data.groupby('Date').first().index
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # Plotting the price on the upper subplot
    ax1.plot(data.index, data['Close'], label='Price', color='blue')
    ax1.set_ylabel('Price', color='blue')
    ax1.set_title('MACD Strategy Visualization')
    ax1.grid(True)
    ax1.legend(loc='upper left')
    
    # Plotting MACD on the lower subplot
    ax2.plot(data.index, data['macd'], label='MACD', color='green')
    ax2.plot(data.index, data['signal'], label='Signal', color='red')
    ax2.bar(data.index, data['histogram'], label='Histogram', color='gray', alpha=0.3)
    ax2.set_ylabel('MACD')
    ax2.grid(True)
    ax2.legend(loc='upper left')
    
    plt.xticks(
        ticks=[data[data['Date'] == date].index[0] for date in daily_indices],
        labels=[date.strftime('%Y-%m-%d') for date in daily_indices],
        rotation=30
    )
    
    plt.tight_layout()
    st.pyplot(fig)

def run_macd(ticker, start_date, end_date, cash, commission, macd_fast, macd_slow, macd_signal, stop_loss_pct, take_profit_pct, enable_shorting, enable_stop_loss, enable_take_profit):
    MACDStrategy.macd_fast = macd_fast
    MACDStrategy.macd_slow = macd_slow
    MACDStrategy.macd_signal = macd_signal
    MACDStrategy.stop_loss_pct = stop_loss_pct
    MACDStrategy.take_profit_pct = take_profit_pct
    MACDStrategy.enable_shorting = enable_shorting
    MACDStrategy.enable_stop_loss = enable_stop_loss
    MACDStrategy.enable_take_profit = enable_take_profit
    
    data = fetch_data(ticker, start_date, end_date)
    
    if data.empty:
        return None
    
    try:
        output = run_backtest(MACDStrategy, data, cash, commission)
        return output
    except Exception as e:
        st.error(f"An error occurred during backtesting: {str(e)}")
        return None