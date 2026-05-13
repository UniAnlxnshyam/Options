import numpy as np
import pandas as pd
from . import data_prep
import os
from pandas.tseries.offsets import DateOffset, Week
import matplotlib.pyplot as plt
from .data_extractor_v3 import DataExtractor as DataExtractor
from .connector import *
from py_vollib.black_scholes.greeks.analytical import delta as delta_computation
from py_vollib_vectorized import vectorized_delta
import time

# def get_premium(df,flag,stk,date,exp_date,interpolator = 'bicubic'):
#     data = extract_clean_data(df,flag = flag,trade_date=date)
#     surface_genrator = GenSurface(data,interpolator=interpolator)
#     surface_genrator.update_surface()
#     # print(date)
#     fwd_mnyness = surface_genrator.fwd_moneyness()
#     x,y= surface_genrator.known_data()
#     surface_genrator.gen_spline()
#     # surface_genrator.abs_error(x,y,z)
#     adj_spot = df[df.TradeDate==date].AdjSpot.iloc[0]
#     # print(exp_date)
#     days_to_expiry = (pd.to_datetime(exp_date,format="%Y%m%d")-pd.to_datetime(date, format="%Y%m%d")).days
#     # print("days",days_to_expiry)
#     x = df[df.TradeDate==date].iloc[0]
#     x.loc['days_to_expiry']=days_to_expiry
#     risk_free_rate = compute_risk_free_rate(x)
#     px,delta,gama,vega,theta,rho = surface_genrator.compute_px(flag,adj_spot,days_to_expiry,risk_free_rate,stk)
#     return px,delta
def fetch_from_db(trade_date):
            
    conn, cursor = get_db()
    cursor.execute('USE test_db')
    cursor.execute(f'SELECT AdjSpot FROM AAPL_SPOT Where TradeDate={trade_date}')
    closing_spot = cursor.fetchone()[0]        
    cursor.close()
    conn.close()
    return closing_spot

def compute_contracts(x,df_cnt,capital):
    spot = x.SpotStart
    tradedate = x.TradeStart
    contracts = capital/(spot*df_cnt.loc[df_cnt.TradeStart==tradedate,'ActiveOptions'].values[0])
    
    return contracts

def stock_pnl(data_st,spot_end,stock=None,iv=None):
    days = 365
    spot_start = data_st.AdjSpot.values[0]
    
    
    dh_inception = stock*(spot_end-spot_start)
    
    
    
    delta_start = delta_computation(data_st.CallPut.values[0],data_st.AdjSpot.values[0],data_st.AdjStrike.values[0],
                                    data_st.days_to_expiry.values[0]/days,data_st.risk_free_rate.values[0],iv)            
    dh_inception_vol = -delta_start*(spot_end-spot_start)
    dh_market_vol = -data_st.Delta*(spot_end-spot_start)
            
    return dh_inception,dh_inception_vol,dh_market_vol

def compute_pnl(data,mt,bot_on,spot,px_trade_start,multiplyer,dh='off',stock = None,iv= None):
    
    data_st = data[data.index==data.index[0]]
    data_st = data_st.copy()
    data_end = data[data.index==data.index[1]]
    px_start = data_st.px.values[0]
    px_end = data_end.px.values[0]
                 
    if data_end.TradeDate.values[0]< data_st.AdjExpiry.values[0]: 
        data_st['OptPxTrade'] = px_end
        
    else:
        data_st['OptPxTrade'] =max(multiplyer*(data_st.ExpirySpot.values[0]-data_st.AdjStrike.values[0]),0)
        

    pnl =  (px_end-px_start)/px_start
    pnl = mt*pnl    

    data_st['BotOn']=bot_on
    data_st['PxStart'] = px_trade_start
    data_st['TradeDate'] = data_end.TradeDate.values[0]
    data_st['Strike'] = data_end.AdjStrike.values[0]
    data_st['SpotStart'] = spot
    data_st['OptPxBot'] = px_start
    
    data_st['SpotPct'] = (data_end.AdjSpot.values[0]-data_st.AdjSpot.values[0])/data_st.AdjSpot.values[0]
    data_st['OptPnl'] = pnl
    # data_st['TradeStart'] = data_st.TradeDate.values[0]
    
    if dh!= 'off':
        dhi,dhiv,dhmv = stock_pnl(data_st,data_end.AdjSpot.values[0],stock=stock,iv=iv)
        data_st['dhi'] =pnl+dhi/px_start
        data_st['dhiv'] =pnl+dhiv/px_start
        data_st['dhmv'] =pnl+dhmv/px_start
    # data_st = data_st.drop(columns =['AdjStrike','px','days_to_expiry'])
    
    return data_st
