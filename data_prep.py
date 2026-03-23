import py_vollib.black_scholes.implied_volatility as iv
from py_vollib.black_scholes import black_scholes as bs
from py_vollib.black_scholes.greeks.analytical import delta, gamma, vega, theta, rho
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import scipy.interpolate as interpolate
from scipy.spatial import Delaunay
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
import warnings

def compute_risk_free_rate(x):
    
    exp_period = [4,8,13,17,26,52]
    weeks_to_expiry = round(x['days_to_expiry']/7)
    if f'risk_free_rate_{weeks_to_expiry}' in x.index.to_list() and pd.notna(x[f'risk_free_rate_{weeks_to_expiry}']):
        risk_free_rate = x[f'risk_free_rate_{weeks_to_expiry}']
        #print(risk_free_rate)
    elif 4< weeks_to_expiry< 52:
        l_lim = max([i  for i in exp_period if i<weeks_to_expiry])
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

def compute_iv(x):
    try:
        implied_vol = iv.implied_volatility(x.px,x.AdjSpot,x.AdjStrike,x.days_to_expiry/365,x.risk_free_rate,x.CallPut)
    except Exception as e:
        # check exception 
        implied_vol = 0
    implied_vol = min(20,implied_vol)
    return implied_vol
    

def check_vertical_arbitrage(data,callput,test = False):
    '''
    data : data with same expiry
    '''
    i=1
    data = data.sort_values(by='AdjStrike')
    # for same expiry px1>px2 for k1<k2 Call
    # for same expiry px1>px2 for k1>k2 Put
    while i < data.shape[0]:
        data = data.reset_index(drop=True)
        if callput =='c':
            
                  
            if data.px.iloc[i-1]<data.px.iloc[i]:
                if test:
                    print(f'option with expiry {data.AdjExpiry.iloc[i]} and strike {data.AdjStrike.iloc[i]} vertical arbitrage')

                if data.Volume.iloc[i-1]==0:
                    if data.Volume.iloc[i]==0:
                        data = data.drop(data.index[i])
                        continue
                    else:
                        data = data.drop(data.index[i-1])
                        continue
                        
                elif data.Volume.iloc[i-1]>0: 
                    if data.Volume.iloc[i-1]>=data.Volume.iloc[i]:
                        data = data.drop(data.index[i])
                        continue
                    else:
                        data = data.drop(data.index[i-1])
                        continue
                        


                
        else: 
            
            if data.px.iloc[i-1]>data.px.iloc[i]:
                if test:
                    print(f'option with expiry {data.AdjExpiry.iloc[i]} and strike {data.AdjStrike.iloc[i]} vertical arbitrage and volume {data.Volume.iloc[i]}')
                if data.Volume.iloc[i-1]==0:
                    if data.Volume.iloc[i]==0:
                        data = data.drop(index=i)
                        continue
                    else:
                        data = data.drop(index=i-1)
                        continue
                else: 
                    if data.Volume.iloc[i-1]>=data.Volume.iloc[i]:
                        data = data.drop(index=i)
                    else:
                        data = data.drop(index=i-1)
                        continue
    
        i+=1
    return data
    
def check_calendar_arbitrage(data,test=False):
    """
    data 'same strike data'
    """
    data = data.sort_values(by='AdjExpiry')
    # for same strike px1>px2 for days_to_exp1>days_to_exp2
    # for i in range(1,data.shape[0]):
    i=1
    while i < data.shape[0]:
        data = data.reset_index(drop=True)
        if data.px.iloc[i-1]>data.px.iloc[i]:
            if test:
                print(f'option with expiry {data.AdjExpiry.iloc[i]} and strike {data.AdjStrike.iloc[i]} calendar arbitrage')
            if data.Volume.iloc[i-1]==0:
                if data.Volume.iloc[i]==0:
                    data = data.drop(data.index[i])
                    continue
                else:
                    data = data.drop(data.index[i-1])
                    continue
                        
            elif data.Volume.iloc[i-1]>0: 
                if data.Volume.iloc[i-1]>=data.Volume.iloc[i]:
                    data = data.drop(data.index[i])
                    continue
                else:
                    data = data.drop(data.index[i-1])
                    continue
        i+=1
    return data
            

def check_iv(data):
    data = data[(.01<=data.ImpliedVolatility)&(data.ImpliedVolatility<=5)]

    return(data)

def date_int_convertor(date):
    dl =  date.split('-')
    fmt_date = ''
    for item in dl:
        fmt_date+=item

    return int(fmt_date)

