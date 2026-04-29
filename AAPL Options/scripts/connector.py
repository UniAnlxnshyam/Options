import mysql.connector
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import os


load_dotenv()
pwd = os.getenv("DB_PASSWORD")
allowed_tables = {"OPTIONS_DATA", "RISK_FREE_RATES", "AAPL_SPOT"}

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








