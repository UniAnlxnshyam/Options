from .misc import *
import argparse

def main(args):
    sizing = args.sizing
    if sizing==None:
        sizing='notional'
    value = args.value
    if value == None:
        value =1
    dh = args.dh
    if dh==None:
        dh = 'off'
    if args.percent==None:
        percent =1
    option_request(callput = args.cp, buysell = args.buysell,symbol=args.symbol,maturity=args.exp,mn_dt=args.mn_dt,strike=args.stk,bot=args.bot,
                   close=args.hold, sizing=sizing,value=value,dh=dh,percent=percent,savingpath=args.path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cp", required=True)
    parser.add_argument("--buysell", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--exp",type = int,required=True)
    parser.add_argument("--mn_dt", required=True)
    parser.add_argument("--stk",type=int, required=True)
    parser.add_argument("--bot", type=int,required=True)
    parser.add_argument("--hold", type=int,required=True)
    parser.add_argument("--sizing")
    parser.add_argument("--value", type=int)
    parser.add_argument("--dh")
    parser.add_argument("--percent", type=int)
    parser.add_argument("--path", required=True)
    args = parser.parse_args()
  
    main(args)