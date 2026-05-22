import requests
import pandas as pd
import numpy as np
from .connector import *
import os
url = "http://127.0.0.1:8000/items/"  
path = os.path.dirname(os.path.abspath(__file__))

saving_path = os.path.join(path,'..','Temp')

def write_to_excell(data_df,wealth,savingpath):
    
    with pd.ExcelWriter(savingpath, engine="xlsxwriter") as writer:
        
        data_df.to_excel(writer, sheet_name="pnl", index=False)
        wealth.to_excel(writer, sheet_name="wealth", index=False)
    print(f'data written to {savingpath}')
        

def option_request(callput='c',buysell='buy',symbol = 'SP',maturity=12,mn_dt = 'delta',strike=15,bot=1,close=12,sizing='notional',
                   value =1,dh = 'on',percent=1,startdate=None,enddate=None,url = url,savingpath = saving_path):

    
    data = {
        "option":callput,
        "buysell": buysell,
        "symbol": symbol,
        'maturity':maturity,
        'mn_dt':mn_dt,
        'strike': strike,
        'open':bot,
        'close':close,
        'sizing':sizing,
        'value':value,
        'dh':dh,
        'percent':percent,
        'start_date':startdate,
        'end_date':enddate

    }

    file_name = f'{mn_dt}_{strike}_{callput}_{symbol}_{maturity}_{sizing}.xlsx'

    response = requests.post(url, json=data)

    print(response.status_code)
    result = response.json()
    data_df = pd.read_json(result['pnl'], orient="split")
    wealth = pd.read_json(result['wealth'],orient='split')
    savingpath = os.path.join(os.path.join(savingpath,file_name))
    write_to_excell(data_df,wealth,savingpath)

def reset_db():

    for item in ['AAPL_SPOT','CONNECTION','OPTION_KEY','OPTIONS_DATA','RISK_FREE_RATES']:
        print(item)
        drop_table(item)
