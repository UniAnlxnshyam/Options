from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from enum import Enum
from .gen_pnl_modified import *
from typing import Literal
import json

class Option(str, Enum):
    call = "c"
    put = "p"

class BuySell(str, Enum):
    buy = 'buy'
    sell = 'sell'
class Symbol(str, Enum):
   sp = 'SP'
   ev = 'EV'
class Mn_Dt(str, Enum):
    mn = 'mn'
    dt = 'delta'
class Sizing(str, Enum):
    notional = 'notional'
    premium = 'premium'
    contracts = 'contracts'
class DeltaHedging(str, Enum):
    on = 'on'
    off = 'off'
 

    
    
class Item(BaseModel):
    option       : Option
    buysell      : BuySell
    symbol       : Symbol
    maturity     : int
    mn_dt        : Mn_Dt
    strike       : int
    open         : int
    close        : int
    sizing       : Sizing
    value        : int
    dh           : DeltaHedging
    percent      : int
    pnl          : Literal[0, 1]
def get_pnl_wealth(data):
    if data['mn_dt'].value=='delta':
        delta = data['strike']
        mn = None
        bydelta = True
    else:
        delta = None
        mn = data['strike']
        bydelta = False
    opt_pnl = gen_options_pnl(delta = delta,bydelta=bydelta,moneyness=mn,time_to_expiry=data['maturity'],callput=data['option'].value,
                              bot=data['open'],hold=data['close'],symbool=data['symbol'].value,dh = data['dh'].value)
    opt_pnl,wealth = wealth_computation(opt_pnl,sizing = data['sizing'].value,hold = data['close'],dh = data['dh'].value,pct = data['percent'])

    return opt_pnl.to_json(orient = 'split'),wealth.to_json(orient='split')


app = FastAPI()

@app.post("/items/")
async def get_data(item: Item):
    data = item.model_dump()
    pnl,wealth = await run_in_threadpool(get_pnl_wealth, data)

    if data['pnl']==1:
        out =  {'pnl':pnl,'wealth':wealth}
    else:
        out = {'wealth':wealth}

    return out



    


