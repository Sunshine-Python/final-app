import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from backtesting import Strategy
from data_handler import fetch_data
from utils import run_backtest, plot_strat_perf, display_metrics

import matplotlib.font_manager as fm

def calculate_dpo(close, dpo_period=20):
    shift = dpo_period // 2 + 1
    sma = close.rolling(window=dpo_period).mean()
    dpo = close.shift(shift) - sma
    return dpo

class DPOStrategy(Strategy):
    dpo_period = 20
    dpo_threshold = 0
    stop_loss_pct = 2.0
    take_profit_pct = 5.0
    enable_shorting = True
    enable_stop_loss = True
    enable_take_profit = True

    def init(self):
        close = pd.Series(self.data.Close)
        self.dpo = self.I(calculate_dpo, close, self.dpo_period)
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
            if self.dpo[-1] > self.dpo_threshold:
                self.buy()
                self.entry_price = self.data.Close[-1]
                self.position_type = 'long'
            elif self.dpo[-1] < -self.dpo_threshold and self.enable_shorting:
                self.sell()
                self.entry_price = self.data.Close[-1]
                self.position_type = 'short'



# Define font properties
font_path = "Times New Roman.ttf"
font_properties = fm.FontProperties(fname=font_path, size=14)
title_font_properties = fm.FontProperties(fname=font_path, size=16, weight='bold')

def dpo_viz(data, dpo_period=20, dpo_threshold=0):
    data = data[data['Volume'] > 0].copy()
    data.reset_index(drop=True, inplace=True)
    
    dpo = calculate_dpo(data['Close'], dpo_period)

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

    ax1.plot(data.index, data['Close'], label='Price', color='#00A86B')  # Flashier pine green
    ax1.set_ylabel('Price', fontproperties=font_properties, color='white')
    ax1.legend(prop=font_properties, facecolor='white', framealpha=0.5)
    ax1.grid(True, axis='y', color='grey', linestyle='-', linewidth=0.5)
    ax1.grid(False, axis='x')

    ax2.plot(data.index, dpo, label='DPO', color='purple')
    ax2.axhline(y=0, color='cyan', linestyle='--', label='Zero Line')
    ax2.axhline(y=dpo_threshold, color='red', linestyle='--', label=f'Upper Threshold ({dpo_threshold})')
    ax2.axhline(y=-dpo_threshold, color='yellow', linestyle='--', label=f'Lower Threshold ({-dpo_threshold})')
    ax2.set_xlabel('Time', fontproperties=font_properties, color='white')
    ax2.set_ylabel('DPO', fontproperties=font_properties, color='white')
    ax2.legend(prop=font_properties, facecolor='white', framealpha=0.5)
    ax2.grid(True, axis='y', color='grey', linestyle='-', linewidth=0.5)
    ax2.grid(False, axis='x')
    
    # Set x-axis ticks
    num_ticks = 10
    tick_locations = np.linspace(0, len(data) - 1, num_ticks, dtype=int)
    ax1.set_xticks(tick_locations)
    ax2.set_xticks(tick_locations)
    
    # Format x-axis labels
    if 'Date' in data.columns:
        date_labels = data.loc[tick_locations, 'Date'].dt.strftime('%Y-%m-%d')
        ax2.set_xticklabels(date_labels, rotation=45, ha='right', fontproperties=font_properties, color='white')
    else:
        ax2.set_xticklabels(tick_locations, fontproperties=font_properties, color='white')
    
    ax1.tick_params(axis='x', colors='white', labelsize=12)
    ax1.tick_params(axis='y', colors='white', labelsize=12)
    ax2.tick_params(axis='x', colors='white', labelsize=12)
    ax2.tick_params(axis='y', colors='white', labelsize=12)
    
    for label in ax1.get_xticklabels() + ax1.get_yticklabels():
        label.set_fontproperties(font_properties)
    for label in ax2.get_xticklabels() + ax2.get_yticklabels():
        label.set_fontproperties(font_properties)

    fig.suptitle('DPO Strategy Visualization', fontproperties=title_font_properties, color='white')
    
    plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.15)
    plt.tight_layout()
    st.pyplot(fig, clear_figure=True)






    
def run_dpo(ticker, start_date, end_date, cash, commission, dpo_period, dpo_threshold, 
            stop_loss_pct, take_profit_pct, enable_shorting, enable_stop_loss, 
            enable_take_profit):
    DPOStrategy.dpo_period = dpo_period
    DPOStrategy.dpo_threshold = dpo_threshold
    DPOStrategy.stop_loss_pct = stop_loss_pct
    DPOStrategy.take_profit_pct = take_profit_pct
    DPOStrategy.enable_shorting = enable_shorting
    DPOStrategy.enable_stop_loss = enable_stop_loss
    DPOStrategy.enable_take_profit = enable_take_profit

    data = fetch_data(ticker, start_date, end_date)
        
    if data.empty:
        return None
    
    try:
        # st.subheader('DPO Visualization')
        # dpo_viz(data, dpo_period, dpo_threshold)
        
        output = run_backtest(DPOStrategy, data, cash, commission)
        return output
    except Exception as e:
        st.error(f"An error occurred during backtesting: {str(e)}")
        return None