def compute_pnl_v1(data,mt,bot_on,spot,px_trade_start,imp_vol):
    
   
                 
    # if data_end.TradeDate.values[0]< data_st.AdjExpiry.values[0]: 
    data['OptPxTrade'] = data['px'].shift(-1)
    data['TradeDate'] = data['TradeDate'].shift(-1)
    data['OptPxBot'] = data['px']
    data['OptPnl'] = mt*(data['OptPxTrade']-data['px'])/data['px']
    data['SpotEnd'] = data.AdjSpot.shift(-1)
    data['SpotPct'] = (data.AdjSpot.shift(-1)-data.AdjSpot)/data.AdjSpot
    
    data = data.dropna()
        
    
    data['BotOn']=data['TradeStart']
    data['PxStart'] = px_trade_start
    
    data['Strike'] = data.AdjStrike
    data['SpotStart'] = spot
    data['iv_start'] = imp_vol
    data['TradeDate'] = data['TradeDate'].astype(int)
    return data


def gen_options_pnl(data_path = 'AAPL_master_data.csv',rates_path = 'RiskFreeRates.csv',moneyness = 100,delta = None,bydelta=False, time_to_expiry = 1,callput = 'p',bot =1,hold = 1, buysell = 'buy',
                    interpolator ='bicubic',symbool='EV',start_date = None,end_date= None,dh='off'):
    
    
    if buysell=='buy':
        mt =1
    else:
        mt =-1
    if bydelta:
        var ='delta'
        val = delta
    else:
        var ='mn'
        val = moneyness
    # opt_key = f'{var}_{val}_{callput}_{symbool}_{time_to_expiry}'
    

   
       
    data_gen = DataExtractor(interpolator=interpolator,data_path = data_path,rates_path = rates_path,symbool = symbool,callput =callput,delta = delta,mn = moneyness,expiry=time_to_expiry)
    
    data_dict = data_gen.gen_data(moneyness = moneyness,delta = delta, bydelta=bydelta,time_to_expiry = time_to_expiry,callput = callput,bot =bot,hold=hold,
                                symbool=symbool,start_date =None,end_date= None)
    df_opt = data_dict['df_options']

    df_opt = df_opt[['TradeDate','AdjExpiry', 'AdjStrike',
                     'AdjSpot', 'ExpirySpot','Moneyness','px', 'Delta',
                     'CallPut', 'Symbol','Flag','TradeStart','ImpliedVolatility','days_to_expiry','risk_free_rate']]
    
    dates = np.sort(data_gen.df.TradeDate.unique())
    if not end_date:
        last_date = dates[-1]
        last_trade = dates[-2]
    else:
        
        last_date = dates[dates<= end_date][-1]
        last_trade = dates[dates<= end_date][-2]
    # print(last_date,last_trade)
   
    option_accumulator = []
    flag = 0 
    date_group = dict(tuple(df_opt.groupby('TradeStart')))
    multiplyer = 1 
    if callput == "p":
        multiplyer = -1
    for k,v in date_group.items():
        # for delta hedging (dh)
        imp_vol = v.ImpliedVolatility.iloc[0]
        
        stock = -v.Delta.iloc[0]
        if k == last_date: # redundant
            break
        spot_start = v[v.TradeDate==k].AdjSpot.values[0]
        px_trade_start = v[v.TradeDate==k].px.values[0]
        
        if v.shape[0]==1 and (k== last_trade or hold==1):
            data_st = v
            
            
            # expiry spot only for expiry otherwise spot, remove expiry spot use spot from spot data and also overcome nans.
            trade_date = dates[dates>data_st.TradeDate.values[0]][0]
            if trade_date>=v.AdjExpiry.iloc[-1]:
                closing_spot = v.ExpirySpot.iloc[-1]
            else:
                closing_spot = fetch_from_db(trade_date)

            px_start = data_st.px.values[0]
            
            data_st['BotOn']=k

            data_st['TradeDate'] =trade_date
            data_st['Strike'] = data_st.AdjStrike.values[0]
            data_st['SpotStart'] = spot_start
            data_st['PxStart'] = px_trade_start
            data_st['AdjSpot'] = spot_start 
            data_st['OptPxBot'] = px_start
            data_st['Delta'] = 0
            px_end = max(multiplyer*(closing_spot-data_st.AdjStrike.values[-1]),0)
            data_st['OptPxTrade'] = px_end
            pnl = (px_end-px_start)/px_start
            pnl = mt*pnl 
            data_st['SpotPct'] = (data_gen.df[data_gen.df.TradeDate ==data_st.TradeDate.values[0]].AdjSpot.iloc[0]-data_st.AdjSpot.values[0])/data_st.AdjSpot.values[0]###
            data_st['OptPnl'] = pnl
            data_st = data_st.drop(columns =['AdjStrike','px'])
            option_pnl = data_st
            if dh!= 'off':
                dhi,dhiv,dhmv = stock_pnl(data_st,v.ExpirySpot.iloc[-1],stock=stock,iv=imp_vol)
                data_st['dhi'] =pnl+dhi/px_start
                data_st['dhiv'] =pnl+dhiv/px_start
                data_st['dhmv'] =pnl+dhmv/px_start
            



        else:
            option_data = []
            
            for i in range(v.shape[0]-1):  
                
                    
                
                data = v.iloc[i:i+2]        
                pnl_frame = compute_pnl(data,mt,k,spot_start,px_trade_start,multiplyer,dh=dh,iv=imp_vol,stock=stock)                  
                option_data.append(pnl_frame)
            option_pnl = pd.concat(option_data, ignore_index=True)
       
        if option_pnl.shape[0]< hold and option_pnl.TradeDate.iloc[-1]<v.AdjExpiry.iloc[-1] and option_pnl.TradeDate.iloc[-1]<=last_trade:

                

            data_st = option_pnl.iloc[[-1]]
            
            trade_date = dates[dates>data_st.TradeDate.values[0]][0]
            if trade_date>=v.AdjExpiry.iloc[-1]:
                closing_spot = v.ExpirySpot.iloc[-1]
            else:
                closing_spot = fetch_from_db(trade_date)
            
            trade_start = data_st.TradeDate.values[0]
            px_start = data_st.OptPxTrade.values[0]
            px_end = max(multiplyer*(closing_spot-data_st.Strike.values[-1]),0)
            pnl = (px_end-px_start)/px_start
            pnl = mt*pnl 
            data_st['BotOn']=k
            data_st['PxStart'] = px_trade_start
            data_st['TradeDate'] = trade_date
            
            data_st['AdjSpot'] = data_gen.df[data_gen.df.TradeDate ==trade_start].AdjSpot.iloc[0]
            data_st['Strike'] = data_st.Strike.values[0]
            data_st['Delta'] = 0
            data_st['SpotStart'] = spot_start
            data_st['OptPxBot'] = px_start
            data_st['OptPxTrade'] = px_end
            if dh!= 'off':
                dhi,dhiv,dhmv = stock_pnl(data_st,v.ExpirySpot.iloc[-1],stock=stock,iv=imp_vol)
                data_st['dhi'] =pnl+dhi/px_start
                data_st['dhiv'] =pnl+dhiv/px_start
                data_st['dhmv'] =pnl+dhmv/px_start
            # used sorting
            try:
                data_st['SpotPct'] = (data_gen.df[data_gen.df.TradeDate ==trade_date].AdjSpot.iloc[0]-data_st['AdjSpot'].values[0])/data_st['AdjSpot']
            except Exception as e:
                print(data_st)
            data_st['OptPnl'] = pnl
            option_pnl = pd.concat([option_pnl,data_st], ignore_index=True)
            
                

        # ________
        
        
        option_accumulator.append(option_pnl)
    df_opt = pd.concat(option_accumulator, ignore_index=True)
    if dh =='off':
        cols = ['Flag','BotOn', 'TradeDate', 'AdjExpiry', 'Strike', 'AdjSpot',
                'ExpirySpot','OptPxBot', 'OptPxTrade', 'SpotPct','Delta',
                'SpotStart','OptPnl','TradeStart','PxStart']
    else : 
         cols = ['Flag','BotOn', 'TradeDate', 'AdjExpiry', 'Strike', 'AdjSpot',
                'ExpirySpot','OptPxBot', 'OptPxTrade', 'SpotPct','Delta',
                'SpotStart','OptPnl','dhi','dhiv','dhmv','TradeStart','PxStart']

        
    df_op = df_opt[cols]
    df_op = df_op.rename(columns ={'AdjSpot':'Spot','AdjExpiry':'ExpiryDate','ExpirySpot':'Spot_at_Expiry'})
    # df_active_contracts  = (df_op.groupby('TradeStart').size().reset_index(name='ActiveOptions'))
    # df_op ['NumOfContracts'] = df_op.apply(lambda x: compute_contracts(x,df_active_contracts,capital),axis=1)
    # df_op = df_op.drop(columns =['TradeStart'])
   
    return df_op

