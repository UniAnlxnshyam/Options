import numpy as np
import pandas as pd
from data_prep import *
import os
from pandas.tseries.offsets import DateOffset, Week
import matplotlib.pyplot as plt
class DataExtractor():
    def __init__(self,df,interpolator ="bicubic",test = False):
       self.test = test
       self.df = df
       self.gen_dict = {}
       self.data = {}
       self.interpolator = interpolator
    def get_days(self,date,months,s1,s2):
        
        '''
        date: trade date
        months : expected months to exp
        s : sorted expiry dates of of the available options on the above trade date
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
        data = extract_clean_data(self.df,flag = flag,trade_date=date)
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
        x = self.df[self.df.TradeDate==date].iloc[0]
        x.loc['days_to_expiry']=days_to_expiry
        risk_free_rate = compute_risk_free_rate(x)
        px,delta,gama,vega,theta,rho = surface_genrator.compute_px(flag,adj_spot,days_to_expiry,risk_free_rate,stk)
        if self.test:
            self.gen_dict[date] = surface_genrator
        return px,delta,gama,vega,theta,rho    

    def check_moneyness(self,df_trade, moneyness):
        idx = (df_trade['AbsMoneyness'] - moneyness).abs().idxmin()
        mn = df_trade.AbsMoneyness.loc[idx]
        df_trade = df_trade[df_trade.AbsMoneyness==mn]
        return df_trade

    def extract_data(self,expiry_in_months = 3,moneyness = 90,callput = 'c',hold=1,bot=1,symbool = 'EV',start_date = None,end_date= None,test=False):
        dates = np.sort(self.df[self.df.Symbol == symbool].TradeDate.unique())
        if start_date:
            dates = dates[dates>=start_date]
        if end_date:
            dates = dates[dates<=end_date]

        self.df = self.df[self.df.Volume>0]
        opt_list = []
        for i in range(0,len(dates),bot):
            current_df = self.df[(self.df.Month_To_Expiry==expiry_in_months)&(self.df.TradeDate==dates[i])&(self.df.CallPut ==callput)]
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

                if not df_trade[(df_trade.Moneyness==moneyness)].empty:
                    df_trade = df_trade[df_trade.Moneyness==moneyness]

                else:
                    df_trade = self.check_moneyness(df_trade, moneyness)
                days_valid = df_trade.days_to_expiry.min()

            elif not current_df[current_df.days_to_expiry<days].empty:
                df_trade = current_df[current_df.days_to_expiry<days]
                if df_trade[(df_trade.Moneyness==moneyness)].shape[0]>=1:
                    df_trade = df_trade[df_trade.Moneyness==moneyness]

                else:
                    df_trade = self.check_moneyness(df_trade, moneyness)
                days_valid = df_trade.days_to_expiry.max()

            else:
                fl = True
                add_factor =1
                while fl:
                    df_trade = self.df[(self.df.TradeDate==dates[i])&(self.df.CallPut ==callput)&(self.df.days_to_expiry>=days)&
                                (self.df.Month_To_Expiry==expiry_in_months+add_factor)]
                    if df_trade.shape[0]>=1:
                        
                        if df_trade[df_trade.Moneyness==moneyness].shape[0]>=1:
                            df_trade = df_trade[df_trade.Moneyness==moneyness]
                        else:
                            df_trade = self.check_moneyness(df_trade, moneyness)
                        days_valid = df_trade.days_to_expiry.min()

                    else:
                        add_factor+=1
                    if df_trade.shape[0]>=1 or add_factor>1:
                        fl = False
                    
                    if not fl and df_trade.empty :
                        data = extract_clean_data(self.df,flag = callput,trade_date=dates[i])
                        surface_genrator = GenSurface(data,interpolator=self.interpolator)
                        surface_genrator.update_surface()
                        # print(date)
                        fwd_mnyness = surface_genrator.fwd_moneyness()
                        x,y= surface_genrator.known_data()
                        surface_genrator.gen_spline()
                        # surface_genrator.abs_error(x,y,z)
                        adj_spot = self.df[self.df.TradeDate==date].AdjSpot.iloc[0]
                        days_to_expiry,exp_date = self.get_days(date,expiry_in_months,pd.to_datetime(x,format="%Y%m%d").unique(), pd.to_datetime(self.df.AdjExpiry).unique())
                        exp_list =exp_date.split('-')
                    
                        
                        adj_expiry = self.df[self.df.AdjExpiry==exp_date].iloc[0].AdjExpiry
                        fmtexpdt = self.df[self.df.AdjExpiry==exp_date].iloc[0].FmtExpiryDate
                        expspot = self.df[self.df.AdjExpiry==exp_date].iloc[0].ExpirySpot
                        x = self.df[self.df.TradeDate==date].iloc[0]
                        x.loc['days_to_expiry']=days_to_expiry
                        risk_free_rate = compute_risk_free_rate(x)
                        available_strikes = np.unique(y)
                        stk = available_strikes[np.abs(available_strikes-moneyness*adj_spot/100).argmin()]
                        exp_date =''
                        for j in exp_list:
                            exp_date+=j
                        exp_date = int(exp_date)
                        # print(exp_date)

                        px,delta,gama,vega,theta,rho = surface_genrator.compute_px(callput,adj_spot,days_to_expiry,risk_free_rate,stk)
                        df_trade = self.df[self.df.TradeDate==dates[i]].head(1)
                        df_trade.AdjStrike = stk
                        df_trade.ExpiryDate = exp_date
                        df_trade.AdjExpiry = adj_expiry
                        df_trade.AskPrice = px
                        df_trade.BidPrice = px
                        df_trade.CallPut = callput
                        df_trade.Symbool = symbool
                        df_trade.Delta = delta
                        df_trade.Gama = gama
                        df_trade.Vega = vega
                        df_trade.Theta = theta
                        df_trade.Rho = rho
                        df_trade.days_to_expiry = days_to_expiry
                        df_trade.Month_To_Expiry = (pd.to_datetime(exp_date,format="%Y%m%d").year - pd.to_datetime(dates[i],format="%Y%m%d").year) * 12 + (pd.to_datetime(exp_date,format="%Y%m%d").month - pd.to_datetime(dates[i],format="%Y%m%d").month)
                        df_trade.Moneyness = moneyness
                        df_trade.AbsMoneyness = round(stk/adj_spot*100,2)
                        df_trade.ExpirySpot = expspot
                        df_trade.FmtExpiryDate = fmtexpdt
                        flag = True
                        if self.test:
                            self.gen_dict[dates[i]] = surface_genrator
                                    
                    else:
                        if test:
                            print(f'Data with moneyness={moneyness},{callput} and expiry in {expiry_in_months} months not traded on {date} checking with expiry in months+={add_factor}')
        
            # max_oi = df_trade.OpenInterest.max()
            if not flag:
                df_trade = df_trade[df_trade.days_to_expiry==days_valid]
                if df_trade.shape[0]>1:
                    idx = (df_trade['AbsMoneyness'] - moneyness).abs().idxmin()
                    mn = df_trade.AbsMoneyness.loc[idx]
                    df_trade = df_trade[df_trade.AbsMoneyness==mn]
                
            opt_list.append(df_trade)
            
        df_opt  = pd.concat(opt_list, ignore_index=True)

        return df_opt
    def hold_options(self,data,hold,last_date):
        df = self.df
        opt_list = []
        f1 = 0
        df_iv = df[(df.AdjExpiry ==data.AdjExpiry.values[0])&(df.CallPut==data.CallPut.values[0])&(df.AdjStrike==data.AdjStrike.values[0])&(df.Symbol==data.Symbol.values[0])]
        
        
        if len(df_iv)==0:
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
                
            elif dates[idx+j] not in df_iv.TradeDate.to_list():
                if dates[idx+j]< data.ExpiryDate.values[0]:
                    px,delta,gama,vega,theta,rho = self.get_premium(data.CallPut.values[0],data.AdjStrike.values[0],dates[idx+j],data.ExpiryDate.values[0])
                    flag =1
                    
                    
                else:
                    px =0
                    delta = 0
                    gama = 0
                    vega = 0
                    theta=0
                    rho=0
                    flag =0
                    f2 =1
                    print(2,dates[idx+j])
                df_opt = data.copy()
                df_opt['AskPrice'] = px
                df_opt['BidPrice'] = px
                df_opt['Delta'] = delta
                df_opt['Gama'] = round(gama,2)
                df_opt['Vega'] = round(vega,2)
                df_opt['Theta'] = round(theta,2)
                df_opt['Rho'] = round(rho,2)
                df_opt['days_to_expiry'] = (pd.to_datetime(data.ExpiryDate, format="%Y%m%d")-pd.to_datetime(dates[idx+j], format="%Y%m%d")).dt.days
                df_opt['Month_To_Expiry'] = (pd.to_datetime(data.ExpiryDate,format="%Y%m%d").dt.year - pd.to_datetime(dates[idx+j],format="%Y%m%d").year) * 12 + (pd.to_datetime(data.ExpiryDate,format="%Y%m%d").dt.month - pd.to_datetime(dates[idx+j],format="%Y%m%d").month)
                
                df_opt['TradeDate'] = dates[idx+j]
                df_opt.AdjSpot = df[df.TradeDate==dates[idx+j]].AdjSpot.iloc[0]
                
                df_opt['AbsMoneyness'] = round(100*data.AdjStrike/df_opt.AdjSpot,2)
                df_opt['Moneyness'] = (df_opt.AbsMoneyness /10).round()*10

                
            

            else:
                df_opt = df_iv[df_iv.TradeDate == dates[idx+j]]
                flag =0
                
            
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
        # print(data.TradeDate.values[0],data.ExpiryDate.values[0],records_available,records_required)
        rec_df = pd.DataFrame({'TradeDate':[data.TradeDate.values[0]], 'Expiry':[data.ExpiryDate.values[0]],'C/P': data.CallPut.values[0],'Moneyness':data.Moneyness.values[0],
                               'Rec Req':[records_required],'Rec Avl':[records_available],'Rec Backfilled':[backfilled],'Rec Missing':[missing]})
        return df_opt, rec_df
        
   



    def gen_data(self,moneyness = 100, time_to_expiry = 1,callput = 'p',bot =1,hold=1,symbool='EV',start_date = None,end_date= None):
        df_opt=self.extract_data(expiry_in_months=time_to_expiry,moneyness=moneyness,callput=callput,hold =hold,symbool=symbool,
                            start_date = start_date,end_date= end_date,bot=bot)
        if not end_date:
            last_date = np.sort(self.df[self.df.Symbol == symbool].TradeDate.unique())[-1]
        else:
            last_date = self.df[self.df.Symbol == symbool].TradeDate[self.df[self.df.Symbol == symbool].TradeDate<= end_date].max()
        option_accumulator = []
        missing = []
        for i in range(df_opt.shape[0]):
            data = df_opt[df_opt.index==i]
            
            if data.TradeDate.values[0] == last_date: # redundant
                break
            pnl_frame,df_rec = self.hold_options(data,hold,last_date)

            option_accumulator.append(pnl_frame)
            missing.append(df_rec)
        df_op = pd.concat(option_accumulator, ignore_index=True)
        msg_data = pd.concat(missing, ignore_index=True)
        self.data[f'mn_{moneyness}_hold_{hold}'] = df_op

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
        