def load_data(path = './Data/master_data.csv'):
    df = pd.read_csv(path)
    df = df.drop_duplicates()
    print(f'no of cols ={len(df.columns)}')   
   
    return df

def extract_clean_data(data,flag = 'c',trade_date = 20190131,test =False):
    data['px'] = (data.AskPrice+data.BidPrice)/2
    data['risk_free_rate'] = data.apply(lambda x:compute_risk_free_rate(x),axis=1)
    data['ImpliedVolatility'] = data.apply(lambda x:compute_iv(x),axis=1)
    if test:
        print(f'{flag} options traded available on {trade_date}:{data.shape[0]}')
    data['AdjExpiry'] = data.AdjExpiry.apply(lambda x :date_int_convertor(x))


    n_data = []
    for exp in data.AdjExpiry.unique():
        d1 = check_vertical_arbitrage(data[(data.AdjExpiry==exp)&(data.CallPut==flag)],flag)
        n_data.append(d1)
    data = pd.concat(n_data, ignore_index=True)
    if test:
        print(f'{flag} options traded available on {trade_date} after vertical arbitrage removed:{data.shape[0]}')

    n_data = []
    for stk in data.AdjStrike.unique():
        dt = check_calendar_arbitrage(data[(data.AdjStrike==stk)&(data.CallPut==flag)])
        n_data.append(dt)
    data = pd.concat(n_data, ignore_index=True)
    if test:
        print(f'{flag} options traded available on {trade_date} after calendar arbitrage removed:{data.shape[0]}')
    data = check_iv(data)
    if test:
        print(f'{flag} options traded available on {trade_date} after removing iv<.01 and iv>5:{data.shape[0]}')
    data = data[(data.BidPrice!=0)&(data.days_to_expiry>=15)]
    data = data[data.Volume!=0]
    data['time_to_exp'] = data.days_to_expiry/365
    
    data = data[data.AbsMoneyness>=70]
    data = data[data.AbsMoneyness<130]
    return data