def gen_options_pnl_v1(data_path = 'AAPL_master_data.csv',rates_path = 'RiskFreeRates.csv',moneyness = 100,delta = None,bydelta=False, time_to_expiry = 1,callput = 'p',bot =1,hold = 1, buysell = 'buy',
                    interpolator ='bicubic',symbool='EV',start_date = None,end_date= None,dh='off'):
    
    
    if buysell=='buy':
        mt =1
    else:
        mt =-1
   
   
    data_gen = DataExtractor(interpolator=interpolator,data_path = data_path,rates_path = rates_path,symbool = symbool,callput =callput,delta = delta,mn = moneyness,expiry=time_to_expiry)
    
    data_dict = data_gen.gen_data(moneyness = moneyness,delta = delta, bydelta=bydelta,time_to_expiry = time_to_expiry,callput = callput,bot =bot,hold=hold,
                                symbool=symbool,start_date =start_date,end_date= end_date)
    df_opt = data_dict['df_options']

    df_opt = df_opt[['TradeDate','AdjExpiry', 'AdjStrike',
                     'AdjSpot', 'ExpirySpot','Moneyness','px', 'Delta',
                     'CallPut', 'Symbol','Flag','TradeStart','ImpliedVolatility','days_to_expiry','risk_free_rate']]
    
    dates = np.sort(data_gen.df.TradeDate.unique())
    if not end_date:
        last_date = dates[-1]
        last_trade = dates[-2]
    else:
        
        last_date = dates[dates<= end_date][-1]
        last_trade = dates[dates<= end_date][-2]
    # print(last_date,last_trade)
   
    option_accumulator = []
    flag = 0 
    date_group = dict(tuple(df_opt.groupby('TradeStart')))
    multiplyer = 1 
    if callput == "p":
        multiplyer = -1

    
    for k,v in date_group.items():
        # for delta hedging (dh)
        imp_vol = v.ImpliedVolatility.iloc[0]
        
        stock = -v.Delta.iloc[0]
        if k == last_date: # redundant
            break
        spot_start = v[v.TradeDate==k].AdjSpot.values[0]
        px_trade_start = v[v.TradeDate==k].px.values[0]
        
        if v.shape[0]==1 and (k== last_trade or hold==1):
            
            data = v
            # expiry spot only for expiry otherwise spot, remove expiry spot use spot from spot data and also overcome nans.
            trade_date = dates[dates>data_st.TradeDate.values[0]][0]
            if trade_date>=v.AdjExpiry.iloc[-1]:
                closing_spot = v.ExpirySpot.iloc[-1]
            else:
                closing_spot = fetch_from_db(trade_date)

            px_start = data_st.px.values[0]
            
            data['BotOn']=data['TradeStart']

            data['TradeDate'] =trade_date
            data['Strike'] = data.AdjStrike
            data['SpotStart'] = spot_start
            data['PxStart'] = px_trade_start 
            data['OptPxBot'] = data['px']
            # data['Delta'] = 0
            px_end = max(multiplyer*(closing_spot-data.AdjStrike.values[-1]),0)
            data['OptPxTrade'] = px_end
            pnl = (px_end-px_start)/px_start
            pnl = mt*pnl 
            data['SpotPct'] = (data_gen.df[data_gen.df.TradeDate ==data.TradeDate.values[0]].AdjSpot.iloc[0]-data.AdjSpot.values[0])/data.AdjSpot.values[0]###
            data['OptPnl'] = pnl
            data['SpotEnd'] = closing_spot
            data['iv_start'] = imp_vol
            # data_st = data_st.drop(columns =['AdjStrike','px'])
            option_pnl = data
    
        else:
           
            option_pnl = compute_pnl_v1(v,mt,k,spot_start,px_trade_start,imp_vol)  
       
        if option_pnl.shape[0]< hold and option_pnl.TradeDate.iloc[-1]<v.AdjExpiry.iloc[-1] and option_pnl.TradeDate.iloc[-1]<=last_trade:


            data_st = option_pnl.iloc[[-1]]
            
            trade_date = dates[dates>data_st.TradeDate.values[0]][0]
            if trade_date>=v.AdjExpiry.iloc[-1]:
                closing_spot = v.ExpirySpot.iloc[-1]
            else:
                closing_spot = fetch_from_db(trade_date)
            
            #trade_start = data_st.TradeDate.values[0]
            px_start = data_st.OptPxTrade.values[0]
            px_end = max(multiplyer*(closing_spot-data_st.Strike.values[-1]),0)
            pnl = (px_end-px_start)/px_start
            pnl = mt*pnl 
            data_st['BotOn']=k
            data_st['PxStart'] = px_trade_start
            data_st['TradeDate'] = trade_date
            
            #data_st['AdjSpot'] = data_gen.df[data_gen.df.TradeDate ==trade_start].AdjSpot.iloc[0]
            data_st['Strike'] = data_st.Strike.values[0]
            # data_st['Delta'] = 0
            data_st['SpotStart'] = spot_start
            data_st['OptPxBot'] = px_start
            data_st['OptPxTrade'] = px_end
            data_st['iv_start'] = imp_vol
          
            try:
                data_st['SpotPct'] = (data_gen.df[data_gen.df.TradeDate ==trade_date].AdjSpot.iloc[0]-data_st['AdjSpot'].values[0])/data_st['AdjSpot']
            except Exception as e:
                print(data_st)
            data_st['OptPnl'] = pnl
            data_st['SpotEnd'] = closing_spot
            option_pnl = pd.concat([option_pnl,data_st], ignore_index=True)
            
        option_accumulator.append(option_pnl)
        
    df_opt = pd.concat(option_accumulator, ignore_index=True)
    if dh!= 'off':
                
        df_opt['dhi'] =df_opt['OptPnl']+(stock*(df_opt['SpotEnd']-df_opt['AdjSpot'])/df_opt['OptPxBot'])
        
        df_opt['Delta_Start'] =  vectorized_delta(flag=df_opt['CallPut'],
                                                        S=df_opt['AdjSpot'],
                                                        K=df_opt['AdjStrike'],
                                                        t=df_opt['days_to_expiry']/365,
                                                        r=df_opt['risk_free_rate'],
                                                        sigma=df_opt['iv_start'],
                                                        model='black_scholes')
        df_opt['dhiv'] =df_opt['OptPnl']+(df_opt['Delta_Start']*(df_opt['SpotEnd']-df_opt['AdjSpot'])/df_opt['OptPxBot'])
        df_opt['dhmv'] =df_opt['OptPnl']+(df_opt['Delta']*(df_opt['SpotEnd']-df_opt['AdjSpot'])/df_opt['OptPxBot'])  
                
    
    if dh =='off':
        cols = ['Flag','BotOn', 'TradeDate', 'AdjExpiry', 'Strike', 'AdjSpot',
                'ExpirySpot','OptPxBot', 'OptPxTrade', 'SpotPct','Delta',
                'SpotStart','OptPnl','TradeStart','PxStart']
    else : 
         cols = ['Flag','BotOn', 'TradeDate', 'AdjExpiry', 'Strike', 'AdjSpot',
                'ExpirySpot','OptPxBot', 'OptPxTrade', 'SpotPct','Delta',
                'SpotStart','OptPnl','dhi','dhiv','dhmv','TradeStart','PxStart','Delta_Start','iv_start','CallPut','AdjStrike','days_to_expiry','risk_free_rate']

        
    df_op = df_opt[cols]
    df_op = df_op.rename(columns ={'AdjSpot':'Spot','AdjExpiry':'ExpiryDate','ExpirySpot':'Spot_at_Expiry'})
    
    return df_op
    

    
