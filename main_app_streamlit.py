# main_app.py

from datetime import datetime
from io import StringIO
import os
import re
import time
import streamlit as st
import sqlite3
import pandas as pd
import sql_db
from prompts.prompts import SYSTEM_MESSAGE
from azure_openai import get_completion_from_messages
from streamlit_js_eval import streamlit_js_eval

def query_database(query, conn):
    """
    Run SQL query and return results in a dataframe
    
    Parameters:
        query (str): The SQL query to be executed
        conn (connection): The database connection object
    
    Returns:
        pandas.DataFrame: The results of the query in a dataframe
    """
    return pd.read_sql_query(query, conn)

def upload_performance_metrics_data():
    """
    Uploads performance results from a CSV file and inserts them into the database.
    
    This function allows the user to upload a CSV file containing performance metrics data.
    It reads the contents of the uploaded file, processes it, and inserts the data into the database.
    The function also displays the contents of the uploaded file and provides feedback on the success of the upload.
    """
    if st.checkbox('Upload Performance Results'):
        # Create an upload file in UI
        uploaded_file = st.file_uploader("Upload Test Results", type="csv")
        if uploaded_file is not None:
            upload = uploaded_file
            # Process the uploaded file
            file_contents = uploaded_file.read().decode('utf-8-sig')
            # st.write("Uploaded file contents:")
            # st.write(uploaded_file.name.split('_')[0])
            # st.write(datetime.strptime(uploaded_file.name.split('_')[1], '%d-%m-%Y-%H-%M-%S'))
            # st.write(datetime.strptime(uploaded_file.name.split('_')[2].split('.')[0], '%d-%m-%Y-%H-%M-%S'))
            # st.write(file_contents)

            try:
                df = pd.read_csv(StringIO(file_contents), skip_blank_lines=True)
            except pd.errors.EmptyDataError:
                st.write("The uploaded file is empty. Please upload a different file.")

            filename_str = os.path.splitext(uploaded_file.name)[0]
            #st.write(filename_str) 

            pattern = r'^[A-Za-z0-9]+[\d.]*_[0-9]{2}-[0-9]{2}-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}$'  
            
            if re.match(pattern, filename_str):                  
                #st.write('Valid String format') 
                cursor = conn.cursor()   
                new_run_id = cursor.execute("SELECT MAX(RunId) + 1 AS NewRunId FROM PerformanceMetrics").fetchone()[0]
                if new_run_id is None:
                    new_run_id = 1
                run_date = datetime.now()
                # Insert the uploaded file into the database.
                for index, row in df.iterrows():
                    data_dict = {
                        "API": row['Label'],
                        "Samples": row['# Samples'],
                        "Average": row['Average'],
                        "Median": row['Median'],
                        "NinetyPercentile": row['90% Line'],
                        "NinetyFivePercentile": row['95% Line'],
                        "NinetyNinePercentile": row['99% Line'],
                        "Minimum": row['Min'],
                        "Maximum": row['Max'],
                        "ErrorPercentage": row['Error %'],
                        "Throughput": row['Throughput'],
                        "ReceivedKBPersecond": row['Received KB/sec'],
                        "StandardDeviation": row['Std. Dev.'],
                        "RunId" : new_run_id,
                        "TestName": uploaded_file.name.split('_')[0],
                        "TestStartTime": datetime.strptime(uploaded_file.name.split('_')[1], '%d-%m-%Y-%H-%M-%S'),
                        "TestEndTime": datetime.strptime(uploaded_file.name.split('_')[2].split('.')[0], '%d-%m-%Y-%H-%M-%S'),
                    }
                    sql_db.insert_data(conn,table_name="PerformanceMetrics", data_dict=data_dict)                       
                
                st.write("File upload was successful.")
            else:  
                st.write("File upload Failed due to Incorrect File format.") 
            time.sleep(4) 
            streamlit_js_eval(js_expressions="parent.window.location.reload()")  
           
            
def generate_sql_queries():
    """
    Generates SQL queries based on user input and displays the results.

    This function prompts the user to enter a message, uses GPT-4 to generate an SQL query based on the message,
    and then executes the SQL query on a database. The generated SQL query and the query results are displayed
    using Streamlit.

    Parameters:
        None

    Returns:
        None
    """
    with col3:
        # Input field for the user to type a message
        user_message = st.text_area("Enter your message:")

        if user_message:
            # Format the system message with the schema
            formatted_system_message = SYSTEM_MESSAGE.format(schema=schemas['PerformanceMetrics'])

            # Use GPT-4 to generate the SQL query
            response = get_completion_from_messages(formatted_system_message, user_message)
            if "```" in response:
                # Find the start and end of the SQL query
                start = response.find('```\n') + 4
                end = response.find('\n```', start)

                # Extract the SQL query
                query = response[start:end]
            else:
                query = response

            st.write("Generated Message for the prompt:")
            st.code(response)
            # Display the generated SQL query
            st.write("Generated SQL Query:")
            st.code(query, language="sql")
            try:
                # Run the SQL query and display the results
                sql_results = query_database(query, conn)
                st.write("Query Results:")
                st.dataframe(sql_results)

            except Exception as e:
                st.write(f"An error occurred: {e}")

def generate_testresults_summary():
    """
    This function generates table for test results history which has run details. The query results are displayed
    using Streamlit.

    Parameters:
        None

    Returns:
        None
    """
    with col2:
        st.header("Test Results History")
        query = "select distinct top 10  RunId,TestName,TestStartTime,TestEndTime FROM [dbo].[PerformanceMetrics] order by RunId Desc"
        try:
                # Run the SQL query and display the results
                sql_results = query_database(query, conn)
                sql_results = sql_results.rename(columns={'RunId': 'Run ID', 'TestName': 'Test Name', 'TestStartTime': 'Test StartTime', 'TestEndTime': 'Test EndTime'})
                st.dataframe(sql_results, hide_index=True,width=4500)

        except Exception as e:
                st.write(f"An error occurred: {e}")
        
if __name__ == "__main__":
    # Create or connect to SQL Server database
    conn = sql_db.create_connection()
    st.set_page_config(layout="wide")
    col1, col2, col3, col4 = st.columns([0.5, 2, 2, 0.5])

    # Generate test results summary
    generate_testresults_summary()
    # Schema Representation for finances table
    schemas = sql_db.get_schema_representation()
    with col3:
        st.header("Perf Analyzer-Chatbot")
        upload_performance_metrics_data()
        generate_sql_queries()
    