class GenSurface():
    def __init__(self,data,interpolator ="bicubic"):
        # x time axis, y strike axis
        self.data = data[['TradeDate','AdjExpiry','CallPut','ImpliedVolatility','Spot','AdjSpot','Strike','AdjStrike','risk_free_rate','time_to_exp','days_to_expiry','px',
                          'AbsMoneyness']]
        self.surface = data[['time_to_exp','ImpliedVolatility','AdjStrike']].pivot_table(values =['ImpliedVolatility'],index = 'AdjStrike',columns='time_to_exp')
        # print(f'check self.surface for discountinities and update')
        self.interpolator = interpolator
        self.x = self.surface['ImpliedVolatility'].columns.values
        self.y =  self.surface['ImpliedVolatility'].index.values
        self.X,self.Y = np.meshgrid(self.x,self.y)
        self.Z = self.surface['ImpliedVolatility'].values
        self.exp_dict ={}
        self.stk_dict ={}
        self.known_x =None
        self.known_y =None
       
        self.known_values =None
        self.Y_f = None
        # self.x_mean = None
        # self.y_mean = None
        # self.x_std = None
        # self.y_std = None
        self.spline = None
        self.n_interp = None
        self.IV = None
    def update_surface(self):
        while True:
            sg = self.surface.values
            status =[]
            for i in range(sg.shape[0]-1):
                flag =0
                for j in range(sg.shape[1]):
                    if not np.isnan(sg[i,j]):
                        
                        if not np.isnan(sg[i+1,j]):
                            flag = 1
                            
                            continue
                        
                        

                status.append(flag)
            idx = 0
            list_ind = []
            for i,j in enumerate(status):
                if i == 0:
                    if not j:
                        if status[i+1]:
                            list_ind.append(self.surface.index[i])
                            # self.surface = self.surface.drop(index=self.surface.index[i])
                        else:
                            list_ind.append(self.surface.index[i+1])
                            # self.surface = self.surface.drop(index=self.surface.index[i+1])
                            idx = i+1
                elif i == idx:
                    continue
                    
                else:  
                    if not j:
                        if idx == i-1:
                            list_ind.append(self.surface.index[i])
                            # self.surface = self.surface.drop(index=self.surface.index[i])
                            idx = i
                            
                        else:
                            list_ind.append(self.surface.index[i+1])
                            # self.surface = self.surface.drop(index=self.surface.index[i+1])
                            idx = i+1
            self.surface = self.surface.drop(index=list_ind)
            if len(status) == sum(status):
                break
        self.update_params()
    def update_params(self):
        self.x = self.surface['ImpliedVolatility'].columns.values
        self.y =  self.surface['ImpliedVolatility'].index.values
        self.X,self.Y = np.meshgrid(self.x,self.y)
        self.Z = self.surface['ImpliedVolatility'].values

    def fwd_moneyness(self):
        """
        df: data frame containing risk free rates for the known expiries, time to expiry in years and D factor.
        returns log forward moneyness
        """
        rfr = self.data[['risk_free_rate','time_to_exp']]
        rfr = rfr.drop_duplicates()
        rfr['DF'] =np.exp(rfr.risk_free_rate*rfr.time_to_exp)
        rfr = rfr.sort_values(by='time_to_exp')
        stk = np.sort(self.surface.index.unique())
        forward_mnyness = []
        spot = self.data.AdjSpot.iloc[0]
        for fct in rfr.DF:
            
            forward_mnyness.append(np.log(stk/(fct*spot)))
        
        forward_mnyness = np.array(forward_mnyness).T   
        for i,st in enumerate(stk):  
            self.stk_dict[st]=forward_mnyness[i,:] 
        self.Y_f = forward_mnyness 
        
    
    def known_data(self):
        points = np.column_stack((self.X.ravel(), self.Y_f.ravel()))
        """
        column_stack(tup)
            Stack 1-D arrays as columns into a 2-D array.
        ravel(...) method of numpy.ndarray instance
            a.ravel([order])
            Return a flattened array.
        """
        values = self.Z.ravel()
        mask = ~np.isnan(values)

        known_points = points[mask]
        known_values = values[mask]
        known_stk = self.Y.ravel()[mask]
        # self.x_mean = known_points[:,0].mean()
        # self.x_std =known_points[:,0].std()
        # self.y_mean = known_points[:,1].mean()
        # self.y_std =known_points[:,1].std()
        

        '''Normalising before fitting bicubic B spline'''

        known_x = np.sqrt(known_points[:,0])# -self.x_mean ) / self.x_std
        known_y = known_points[:,1]# -self.y_mean ) / self.y_std
        self.known_x=known_x
        self.known_y=known_y
        self.known_values = known_values
        
        sorted_x = np.sort(np.unique(known_x))
        # print(f'sorted x :{sorted_x}')
        sorted_exp = np.sort(self.data.AdjExpiry.unique())
        # print(f'sorted exp :{sorted_exp}')
        if len(sorted_x)==len(sorted_exp):
            
            for i in range(len(sorted_x)):
                self.exp_dict[sorted_exp[i]]=sorted_x[i]
        # for i,fwd_mn in enumerate(known_points[:,1]):
        #     if known_stk[i] in self.stk_dict.keys():
        #         self.stk_dict[known_stk[i]].append(fwd_mn)
        #     else:
        #         self.stk_dict[known_stk[i]] = [fwd_mn]
        
        return sorted_exp, known_stk
    

    def gen_spline(self,s =.05):
        if self.interpolator=='bicubic':
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                self.spline = interpolate.SmoothBivariateSpline(
                    self.known_x,
                    self.known_y,
                    self.known_values,
                    s=s
                    )
        else:
            self.spline = interpolate.LinearNDInterpolator(np.column_stack((self.known_x, self.known_y)),self.known_values)
        self.n_interp = interpolate.NearestNDInterpolator(np.column_stack((self.known_x, self.known_y)),self.known_values)
    
    def get_known_iv_surface(self):
        points = np.column_stack([self.known_x,self.known_y])   # scaled coordinates used in fit
        hull = Delaunay(points)
        x_new = np.linspace(self.known_x.min(), self.known_x.max(), 100)
        y_new = np.linspace(self.known_y.min(), self.known_y.max(), 100)
        X_new, Y_new = np.meshgrid(x_new, y_new)
        grid_points = np.column_stack([X_new.ravel(), Y_new.ravel()])
        inside = hull.find_simplex(grid_points) >= 0
        IV = np.full(X_new.size, np.nan)   # everything outside = NaN
        if self.interpolator == 'bicubic':
            IV[inside] = self.spline.ev(
                grid_points[inside, 0],
                grid_points[inside, 1]
            )
        else:
            IV[inside] = self.spline(
                grid_points[inside, 0],
                grid_points[inside, 1]
            )
        IV_inside = IV[inside]
        mask = np.isnan(IV_inside)
        IV_inside[mask] = self.n_interp(grid_points[inside, 0][mask],
                                        grid_points[inside, 1][mask])
        IV[inside] = IV_inside
        IV = IV.reshape(X_new.shape).T
        self.IV = IV
        return IV
    

    def abs_error(self):
        if self.interpolator == 'bicubic':
            iv_fitted = self.spline.ev(self.known_x, self.known_y)
        else:
            iv_fitted = self.spline(self.known_x, self.known_y)
        mask = np.isnan(iv_fitted)
        iv_fitted[mask] = self.n_interp(self.known_x[mask],self.known_y[mask])
        err = iv_fitted - self.known_values
        print("Mean abs error:", np.mean(np.abs(err)))
        print("Max abs error :", np.max(np.abs(err)))

    
        
    def plot_volatility_surface(self,X, Y,elev,azim):
        plt.style.use("default")
        sns.set_style("whitegrid", {"axes.grid": True})

        fig = plt.figure(figsize=(12, 12))
        ax = fig.add_subplot(111, projection="3d")

        ax.plot_surface(
            X, Y, self.IV, cmap="coolwarm", alpha=0.9, linewidth=0, antialiased=True
        )

        ax.set_xlabel("Days to Expiry")
        ax.set_ylabel("Strike")
        ax.set_zlabel("Implied Volatility")
        ax.set_title("Volatility Surface, Spot=166.44,Trade Date = 20190131")
        ax.view_init(elev=elev, azim=azim)

        plt.tight_layout()
        plt.show()

    def plot_surface(self,elev =20,azim=135):
        
        x = np.linspace(self.data.days_to_expiry.min(), self.data.days_to_expiry.max(), 100)
        x = np.rint(x).astype(int)   # round to nearest integer
        y = np.linspace(self.surface.index.min(), self.surface.index.max(), 100)
        X, Y = np.meshgrid(x,y)
        self.plot_volatility_surface(X,Y,elev,azim)

    def scatter_plot_iv_exp(self,ax,exp):
        if self.interpolator == 'bicubic':
            iv_fitted = self.spline.ev(self.known_x, self.known_y)
        else:
            iv_fitted = self.spline(self.known_x, self.known_y)
        mask = np.isnan(iv_fitted)
        iv_fitted[mask] = self.n_interp(self.known_x[mask],self.known_y[mask])
        mask = (self.known_x == self.exp_dict[exp])
        ax.scatter(self.known_y[mask],self.known_values[mask],label='Market')
        ax.scatter(self.known_y[mask],iv_fitted[mask],label='Spline')
        ax.set_title(f'Comparison of IV const exp: Market vs Spline\n Trade Date:{self.data.TradeDate.iloc[0]},expiry date:{exp}')
        ax.legend()
        
    def scatter_plot_iv_stk(self,ax,stk):
        x = np.sort(np.sqrt(self.surface['ImpliedVolatility'].columns.values))
        y = self.stk_dict[stk]
        if self.interpolator == 'bicubic':
            iv_fitted = self.spline.ev(x, y)
        else:
            iv_fitted = self.spline(x, y)
        
        mask = [ind for ind,fwd_mn in enumerate(self.known_y) if fwd_mn in y]
        ax.scatter(self.known_x[mask],self.known_values[mask],label='Market')
        ax.scatter(x,iv_fitted,label='Spline')
        
        ax.set_title(f'IV stk constant\n Market vs SplineTrade Date:{self.data.TradeDate.iloc[0]},stk:{stk}')
        ax.legend()
        

    def get_implied_volatility(self,days_to_exp,risk_free_rate,stk,adjspot):
        days =365        
        time_to_exp = days_to_exp/days
        df = np.exp(risk_free_rate*days_to_exp/days)
        fwd_mn = np.log(stk/df*adjspot)
        x = np.sqrt(time_to_exp) # - self.x_mean) / self.x_std
        y = fwd_mn # - self.y_mean) / self.y_std
        if self.interpolator=='bicubic':
            imp_vol = self.spline.ev(x, y)
        else:
            imp_vol = self.spline(x,y)
        if np.isnan(imp_vol):
            imp_vol = self.n_interp(x,y)

        return imp_vol
    def compute_px(self,flag,adjspot,days_to_expiry,risk_free_rate,stk,fl =True):
        days =365
        imp_vol =  self.get_implied_volatility(days_to_expiry,risk_free_rate,stk,adjspot)
        # imp_vol = max(1e-1,imp_vol)
        # print(imp_vol)
        px = bs(flag,adjspot,stk,days_to_expiry/days,risk_free_rate,imp_vol)
        valid_px = self.data[self.data.px>0].px.min()
        if px<=valid_px:
            px = valid_px
        
        d = delta(flag,adjspot,stk,days_to_expiry/days,risk_free_rate,imp_vol)
        g = gamma(flag,adjspot,stk,days_to_expiry/days,risk_free_rate,imp_vol)
        v = vega(flag,adjspot,stk,days_to_expiry/days,risk_free_rate,imp_vol)
        th = theta(flag,adjspot,stk,days_to_expiry/days,risk_free_rate,imp_vol)
        rh = rho(flag,adjspot,stk,days_to_expiry/days,risk_free_rate,imp_vol)
        if fl:
            return px, d,g,v,th,rh
        else:
            return px
    
    def scatter_plot_px_exp(self,ax,exp):
        data = self.data[['TradeDate','AdjExpiry','CallPut','AdjSpot','days_to_expiry','risk_free_rate','AdjStrike','px']]
        data = data[data.AdjExpiry==exp]
        data['px_cmpt'] = data.apply(lambda x: self.compute_px(x.CallPut,x.AdjSpot,x.days_to_expiry,x.risk_free_rate,x.AdjStrike,fl = False),axis=1)
        ax.scatter(data.AdjStrike,data.px_cmpt.values,label = 'Computed')
        ax.scatter(data.AdjStrike,data.px.values, label = 'Market')
        trade_date = data.TradeDate.iloc[0]
        exp_date = data.AdjExpiry.iloc[0]
        spot = data.AdjSpot.iloc[0]
        ax.set_title(f'Comparison of premium Market vs Computed for:\n Trade Date:{trade_date},expdate:{exp_date}, adjusted spot:{spot}')
        ax.set_xlabel('Strike')
        ax.set_ylabel('Premium')
        ax.legend()
        return data
    def scatter_plot_px_stk(self,ax,stk):
        data = self.data[['TradeDate','AdjExpiry','CallPut','AdjSpot','days_to_expiry','risk_free_rate','AdjStrike','px']]
        data = data[data.AdjStrike==stk]
        data['px_cmpt'] = data.apply(lambda x: self.compute_px(x.CallPut,x.AdjSpot,x.days_to_expiry,x.risk_free_rate,x.AdjStrike,fl = False),axis=1)
        ax.scatter(data.days_to_expiry,data.px_cmpt.values,label = 'Computed')
        ax.scatter(data.days_to_expiry,data.px.values, label = 'Market')
        ax.plot(data.days_to_expiry,data.px_cmpt.values)
        ax.plot(data.days_to_expiry,data.px.values)
        trade_date = data.TradeDate.iloc[0]
        adj_stk = data.AdjStrike.iloc[0]
        spot = data.AdjSpot.iloc[0]
        ax.set_title(f'Comparison of premium Market vs Computed for:\n Trade Date:{trade_date},adjstk:{adj_stk}, adjusted spot:{spot}')
        ax.set_xlabel('Expiry')
        ax.set_ylabel('Premium')
        ax.legend()
        return data

    def plot_simulation_results(self):
        fig = plt.figure(figsize=(20, 20))
        
        # IV comparison exp:
        ind = 1 
        ax = plt.subplot(4,3, 1)
        for i,key in enumerate(self.exp_dict.keys()):
            mid = len(self.exp_dict.keys())//2
            if i in [0,mid,len(self.exp_dict.keys())-1]:
                ax = plt.subplot(4, 3, ind)
                self.scatter_plot_iv_exp(ax,key)
                ind+=1
        # Prem comparison exp
        for i,key in enumerate(self.exp_dict.keys()):
            mid = len(self.exp_dict.keys())//2
            if i in [0,mid,len(self.exp_dict.keys())-1]:
                ax = plt.subplot(4,3, ind)
                data = self.scatter_plot_px_exp(ax,key)
                ind+=1
        # IV comparison stk
        stk_90 = self.data.AdjStrike.iloc[(self.data.AbsMoneyness-90).abs().argmin()]
        stk_110 = self.data.AdjStrike.iloc[(self.data.AbsMoneyness-110).abs().argmin()]
        stk_120 = self.data.AdjStrike.iloc[(self.data.AbsMoneyness-120).abs().argmin()]
        for i,key in enumerate(self.stk_dict.keys()):
            
            
            if key in [stk_90,stk_110,stk_120]:
                ax = plt.subplot(4,3, ind)
                self.scatter_plot_iv_stk(ax,key)
                ind+=1


        for i,key in enumerate(self.stk_dict.keys()):
            spot =self.data.AdjSpot.iloc[0]
            mn = key/spot
            
            if key in [stk_90,stk_110,stk_120]:
                ax = plt.subplot(4,3, ind)
                data = self.scatter_plot_px_stk(ax,key)
                ind+=1

    

