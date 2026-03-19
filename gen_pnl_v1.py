import numpy as np
import pandas as pd
from data_prep import *
import os
from pandas.tseries.offsets import DateOffset, Week
import matplotlib.pyplot as plt
from data_extractor import *

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

def compute_contracts(x,df_cnt,capital):
    spot = x.SpotStart
    tradedate = x.TradeStart
    contracts = capital/(spot*df_cnt.loc[df_cnt.TradeStart==tradedate,'ActiveOptions'].values[0])
    
    return contracts

def compute_pnl(data,mt,bot_on,spot):
    multiplyer = 1   
    if data.CallPut.values[0] == "p":
        multiplyer = -1
    
    data_st = data[data.index==data.index[0]]
    data_end = data[data.index==data.index[1]]
    px_start = (data_st.AskPrice.values[0]+data_st.BidPrice.values[0])/2
    px_end = (data_end.AskPrice.values[0]+data_end.BidPrice.values[0])/2
                 
    if data_end.TradeDate.values[0]<= data_st.ExpiryDate.values[0]: 

        pnl =  (px_end-px_start)/px_start
    else:
        flag =1
        pnl = (max(multiplyer*(data_st.ExpirySpot.values[0]-data_st.AdjStrike.values[0]),0)-px_start)/px_start
    pnl = mt*pnl    

    data_st['BotOn']=bot_on
    data_st['TradeDate'] = data_end.TradeDate.values[0]
    data_st['Strike'] = data_end.AdjStrike.values[0]
    data_st['SpotStart'] = spot
    data_st['OptPxBot'] = px_start
    data_st['OptPxTrade'] = px_end
    data_st['SpotPct'] = (data_end.AdjSpot.values[0]-data_st.AdjSpot.values[0])/data_st.AdjSpot.values[0]
    data_st['OptPnl'] = pnl
    data_st['TradeStart'] = data_st.TradeDate.values[0]
       
        
    # pnl_frame = pd.DataFrame({'BotOn':BotOn,'Flag':Synth,'TradeDate':TradeDate,'Exp':Exp,'StrikeBot':StrikeBot,'SpotStart':SpotStart,
    #                           'Spot':Spot,'SpotExp':SpotExp, 'OptPxBot':OptPxBot,'OptPxTrade':OptPxTrade,'OptDelta':OptDelta,
    #                           'SpotPct':SpotPct,'OptPnl':OptPnl,'TradeStart':TradeStart})
    
    return data_st


