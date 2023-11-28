# main_app.py

from datetime import datetime
from io import StringIO
import streamlit as st
import sqlite3
import pandas as pd
import sql_db
from prompts.prompts import SYSTEM_MESSAGE
from azure_openai import get_completion_from_messages

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
        # Read the boolean value from the text file
        with open('myfile.txt', 'r') as f:
            value = f.read()
            upload = value == 'True'
            
        if uploaded_file is not None and upload:
            upload = uploaded_file
            # Process the uploaded file
            file_contents = uploaded_file.read().decode('utf-8-sig')
            st.write("Uploaded file contents:")
            st.write(file_contents)

            try:
                df = pd.read_csv(StringIO(file_contents), skip_blank_lines=True)
            except pd.errors.EmptyDataError:
                st.write("The uploaded file is empty. Please upload a different file.")
            cursor = conn.cursor()   
            new_run_id = cursor.execute("SELECT MAX(RunId) + 1 AS NewRunId FROM PerformanceMetrics").fetchone()[0]
            run_date = datetime.now()
            # Insert the uploaded file into the database
            for index, row in df.iterrows():
                data_dict = {
                    "API": row['API'],
                    "Samples": row['Samples'],
                    "Average": row['Average'],
                    "Median": row['Median'],
                    "NintyPercentage": row['NintyPercentage'],
                    "NintyFivePercentage": row['NintyFivePercentage'],
                    "NintyNinePercentage": row['NintyNinePercentage'],
                    "Minimum": row['Minimum'],
                    "Maximum": row['Maximum'],
                    "ErrorPercentage": row['ErrorPercentage'],
                    "Throughput": row['Throughput'],
                    "ReceivedKBPersecond": row['ReceivedKBPersecond'],
                    "StandardDeviation": row['StandardDeviation'],
                    "RunId" : new_run_id,
                    "RunDate": run_date,
                }
                sql_db.insert_data(conn,table_name="PerformanceMetrics", data_dict=data_dict)
            st.write("Uploaded file inserted into database successfully.")
            # Create a text file and write a boolean value to it
            with open('myfile.txt', 'w') as f:
                f.write(str(False))  # Convert the boolean to a string before writing
            
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
    st.write("Enter your message to generate SQL and view results.")

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
        with open('myfile.txt', 'w') as f:
            f.write(str(True))  # Convert the boolean to a string before writing
        
def createTextFile():
    # Create a text file and write a boolean value to it
    with open('myfile.txt', 'w') as f:
        f.write(str(True))  # Convert the boolean to a string before writing

if __name__ == "__main__":
    # Create or connect to SQL Server database
    conn = sql_db.create_connection()

    # Schema Representation for finances table
    schemas = sql_db.get_schema_representation()
    st.title("Performance Analyzer with GPT-4")
    createTextFile()
    upload_performance_metrics_data()
    generate_sql_queries()
    
