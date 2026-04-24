import numpy as np
import pandas as pd
import os
import py_vollib.black_scholes.implied_volatility as iv
from py_vollib.black_scholes import black_scholes as bs
from py_vollib.black_scholes.greeks.analytical import delta, gamma, vega, theta, rho
import warnings
warnings.filterwarnings("ignore")
base_path = os.path.join(os.getcwd(),'Data','Raw Data')
rate_files = ['bill-rates-2002-2023.csv','daily-treasury-rates-2024.csv','daily-treasury-rates-2025.csv','daily-treasury-rates-2026.csv']
def symbol(date,last_dates):
    if date in last_dates.values:
        return 'EV'
    else:
        return 'SP'
def date_int_convertor(date):
    dl =  str(date).split(' ')[0].split('-')
    fmt_date = ''
    for item in dl:
        fmt_date+=item

    return int(fmt_date)
def adjust_stock(x,sp = 'Spot',):
    
    if x.TradeDate<20140609:
        factor = 28
    elif 20140609<=x.TradeDate<20200831:
        factor = 4
    else:
        factor = 1
    {''}
    adj_spot =  x[sp]/factor
    return adj_spot
def date_formatting(date):
    obj = date.split('/')
    try:
        if len(obj[0])==1:
            obj[0] = f'0{obj[0]}'
        if len(obj[1])==1:
            obj[1] = f'0{obj[1]}'
            
    except Exception as e:
        print(date)
    
    return int(f'{obj[2]}{obj[0]}{obj[1]}')
def compute_continous_rate(df):
    for col in df.columns:
        if col == 'date':
            continue
        period = int(col.split(' ')[0])
        df[f'risk_free_rate_{period}'] = 365*np.log(1+(7*period*df[col])/(100*365))/(7*period)
def compute_iv(x):
    try:
        implied_vol = iv.implied_volatility(x.px,x.AdjSpot,x.AdjStrike,x.days_to_expiry/365,x.risk_free_rate,x.CallPut)
    except Exception as e:
        # check exception 
        implied_vol = 0
    implied_vol = min(20,implied_vol)
    return implied_vol
def compute_greeks(flag,adjspot,days_to_expiry,risk_free_rate,stk,imp_vol):
        days =365
        
        # min_px = df[df.TradeDate==trade_date].px.min()
        # px = bs(flag,adjspot,stk,days_to_expiry/days,risk_free_rate,imp_vol)
        
        # if px<=min_px:
        #         px = min_px
        if days_to_expiry == 0:
                d=g=v=th=rh = 0
        else:
        #print(px)
                d = delta(flag,adjspot,stk,days_to_expiry/days,risk_free_rate,imp_vol)
                g = gamma(flag,adjspot,stk,days_to_expiry/days,risk_free_rate,imp_vol)
                v = vega(flag,adjspot,stk,days_to_expiry/days,risk_free_rate,imp_vol)
                th = theta(flag,adjspot,stk,days_to_expiry/days,risk_free_rate,imp_vol)
                rh = rho(flag,adjspot,stk,days_to_expiry/days,risk_free_rate,imp_vol)
        
        return (d,g,v,th,rh)
