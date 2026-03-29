import numpy as np
import pandas as pd
from data_prep import *
import os
from pandas.tseries.offsets import DateOffset, Week
import matplotlib.pyplot as plt
class DataExtractor():
    def __init__(self,interpolator ="linear",test = False,data_path = 'AAPL_master_data.csv',rates_path = 'RiskFreeRates.csv'):
       self.test = test
       self.data_path = data_path
       self.df = pd.read_csv(os.path.join(os.getcwd(),'Data',data_path))
       self.rates = pd.read_csv(os.path.join(os.getcwd(),'Data',rates_path))
       self.gen_dict = {}
       self.data = {}
       self.interpolator = interpolator
    def get_days(self,date,months,s1,s2):
        
        '''
        date: trade date
        months : expected months to exp
        s1 : sorted expiry dates of of the available options on the above trade date
        '''
        if months <6:
            days = 30
        else:
            days = 45
        trade_date = pd.to_datetime(date, format="%Y%m%d")
        target = trade_date + DateOffset(months=months)
        exp = s1[s1 >= target]
        if exp.empty:
            exp = s2[s2 >= target]
        expiry = exp.min()
        days_to_expiry = (exp.min()-pd.to_datetime(date, format="%Y%m%d")).days

        # safety check
        if days_to_expiry > months * 30 + days:
            target = trade_date + DateOffset(months=months)
            exp = s2[s2 >= target]
            expiry = exp.min()
            days_to_expiry = (expiry - trade_date).days

        return days_to_expiry, str(expiry.date())
    def get_premium(self,flag,stk,date,exp_date,):
        data = self.df[(self.df.TradeDate==date)&(self.df.CallPut==flag)].copy()
        data = extract_clean_data(data,trade_date=date,flag = flag)
        surface_genrator = GenSurface(data,interpolator=self.interpolator)
        surface_genrator.update_surface()
        # print(date)
        fwd_mnyness = surface_genrator.fwd_moneyness()
        x,y= surface_genrator.known_data()
        surface_genrator.gen_spline()
        # surface_genrator.abs_error(x,y,z)
        adj_spot = self.df[self.df.TradeDate==date].AdjSpot.iloc[0]
        # print(exp_date)
        days_to_expiry = (pd.to_datetime(exp_date,format="%Y%m%d")-pd.to_datetime(date, format="%Y%m%d")).days
        # print("days",days_to_expiry)
        z = self.rates[self.rates.TradeDate==date]
        x = self.df[self.df.TradeDate==date].iloc[0]
        x.loc['days_to_expiry']=days_to_expiry
        # check risk free rate already computed
        risk_free_rate = compute_risk_free_rate(z,days_to_expiry)
        imp_vol = surface_genrator.get_implied_volatility(days_to_expiry,risk_free_rate,stk,adj_spot)
        px,delta,gama,vega,theta,rho = surface_genrator.compute_px(flag,date,adj_spot,days_to_expiry,risk_free_rate,stk)
        if self.test:
            self.gen_dict[date] = surface_genrator
        return px,delta,gama,vega,theta,rho,risk_free_rate,imp_vol   

    def check_moneyness(self,df_trade, var,val):
        
        idx = (df_trade[var] - val).abs().idxmin()
        mn = df_trade[var].loc[idx]
        df_trade = df_trade[df_trade[var]==mn]
        
        return df_trade

    def extract_data(self,expiry_in_months = 3,moneyness = 90,delta = None,bydelta = False,callput = 'c',hold=1,bot=1,symbool = 'EV',start_date = None,end_date= None,test=False):
        if moneyness and bydelta==False:
            band = .05
            val = moneyness
            var = 'Moneyness'
        elif bydelta and delta:
            delta = delta/100
            moneyness = None
            band = .1
            var = 'Delta'
            val = delta
            if callput=='p':
                band = -band
                val = -delta
                delta = -delta
        else:
            raise ValueError('if by delta is true delta cannot be None')
        dates = np.sort(self.df[self.df.Symbol == symbool].TradeDate.unique())
        if start_date:
            dates = dates[dates>=start_date]
        if end_date:
            dates = dates[dates<=end_date]

        self.df = self.df[(self.df.Volume>0)|(self.df.Flag==1)]
        opt_list = []
        
        for i in range(0,len(dates),bot):
            current_df = self.df[(self.df.Month_To_Expiry==expiry_in_months)&(self.df.TradeDate==dates[i])&(self.df.CallPut ==callput)&(self.df[var]>val*(1-band))&(self.df[var]<val*(1+band))]
            flag = False
            date = dates[i]
            if i+hold<len(dates-1):
                last_trade = dates[i+hold]
            else:
                last_trade = dates[-1]
            d1 = pd.to_datetime(dates[i], format="%Y%m%d")
            d2 = pd.to_datetime(last_trade, format="%Y%m%d")
            days = (d2 - d1).days
            
            
            if not current_df[current_df.days_to_expiry>=days].empty:
                df_trade = current_df[current_df.days_to_expiry>=days]
                df_trade = self.check_moneyness(df_trade, var,val)
                days_valid = df_trade.days_to_expiry.min()

            elif not current_df[current_df.days_to_expiry<days].empty:
                df_trade = current_df[current_df.days_to_expiry<days]
                df_trade = self.check_moneyness(df_trade, var,val)
                days_valid = df_trade.days_to_expiry.max()

            else:
                
                current_df = self.df[(self.df.TradeDate==dates[i])&(self.df.CallPut ==callput)&(self.df[var]>val*(1-band))&(self.df[var]<val*(1+band))&
                                     (self.df.Month_To_Expiry==expiry_in_months+1)]
                if current_df.shape[0]>=1:
                    df_trade = current_df[current_df.days_to_expiry>=days]
                    df_trade = self.check_moneyness(df_trade, var,val)
                    days_valid = df_trade.days_to_expiry.min()
                    

                else:
                    
                    data = self.df[(self.df.TradeDate==dates[i])&(self.df.CallPut==callput)].copy()
                    data = extract_clean_data(data,trade_date=dates[i],flag = callput)
                    surface_genrator = GenSurface(data,interpolator=self.interpolator)
                    surface_genrator.update_surface()
                    # print(date)
                    fwd_mnyness = surface_genrator.fwd_moneyness()
                    x,y= surface_genrator.known_data()
                    surface_genrator.gen_spline()
                    # surface_genrator.abs_error(x,y,z)
                    adj_spot = self.df[self.df.TradeDate==date].AdjSpot.iloc[0]
                    days_to_expiry,exp_date = self.get_days(date,expiry_in_months,pd.to_datetime(x,format="%Y%m%d").unique(), pd.to_datetime(self.df.AdjExpiry,format="%Y%m%d").unique())
                    
                    exp_list =exp_date.split('-')
                    exp_date =''
                    for j in exp_list:
                        exp_date+=j
                    
                    exp_date = int(exp_date)
                    # print(exp_date)
                
                    
                    # adj_expiry = self.df[self.df.AdjExpiry==exp_date].iloc[0].AdjExpiry
                    # FmtExpiryDate no longer exists
                    # fmtexpdt = self.df[self.df.AdjExpiry==exp_date].iloc[0].FmtExpiryDate
                    expspot = self.df[self.df.AdjExpiry==exp_date].iloc[0].ExpirySpot
                    x = self.df[self.df.TradeDate==date].iloc[0]
                    x.loc['days_to_expiry']=days_to_expiry
                    z = self.rates[self.rates.TradeDate==date]
                    risk_free_rate = compute_risk_free_rate(z,days_to_expiry)
                    if bydelta:
                        available_strikes = np.sort(self.df[self.df.TradeDate==date].AdjStrike.unique())
                        min_abs_diff = 1
                        cond_satisfied = False
                        for stk in available_strikes:
                            
                        
                            imp_vol = surface_genrator.get_implied_volatility(days_to_expiry,risk_free_rate,stk,adj_spot)
                            px,dlta,gama,vega,theta,rho = surface_genrator.compute_px(callput,date,adj_spot,days_to_expiry,risk_free_rate,stk)


                            if delta*(1-band)<dlta<delta*(1+band):
                                cond_satisfied = True
                                break
                            elif np.abs(delta-dlta) < min_abs_diff: 
                                min_abs_diff = np.abs(delta-dlta)
                                min_stk = stk


                        if cond_satisfied==False: 

                            px,dlta,gama,vega,theta,rho = surface_genrator.compute_px(callput,date,adj_spot,days_to_expiry,risk_free_rate,min_stk)
                    else:   
                        available_strikes = np.unique(y)
                        stk = available_strikes[np.abs(available_strikes-moneyness*adj_spot/100).argmin()]
                        
                        imp_vol = surface_genrator.get_implied_volatility(days_to_expiry,risk_free_rate,stk,adj_spot)
                        px,dlta,gama,vega,theta,rho = surface_genrator.compute_px(callput,date,adj_spot,days_to_expiry,risk_free_rate,stk)
                    df_trade = self.df[self.df.TradeDate==dates[i]].head(1)
                    df_trade.AdjStrike = stk
                    df_trade.Strike = (df_trade.Spot/adj_spot)*stk
                    df_trade.ExpiryDate = exp_date
                    df_trade.AdjExpiry = exp_date
                    # ASk and Bid Removed
                    df_trade.px = px
                    # df_trade.BidPrice = px
                    df_trade.CallPut = callput
                    df_trade.Symbool = symbool
                    df_trade.Delta = dlta
                    df_trade.Gama = gama
                    df_trade.Vega = vega
                    df_trade.Theta = theta
                    df_trade.Rho = rho
                    df_trade.days_to_expiry = days_to_expiry
                    df_trade.Month_To_Expiry = (pd.to_datetime(exp_date,format="%Y%m%d").year - pd.to_datetime(dates[i],format="%Y%m%d").year) * 12 + (pd.to_datetime(exp_date,format="%Y%m%d").month - pd.to_datetime(dates[i],format="%Y%m%d").month)
                    # df_trade.Moneyness = moneyness
                    df_trade.Moneyness = (stk/adj_spot*100)
                    df_trade.ExpirySpot = expspot
                    df_trade['OpenInterest']=df_trade['Volume']=0
                    df_trade.risk_free_rate = risk_free_rate
                    df_trade.ImpliedVolatility = imp_vol
                    df_trade.Flag =1
                    # FmtEXpiryDate removed
                    # df_trade.FmtExpiryDate = fmtexpdt
                    flag = True
                    
                    if self.test:
                        self.gen_dict[dates[i]] = surface_genrator
                                
                # else:
                #     if test:
                #         print(f'Data with moneyness={moneyness},{callput} and expiry in {expiry_in_months} months not traded on {date} checking with expiry in months+={add_factor}')
        
            # max_oi = df_trade.OpenInterest.max()
            if not flag:
                df_trade = df_trade[df_trade.days_to_expiry==days_valid]
                if df_trade.shape[0]>1:
                    idx = (df_trade[var] - val).abs().idxmin()
                    mn = df_trade[var].loc[idx]
                    df_trade = df_trade[df_trade[var]==mn]
                
            opt_list.append(df_trade)
            
        df_opt  = pd.concat(opt_list, ignore_index=True)
        
        return df_opt
    def hold_options(self,data,hold,last_date,count):
        df = self.df
        opt_list = []
        f1 = 0
        df_iv = df[(df.AdjExpiry ==data.AdjExpiry.values[0])&(df.CallPut==data.CallPut.values[0])&(df.AdjStrike==data.AdjStrike.values[0])&(df.Symbol==data.Symbol.values[0])]
        
        
        if len(df_iv)==0  :
            df_iv = data
            f1 = 1
            
        dates = np.sort(df[df.Symbol == data.Symbol.values[0]].TradeDate.unique())

        idx = np.where(dates==data['TradeDate'].values)[0][0]
        
        flag = 0
        f2 = 0
        for j in range(hold+1):
           
            if j==0 and f1 :
                
                
                df_opt = data
                flag = 1
                count +=1
            elif dates[idx+j] not in df_iv.TradeDate.to_list():
                # replace ExpiryDate with AdjExpiry next two
                if dates[idx+j]< data.AdjExpiry.values[0]:
                    px,delta,gama,vega,theta,rho,rfr,imp_vol = self.get_premium(data.CallPut.values[0],data.AdjStrike.values[0],dates[idx+j],data.AdjExpiry.values[0])
                    flag =1
                    count+=1
                    
                else:
                    px = delta = gama = vega = theta = rho=0
                    rfr = imp_vol = 0
                    flag =0
                    f2 =1
                    # print(2,dates[idx+j])
                df_opt = data.copy()
                df_opt['px'] = px
                # df_opt['BidPrice'] = px
                df_opt['Delta'] = delta
                df_opt['Gamma'] = gama
                df_opt['Vega'] = vega
                df_opt['Theta'] = theta
                df_opt['Rho'] = rho
                df_opt['days_to_expiry'] = (pd.to_datetime(data.AdjExpiry, format="%Y%m%d")-pd.to_datetime(dates[idx+j], format="%Y%m%d")).dt.days
                df_opt['Month_To_Expiry'] = (pd.to_datetime(data.AdjExpiry,format="%Y%m%d").dt.year - pd.to_datetime(dates[idx+j],format="%Y%m%d").year) * 12 + (pd.to_datetime(data.AdjExpiry,format="%Y%m%d").dt.month - pd.to_datetime(dates[idx+j],format="%Y%m%d").month)
                df_opt['OpenInterest']=df_opt['Volume']=0
                df_opt['TradeDate'] = dates[idx+j]
                df_opt.AdjSpot = df[df.TradeDate==dates[idx+j]].AdjSpot.iloc[0]
                df_opt.Spot = df[df.TradeDate==dates[idx+j]].Spot.iloc[0]
                df_opt['Moneyness'] = 100*data.AdjStrike/df_opt.AdjSpot
                # df_opt['Moneyness'] = (df_opt.AbsMoneyness /10).round()*10
                # add ExpiryDate and AdjExpiry
                df_opt.risk_free_rate = rfr
                df_opt.ImpliedVolatility = imp_vol
                
            

            else:
                df_opt = df_iv[df_iv.TradeDate == dates[idx+j]]
                flag = df_opt['Flag']
                
            
            df_opt['Flag'] = flag     
            
            opt_list.append(df_opt)
            
            
                    
            if dates[idx+j] == last_date:
                break
        df_opt  = pd.concat(opt_list, ignore_index=True)
        
        records_required = len(df_opt)
        if f2:
            records_required -=1
        records_available = records_required-df_opt.Flag.sum()
        backfilled = df_opt.Flag.sum() 
        missing = records_required - records_available -backfilled
        # replace ExpiryDate with AdjExpiry
        rec_df = pd.DataFrame({'TradeDate':[data.TradeDate.values[0]], 'Expiry':[data.ExpiryDate.values[0]],'C/P': data.CallPut.values[0],'Moneyness':data.Moneyness.values[0],
                               'Rec Req':[records_required],'Rec Avl':[records_available],'Rec Backfilled':[backfilled],'Rec Missing':[missing]})
        return df_opt, rec_df,count
        
   



    def gen_data(self,moneyness = 100,delta=None,bydelta = False, time_to_expiry = 1,callput = 'p',bot =1,hold=1,symbool='EV',start_date = None,end_date= None):
        df_opt=self.extract_data(expiry_in_months=time_to_expiry,moneyness=moneyness,delta=delta,bydelta=bydelta,callput=callput,hold =hold,symbool=symbool,
                            start_date = start_date,end_date= end_date,bot=bot)
        if not end_date:
            last_date = np.sort(self.df[self.df.Symbol == symbool].TradeDate.unique())[-1]
        else:
            last_date = self.df[self.df.Symbol == symbool].TradeDate[self.df[self.df.Symbol == symbool].TradeDate<= end_date].max()
        option_accumulator = []
        missing = []
        count = 0
        for i in range(df_opt.shape[0]):
            data = df_opt[df_opt.index==i]
            
            if data.TradeDate.values[0] == last_date: # redundant
                break
            pnl_frame,df_rec,count = self.hold_options(data,hold,last_date,count)

            option_accumulator.append(pnl_frame)
            missing.append(df_rec)
        df_op = pd.concat(option_accumulator, ignore_index=True)
        msg_data = pd.concat(missing, ignore_index=True)
        self.data[f'mn_{moneyness}_hold_{hold}'] = df_op
        if count:
            print(f'current simulation backfilled: {count} records')
            df = pd.read_csv(os.path.join(os.getcwd(),'Data',self.data_path))
            df = pd.concat([df,df_op[df_op.Flag==1]],ignore_index=True)
            df = df.drop_duplicates()
            df.to_csv(os.path.join(os.getcwd(),'Data','AAPL_master_data.csv'),index=False)

        return df_op, msg_data
    
    def plot_px_sp(self,mn,hold,exp,stk):
        data = self.data[f'mn_{mn}_hold_{hold}']
        data = data[(data.ExpiryDate==exp)&(data.AdjStrike==stk)]
        
        px = (data.AskPrice + data.BidPrice)/2
        adj_spot = data.AdjSpot

        datex = pd.to_datetime(data.TradeDate,format="%Y%m%d")   # convert to datetime
        fig, ax1 = plt.subplots()
        ax1.plot(datex,adj_spot,'r',label='Spot')

        ax1.plot([datex.iloc[0],datex.iloc[-1]],[data.AdjStrike,data.AdjStrike],'k')
        ax1.set_ylabel("Spot",)
        ax2 = ax1.twinx()
        ax2.plot(datex,px, label = "PX")
        ax2.set_ylabel("Premium")
        ax1.set_xticks(datex)
        ax1.set_xticklabels(data.days_to_expiry)
        ax1.tick_params(axis='x', rotation=45)
        # lines = [l1, l2, l3]
        # labels = [l.get_label() for l in lines]

        fig.legend()
        
        
        plt.title(f'Spot vs Premium on different trade dates for exp:{exp} and stk:{stk}')
        