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
    spot = x.Spot
    tradedate = x.TradeStart
    contracts = capital/(spot*df_cnt.loc[df_cnt.TradeStart==tradedate,'ActiveOptions'].values[0])
    
    return contracts

def compute_pnl(df,data,hold,mt,interpolator = 'bicubic'):
    BotOn=[]
    TradeDate = []
    Exp = []
    StrikeBot = []
    SpotStart = []
    Spot = []
    OptPxBot = []
    OptPxTrade = []
    OptDelta = []
    SpotPct = []
    OptPnl = []
    SpotExp = []
    TradeStart = []
    Synth = []
    f1 = 0
    df_iv = df[(df.AdjExpiry ==data.AdjExpiry.values[0])&(df.CallPut==data.CallPut.values[0])&(df.AdjStrike==data.AdjStrike.values[0])&(df.Symbol==data.Symbol.values[0])]
    
    if len(df_iv)==0:
         df_iv = data
         f1 = 1
        
    dates = np.sort(df[df.Symbol == data.Symbol.values[0]].TradeDate.unique())
    last_trade_date = dates[-1]
    idx = np.where(dates==data['TradeDate'].values)[0][0]
    
    
    multiplyer = 1   
    if data.CallPut.values[0] == "p":
        multiplyer = -1
    flag = 0
    
    for j in range(hold):
        
        if dates[idx+j] == dates[-1]:
            break
        strike = data.AdjStrike.values[0]
        spot_start = data.AdjSpot.values[0]
        spot = df[df.TradeDate==dates[idx+j]]['AdjSpot'].iloc[0]
        next_spot = df.loc[df['TradeDate'] == dates[idx+j+1],'AdjSpot'].iloc[0]
        exp_dt = data.ExpiryDate.values[0]
            
        if dates[idx+j] not in df_iv.TradeDate.to_list() and dates[idx+j]<data.ExpiryDate.values[0]:
            if j == 0:

                delta = data['Delta'].values[0]
                px = (data['AskPrice'].values[0]+data['BidPrice'].values[0])/2
            else: 

                px = nextpx                
                delta = nextdelta
        else:
            delta = df_iv[df_iv.TradeDate==dates[idx+j]]['Delta'].iloc[0]
            px = (df_iv[df_iv.TradeDate==dates[idx+j]]['AskPrice'].iloc[0]+df_iv[df_iv.TradeDate==dates[idx+j]]['BidPrice'].iloc[0])/2     
        print(data.ExpiryDate.values[0])
        if dates[idx+j+1] not in df_iv.TradeDate.to_list() and dates[idx+j+1]<data.ExpiryDate.values[0]: 

            print(f'option with exp date {exp_dt} and strike  {strike}  not traded on {dates[idx+j+1]}')
            # delta = data.Delta.values[0]
            nextpx,nextdelta = get_premium(df,data.CallPut.values[0],data.AdjStrike.values[0],dates[idx+j+1],data.ExpiryDate.values[0],interpolator=interpolator)
                    
            f1 =1
             
        
        elif dates[idx+j+1]<data.ExpiryDate.values[0]:
        
            nextpx = (df_iv[df_iv.TradeDate==dates[idx+j+1]]['AskPrice'].values[0]+df_iv[df_iv.TradeDate==dates[idx+j+1]]['BidPrice'].values[0])/2
            nextdelta = df_iv[df_iv.TradeDate==dates[idx+j+1]]['Delta'].values[0]
            
                
        else:
                 
            nextpx = 0
            nextdelta = 0
                 
        if dates[idx+j+1]<= data.ExpiryDate.values[0]:
            # next_date_optpx = (df_iv[df_iv.TradeDate==dates[idx+j+1]]['AskPrice'].values[0]+df_iv[df_iv.TradeDate==dates[idx+j+1]]['BidPrice'].values[0])/2
            pnl =  (nextpx-px)/px
        else:
            flag =1
            pnl = (max(multiplyer*(data.ExpirySpot.values[0]-strike),0)-px)/px
        pnl = mt*pnl    

            # to be reviewed
            # elif j==hold-1:
            #     OptPx.append(OptPx[-1])
            #     OptDelta.append(OptDelta[-1])
                
            #     SpotPct.append(SpotPct[-1])
            #     if TradeDate[-1]<= data.ExpiryDate:
            #         spot = df.loc[df['TradeDate'] == TradeDate[-1],'Spot'].values[0]
            #         pnl = max(multiplyer*(spot-StrikeBot[-1]),0)-OptPx[-1]
            #     else:
            #         pnl = max(multiplyer*(data.ExpirtSpot-StrikeBot[-1]),0)-OptPx[-1]
        SpotPct.append((next_spot - spot)/spot)

        OptDelta.append(delta)         
        Spot.append(spot)          
        OptPxBot.append(px)
        OptPxTrade.append(nextpx)
        Exp.append(data.ExpiryDate.values[0])
        BotOn.append(data.TradeDate.values[0])
        TradeDate.append(dates[idx+j+1])
        SpotStart.append(spot_start)
        StrikeBot.append(strike)
        SpotExp.append(data.ExpirySpot.values[0])
        TradeStart.append(dates[idx+j])
        OptPnl.append(pnl)
        Synth.append(f1)
        f1= 0
        if TradeDate[-1] == last_trade_date:

            flag =1        


        if flag:
             
             break
        
    pnl_frame = pd.DataFrame({'BotOn':BotOn,'Flag':Synth,'TradeDate':TradeDate,'Exp':Exp,'StrikeBot':StrikeBot,'SpotStart':SpotStart,
                              'Spot':Spot,'SpotExp':SpotExp, 'OptPxBot':OptPxBot,'OptPxTrade':OptPxTrade,'OptDelta':OptDelta,
                              'SpotPct':SpotPct,'OptPnl':OptPnl,'TradeStart':TradeStart})
    
    return pnl_frame


