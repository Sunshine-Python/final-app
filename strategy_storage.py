import json
import os
import streamlit as st
import pandas as pd
from data_handler import fetch_data
from utils import display_metrics, run_backtest
import importlib
import shutil


STRATEGIES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_strategies')

def save_strategy(name, strategy_type, parameters):
    print(f"Attempting to save strategy: {name}")
    print(f"STRATEGIES_DIR: {STRATEGIES_DIR}")
    
    if not os.path.exists(STRATEGIES_DIR):
        print(f"Creating directory: {STRATEGIES_DIR}")
        os.makedirs(STRATEGIES_DIR)
    
    filename = os.path.join(STRATEGIES_DIR, f"{name}.json")
    print(f"Saving to file: {filename}")
    
    data = {
        "name": name,
        "type": strategy_type,
        "parameters": parameters
    }
    
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Strategy successfully saved to: {filename}")
        return True
    except Exception as e:
        print(f"Error saving strategy: {str(e)}")
        return False



def load_strategy(name):
    filename = os.path.join(STRATEGIES_DIR, f"{name}.json")
    if not os.path.exists(filename):
        return None
    
    with open(filename, 'r') as f:
        data = json.load(f)
    
    return data

def list_saved_strategies():
    if not os.path.exists(STRATEGIES_DIR):
        return []
    
    return [f.split('.')[0] for f in os.listdir(STRATEGIES_DIR) if f.endswith('.json')]

def clear_saved_strategies():
    if os.path.exists(STRATEGIES_DIR):
        shutil.rmtree(STRATEGIES_DIR)
        os.makedirs(STRATEGIES_DIR)
    return True



def display_saved_strategies(ticker, start_date, end_date, cash, commission):
    saved_strategies = list_saved_strategies()
    if not saved_strategies:
        st.write("No saved strategies found.")
        return

    # Create a list to hold the data for our table
    table_data = []

    for strategy_name in saved_strategies:
        strategy_data = load_strategy(strategy_name)
        if strategy_data:
            strategy_type = strategy_data['type']
            params = strategy_data['parameters']
            
            # Import the specific strategy function
            module_name = f"strategies.{strategy_type.lower().replace(' ', '_')}"
            try:
                strategy_module = importlib.import_module(module_name)
                run_strategy = getattr(strategy_module, f"run_{strategy_type.lower().replace(' ', '_')}")

                # Fetch data and run backtest
                data = fetch_data(ticker, start_date, end_date)
                if not data.empty:
                    output = run_strategy(
                        ticker, 
                        start_date, 
                        end_date, 
                        cash, 
                        commission, 
                        **{k: v for k, v in params.items() if k not in ['cash', 'commission', 'start_date', 'end_date']}
                    )
                    
                    if output is not None:
                        metrics = display_metrics(output)
                        table_data.append({
                            "Strategy Name": strategy_name,
                            "Type": strategy_type,
                            "Win Rate": f"{metrics['Win Rate [%]']:.2f}%",
                            "Total Return": f"{metrics['Return [%]']:.2f}%",
                            "Sharpe Ratio": f"{metrics['Sharpe Ratio']:.2f}",
                            "Max Drawdown": f"{metrics['Max. Drawdown [%]']:.2f}%"                            
                        })
            except Exception as e:
                st.error(f"Error running strategy {strategy_name}: {str(e)}")

    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df.style.highlight_max(subset=['Total Return', 'Win Rate'], color='lightgreen')
                            
    else:
        st.write("No performance data available for saved strategies.")
