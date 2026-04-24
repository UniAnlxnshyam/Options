from .data_extractor_v3 import DataExtractor as data_extractor
#from gen_pnl_v1 import*
from . import data_preprocessor
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import as_completed
import warnings
warnings.filterwarnings("ignore")


def gen_data(mn,cp,sym,ex,type,start):

    if type == 'delta':
        delta = mn
        bydelta = True
        key = f'delta_{mn}_{cp}_{sym}_{ex}'
        moneyness = None
    else:
        moneyness = mn
        delta = None
        bydelta = False    
        key = f'mn_{mn}_{cp}_{sym}_{ex}'
    
    data_gen = data_extractor(interpolator='linear',callput=cp,symbool=sym)
    if start:
        out_data = data_gen.extract_data(delta=delta,bydelta=bydelta ,expiry_in_months=ex,callput = cp,bot =1,moneyness=moneyness,
                                         hold=ex,symbool=sym,)

    else:
        print(f'generating {key}')
        out_data = data_gen.gen_data(delta=delta,bydelta=bydelta ,time_to_expiry =ex,callput = cp,bot =1,moneyness=moneyness,
                                    hold=ex,symbool=sym,start_date = 20100121,multiprocess=True)
    out_dict = {key : out_data}
    return out_dict

    
        
    



# data_gen = DataExtractor(interpolator='linear')
def generate_data(cp,sym,ex,type = 'delta',start = False):
    params_list = []
    # if type =='delta':
    #     deltas = [5,10,15,20,25,30]
    # else:
    for sym in ['SP','EV']:    
        for cp in ['c','p']:
            if type =='delta':
                deltas = [5,10,15,20,25,30]
            else:
                if cp =='c':
                    deltas = [100,110,120]
                elif cp == 'p':
                    deltas = [80,90,100]

        
            for delta in deltas:
                params_list.append((delta,cp,sym,ex,type,start))

        # key = f'mn_{mn}_{cp}_{sym}_{ex}'

        # if key in data_dict.keys():
        #     continue
        # print(f'generating {key}')
    
        # df_op,msg_data = data_gen.gen_data(delta=mn,bydelta=True,time_to_expiry = ex,callput = cp,bot =1,hold=ex,symbool=sym,start_date = 20100121)
    
    
    with ProcessPoolExecutor() as executor:
        futures = []
        for params in params_list:
        
        
            fut = executor.submit(gen_data, *params)
            
            futures.append(fut)
        result = [f.result() for f in futures]  
        
    return result
            
                    
    