# sql_db.py

import csv
from datetime import date, timedelta
from gettext import npgettext
import random
from sqlite3 import Error
import sqlite3

import pyodbc
from tqdm import tqdm

import numpy as np
import pandas as pd


DATABASE_NAME = "expenseManager"
server = 'expensemgr.database.windows.net'
username = 'SQLadmin' 
password = 'password$123'
connection_url = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={DATABASE_NAME};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30';


def create_connection():
    """ 
    Create or connect to an SQLite database 
    
    Returns:
        conn: Connection object to the SQLite database
    """
    conn = None;
    try:
        conn = pyodbc.connect(connection_url)
    except Error as e:
        print(e)
    return conn


def create_table(conn, create_table_sql):
    """
    Create a table with the specified SQL command.

    Args:
        conn: The connection object to the database.
        create_table_sql: The SQL command to create the table.

    Returns:
        None
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)


def insert_data(conn, table_name, data_dict):
    """
    Insert a new data into a table.

    Parameters:
    conn (Connection): The database connection object.
    table_name (str): The name of the table to insert data into.
    data_dict (dict): A dictionary containing the data to be inserted, where the keys represent the column names and the values represent the corresponding values.

    Returns:
    int: The ID of the last inserted row.
    """
    columns = ', '.join(data_dict.keys())
    placeholders = ', '.join('?' * len(data_dict))
    sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    cur = conn.cursor()
    # Convert numpy.int64 values to int
    values = [int(value) if isinstance(value, np.int64) else value for value in data_dict.values()]
    cur.execute(sql, values)
    conn.commit()
    # Fetch the ID of the last inserted row
    cur.execute("SELECT SCOPE_IDENTITY()")
    lastrowid = cur.fetchone()[0]
    return lastrowid


def query_database(query):
    """
    Run SQL query and return results in a dataframe.

    Parameters:
    query (str): The SQL query to be executed.

    Returns:
    pandas.DataFrame: The results of the query in a dataframe.
    """
    conn = create_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# Create a Performance Metrics table
def setup_performance_metrics_table():
    """
    Creates the API_Performance table in the database and inserts data from a CSV file.

    This function creates the API_Performance table with the specified columns in the database.
    It then reads data from a CSV file and inserts each row into the API_Performance table.

    Args:
        None

    Returns:
        None
    """
    conn = create_connection()
    cursor = conn.cursor()  
    sql_create_performance_metrics_table = """
    CREATE TABLE API_Performance (
        API VARCHAR(255),
        Samples INT,
        Average DECIMAL(10, 2),
        Median DECIMAL(10, 2),
        NintyPercentage DECIMAL(10, 2),
        NintyFivePercentage DECIMAL(10, 2),
        NintyNinePercentage DECIMAL(10, 2),
        Minimum INT,
        Maximum INT,
        ErrorPercentage VARCHAR(10),
        Throughput DECIMAL(10, 2),
        ReceivedKBPersecond DECIMAL(10, 2),
        StandardDeviation DECIMAL(10, 2),
        RunId INT,
        RunDate DATE
    );
    """
    # create_table(conn, sql_create_performance_metrics_table)

    with open('PerfMetrics.csv', 'r') as csv_file:
        # Create a CSV reader
        csv_reader = csv.reader(csv_file)

        # Skip the header row
        next(csv_reader)

        # Insert each row into the PerformanceMetrics table
        for row in csv_reader:
            cursor.execute("""
                INSERT INTO PerformanceMetrics (
                    API, Samples, Average, Median, NintyPercentage, NintyFivePercentage, NintyNinePercentage, 
                    Minimum, Maximum, ErrorPercentage, Throughput, ReceivedKBPersecond, 
                    StandardDeviation, RunId, RunDate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, row)

    # Commit the changes and close the connection
    conn.commit()
    conn.close()


def get_schema_representation():
    """ 
    Get the database schema in a JSON-like format 
    
    Returns:
        dict: A dictionary representing the database schema, where the keys are table names and the values are dictionaries representing column details.
    """
    conn = create_connection()
    cursor = conn.cursor()
    
    # Query to get all table names
    cursor.execute("SELECT table_name, column_name, data_type, is_nullable,column_default FROM information_schema.columns WHERE table_name = 'PerformanceMetrics'")
    tables = cursor.fetchall()
    
    db_schema = {}
    
    for table in tables:
        table_name = table[0]
        columns = cursor.fetchall()        
        column_details = {}
        for column in columns:
            column_name = column[1]
            column_type = column[2]
            column_details[column_name] = column_type
        
        db_schema[table_name] = column_details
    
    conn.close()
    return db_schema


# This will create the table and insert 100 rows when you run sql_db.py
if __name__ == "__main__":

    # Setting up the Performance Metrics table
    setup_performance_metrics_table()

    # Querying the database
    print(query_database("SELECT * FROM PerformanceMetrics"))

    # Getting the schema representation
    print(get_schema_representation())