def compute_risk_free_rate(x):
    exp_period = [4,6,8,13,17,26,52]
    weeks_to_expiry = round(x['days_to_expiry']/7)
    #print(weeks_to_expiry)
    if f'risk_free_rate_{weeks_to_expiry}' in x.index.to_list() and pd.notna(x[f'risk_free_rate_{weeks_to_expiry}']):
        risk_free_rate = x[f'risk_free_rate_{weeks_to_expiry}']
        #print(risk_free_rate)
    elif 4< weeks_to_expiry< 52:
        l_lim = max([i  for i in exp_period if i<weeks_to_expiry])
        if pd.notna(x[f'risk_free_rate_{l_lim}']):
            rfr_l = x[f'risk_free_rate_{l_lim}']
            
        else:
            l_lim = max([i  for i in exp_period if i<l_lim])
            if pd.notna(x[f'risk_free_rate_{l_lim}']):
                rfr_l = x[f'risk_free_rate_{l_lim}']
            else:
                l_lim = max([i  for i in exp_period if i<l_lim])
                rfr_l = x[f'risk_free_rate_{l_lim}']
        u_lim = min([i  for i in exp_period if i>weeks_to_expiry])
        if pd.notna(x[f'risk_free_rate_{u_lim}']):
            rfr_u = x[f'risk_free_rate_{u_lim}']
        else:
            u_lim = min([i  for i in exp_period if i>u_lim])
            if pd.notna(x[f'risk_free_rate_{u_lim}']):
                rfr_u = x[f'risk_free_rate_{u_lim}']
            else:
                u_lim = min([i  for i in exp_period if i>u_lim])
                rfr_u = x[f'risk_free_rate_{u_lim}']

        # print(rfr_l,rfr_u)
        df_l =  np.exp(-rfr_l * 7*l_lim/365) 
        df_u =  np.exp(-rfr_u * 7*u_lim/365)

        w = (weeks_to_expiry - l_lim)/(u_lim-l_lim)
        log_df_curr = np.log(df_l) + w * (np.log(df_u) - np.log(df_l))
        risk_free_rate = -log_df_curr/(7*weeks_to_expiry/365)
    elif weeks_to_expiry> 52:
        df_1 = np.exp(-x.risk_free_rate_52)
        df_t = df_1*np.exp(-x.risk_free_rate_52*((x.days_to_expiry/365)-1))
        risk_free_rate = -np.log(df_t)/(x.days_to_expiry/365) 
    else :
        risk_free_rate = x.risk_free_rate_4
    return risk_free_rate
def load_preprocess(path = 'Options_AAPL_Monthly.csv'):
    
    df = pd.read_csv(os.path.join(base_path,path))
    df = df.drop_duplicates()
    print(df.info())
    df['AdjStrike'] = df.apply(lambda x:adjust_stock(x,sp="Strike"),axis=1)
    df['AskPrice'] = df.apply(lambda x:adjust_stock(x,sp="AskPrice"),axis=1)
    df['BidPrice'] = df.apply(lambda x:adjust_stock(x,sp="BidPrice"),axis=1)
    df['LastTradePrice'] = df.apply(lambda x:adjust_stock(x,sp="LastTradePrice"),axis=1)
    df["FmtTradeDate"] = pd.to_datetime(df["TradeDate"], format="%Y%m%d")
    df["FmtExpiryDate"] = pd.to_datetime(df["ExpiryDate"], format="%Y%m%d")
    last_dates = (df.groupby(df["FmtTradeDate"].dt.to_period("M"))["FmtTradeDate"].max())
    df['Symbol'] = df.FmtTradeDate.apply(lambda x: symbol(x,last_dates))
    

    return df

def load_stock(path ='AAPL.CSV' ):
    df = pd.read_csv(os.path.join(base_path,path))
    df = df.drop(columns=[' 0.21000000', ' 0.21000000.1', ' 0.20000000',
                                  ' 0.21000000.2', ' 2191845', '       0', ' 2191845.1', '       0.1',
                                  ' 0.21000000.3', ' 0.21000000.4', 'Technology', '              0',
                                  '  -99999999.000', '  -99999999.000.1', '  -99999999.000.2',
                                  '          0.000', '         460287'])
    df = df.rename(columns={'19980501': 'TradeDate',"28.00000000": 'Spot'})
    df['AdjSpot'] =  df.apply(lambda x:adjust_stock(x,sp="Spot"),axis=1)

    return df
def load_risk_free_rates():
    rate_list = []
    for f_pth in rate_files:
        df_r = pd.read_csv(os.path.join(base_path,f_pth))
        rate_list.append(df_r)
    
    for i,frame in enumerate(rate_list):
        cols = list(rate_list[i].columns)
        cols = [col.lower() for col in cols]
        cols_dict = {}
        for j in range(len(cols)):
            cols_dict[rate_list[i].columns[j]] = cols[j]
        rate_list[i] =  frame.rename(columns=cols_dict)
    df_r = pd.concat(rate_list, ignore_index=True) 
    df_r = df_r.drop(columns=['4 weeks bank discount','6 weeks bank discount','8 weeks bank discount',
                              '13 weeks bank discount','17 weeks bank discount',
                              '26 weeks bank discount','52 weeks bank discount']) 
    df_r.date = df_r.date.apply(lambda x:x.replace('-',"/"))
    df_r.date = df_r.date.apply(lambda x:date_formatting(x))  
    compute_continous_rate(df_r)
    df_r = df_r.drop(columns=['4 weeks coupon equivalent','6 weeks coupon equivalent','8 weeks coupon equivalent',
                              '13 weeks coupon equivalent','17 weeks coupon equivalent', '26 weeks coupon equivalent','52 weeks coupon equivalent',])
    df_r = df_r.sort_values("date", ascending=True)
    return df_r
    


