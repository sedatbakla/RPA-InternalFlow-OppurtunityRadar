import pandas as pd #the dictionary we going to use.
from database import get_connection #our main db file in this project so we need to connect them.

def import_flows():
    conn = get_connection()  #connetcion with db

    df = pd.read_csv("Templates/Data/flow_catalog_sample.csv")  # pandas is reading this file as data frame
    df.to_sql(        
        name="flows", #file name in db
        con=conn,     #A link opens for each section.
        if_exists="replace", #if this file exist in sqlite,the last file will take the old ones place.
        index=False
    )

    conn.close()  #and the opened connection is closed; the reason for this is to prevent memory leaks.

    print("Flows table created")

def import_taxonomy():

    conn = get_connection()

    df = pd.read_csv("Templates/Data/task_capability_taxonomy.csv")

    df.to_sql(
        name="taxonomy",
        con=conn,
        if_exists="replace",
        index=False
    )

    conn.close()

    print("Taxonomy table created.")


def main():  #Beginning of the program.

    import_flows()      #The files are transferred to the database.

    import_taxonomy()

    print("All datas is in sqlite")

if __name__ == "__main__":  
    main() 
