import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover
from backtesting.test import SMA
from data_handler import fetch_data
from utils import run_backtest, plot_strat_perf, display_metrics

import matplotlib.font_manager as fm

class RsiCross(Strategy):
    rsi_sma_short = 10
    rsi_sma_long = 20
    rsi_period = 14
    stop_loss_pct = 2.0
    take_profit_pct = 5.0
    enable_shorting = True
    enable_stop_loss = True
    enable_take_profit = True

    def init(self):
        # Calculate RSI
        close = self.data.Close
        delta = pd.Series(close).diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.rsi_period, min_periods=1).mean()
        avg_loss = loss.rolling(window=self.rsi_period, min_periods=1).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)  # Fill NaN values with 50 (neutral)
        
        self.rsi = self.I(lambda: rsi)
        self.rsi1 = self.I(SMA, self.rsi, self.rsi_sma_short)
        self.rsi2 = self.I(SMA, self.rsi, self.rsi_sma_long)
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
            if crossover(self.rsi1, self.rsi2):
                self.buy()
                self.entry_price = self.data.Close[-1]
                self.position_type = 'long'
            elif crossover(self.rsi2, self.rsi1) and self.enable_shorting:
                self.sell()
                self.entry_price = self.data.Close[-1]
                self.position_type = 'short'


font_path = "Times New Roman.ttf"
font_properties = fm.FontProperties(fname=font_path, size=14)
title_font_properties = fm.FontProperties(fname=font_path, size=16, weight='bold')

def rsi_cross_viz(data, rsi_sma_short=10, rsi_sma_long=20, rsi_period=14):
    data = data[data['Volume'] > 0]
    data.reset_index(inplace=True)

    if 'Datetime' not in data.columns:
        data['Datetime'] = data.index

    # Calculate RSI
    close = data['Close']
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=rsi_period, min_periods=1).mean()
    avg_loss = loss.rolling(window=rsi_period, min_periods=1).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)  # Fill NaN values with 50 (neutral)
    short_rsi = rsi.rolling(window=rsi_sma_short, min_periods=1).mean()
    long_rsi = rsi.rolling(window=rsi_sma_long, min_periods=1).mean()

    data['Date'] = data['Datetime'].dt.date
    daily_indices = data.groupby('Date').first().index

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6), sharex=True, facecolor='none')

    # Set transparent background
    fig.patch.set_alpha(0)
    ax1.set_facecolor('none')
    ax2.set_facecolor('none')

    # Remove the outline of the axes
    for spine in ax1.spines.values():
        spine.set_visible(False)
    for spine in ax2.spines.values():
        spine.set_visible(False)

    line1, = ax1.plot(data.index, data['Close'], label='Price', color='#66FF66')
    ax1.set_ylabel('Price', fontproperties=font_properties, color='white')
    ax1.legend(prop=font_properties, facecolor='white', framealpha=0.5)
    ax1.grid(True, axis='y', color='grey', linestyle='-', linewidth=0.5)
    ax1.grid(False, axis='x')

    line2, = ax2.plot(data.index, rsi, label='RSI', color='purple')
    line3, = ax2.plot(data.index, short_rsi, label=f'RSI SMA({rsi_sma_short})', color='#FF6666')
    line4, = ax2.plot(data.index, long_rsi, label=f'RSI SMA({rsi_sma_long})', color='#4682B4')
    ax2.set_ylabel('RSI', fontproperties=font_properties, color='white')
    ax2.set_ylim(-5, 105)
    ax2.legend(prop=font_properties, facecolor='white', framealpha=0.5)
    ax2.grid(True, axis='y', color='grey', linestyle='-', linewidth=0.5)
    ax2.grid(False, axis='x')

    # Limit the number of x-ticks to 7
    xtick_locs = np.linspace(0, len(data) - 1, 7, dtype=int)
    xtick_labels = [data.iloc[i]['Date'].strftime('%Y-%m-%d') for i in xtick_locs]
    
    ax1.set_xticks(xtick_locs)
    ax1.set_xticklabels(xtick_labels, rotation=30, fontproperties=font_properties, color='white')

    ax1.tick_params(axis='x', colors='white', labelsize=12)
    ax1.tick_params(axis='y', colors='white', labelsize=12)
    ax2.tick_params(axis='x', colors='white', labelsize=12)
    ax2.tick_params(axis='y', colors='white', labelsize=12)

    for label in ax1.get_xticklabels() + ax1.get_yticklabels():
        label.set_fontproperties(font_properties)
    for label in ax2.get_xticklabels() + ax2.get_yticklabels():
        label.set_fontproperties(font_properties)

    # Title and labels
    fig.suptitle('RSI Cross Visualization', fontproperties=title_font_properties, color='white')
    ax2.set_xlabel('Time', fontproperties=font_properties, color='white')

    plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.15)
    plt.tight_layout()

    st.pyplot(fig, clear_figure=True)








def run_rsi_cross(ticker, start_date, end_date, cash, commission, rsi_sma_short, rsi_sma_long, rsi_period, stop_loss_pct, take_profit_pct, enable_shorting, enable_stop_loss, enable_take_profit):
    RsiCross.rsi_sma_short = rsi_sma_short
    RsiCross.rsi_sma_long = rsi_sma_long
    RsiCross.rsi_period = rsi_period
    RsiCross.stop_loss_pct = stop_loss_pct
    RsiCross.take_profit_pct = take_profit_pct
    RsiCross.enable_shorting = enable_shorting
    RsiCross.enable_stop_loss = enable_stop_loss
    RsiCross.enable_take_profit = enable_take_profit

    data = fetch_data(ticker, start_date, end_date)
    
    if data.empty:
        return None
    
    try:
        output = run_backtest(RsiCross, data, cash, commission)
        return output
    except Exception as e:
        st.error(f"An error occurred during backtesting: {str(e)}")
        return None
