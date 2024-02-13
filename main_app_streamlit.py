# main_app.py

from datetime import datetime
from io import StringIO
import appConfig
import io
import os
import time
import streamlit as st
import sqlite3
import pandas as pd
import sql_db
from prompts.prompts import SYSTEM_MESSAGE
from azure_openai import get_completion_from_messages
from streamlit import components  
import re
from datetime import datetime
from streamlit_js_eval import streamlit_js_eval

from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email import encoders
from email.utils import COMMASPACE, formatdate
import smtplib
from PIL import ImageGrab
#from reportlab.pdfgen import canvas
import time
from PIL import Image


def generate_testresults_summary():
    """
    This function generates table for test results summary. The results are displayed
    using Streamlit.

    Parameters:
        None

    Returns:
        None
    """    

    
    # Create an upload file in UI
    uploaded_file = st.file_uploader("Upload test results to generate test summary", type="csv")
    if uploaded_file is not None:
        upload = uploaded_file
        # Process the uploaded file
        file_contents = uploaded_file.read().decode('utf-8-sig')
        data = pd.read_csv(io.StringIO(file_contents))      
        
        acceptable_error_percentage = int(appConfig.fetchKey("Acceptable_Error_rate"))
        sla_configuration_secs = int(appConfig.fetchKey("Sla_Config_secs"))        

        sla_config_millsec = sla_configuration_secs * 1000        
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
        st.markdown(html_code, unsafe_allow_html=True)
        

        # smtp_server = 'smtp.office365.com'  
        # smtp_port = 587  
        # smtp_username = 'taniyagupta250295@gmail.com'
        # smtp_password = 'cdkcncdcn2@T'  
        #receiver_emails = ['Taniya.Gupta@microsoft.com','Anvesh.Bonagiri@microsoft.com','Shwetha.Punnam@microsoft.com','angolla@microsoft.com']        

        smtp_server = appConfig.fetchKey("smtp_server")
        smtp_port = int(appConfig.fetchKey("smtp_port"))  
        smtp_username = appConfig.fetchKey("smtp_username")
        smtp_password = appConfig.fetchKey("smtp_password")
        receiver_emails = appConfig.fetchKey("receiver_emails")


        # Global Config End
        release_number = uploaded_file.name.split('_')[0]
        message_body = f'''  
        Hi Team,

        Please find the performance Test Report of {release_number}.

        Thanks,
        Performance Test Team.
        '''
        test_report_name = f'{release_number}_PerfTestReport.html'        

        # Create the email message  
        msg = MIMEMultipart()  
        msg['From'] = smtp_username
        msg['To'] = ", ".join(receiver_emails)  
        msg['Subject'] = 'Performance Test Report'  
        
        
        # Add the HTML text as a MIMEText object          
        msg.attach(MIMEText(message_body, 'plain'))  
       
        # Add the HTML text as an attachment  
        attachment = MIMEApplication(html_code.encode('utf-8'), _subtype='html')  
        attachment.add_header('Content-Disposition', 'attachment', filename=test_report_name)  
        msg.attach(attachment)  
        
        # Send the email  
        with smtplib.SMTP(smtp_server, smtp_port) as server: 
            print('Email started running successfully!')   
            server.ehlo()  
            server.starttls()  
            server.login(smtp_username, smtp_password)  
            server.sendmail(smtp_username, receiver_emails, msg.as_string())                       
            print('Email sent successfully!')  


   

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

            file_contents = uploaded_file.read().decode('utf-8-sig')
            try:
                df = pd.read_csv(StringIO(file_contents), skip_blank_lines=True)
            except pd.errors.EmptyDataError:
                st.write("The uploaded file is empty. Please upload a different file.")

            filename_str = os.path.splitext(uploaded_file.name)[0]           

            pattern = r'^[A-Za-z0-9]+[\d.]*_[0-9]{2}-[0-9]{2}-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}$'  
            
            if re.match(pattern, filename_str):                                  
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
        #Anil-Final
        query = "select distinct top 10  RunId,TestName,TestStartTime,TestEndTime FROM [dbo].[PerformanceMetrics] order by RunId Desc"
        try:
                # Run the SQL query and display the results
                sql_results = query_database(query, conn)
                sql_results = sql_results.rename(columns={'RunId': 'Run ID', 'TestName': 'Test Name', 'TestStartTime': 'Test StartTime', 'TestEndTime': 'Test EndTime'})

                df = pd.DataFrame(sql_results)
                st.dataframe(df, hide_index=True, width=4500)

        except Exception as e:
                st.write(f"An error occurred: {e}")



        
if __name__ == "__main__":
    
    st.set_page_config(  
        page_title="AI PerfInsights",          
        layout="wide",  
        initial_sidebar_state="expanded"        
    )      
    menu_items = ["TestSummary", "PerfTestAnalyzer", "Help"]     
    st.markdown(  
        """  
        <style>  
        .sidebar .sidebar-content {  
            width: 5px;  
        }  
        </style>  
        """,  
        unsafe_allow_html=True  
    )  
    
    # Add content to sidebar  
    st.sidebar.title("AI PerfInsights")  
    
    # Create sidebar menu  
    menu_selection = st.sidebar.selectbox("Select a page", menu_items)  
  
    # Display content on the right pane based on menu item clicked  
    if menu_selection == "TestSummary":          
        st.markdown(f"<h2 style='text-align: center'>Test Results Summary</h1>", unsafe_allow_html=True)
        generate_testresults_summary()  
    elif menu_selection == "PerfTestAnalyzer":  
        conn = sql_db.create_connection()
        col1, col2, col3, col4 = st.columns([0.2, 2, 2, 0.5])         
        generate_testresults_history()         
        schemas = sql_db.get_schema_representation()
        with col3:
            st.header("Perf Analyzer-Chatbot")
            upload_performance_metrics_data()                                             
            generate_sql_queries()
    elif menu_selection == "Help":  
        st.markdown("""
        ### Sample Queries to Analyze Performance Results
 
        1. **List all API/Transactions with response time > 400 for given Run-ID**
            - Display records which has NinetyPercentile greater than 400 at RunID 1
        2. **List Specific API/Transactions with response time > 400 for given Run-ID**
            - Display API, NinetyPercentile columns for records which has NinetyPercentile greater than 400 at RunID 1
        3. **List all API/Transactions with response time is between a range for given Run-ID**
            - Get me list of API,NinetyPercentile which has NinetyPercentile > 1000 and < 2000 at RunID 3
        4. **Compare and analyze API Response time between Test Runs**
            - Get me list of API,Average,RunID of records with API names in SearchAPI, HomeAPI at RunID 1,2
        """)