def wealth_computation(df,sizing ='notional',pct = 1,num_contracts =1000,contract_size = 1,bot =1,hold=1,init_cap = 1000000,dh = 'off',value = 1):
    capital = init_cap*(bot/hold)
    
    opt_df = df.copy()
    if sizing == 'notional':
        capital = value*capital

        opt_df['NumContracts'] = capital/(contract_size*opt_df['SpotStart'])
        opt_df['OptPnlNotional'] = contract_size*opt_df.NumContracts*(opt_df.OptPxBot*opt_df.OptPnl)
        agg_pnl = opt_df.groupby(by='TradeDate').OptPnlNotional.sum()        
        wealth  = init_cap+agg_pnl.cumsum()
       
        if dh!='off':
            opt_df['dhi_PnlNotional'] = contract_size*opt_df.NumContracts*(opt_df.OptPxBot*opt_df.dhi)
            agg_pnl_dhi = opt_df.groupby(by='TradeDate').dhi_PnlNotional.sum()
            wealth_dhi  = init_cap+agg_pnl_dhi.cumsum()
            opt_df['dhiv_PnlNotional'] = contract_size*opt_df.NumContracts*(opt_df.OptPxBot*opt_df.dhiv)
            agg_pnl_dhiv = opt_df.groupby(by='TradeDate').dhiv_PnlNotional.sum()
            wealth_dhiv  = init_cap+agg_pnl_dhiv.cumsum()
            opt_df['dhmv_PnlNotional'] = contract_size*opt_df.NumContracts*(opt_df.OptPxBot*opt_df.dhmv)
            agg_pnl_dhmv = opt_df.groupby(by='TradeDate').dhmv_PnlNotional.sum()
            wealth_dhmv  = init_cap+agg_pnl_dhmv.cumsum()
            
            df_w = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'Wealth':wealth,'AggPNL_DHI':agg_pnl_dhi,'Wealth_DHI':wealth_dhi,'AggPNL_DHIV':agg_pnl_dhiv,'Wealth_DHIV':wealth_dhiv,
                                  'AggPNL_DHMV':agg_pnl_dhmv,'Wealth_DHMV':wealth_dhmv})).reset_index()
        else:
            df_w = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'Wealth':wealth})).reset_index()
        
    elif sizing == 'premium':
        capital = (capital*pct/100)*bot/12
        opt_df['NumContracts'] = capital/(contract_size*opt_df['PxStart'])
        opt_df['OptPnlPremium'] = contract_size*opt_df.NumContracts*(opt_df.OptPxBot*opt_df.OptPnl)
        agg_pnl = opt_df.groupby(by='TradeDate').OptPnlPremium.sum()
        wealth  = init_cap+agg_pnl.cumsum()
        df_w = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'Wealth':wealth})).reset_index()
        if dh!='off':
            opt_df['dhi_PnlNotional'] = contract_size*opt_df.NumContracts*(opt_df.OptPxBot*opt_df.dhi)
            agg_pnl_dhi = opt_df.groupby(by='TradeDate').dhi_PnlNotional.sum()
            wealth_dhi  = init_cap+agg_pnl_dhi.cumsum()
            opt_df['dhiv_PnlNotional'] = contract_size*opt_df.NumContracts*(opt_df.OptPxBot*opt_df.dhiv)
            agg_pnl_dhiv = opt_df.groupby(by='TradeDate').dhiv_PnlNotional.sum()
            wealth_dhiv  = init_cap+agg_pnl_dhiv.cumsum()
            opt_df['dhmv_PnlNotional'] = contract_size*opt_df.NumContracts*(opt_df.OptPxBot*opt_df.dhmv)
            agg_pnl_dhmv = opt_df.groupby(by='TradeDate').dhmv_PnlNotional.sum()
            wealth_dhmv  = init_cap+agg_pnl_dhmv.cumsum()
            df_w = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'Wealth':wealth,'AggPNL_DHI':agg_pnl_dhi,'Wealth_DHI':wealth_dhi,'AggPNL_DHIV':agg_pnl_dhiv,'Wealth_DHIV':wealth_dhiv,
                                  'AggPNL_DHMV':agg_pnl_dhmv,'Wealth_DHMV':wealth_dhmv})).reset_index()
        else:
            df_w = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'Wealth':wealth})).reset_index()
   
    elif sizing == 'contracts': 
        opt_df['OptPnlContracts'] =contract_size*opt_df.OptPnl*opt_df.OptPxBot*num_contracts # value no of contracts
        opt_df['NumContracts'] = num_contracts
        agg_pnl =opt_df.groupby(by='TradeDate').OptPnlContracts.sum()
        wealth = init_cap+agg_pnl.cumsum()
        
    
        if dh!='off':
            opt_df['dhi_PnlNotional'] = contract_size*opt_df.NumContracts*(opt_df.OptPxBot*opt_df.dhi)
            agg_pnl_dhi = opt_df.groupby(by='TradeDate').dhi_PnlNotional.sum()
            wealth_dhi  = init_cap+agg_pnl_dhi.cumsum()
            opt_df['dhiv_PnlNotional'] = contract_size*opt_df.NumContracts*(opt_df.OptPxBot*opt_df.dhiv)
            agg_pnl_dhiv = opt_df.groupby(by='TradeDate').dhiv_PnlNotional.sum()
            wealth_dhiv  = init_cap+agg_pnl_dhiv.cumsum()
            opt_df['dhmv_PnlNotional'] = contract_size*opt_df.NumContracts*(opt_df.OptPxBot*opt_df.dhmv)
            agg_pnl_dhmv = opt_df.groupby(by='TradeDate').dhmv_PnlNotional.sum()
            wealth_dhmv  = init_cap+agg_pnl_dhmv.cumsum()
            df_w = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'Wealth':wealth,'AggPNL_DHI':agg_pnl_dhi,'Wealth_DHI':wealth_dhi,'AggPNL_DHIV':agg_pnl_dhiv,'Wealth_DHIV':wealth_dhiv,
                                  'AggPNL_DHMV':agg_pnl_dhmv,'Wealth_DHMV':wealth_dhmv})).reset_index()
        else:
            df_w = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'Wealth':wealth})).reset_index()

    return opt_df,df_w
    



       
        


