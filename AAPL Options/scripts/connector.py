import mysql.connector
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import os


load_dotenv()
pwd = os.getenv("DB_PASSWORD")
allowed_tables = {"OPTIONS_DATA", "RISK_FREE_RATES", "AAPL_SPOT","OPTION_KEY","CONNECTION"}

def get_db():
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password=pwd,
        database="test_db"
    )

    cursor = conn.cursor()
    return conn, cursor


def get_cols_info(df):
    col_dict = {}
    for col in df.columns:
        
        if pd.api.types.is_object_dtype(df[col]):
            length = len(df[col].iloc[0])
            dt = 'object'
        elif df[col].dtype==np.float64:
            dt = 'f64'
            length = 'na'

        elif df[col].dtype==np.int32:
            dt = 'int32'
            length = 'na'
        col_dict[col] = {'col_type':dt,'length':length}
    return col_dict

def create_table_query(col_dict,name):
    query = f'CREATE TABLE {name} ('
    populate_query = f'INSERT IGNORE INTO {name} VALUES('
    for k,v in col_dict.items():
        populate_query+= "%s,"
        if v['col_type'] == 'object':
            length = v['length']
            typ = f'CHAR({length})'


            query+=f'{k} {typ}, '
            
        
        elif v['col_type'] =='f64':
            typ = f'DOUBLE'


            query+=f'{k} {typ}, '
        else:
            typ = f'INT'

            query+=f'{k} {typ}, '
    if name == "OPTIONS_DATA":
        pk = 'PRIMARY KEY (TradeDate, AdjExpiry,AdjStrike,CallPut));'
    else: 
        pk = 'PRIMARY KEY (TradeDate));'
    
    query += pk
    populate_query = populate_query.strip(',')
    populate_query+= ')'

    return query,populate_query



        


def create_tabels(df,name):
    col_dict = get_cols_info(df)
    query,_ = create_table_query(col_dict,name)

    conn, cursor = get_db()
    # cursor.execute("SELECT DATABASE();")
    cursor.execute('USE test_db')
    cursor.execute(query)
    conn.commit()
    cursor.close()

def populate_table(df,name):
    col_dict = get_cols_info(df)
    df = df.replace({np.nan: None, pd.NA: None})
    
    _,populate_query = create_table_query(col_dict,name)
    data = list(df.itertuples(index=False, name=None))
    conn, cursor = get_db()
    # cursor.execute("SELECT DATABASE();")
    cursor.execute('USE test_db')
    batch_size = 1000
    for i in range(0, len(data), batch_size):
        chunk = data[i:i+batch_size]
        cursor.executemany(populate_query, chunk)
        conn.commit()
    cursor.close()
    
def drop_table(name):
    conn, cursor = get_db()
    # cursor.execute("SELECT DATABASE();")
    cursor.execute('USE test_db')
    
    if name in allowed_tables:
        cursor.execute(f"DROP TABLE {name}")
    else:
        raise ValueError("Invalid table name")
    
    conn.commit()
    cursor.close()

def print_tabels():
    conn, cursor = get_db()
    # cursor.execute("SELECT DATABASE();")
    cursor.execute('USE test_db')
    cursor.execute('SHOW TABLES')

    tables = cursor.fetchall()
    cursor.close()
    return tables
def get_cols(tablename):
    conn, cursor = get_db()
    # cursor.execute("SELECT DATABASE();")
    cursor.execute('USE test_db')
    cursor.execute(f"DESCRIBE {tablename};")
    cols = cursor.fetchall()
    cursor.close()
    return cols

def create_secondary_tabels():
    conn, cursor = get_db()
    cursor.execute('USE test_db')
    cursor.execute("CREATE TABLE  OPTION_KEY(OptionKey VARCHAR(50) PRIMARY KEY); ")
    cursor.execute("""CREATE TABLE  CONNECTION(OptionKey VARCHAR(50), TradeStart INT,TradeDate INT,
                   AdjExpiry INT,AdjStrike DOUBLE,CallPut CHAR(1),
                   PRIMARY KEY (OptionKey, TradeStart,TradeDate, CallPut),FOREIGN KEY (OptionKey)
                   REFERENCES OPTION_KEY(OptionKey),FOREIGN KEY (TradeDate, AdjExpiry,AdjStrike,CallPut)
                   REFERENCES OPTIONS_DATA(TradeDate, AdjExpiry,AdjStrike,CallPut));""")
    
    conn.commit()
    cursor.close()
def write_opt_key(key):
    conn, cursor = get_db()
    cursor.execute('USE test_db')
    cursor.execute(f'INSERT IGNORE INTO OPTION_KEY (OptionKey) VALUES (%s);',(key,))
    conn.commit()
    cursor.close()

def check_key(key):
    conn, cursor = get_db()
    cursor.execute("""
    SELECT EXISTS (
        SELECT 1
        FROM OPTION_KEY
        WHERE OptionKey = %s
    )
    """, (key,))

    exists = cursor.fetchone()[0]
    cursor.close()
    return exists

def extract_from_db(key):
    conn, cursor = get_db()
    df = pd.read_sql(f"""SELECT a.* FROM OPTIONS_DATA a RIGHT JOIN CONNECTION b
                     ON a.TradeDate = b.TradeDate and a.AdjExpiry = b.AdjExpiry
                     and a.AdjStrike = b.AdjStrike and a.CallPut = b.CallPut    
                     WHERE b.OptionKey='{key}' ORDER by AdjExpiry, TradeDate;""",conn)

    cursor.close()                                                                              


    return df
def extract_start_data(key):
    conn, cursor = get_db()
    df = pd.read_sql(f"""SELECT a.* FROM OPTIONS_DATA a RIGHT JOIN CONNECTION b
                     ON a.TradeDate = b.TradeDate and a.AdjExpiry = b.AdjExpiry
                     and a.AdjStrike = b.AdjStrike and a.CallPut = b.CallPut    
                     WHERE b.OptionKey='{key}' and b.TradeStart = b.TradeDate ORDER by TradeDate;""",conn)

    cursor.close()                                                                              


    return df


def load_full_data(callput,symbool):
    conn, cursor = get_db()

        

    df = pd.read_sql(f'SELECT * FROM OPTIONS_DATA WHERE CallPut="{callput}" and Symbol="{symbool}"',conn)
    for col in df.columns:
    
        if df[col].dtype==np.int64:
            df[col] = df[col].astype('int32')
    rates = pd.read_sql('SELECT * FROM RISK_FREE_RATES',conn)
    for col in rates.columns:
    
        if rates[col].dtype==np.int64:
            rates[col] = rates[col].astype('int32')

    spot_data = pd.read_sql('SELECT * FROM AAPL_SPOT',conn)
    for col in spot_data.columns:
    
        if spot_data[col].dtype==np.int64:
            spot_data[col] = spot_data[col].astype('int32')
    cursor.close()
    conn.close()

    return df, rates, spot_data

