import numpy as np
import pandas as pd
from data_prep import *
import os
from pandas.tseries.offsets import DateOffset, Week
import matplotlib.pyplot as plt
import time

class DataExtractor():
    def __init__(self,symbool = 'SP',callput ='c',interpolator ="linear",test = False,data_path = 'AAPL_master_data.csv',rates_path = 'RiskFreeRates.csv',spot_path = 'AAPL_spot.csv'):
       self.test = test
       self.data_path = data_path
       self.df = pd.read_csv(os.path.join(os.getcwd(),'Data',data_path))
       self.df = self.df[(self.df.Symbol==symbool)&(self.df.CallPut==callput)].drop_duplicates()
       self.rates = pd.read_csv(os.path.join(os.getcwd(),'Data',rates_path))
       self.spot_data = pd.read_csv(os.path.join(os.getcwd(),'Data',spot_path))
       self.gen_dict = {}
       self.data = {}
       self.interpolator = interpolator
       # self.test_data = []
    def get_days(self,date,months,symbool,s1,s2,returned_dates = []):
         
       
        '''
        date: trade date
        months : expected months to exp
        s1 : sorted expiry dates of of the available options on the above trade date
        '''
        
        last_itr = False
        if len(returned_dates)>0:
            returned_dates = pd.to_datetime(returned_dates, format="%Y%m%d") 

        # print(date,returned_dates)
        
        trade_date = pd.to_datetime(date, format="%Y%m%d")
        if symbool == 'EV':
            l_lim = trade_date + DateOffset(months=months)
            l_lim = l_lim.replace(day=1)+pd.offsets.Week(2)+pd.offsets.Week(weekday=2)
            
            u_lim = trade_date + DateOffset(months=months+1)
            u_lim = u_lim.replace(day=1)+pd.offsets.Week(2)+pd.offsets.Week(weekday=5)
        elif symbool == 'SP':
            l_lim = trade_date + DateOffset(months=months)
            l_lim = l_lim.replace(day=1)+pd.offsets.Week(2)+pd.offsets.Week(weekday=2)
            u_lim = trade_date + DateOffset(months=months)
            u_lim = u_lim.replace(day=1)+pd.offsets.Week(2)+pd.offsets.Week(weekday=5)
        exp = s1[(s1 >= l_lim)&(s1<u_lim)]
        exp = pd.Series([dt for dt in exp if dt not in returned_dates])
       
            
        if exp.empty:
            exp = s2[(s2 >= l_lim)&(s2<u_lim)]
            exp = pd.Series([dt for dt in exp if dt not in returned_dates])
         
            
            
        if exp.empty:
                exp = trade_date + DateOffset(months=months)
                exp = exp.replace(day=1)+pd.offsets.Week(2)+pd.offsets.Week(weekday=4)
                if exp in self.spot_data.TradeDate:
                    exp= pd.Series([exp])
                else:
                    exp = exp-pd.Timedelta(days=1)
                    exp= pd.Series([exp])
                
             
        if len(exp)==1:
            
            last_itr= True
        expiry = exp.min()
        
        
        days_to_expiry = (exp.min()-trade_date).days

        # safety check
        # if days_to_expiry > months * 30 + days:
        #     target = trade_date + DateOffset(months=months)
        #     exp = s2[s2 >= target]
        #     expiry = exp.min()
        #     days_to_expiry = (expiry - trade_date).days

        return days_to_expiry, str(expiry.date()),last_itr
    
    def third_friday(self,date):
        date =pd.to_datetime(date,format="%Y%m%d")
        first = pd.Timestamp(year=date.year, month=date.month, day=1)
        first_friday = first + pd.offsets.Week(weekday=4)
        return first_friday + pd.offsets.Week(2)
    
    def is_third_week_expiry(self,date):
        date = pd.to_datetime(date,format="%Y%m%d")
        fri = self.third_friday(date)
        wed = fri - pd.Timedelta(days=2)
        
        return wed <= date <= fri
    def get_premium(self,flag,stk,date,exp_date,):
        if date in self.gen_dict:
            surface_genrator = self.gen_dict[date]
        else:
            data = self.df[self.df.TradeDate==date].copy()
            surface_genrator,x,y = self.gen_iv_surface(data,date,flag)
            # data = extract_clean_data(data,trade_date=date,flag = flag)
            # surface_genrator = GenSurface(data,interpolator=self.interpolator)
            # surface_genrator.update_surface()
            # # print(date)
            # fwd_mnyness = surface_genrator.fwd_moneyness()
            # x,y= surface_genrator.known_data()
            # surface_genrator.gen_spline()
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
    def gen_iv_surface(self,data,date,callput):
     
        # extract data based on trade date and callput & clean ang gen iv surface
        data = data.copy()
        data = extract_clean_data(data,trade_date=date,flag = callput)
        surface_genrator = GenSurface(data,interpolator=self.interpolator)
        surface_genrator.update_surface()
        # print(date)
        fwd_mnyness = surface_genrator.fwd_moneyness()
        exp_dates,y= surface_genrator.known_data()
        surface_genrator.gen_spline()
        
        return surface_genrator,exp_dates,y
    


    def get_params_by_trade_date(self,date,callput,expiry):
            surface_genrator,exp_dates,y = self.gen_iv_surface(date,callput)  
            returned_dates = []  
            last_itr = False
            td = []
            exp =[]
            sp = []
            stk_list = []
            dlt = []
            fl = []
            imp_vol_l = []
            px_l = []
    
            while not last_itr:
                adj_spot = self.df[self.df.TradeDate==date].AdjSpot.iloc[0]
                days_to_expiry,exp_date,last_itr = self.get_days(date,expiry,pd.to_datetime(exp_dates,format="%Y%m%d").unique(), pd.to_datetime(self.df.AdjExpiry,format="%Y%m%d").unique(),returned_dates=returned_dates)
                            
                exp_list =exp_date.split('-')
                exp_date =''
                for j in exp_list:
                    exp_date+=j
                
                exp_date = int(exp_date)
                # print(exp_date)
                
                
                z = self.rates[self.rates.TradeDate==date]
                risk_free_rate = compute_risk_free_rate(z,days_to_expiry)
                available_strikes = np.sort(self.df[(self.df.TradeDate==date)&(self.df.CallPut==callput)].AdjStrike.unique())
                for stk in available_strikes:
                                    
                                    
                                
                    imp_vol = surface_genrator.get_implied_volatility(days_to_expiry,risk_free_rate,stk,adj_spot)
                    px,dlta,gama,vega,theta,rho = surface_genrator.compute_px(callput,date,adj_spot,days_to_expiry,risk_free_rate,stk)
                    test_flag =1
                    
                    exp_data = self.df[(self.df.TradeDate==date)&(self.df.CallPut==callput)&(self.df.AdjExpiry==exp_date)]
                    if stk in np.sort(exp_data.AdjStrike.unique()):
                        # print(stk,dlta,exp_data[exp_data.AdjStrike==stk].Delta.values[0])
                        
                        test_flag = exp_data[exp_data.AdjStrike==stk].Flag.values[0]
                
                    td.append(date)
                    exp.append(exp_date)
                    sp.append(adj_spot)
                    stk_list.append(stk)
                    dlt.append(dlta)
                    fl.append(test_flag)
                    imp_vol_l.append(imp_vol)
                    px_l.append(px)
                returned_dates.append(exp_date)
            return pd.DataFrame({'TradeDate':td,'ExpiryDate':exp,'SP':sp,'Stk':stk_list,'px':px_l,'IV':imp_vol_l,'Delta':dlt,'Flag':fl})
    
    def backfill(self,date_group_dt,df,date,callput,bydelta,delta,moneyness,band,symbool,expiry_in_months):
        surface_genrator,exp_dates,y = self.gen_iv_surface(self.df[self.df.TradeDate == date],date,callput)
                
        exp_dates = [dt for dt in exp_dates if self.is_third_week_expiry(dt)]
        
        
        # surface_genrator.abs_error(x,y,z)
        adj_spot = self.df[self.df.TradeDate==date].AdjSpot.iloc[0]
        cond_satisfied = False
        returned_dates = []
        min_abs_diff = 1
        
        s3 =pd.to_datetime(df.AdjExpiry,format="%Y%m%d").unique()
        
        
        
        
        while not cond_satisfied:
            
            days_to_expiry,exp_date,last_itr = self.get_days(date,expiry_in_months,symbool,pd.to_datetime(exp_dates,format="%Y%m%d").unique(),
                                                                s3,returned_dates=returned_dates)
            
            exp_list =exp_date.split('-')
            exp_date =''
            for j in exp_list:
                exp_date+=j
                        
            exp_date = int(exp_date)
            # print(exp_date)
            
            
            # adj_expiry = self.df[self.df.AdjExpiry==exp_date].iloc[0].AdjExpiry
            # FmtExpiryDate no longer exists
            # fmtexpdt = self.df[self.df.AdjExpiry==exp_date].iloc[0].FmtExpiryDate
            
            if exp_date>self.spot_data.TradeDate.max():
                expspot = self.spot_data[self.spot_data.TradeDate==self.spot_data.TradeDate.max()].AdjSpot.values[0]
                # use na
            else:
                #if not self.spot_data[self.spot_data.TradeDate==exp_date].empty:
                expspot = self.spot_data[self.spot_data.TradeDate==exp_date].AdjSpot.values[0]
                #else
                
            # x = self.df[self.df.TradeDate==date].iloc[0]
            # x.loc['days_to_expiry']=days_to_expiry
            z = self.rates[self.rates.TradeDate==date]
            risk_free_rate = compute_risk_free_rate(z,days_to_expiry)
            if bydelta:
                available_strikes = np.sort(date_group_dt.AdjStrike.unique())
                
                # print(date,exp_date)
                
                for stk in available_strikes:
                    
                    
                
                    imp_vol = surface_genrator.get_implied_volatility(days_to_expiry,risk_free_rate,stk,adj_spot)
                    px,dlta,gama,vega,theta,rho = surface_genrator.compute_px(callput,date,adj_spot,days_to_expiry,risk_free_rate,stk)
                    # if self.test:
                    #     test_flag =1
                    #     if exp_date in np.sort(self.df[(self.df.TradeDate==date)&(self.df.CallPut==callput)].AdjExpiry.unique()):
                    #         exp_data = self.df[(self.df.TradeDate==date)&(self.df.CallPut==callput)&(self.df.AdjExpiry==exp_date)]
                    #         if stk in np.sort(exp_data.AdjStrike.unique()):
                    #             # print(stk,dlta,exp_data[exp_data.AdjStrike==stk].Delta.values[0])
                                
                    #             test_flag = exp_data[exp_data.AdjStrike==stk].Flag.values[0]
                        
                    #     self.test_data.append({'TradeDate':date,'ExpiryDate':exp_date,'Spot':adj_spot,'Stk':stk,'Delta':dlta,'Flag':test_flag})

                    

                    if delta*(1-band)<dlta<delta*(1+band):
                        cond_satisfied = True
                        
                        break
                    elif np.abs(delta-dlta) < min_abs_diff: # here for delta adjustment
                                
                        
                        
                        min_abs_diff = np.abs(delta-dlta)
                        params_min_dlta = (px,dlta,gama,vega,theta,rho,exp_date,stk)
                        

                        

                if cond_satisfied==False: 
                    returned_dates.append(exp_date)
                    
                    px,dlta,gama,vega,theta,rho,exp_date,stk = params_min_dlta
                    
                    if last_itr:
                        cond_satisfied = True
                
            else:  
                    
                available_strikes = np.unique(y)
                stk = available_strikes[np.abs(available_strikes-moneyness*adj_spot/100).argmin()]
                
                imp_vol = surface_genrator.get_implied_volatility(days_to_expiry,risk_free_rate,stk,adj_spot)
                px,dlta,gama,vega,theta,rho = surface_genrator.compute_px(callput,date,adj_spot,days_to_expiry,risk_free_rate,stk)
                cond_satisfied = True
        
        
        df_trade = date_group_dt.head(1)
        df_trade.AdjStrike = stk
        df_trade.Strike = round((df_trade.Spot/adj_spot)*stk,4)
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
        df_trade.Month_To_Expiry = (pd.to_datetime(exp_date,format="%Y%m%d").year - pd.to_datetime(date,format="%Y%m%d").year) * 12 + (pd.to_datetime(exp_date,format="%Y%m%d").month - pd.to_datetime(date,format="%Y%m%d").month)
        # df_trade.Moneyness = moneyness
        df_trade.Moneyness = (stk/adj_spot*100)
        df_trade.ExpirySpot = expspot
        df_trade['OpenInterest']=df_trade['Volume']=0
        df_trade.risk_free_rate = risk_free_rate
        df_trade.ImpliedVolatility = imp_vol
        df_trade.Flag =1
        # FmtEXpiryDate removed
        # df_trade.FmtExpiryDate = fmtexpdt
        return df_trade, surface_genrator
        

    def extract_data(self,expiry_in_months = 3,moneyness = 90,delta = None,bydelta = False,callput = 'c',hold=1,bot=1,symbool = 'EV',start_date = None,end_date= None):
        
        if moneyness and bydelta==False:
            band = .05
            val = moneyness
            var = 'Moneyness'
        elif bydelta and delta:
            delta = delta/100
            moneyness = None
            if delta < .15:
                band = .20
            else:
                band =.10
            var = 'Delta'
            val = delta
            if callput=='p':
                band = -band
                val = -delta
                delta = -delta
        else:
            raise ValueError('if by delta is true delta cannot be None')
        dates = np.sort(self.df.TradeDate.unique())
        if start_date:
            dates = dates[dates>=start_date]
        if end_date:
            dates = dates[dates<=end_date]

        # self.df = self.df[(self.df.Volume>0)|(self.df.Flag==1)]
        opt_list = []
        df  = self.df[self.df.AdjExpiry.apply(lambda x:self.is_third_week_expiry(x))]
        date_group = dict(tuple(df.groupby('TradeDate')))
        
        for i in range(0,len(dates),bot):
            flag = True
            
            if dates[i]==dates[-1]:
                break
            date = dates[i]
            
            if i+hold<len(dates)-1:
                last_trade = dates[i+hold]
            else:
                last_trade = pd.to_datetime(date,format="%Y%m%d") + pd.DateOffset(months=expiry_in_months)
                if symbool == 'EV':
                    
                    last_trade = last_trade + pd.offsets.BMonthEnd(0)

                elif symbool == 'SP':
                    last_trade = last_trade.replace(day=1)
                    last_trade = last_trade + pd.offsets.WeekOfMonth(week=2, weekday=4)

                # last_trade = dates[-1]
            d1 = pd.to_datetime(date, format="%Y%m%d")
            d2 = pd.to_datetime(last_trade, format="%Y%m%d")
            days = (d2 - d1).days
            current_df = date_group[date]
            current_df = current_df[(current_df[var]>val*(1-band))&(current_df[var]<val*(1+band))]
            # current_df = current_df[current_df.AdjExpiry.map(self.is_third_week_expiry)]
            
            if symbool=='EV':
                if not current_df[(current_df.days_to_expiry>=days)&(current_df.Month_To_Expiry==expiry_in_months+1)].empty:
                    df_trade = current_df[(current_df.days_to_expiry>=days)&((current_df.Month_To_Expiry==expiry_in_months+1))]
                    df_trade = self.check_moneyness(df_trade, var,val)
                    days_valid = df_trade.days_to_expiry.min()
                    flag = False

                elif not current_df[(current_df.Month_To_Expiry==expiry_in_months)&(current_df.days_to_expiry<days)].empty :
                    df_trade = current_df[(current_df.Month_To_Expiry==expiry_in_months)&(current_df.days_to_expiry<days)]
                    
                    df_trade = self.check_moneyness(df_trade, var,val)
                    days_valid = df_trade.days_to_expiry.max()
                    flag = False
                
                
            elif symbool=='SP':
                if not current_df[(current_df.days_to_expiry>=days)&(current_df.Month_To_Expiry==expiry_in_months)].empty:
                    df_trade = current_df[(current_df.days_to_expiry>=days)&(current_df.Month_To_Expiry==expiry_in_months)]
                    df_trade = self.check_moneyness(df_trade, var,val)
                    days_valid = df_trade.days_to_expiry.min()
                    flag = False
        
                
                elif not current_df[(current_df.Month_To_Expiry==expiry_in_months)&(current_df.days_to_expiry<days)].empty:
                    df_trade = current_df[(current_df.Month_To_Expiry==expiry_in_months)&(current_df.days_to_expiry<days)]
                
                    df_trade = self.check_moneyness(df_trade, var,val)
                    days_valid = df_trade.days_to_expiry.max()
                    flag = False
            
                
                            
           
            if not flag:
                df_trade = df_trade[df_trade.days_to_expiry==days_valid]
                if df_trade.shape[0]>1:
                    idx = (df_trade[var] - val).abs().idxmin()
                    mn = df_trade[var].loc[idx]
                    df_trade = df_trade[df_trade[var]==mn]
                    ###### check
                if df_trade.shape[0]>1:
                    raise ValueError(f'Duplicates for date:{date}')
            else:
                    df_trade,surface_genrator = self.backfill(date_group[date],df,date,callput,bydelta,delta,moneyness,band,symbool,expiry_in_months)
        
                    
                    self.gen_dict[date] = surface_genrator
               
            opt_list.append(df_trade)
            
        df_opt  = pd.concat(opt_list, ignore_index=True)
        
        return df_opt
    def hold_options(self,data,hold,last_date,count,var):
        df = self.df
        opt_list = []
        # f1 = False # true if no record matching expiry and stk in the original Data correspondint to the trade date of data(input data)
        flag = 0 # 1 for back filled
        # f2 = 0 # 1 if trade date is after expiry
        df_iv = df[(df.AdjExpiry ==data.AdjExpiry.values[0])&(df.AdjStrike==data.AdjStrike.values[0])].drop_duplicates()
        # df_iv = df_iv[(df_iv.Volume>0)|(df_iv.Flag==1)]
        
        # if len(df_iv)==0  : # option back filled and not in the data
        #     f1 = True
        #     df_iv = data
            
            
        dates = np.sort(df.TradeDate.unique())

        idx = np.where(dates==data['TradeDate'].values)[0][0]
        
        
        for j in range(hold+1):
            if dates[idx+j]>data.AdjExpiry.values[0]:
                break
           
            if df_iv.empty :
                df_iv = df_opt = data
                
                flag = 1
                count +=1
            elif dates[idx+j] not in df_iv.TradeDate.to_list():
                # replace ExpiryDate with AdjExpiry next two
                if dates[idx+j]< data.AdjExpiry.values[0]:
                    px,delta,gama,vega,theta,rho,rfr,imp_vol = self.get_premium(data.CallPut.values[0],data.AdjStrike.values[0],dates[idx+j],data.AdjExpiry.values[0])
                    flag =1
                    count+=1
                    
                    # else:
                    #     px = delta = gama = vega = theta = rho=0
                    #     rfr = imp_vol = 0
                    #     flag =0
                    #     f2 =1
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
                    df_opt['ExpiryDate'] = data.AdjExpiry.values[0] 
                    # add ExpiryDate and AdjExpiry
                    df_opt.risk_free_rate = rfr
                    df_opt.ImpliedVolatility = imp_vol
                    
                else:
                    continue

            

            else:
                df_opt = df_iv[df_iv.TradeDate == dates[idx+j]]#.iloc[[0]]
                flag = df_opt['Flag'].values[0]
                
            
            df_opt['Flag'] = flag    

            if len(df_opt)>1:
                print(df_opt)
                raise ValueError(f'Duplicates from hold')
            
            opt_list.append(df_opt)
            
            
            if dates[idx+j] == last_date:
                
                break        
            

        df_opt  = pd.concat(opt_list, ignore_index=True)
        df_opt['TradeStart'] = data.TradeDate.values[0]
        df_opt = df_opt.drop_duplicates(subset=['TradeDate','AdjExpiry','AdjStrike','CallPut'])
        records_required = len(df_opt)
        # if f2:
        #     records_required -=1
        records_available = records_required-df_opt.Flag.sum()
        backfilled = df_opt.Flag.sum() 
        missing = records_required - records_available -backfilled
        # replace ExpiryDate with AdjExpiry
        rec_df = pd.DataFrame({'TradeDate':[data.TradeDate.values[0]], 'Expiry':[data.AdjExpiry.values[0]],'C/P': data.CallPut.values[0],var:data[var].values[0],
                               'Rec Req':[records_required],'Rec Avl':[records_available],'Rec Backfilled':[backfilled],'Rec Missing':[missing]})
        return df_opt, rec_df,count
        
   



    def gen_data(self,moneyness = 100,delta=None,bydelta = False, time_to_expiry = 1,callput = 'p',bot =1,hold=1,symbool='EV',start_date = None,end_date= None,multiprocess = False):
      
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
            data = df_opt.iloc[[i]]
            
            if data.TradeDate.values[0] == last_date: # redundant
                break
            if bydelta:
                var = 'Delta'
            else:
                var = 'Moneyness'
            pnl_frame,df_rec,count = self.hold_options(data,hold,last_date,count,var)

            option_accumulator.append(pnl_frame)
            missing.append(df_rec)
        df_op = pd.concat(option_accumulator, ignore_index=True)
        msg_data = pd.concat(missing, ignore_index=True)
        self.data[f'mn_{moneyness}_hold_{hold}'] = df_op
        if not multiprocess:
            print(f'current simulation backfilled: {count} records')
            df = pd.read_csv(os.path.join(os.getcwd(),'Data',self.data_path))
            df_or = df_op.drop(columns=['TradeStart'])
            df = pd.concat([df,df_or[df_or.Flag==1]],ignore_index=True)
            df = df.drop_duplicates()
            
            df.to_csv(os.path.join(os.getcwd(),'Data','AAPL_master_data.csv'),index=False)
            

        return {'df_options':df_op,'missing_df':msg_data,'count':count}
    
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
        