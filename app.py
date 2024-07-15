import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import os

from pinescript.pinescripter import pinescripter

from data_handler import fetch_data
from utils import display_metrics, plot_strat_perf
from strategy_storage import save_strategy, load_strategy, list_saved_strategies, display_saved_strategies, clear_saved_strategies
from strategy_config import get_strategy_params, visualize_strategy
from strategies.sma_cross import run_sma_cross
from strategies.rsi_cross import run_rsi_cross
from strategies.bollinger_bands import run_bollinger_bands
from strategies.macd import run_macd
from strategies.vwap import run_vwap
from strategies.stochastic import run_stochastic
from strategies.mean_reversion import run_mean_reversion
from strategies.momentum import run_momentum
from strategies.adx import run_adx
from strategies.cci import run_cci
from strategies.dpo import run_dpo
from strategies.obv import run_obv
from strategies.atr import run_atr
from strategies.standard_deviation import run_standard_deviation


st.set_page_config(layout="wide", page_title="Little John")
logo_url = "little-john-leaf.png"
st.logo(logo_url)

# Function to load CSS file
def load_css(style):
    with open(style) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Load CSS
load_css("style.css")


def main():
    st.title('Little John')

    col1, col2 = st.columns([1, 4])

    with col1:
        st.subheader(' ')  # Adding an empty space subheader
        
        strategy_groups = {
            'Momentum': ['RSI Cross', 'MACD', 'Stochastic', 'Momentum'],
            'Trend': ['ADX', 'DPO', 'CCI'],
            'Volume': ['VWAP', 'OBV'],
            'Volatility': ['Bollinger Bands', 'ATR', 'Standard Deviation'],
            'Mean Reversion': ['Mean Reversion']
        }

        sixty_days_ago = datetime.now() - timedelta(days=59)
        ten_days_ago = datetime.now() - timedelta(days=10)

        with st.expander("Timeframe | Cash | Commission", expanded=True):
                start_date = st.date_input(
                'Start Date', 
                value=ten_days_ago,
                min_value=sixty_days_ago,
                max_value=datetime.now()-timedelta(days=1)
                )
    
                min_end_date = start_date + timedelta(days=1)
    
                end_date = st.date_input(
                'End Date', 
                value=datetime.now(),
                min_value=min_end_date,
                max_value=datetime.now()
                )
            
                cash = st.number_input('Initial Cash', min_value=1000, max_value=1000000, value=10000)
                commission = st.slider('Commission (%)', min_value=0.0, max_value=1.0, value=0.0, step=0.01)


        ticker = st.text_input('Enter stock ticker', value='META')


        with st.expander("Strategy", expanded=True):
            group = st.selectbox('Select Strategy Type', list(strategy_groups.keys()), key='group')
            strategy = st.selectbox('Strategy', strategy_groups[group], key='strategy')




        # Get strategy-specific parameters
        strategy_params = get_strategy_params(strategy)
            
        with st.expander("Stop Loss / Take Profit", expanded=True):
            stop_loss_pct = st.slider('Stop Loss %', min_value=0.0, max_value=10.0, 
                                      value=2.0, step=0.1)
            take_profit_pct = st.slider('Take Profit %', min_value=0.0, max_value=10.0, 
                                        value=5.0, step=0.1)
            enable_stop_loss = st.checkbox('Enable Stop Loss', value=True)
            enable_take_profit = st.checkbox('Enable Take Profit', value=True)
            enable_shorting = st.checkbox('Enable Shorting', value=True)

        # Add option to save current strategy
        with st.expander("Store Strategy", expanded=True):

            strategy_name = st.text_input('Enter a name for this strategy:')
            save_strategy_button = st.button('Save Current Strategy')

            if save_strategy_button and strategy_name:
                current_params = {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'cash': cash,
                    'commission': commission,
                    'enable_shorting': enable_shorting,
                    'stop_loss_pct': stop_loss_pct,
                    'take_profit_pct': take_profit_pct,
                    'enable_stop_loss': enable_stop_loss,
                    'enable_take_profit': enable_take_profit,
                    **strategy_params
                }
                success = save_strategy(strategy_name, strategy, current_params)
                if success:
                    st.success(f"Strategy '{strategy_name}' saved successfully!")
                else:
                    st.error(f"Failed to save strategy '{strategy_name}'. Check the console for more information.")

            # Add option to clear saved strategies
            if st.button('Clear Saved Strategies'):
                if clear_saved_strategies():
                    st.success("All saved strategies have been cleared.")
                else:
                    st.error("Failed to clear saved strategies. Check the console for more information.")
                    
            saved_strategies_dir = 'saved_strategies'
            json_files = [f for f in os.listdir(saved_strategies_dir) if f.endswith('.json')]
            selected_json = st.selectbox('Select a saved strategy', [''] + json_files)

            if selected_json:
                if st.button('Generate PineScript'):
                    json_path = os.path.join(saved_strategies_dir, selected_json)
                    try:
                        pinescripter(json_path)
                        st.success(f"PineScript generated for {selected_json}")
                    except Exception as e:
                        st.error(f"Error generating PineScript: {str(e)}")



    with col2:
        data = fetch_data(ticker, start_date, end_date)
        
        if data.empty:
            st.warning("No data available for the selected date range.")
        else:
            st.subheader(f'{strategy} Strategy')
            with st.expander('Visualization', expanded=True):
                visualize_strategy(strategy, data, strategy_params)

            if strategy == 'SMA Cross':
                output = run_sma_cross(ticker, start_date, end_date, cash, commission, 
                                       strategy_params['sma_short'], strategy_params['sma_long'], 
                                       stop_loss_pct, take_profit_pct, enable_shorting, 
                                       enable_stop_loss, enable_take_profit)

            elif strategy == 'RSI Cross':
                output = run_rsi_cross(ticker, start_date, end_date, cash, commission, 
                                       strategy_params['rsi_sma_short'], strategy_params['rsi_sma_long'], 
                                       strategy_params['rsi_period'], stop_loss_pct, take_profit_pct, 
                                       enable_shorting, enable_stop_loss, enable_take_profit)
            elif strategy == 'Bollinger Bands':
                output = run_bollinger_bands(ticker, start_date, end_date, cash, commission, 
                                             strategy_params['bb_period'], strategy_params['bb_std_dev'],
                                             stop_loss_pct, take_profit_pct, enable_shorting, 
                                             enable_stop_loss, enable_take_profit)
            elif strategy == 'MACD':
                output = run_macd(ticker, start_date, end_date, cash, commission, 
                                           strategy_params['macd_fast'], strategy_params['macd_slow'], 
                                           strategy_params['macd_signal'], stop_loss_pct, take_profit_pct, 
                                           enable_shorting, enable_stop_loss, enable_take_profit)
            elif strategy == 'VWAP':
                output = run_vwap(ticker, start_date, end_date, cash, commission, 
                                           strategy_params['vwap_periods'], stop_loss_pct, take_profit_pct, 
                                           enable_shorting, enable_stop_loss, enable_take_profit)
            elif strategy == 'Stochastic':
                output = run_stochastic(ticker, start_date, end_date, cash, commission, 
                                            strategy_params['stoch_k'], strategy_params['stoch_d'], 
                                            strategy_params['stoch_overbought'], strategy_params['stoch_oversold'], 
                                            stop_loss_pct, take_profit_pct, enable_shorting, 
                                            enable_stop_loss, enable_take_profit)
            elif strategy == 'Mean Reversion':
                output = run_mean_reversion(ticker, start_date, end_date, cash, commission, 
                                            strategy_params['mr_period'], strategy_params['mr_entry_std'], 
                                            strategy_params['mr_exit_std'], stop_loss_pct, take_profit_pct, 
                                            enable_shorting, enable_stop_loss, enable_take_profit)
            elif strategy == 'Momentum':
                output = run_momentum(ticker, start_date, end_date, cash, commission, 
                                      strategy_params['mom_period'], strategy_params['mom_threshold'], 
                                      stop_loss_pct, take_profit_pct, enable_shorting, 
                                      enable_stop_loss, enable_take_profit)
            elif strategy == 'ADX':
                output = run_adx(ticker, start_date, end_date, cash, commission, 
                                 strategy_params['adx_period'], strategy_params['adx_threshold'], 
                                 stop_loss_pct, take_profit_pct, enable_shorting, 
                                 enable_stop_loss, enable_take_profit)
            elif strategy == 'CCI':
                output = run_cci(ticker, start_date, end_date, cash, commission, 
                                 strategy_params['cci_period'], strategy_params['cci_overbought'], 
                                 strategy_params['cci_oversold'], stop_loss_pct, take_profit_pct, 
                                 enable_shorting, enable_stop_loss, enable_take_profit)
            elif strategy == 'DPO':
                output = run_dpo(ticker, start_date, end_date, cash, commission, 
                                 strategy_params['dpo_period'], strategy_params['dpo_threshold'],
                                 stop_loss_pct, take_profit_pct, enable_shorting, 
                                 enable_stop_loss, enable_take_profit)
            elif strategy == 'OBV':
                output = run_obv(ticker, start_date, end_date, cash, commission, 
                                          strategy_params['obv_periods'], stop_loss_pct, take_profit_pct, 
                                          enable_shorting, enable_stop_loss, enable_take_profit)
            elif strategy == 'ATR':
                output = run_atr(ticker, start_date, end_date, cash, commission, 
                                          strategy_params['atr_period'], strategy_params['atr_multiplier'],
                                          stop_loss_pct, take_profit_pct, enable_shorting, 
                                          enable_stop_loss, enable_take_profit)
            elif strategy == 'Standard Deviation':
                output = run_standard_deviation(ticker, start_date, end_date, cash, commission, 
                                              strategy_params['std_period'], strategy_params['std_multiplier'],
                                              stop_loss_pct, take_profit_pct, enable_shorting, 
                                              enable_stop_loss, enable_take_profit)

        if output is not None:
            with st.expander('Strategy Performance', expanded=True):
                plot_strat_perf(output, f"{strategy} Strategy Performance - {ticker}")
            
            with st.expander('Key Performance Metrics', expanded=True):
                metrics = display_metrics(output)
                metrics_df = pd.DataFrame([metrics]).T
                metrics_df.columns = ['Value']
                
                # Display key metrics in a more prominent way
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("Total Return", f"{metrics['Return [%]']:.2f}%")
                col2.metric("Max Drawdown", f"{metrics['Max. Drawdown [%]']:.2f}%")
                col3.metric("Win Rate", f"{metrics['Win Rate [%]']:.2f}%")
                col4.metric("Best Trade", f"{metrics['Best Trade [%]']:.2f}%")
                col5.metric("Worst Trade", f"{metrics['Worst Trade [%]']:.2f}%")
            
            with st.expander('Trade Log', expanded=False):
                if '_trades' in output:
                    trades_df = output['_trades']
                    
                    # List of columns we want to display if they're available
                    columns_to_display = ['Size', 'PnL', 'ReturnPct', 'EntryPrice', 'ExitPrice', 'EntryTime', 'ExitTime', 'Duration']
                    
                    # Filter the DataFrame to only include available columns
                    trades_df_display = trades_df[[col for col in columns_to_display if col in trades_df.columns]]
                    
                    # Format specific columns if they exist
                    if 'ReturnPct' in trades_df_display.columns:
                        trades_df_display['ReturnPct'] = trades_df_display['ReturnPct'].apply(lambda x: f"{x:.2f}%")
                    if 'Duration' in trades_df_display.columns:
                        trades_df_display['Duration'] = trades_df_display['Duration'].apply(lambda x: str(x))
                    if 'PnL' in trades_df_display.columns:
                        trades_df_display['PnL'] = trades_df_display['PnL'].apply(lambda x: f"{x:.2f}")
                    
                    # Display the trade log
                    st.dataframe(trades_df_display)
                else:
                    st.write("No trade data available.")
            
            with st.expander('Trade Summary', expanded=False):
                if '_trades' in output:
                    trades_df = output['_trades']
                    summary = pd.DataFrame({
                        'Total Trades': len(trades_df),
                        'Profitable Trades': (trades_df['PnL'] > 0).sum() if 'PnL' in trades_df.columns else 'N/A',
                        'Loss-Making Trades': (trades_df['PnL'] < 0).sum() if 'PnL' in trades_df.columns else 'N/A',
                        'Total PnL': trades_df['PnL'].sum() if 'PnL' in trades_df.columns else 'N/A',
                        'Average PnL per Trade': trades_df['PnL'].mean() if 'PnL' in trades_df.columns else 'N/A',
                    }, index=['Value'])
                    st.dataframe(summary.T)
                    st.dataframe(metrics_df)
                else:
                    st.write("No trade summary available.")
            
            with st.expander('Saved Strategies Performance', expanded=False):
                display_saved_strategies(ticker, start_date, end_date, cash, commission)
        else:
            st.warning("Backtest did not complete successfully. Please check your parameters.")

if __name__ == "__main__":
    main()

st.markdown("<div class='footer'>© Little John - Your Companion in Mastering the Markets</div>", unsafe_allow_html=True)