def gen_options_pnl(df,moneyness = 100, time_to_expiry = 1,callput = 'p',bot =1,hold = 1, buysell = 'buy',
                    value = 1,sizing = "notional",interpolator ='bicubic',pct = 1,contract_size =100,symbool='EV',start_date = None,end_date= None):
    capital = 10000000
    if buysell=='buy':
        mt =1
    else:
        mt=-1
    df_opt=extract_data(df,expiry_in_months=time_to_expiry,moneyness=moneyness,callput=callput,hold =hold,symbool=symbool,
                        start_date = start_date,end_date= end_date,bot=bot,interpolator = interpolator)
    df_opt['NextSpot'] = df_opt.Spot.shift(-1)
    df_opt['NextSpot'] = df_opt['NextSpot'].ffill()
    df_opt = df_opt.iloc[:-1]
    # df_opt['IV'] = (df.AskImpliedVolatility + df.BidImpliedVolatility)/2
    last_date = np.sort(df[df.Symbol == symbool].TradeDate.unique())[-1]
    # df_opt['delta_IV'] = df_opt.apply(lambda x:compute_delta_iv(x),axis =1)
   
    option_accumulator = []
    for i in range(df_opt.shape[0]):
        
        
        data = df_opt[df_opt.index==i]
        
        if data.TradeDate.values[0] == last_date: # redundant
            break
        pnl_frame = compute_pnl(data,hold,mt,interpolator=interpolator)
        option_accumulator.append(pnl_frame)
    df_op = pd.concat(option_accumulator, ignore_index=True)
        
    #??? correction here also
    if sizing == 'notional':
        df_op['OptPnlNotional'] = (df_op.OptPxBot*df_op.OptPnl/df_op.Spot)*value  # value no of options 
    if sizing == 'premium':
        df_op['OptPnlPremium'] = (df_op.OptPnl)*pct/100

    if sizing == 'contracts': 
        df_op['OptPnlContracts'] =df_op.OptPnl*df_op.OptPxBot*contract_size*value # value no of contracts
    # hold
    df_active_contracts  = (df_op.groupby('TradeStart').size().reset_index(name='ActiveOptions'))
    df_op ['NumOfContracts'] = df_op.apply(lambda x: compute_contracts(x,df_active_contracts,capital),axis=1)
    df_op = df_op.drop(columns =['TradeStart'])
    return df_op

    
def wealth_computation(df,nav =1000,sizing ='notional',hold=1):
    if hold==1:
        if sizing =='notional':
            df['Wealth']  = nav*(1 + df['OptPnlNotional']).cumprod()
        elif sizing =='premium':
            #df['OptPnlPremium'] = df['OptPnlPremium'].replace([np.inf, -np.inf], 0,)
            df['Wealth']  = nav*(1 + df['OptPnlPremium']).cumprod()
            
        elif sizing == 'contracts':
            df['CumPnL'] = df['OptPnlContracts'].cumsum()
            df['Wealth'] = nav + df['CumPnL']
            # df['r_t'] = df['CumPnL'] / df['NAV'].shift(1)
            # df.loc[0,'r_t'] = df['CumPnL'].iloc[0]/nav
            # df['wealth'] = nav * (1 + df['r_t']).cumprod()
       
    else : 
        
        if sizing =='notional':
            agg_pnl = df.groupby(by='TradeDate').OptPnlNotional.sum()
            wealth  = nav*(1 + agg_pnl).cumprod()
            df = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'Wealth':wealth})).reset_index()
        elif sizing =='premium':
            #df['OptPnlPremium'] = df['OptPnlPremium'].replace([np.inf, -np.inf], 0,)
            agg_pnl = df.groupby(by='TradeDate').OptPnlPremium.sum()
            wealth  = nav*(1 + agg_pnl).cumprod()
            df = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'Wealth':wealth})).reset_index()
        elif sizing == 'contracts':
            agg_pnl = df.groupby(by='TradeDate').OptPnlContracts.sum()
            cumpnl = agg_pnl.cumsum()
            wealth = nav+cumpnl
            df = (pd.DataFrame({'AggrigatedPnl':agg_pnl,'CumPnl':cumpnl,'Wealth':wealth})).reset_index()
            


    return df
    



       
        