def gen_options_pnl(df,moneyness = 100, time_to_expiry = 1,callput = 'p',bot =1,hold = 1, buysell = 'buy',capital = 10000000,
                    interpolator ='bicubic',symbool='EV',start_date = None,end_date= None):
    
    if buysell=='buy':
        mt =1
    else:
        mt=-1
    
    data_gen = DataExtractor(df,interpolator=interpolator,test=True)
    df_opt = data_gen.gen_data(moneyness = moneyness, time_to_expiry = time_to_expiry,callput = callput,bot =bot,hold=hold,
                               symbool=symbool,start_date =start_date,end_date= end_date)
    # df_opt['NextSpot'] = df_opt.Spot.shift(-1)
    # df_opt['NextSpot'] = df_opt['NextSpot'].ffill()
    # df_opt = df_opt.iloc[:-1]
    df_opt = df_opt[['Flag','TradeDate', 'ExpiryDate', 'CallPut', 'AdjStrike',
                     'AdjSpot','Month_To_Expiry', 'days_to_expiry', 'ExpirySpot',
                     'AdjExpiry', 'Moneyness', 'AbsMoneyness', 'Symbol',
                     'BidPrice', 'AskPrice', 'Delta', ]]
    if not end_date:
        last_date = np.sort(df[df.Symbol == symbool].TradeDate.unique())[-1]
    else:
        last_date = df[df.Symbol == symbool].TradeDate[df[df.Symbol == symbool].TradeDate<= end_date].max()
   
   
    option_accumulator = []
    flag = 0 
    for i in range(df_opt.shape[0]-1):
        
        
        data = df_opt.iloc[i:i+2]
        if data.AdjStrike.iloc[0]==data.AdjStrike.iloc[1] and data.AdjExpiry.iloc[0]==data.AdjExpiry.iloc[1]:
            if flag ==0:
                bot_on = data.TradeDate.iloc[0]
                spot = data.AdjSpot.iloc[0]
                flag = 1
            pnl_frame = compute_pnl(data,mt,bot_on,spot)
            
        else:
            flag = 0
            continue
        # ________
        if data.TradeDate.values[0] == last_date: # redundant
            break
        
        option_accumulator.append(pnl_frame)
    df_opt = pd.concat(option_accumulator, ignore_index=True)
    
        
    df_op = df_opt[['Flag','BotOn', 'TradeDate', 'ExpiryDate', 'CallPut', 'AdjStrike', 'AdjSpot',
                     'ExpirySpot','Symbol',  'OptPxBot', 'OptPxTrade', 'SpotPct','Delta',
                     'Strike', 'SpotStart','OptPnl', 'TradeStart']]
    df_op = df_op.rename(columns ={'AdjSpot':'Spot','AdjStrike':'Strike','ExpirySpot':'Spot_at_Expiry'})
    df_active_contracts  = (df_op.groupby('TradeStart').size().reset_index(name='ActiveOptions'))
    df_op ['NumOfContracts'] = df_op.apply(lambda x: compute_contracts(x,df_active_contracts,capital),axis=1)
    df_op = df_op.drop(columns =['TradeStart'])
    return df_op
    

    
def wealth_computation(df,nav =1000,sizing ='notional',pct = 1,contract_size =100,value = 1,hold=1,):
    opt_df = df.copy()
    if sizing == 'notional':
        opt_df['OptPnlNotional'] = (df.OptPxBot*df.OptPnl/df.Spot)*value  # value no of options 
        
    elif sizing == 'premium':
        opt_df['OptPnlPremium'] = (df.OptPnl)*pct/100
   
    elif sizing == 'contracts': 
        opt_df['OptPnlContracts'] =df.OptPnl*df.OptPxBot*contract_size*value # value no of contracts
        
    # hold
    
    
    if hold==1:
        if sizing =='notional':
            opt_df['Wealth']  = nav*(1 + df['OptPnlNotional']).cumprod()
        elif sizing =='premium':
            #df['OptPnlPremium'] = df['OptPnlPremium'].replace([np.inf, -np.inf], 0,)
            opt_df['Wealth']  = nav*(1 + df['OptPnlPremium']).cumprod()
            
        elif sizing == 'contracts':
            opt_df['CumPnL'] = df['OptPnlContracts'].cumsum()
            opt_df['Wealth'] = nav + df['CumPnL']
            # df['r_t'] = df['CumPnL'] / df['NAV'].shift(1)
            # df.loc[0,'r_t'] = df['CumPnL'].iloc[0]/nav
            # df['wealth'] = nav * (1 + df['r_t']).cumprod()
        return df
       
    else : 
        
        if sizing =='notional':
            agg_pnl = opt_df.groupby(by='TradeDate').OptPnlNotional.sum()
            wealth  = nav*(1 + agg_pnl).cumprod()
            df_w = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'Wealth':wealth})).reset_index()
        elif sizing =='premium':
            #df['OptPnlPremium'] = df['OptPnlPremium'].replace([np.inf, -np.inf], 0,)
            agg_pnl = opt_df.groupby(by='TradeDate').OptPnlPremium.sum()
            wealth  = nav*(1 + agg_pnl).cumprod()
            df_w = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'Wealth':wealth})).reset_index()
        elif sizing == 'contracts':
            agg_pnl =opt_df.groupby(by='TradeDate').OptPnlContracts.sum()
            cumpnl = agg_pnl.cumsum()
            wealth = nav+cumpnl
            df_w = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'CumPnl':cumpnl,'Wealth':wealth})).reset_index()

        return opt_df,df_w
    



       
        


