from data_extractor_v1 import*
#from gen_pnl_v1 import*
from data_preprocessor import*
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import as_completed
import warnings
warnings.filterwarnings("ignore")
df = pd.read_csv(os.path.join(os.getcwd(),'Data/AAPL_master_data.csv'))

print(df.shape)

def gen_data(mn,cp,sym,ex):

    
    key = f'mn_{mn}_{cp}_{sym}_{ex}'
    print(key)
    data_gen = DataExtractor(interpolator='linear')
    print(f'generating {key}')
    out_data = data_gen.gen_data(delta=mn,bydelta=True,time_to_expiry =ex,callput = cp,bot =1,
                                 hold=ex,symbool=sym,start_date = 20100121,multiprocess=True)
    out_dict = {key : out_data}
    return out_dict
    
        
    
deltas = [5,10,15,20,25,30]

# data_gen = DataExtractor(interpolator='linear')
def generate_data(cp,sym,ex):
    
    params_list = []
    for delta in deltas:
        params_list.append((delta,cp,sym,ex))

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
            
                    
    