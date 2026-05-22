from .data_extractor_v3 import DataExtractor as data_extractor
#from gen_pnl_v1 import*
#from . import data_preprocessor
from .connector import *
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import as_completed
import warnings
warnings.filterwarnings("ignore")
import json
path = os.path.dirname(os.path.abspath(__file__))
file_path =  os.path.join(path,'..','data.json')
with open(file_path, "r") as f:
    generation_data = json.load(f)


def gen_data(mn,cp,sym,ex,type):

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
    
    data_gen = data_extractor(interpolator='linear',callput=cp,symbool=sym,delta = delta,mn = moneyness,expiry =ex)
    

    
    print(f'generating {key}')
    out_data = data_gen.gen_data(delta=delta,bydelta=bydelta ,time_to_expiry =ex,callput = cp,bot =1,moneyness=moneyness,
                                hold=ex,symbool=sym,multiprocess=True)
    out_dict = {key : out_data}
    return out_dict

    
        
    



# data_gen = DataExtractor(interpolator='linear')
def generate_data_by_exp(ex,type = 'delta'):
    params_list = []
    # if type =='delta':
    #     deltas = [5,10,15,20,25,30]
    # else:
    for sym in generation_data['symbol']:    
        for cp in generation_data['callput']:
            if type =='delta':
                deltas = generation_data['delta']
            else:
                if cp =='c':
                    deltas = generation_data['mn_call']
                elif cp == 'p':
                    deltas = generation_data['mn_put']

        
            for delta in deltas:
                params_list.append((delta,cp,sym,ex,type))

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
            
                    
def get_options_data(by = 'mn',db = True):
    if not db:
        df = pd.read_csv(os.path.join(os.getcwd(),'Data','AAPL_master_data.csv'))
    
    
    
    # for sym in symbool:
    # for cp in callput:
    for ex in generation_data['exp']:
        
        results = generate_data_by_exp(ex,type = by)
        for item in results:
            for k,v in item.items():
                
                no_records = v['count']
                df_op = v['df_options']
                print(f'{k} total records:{len(df_op)},backfilled: {no_records} ')
                df_op = v['df_options']
                df_or = df_op.drop(columns=['TradeStart'])
                
                if not db:
                    df = pd.concat([df,df_or[df_or.Flag==1]],ignore_index=True)
                    df = df.drop_duplicates(subset=['TradeDate', 'ExpiryDate','CallPut','Strike'])
                else:
                    populate_table(df_or[df_or.Flag==1],"OPTIONS_DATA")
                    write_opt_key(k)
                    
                    df_opt = df_op[['TradeStart','TradeDate', 'AdjExpiry','AdjStrike','CallPut']]
                    df_opt['OptionKey'] = k
                    populate_table(df_opt[['OptionKey','TradeStart','TradeDate', 'AdjExpiry','AdjStrike','CallPut']],'CONNECTION')
                
        if not db:
            df.to_csv(os.path.join(os.getcwd(),'Data','AAPL_master_data.csv'),index=False)

def generate_data():
    for item in ('mn','delta'):
        get_options_data(by=item)