def merge_data(path_options,path_stock):
    df = load_preprocess(path=path_options)
    df_spot = load_stock(path = path_stock)
    df = df.merge(df_spot, how='left', left_on='TradeDate', right_on='TradeDate')
    df = df.sort_values("TradeDate", ascending=True)
    # print(df.keys())
    
    # adjust non trade date expiries
    df['AdjExpiry'] = df['FmtExpiryDate']
    df.loc[df['AdjExpiry'].dt.weekday == 5, 'AdjExpiry'] -= pd.Timedelta(days=1)
    # good friday expiry
    df.loc[df.ExpiryDate==20140419,'AdjExpiry']-=pd.Timedelta(days=1)
    df["days_to_expiry"] = (df["AdjExpiry"] - df["FmtTradeDate"]).dt.days
    df['Month_To_Expiry'] = (df.AdjExpiry.dt.year - df.FmtTradeDate.dt.year) * 12 + (df.AdjExpiry.dt.month - df.FmtTradeDate.dt.month)
    df_spot["FmtTradeDate"] = pd.to_datetime(df_spot["TradeDate"], format="%Y%m%d")
    # merge spot at expiry with main data
    df = df.merge(df_spot, how='left', left_on='AdjExpiry', right_on='FmtTradeDate',
                  suffixes=('', '_expiry')).drop(columns=['FmtTradeDate_expiry','TradeDate_expiry',
                                                          'Spot_expiry']).rename(columns={'AdjSpot_expiry': 'ExpirySpot'})
    # spot at expiry for options expiring after last date in date is set to spot at last date redundant
    df['ExpirySpot'] = df['ExpirySpot'].fillna(df.iloc[-1]['Spot'])
    df_r = load_risk_free_rates()
    df = df.merge(df_r, how='left', left_on='TradeDate', right_on='date')
    df = df.drop(columns='date')
    # print(df.columns)
    df['px'] = (df.AskPrice+df.BidPrice)/2
    df['risk_free_rate'] = df.apply(lambda x:compute_risk_free_rate(x),axis=1)
    df['AdjExpiry'] = df.AdjExpiry.apply(lambda x :date_int_convertor(x))
    rfr_df = df[['TradeDate','risk_free_rate_4','risk_free_rate_6', 'risk_free_rate_8',
                 'risk_free_rate_13', 'risk_free_rate_17', 'risk_free_rate_26','risk_free_rate_52']]
    rfr_df = rfr_df.drop_duplicates()
    df = df.drop(columns=["FmtTradeDate","FmtExpiryDate",'risk_free_rate_4','risk_free_rate_6', 'risk_free_rate_8',
                          'risk_free_rate_13', 'risk_free_rate_17', 'risk_free_rate_26','risk_free_rate_52',
                          'BidPrice', 'AskPrice', 'BidImpliedVolatility','AskImpliedVolatility','LastTradePrice'])
    # df['D1'] = df.Delta
    df['Moneyness'] = round(100*(df.AdjStrike/df.AdjSpot),2)
    df['ImpliedVolatility']=df.apply(lambda x:compute_iv(x),axis=1)
    df['params'] = df.apply(lambda x: compute_greeks(x.CallPut,x.AdjSpot,x.days_to_expiry,x.risk_free_rate,x.AdjStrike,x.ImpliedVolatility),axis=1)
    for i,item in enumerate(['Delta', 'Gamma','Vega', 'Theta', 'Rho']):
        df[item] = df.params.apply(lambda x:round(x[i],10))
    df =df.drop(columns='params')
    df['Flag'] = 0
    df.to_csv(os.path.join(os.getcwd(),'Data','AAPL_master_data.csv'),index=False)
    rfr_df.to_csv(os.path.join(os.getcwd(),'Data','RiskFreeRates.csv'),index=False)
    df_spot.to_csv(os.path.join(os.getcwd(),'Data','AAPL_spot.csv'),index=False)
    return df


## comput ask_iv,bid_iv