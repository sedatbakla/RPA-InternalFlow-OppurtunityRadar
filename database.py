<<<<<<<<< Temporary merge branch 1
#main connection file to database

import pandas as pd
import sqlite3 #database we are going to use

DATABASE_NAME = "arya.db"  

def get_connection():  #creaiting a connection.
   try:
        conn = sqlite3.connect(DATABASE_NAME)
        return conn
   except sqlite3.Error as e:  #testing the connection.
        print(f"Veritabanına bağlanırken bir hata oluştu: {e}")
        return None

def get_all_flows():  #Retrieve all flows from the database
    conn=get_connection()  

    df=pd.read_sql(
        "SELECT * FROM flows",conn  #Retrieve flows from the database
    )
    conn.close()  #closing the connection
    return df  


def get_taxonomy():
    conn = get_connection()

    df = pd.read_sql(
        "SELECT * FROM taxonomy",conn
    )
    conn.close()
    return df


def save_scores(df):  #The scores has been calculated , is going to new table.

    conn = get_connection()

    df.to_sql(
        name="flow_scores",
        con=conn,
        if_exists="replace",
        index=False
    )

    conn.close()

print("Flow scores table created.")


def save_classification(df):

    conn = get_connection()

    df.to_sql(
        "flow_classification",
        conn,
        if_exists="replace",
        index=False
    )

    conn.close()
    
print("Classification table created.")

#main connection file to database


import pandas as pd
import sqlite3 #database we are going to use

DATABASE_NAME = "arya.db"  

def get_connection():  #creaiting a connection.
   try:
        conn = sqlite3.connect(DATABASE_NAME)
        return conn
   except sqlite3.Error as e:  #testing the connection.
        print(f"Veritabanına bağlanırken bir hata oluştu: {e}")
        return None

def get_all_flows():  #Retrieve all flows from the database
    conn=get_connection()  

    df=pd.read_sql(
        "SELECT * FROM flows",conn  #Retrieve flows from the database
    )
    conn.close()  #closing the connection
    return df  


def get_taxonomy():
    conn = get_connection()

    df = pd.read_sql(
        "SELECT * FROM taxonomy",conn
    )
    conn.close()
    return df


def save_scores(df):  #The scores has been calculated , is going to new table.

    conn = get_connection()

    df.to_sql(
        name="flow_scores",
        con=conn,
        if_exists="replace",
        index=False
    )

    conn.close()

print("Flow scores table created.")


def save_classification(df):

    conn = get_connection()

    df.to_sql(
        "flow_classification",
        conn,
        if_exists="replace",
        index=False
    )

    conn.close()
    
print("Classification table created.")

