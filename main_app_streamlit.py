# main_app.py

from datetime import datetime
from io import StringIO
import os
import re
import time
import streamlit as st
import sqlite3
import io
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

def generate_testresults_history():
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

def generate_testresults_summary():
    """
    This function generates table for test results summary. The results are displayed
    using Streamlit.

    Parameters:
        None

    Returns:
        None
    """
    
    st.header("Test Results Summary")
    # Create an upload file in UI
    uploaded_file = st.file_uploader("Upload Test Results", type="csv")
    if uploaded_file is not None:
        upload = uploaded_file
        # Process the uploaded file
        file_contents = uploaded_file.read().decode('utf-8-sig')
        data = pd.read_csv(io.StringIO(file_contents))

        # Global Configuration Start, TBD to be updated in Config or .env file
        acceptable_error_percentage = 5
        sla_configuration_secs = 1
        # Global Configuration End

        sla_config_millsec = sla_configuration_secs * 1000

        # Get the data of last row, column 'Throughput'        
        overall_rps = data.loc[data['Label'] == 'TOTAL', 'Throughput'].values[0]  

        error_percentage_str = data.loc[data['Label'] == 'TOTAL', 'Error %'].values[0]  
        error_perc_decimal = float(error_percentage_str[:-1])         
        if error_perc_decimal > acceptable_error_percentage:
            test_status = "FAIL"
            teststatus_html = f'<t5r><td><b>TestStatus</b></td><td style="color:red;">{test_status}</td></tr>'
        else:
            test_status = "PASS"
            teststatus_html = f'<t5r><td><b>TestStatus</b></td><td style="color:Green;">{test_status}</td></tr>'
         
        total_samples_count = data.loc[data['Label'] == 'TOTAL', '# Samples'].values[0]          
        failed_samples_count = round(total_samples_count * (error_perc_decimal / 100))   
        passed_samples_count = total_samples_count - failed_samples_count
        samples_with_sla_count = len(data[(data['Label'] != 'TOTAL') & (data['90% Line'] <= sla_config_millsec)]['Label'].unique())   
        samples_with_no_sla_count = len(data[(data['Label'] != 'TOTAL') & (data['90% Line'] > sla_config_millsec)]['Label'].unique())   
        labels = data[(data['Label'] != 'TOTAL') & (data['90% Line'] > sla_config_millsec)][['Label', '90% Line']]          

        test_start_time = datetime.strptime(uploaded_file.name.split('_')[1], '%d-%m-%Y-%H-%M-%S')
        test_end_time =datetime.strptime(uploaded_file.name.split('_')[2].split('.')[0], '%d-%m-%Y-%H-%M-%S')
        
        duration = test_end_time - test_start_time

        minutes = duration.seconds // 60
        seconds = duration.seconds % 60
        
        
        duration_str = '{:02d}:{:02d}'.format(minutes, seconds)

        # Required for debugging, To be deleted in final version
        # print("################## TestSummary ##################")
        # print("Test Status :",test_status)
        # print("RequestPerSecond Achieved :",overall_rps)

        # print("*************Test Configuration *************")
        # print("StartTime :",test_start_time)
        # print("EndTime :",test_end_time)
        # print("Run Duration :",duration_str)

        # print("*************Test Execution Summary *************")
        # print("Transactions :",total_samples_count)
        # print("Passed :",passed_samples_count)
        # print("Failed :",failed_samples_count)
        # print("Meeting SLA (1 sec):",samples_with_sla_count)
        # print("Not Meeting SLA (1 sec): :",samples_with_no_sla_count)

        # print("************* Transactions-Not Meeting SLA(90th Percentile) *************")
        # print(labels)

        dft = pd.DataFrame(labels)        
        
        # Define the layout of the table
        table_layout = """
        <style>
        table {
        border-collapse: collapse;
        width: 90%;
        }

        th, td {
        text-align: left;
        padding: 8px;
        border: 1px solid black;
        }

        </style>
        """
        table_html = f'<table>{table_layout}'        
        
        table_header = f'<tr><th colspan="3" style="text-align:center;">Performance Test Summary</th></tr>'
        rps_html = f'<tr><td><b>RequestPerSecond</b></td><td>{overall_rps}</td></tr>'  
        testconfig_html = f'<tr><td><b>Test Configuration</b></td><td><table><tr><td>Run Duration</td><td>{duration_str}</td></tr><tr><td>StartTime</td><td>{test_start_time}</td></tr><tr><td>EndTime</td><td>{test_end_time}</td></tr></table></td></tr>'        
        test_execution_summary_html = f'<tr><td><b>Test Execution Summary</b></td><td><table><tr><td>Transactions</td><td>{total_samples_count}</td></tr><tr><td>Passed</td><td style="color:Green;">{passed_samples_count}</td></tr><tr><td>Failed</td><td style="color:red;">{failed_samples_count}</td></tr><tr><td>Meeting SLA ({sla_configuration_secs} sec):</td><td style="color:Green;">{samples_with_sla_count}</td></tr><tr><td>Not Meeting SLA ({sla_configuration_secs} sec)</td><td style="color:Red;">{samples_with_no_sla_count}</td></tr></table></td></tr>'

        stable_html = f'<table>'
        for row in dft.values:            
            table_row = '<tr>'
            for value in row:                
                table_row += f'<td>{value}</td>'
            table_row += '</tr>'
            stable_html += table_row
        stable_html += '</table>'              

        sla_table_html = f'<tr><td><b>Transactions-Not Meeting SLA(90th Percentile)</b></td><td>{stable_html}</td></tr>'
        table_html += table_header + teststatus_html + rps_html + testconfig_html + test_execution_summary_html +sla_table_html                                          
        
        table_html += '</table>'              
        html_code = f"""
        {table_html}
        """

        #print(html_code)
        st.markdown(html_code, unsafe_allow_html=True)
        
        # Set up the SMTP server  
        smtp_server = 'smtp.office365.com'  
        smtp_port = 587  
        smtp_username = 'savvysouls@vk4421.onmicrosoft.com'
        smtp_password = 'kGZ-i.e37tKFaXG'  
        message_body = 'Hi Team, Please find the performance Test Report. '
        test_report_name = uploaded_file.name.split('_')[0] + '_PerfTestReport.html'

        receiver_emails = ['angolla@microsoft.com','Taniya.Gupta@microsoft.com','Anvesh.Bonagiri@microsoft.com','shpunnam@microsoft.com']

        # Create the email message  
        msg = MIMEMultipart()  
        msg['From'] = 'savvysouls@vk4421.onmicrosoft.com'  
        #msg['To'] = ['angolla@microsoft.com','Taniya.Gupta@microsoft.com']
        msg['To'] = ", ".join(receiver_emails)  
        msg['Subject'] = 'PerformanceTestReport'  
        
        
        # Add the HTML text as a MIMEText object          
        msg.attach(MIMEText(message_body, 'plain'))  
        
        # Add the HTML text as an attachment  
        attachment = MIMEApplication(html_code.encode('utf-8'), _subtype='html')  
        attachment.add_header('Content-Disposition', 'attachment', filename=test_report_name)  
        msg.attach(attachment)  
        
        # Send the email  
        with smtplib.SMTP(smtp_server, smtp_port) as server: 
            print('Email started run13 successfully!')   
            server.ehlo()  
            server.starttls()  
            server.login(smtp_username, smtp_password)  
            server. send_message(msg,msg['From'],msg['To'])                        
            print('Email sent successfully!')  
    
        
        
if __name__ == "__main__":
    # Create or connect to SQL Server database
    st.set_page_config(layout="wide")
    # Define the menu items
    menu = ["UseCase1", "UseCase2"]
    # Create a selectbox in the sidebar
    choice = st.sidebar.selectbox("Menu", menu)

    # Depending on the user's choice, display different pages
    if choice == "UseCase1":
        generate_testresults_summary()
    elif choice == "UseCase2":
        conn = sql_db.create_connection()    
        col1, col2, col3, col4 = st.columns([0.25, 2.25, 2.25, 0.25])
        # Generate test results summary
        generate_testresults_history()
        # Schema Representation for finances table
        schemas = sql_db.get_schema_representation()
        with col3:
            st.header("Perf Analyzer-Chatbot")
            upload_performance_metrics_data()
            generate_sql_queries()
    
