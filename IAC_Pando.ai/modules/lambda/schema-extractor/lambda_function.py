import boto3
import pandas as pd
import json
import time
import io
import os

# AWS Clients
athena_client = boto3.client("athena")
s3_client = boto3.client("s3")

# S3 Configuration
S3_BUCKET = "athena-neptune-data"  # ✅ Remove trailing space  #os.environ['S3_BUCKET']  this is where the output csv files will go
S3_TARGET_PATH = "neptune-nodes-data/"  # ✅ Use folder path, not URL
S3_OUTPUT_LOCATION = "s3://pando-freight-agent/output/"     # used by athena, where the query results will go

# Initialize global counters
node_id_counter = 10000000
rel_id_counter = 30000000
table_ids = {}
column_ids = {}
table_nodes = []
column_nodes = []
table_column_rels = []

def execute_athena_query(database, query):
    """Executes an Athena query and waits for results."""
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": S3_OUTPUT_LOCATION}
    )
    query_execution_id = response["QueryExecutionId"]
    
    while True:
        status = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        if state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            break
        time.sleep(2)
    
    if state != "SUCCEEDED":
        raise Exception(f"Athena query failed: {state}")
    
    return query_execution_id

def get_query_results(query_execution_id):
    """Fetches Athena query results."""
    results = athena_client.get_query_results(QueryExecutionId=query_execution_id)
    processed_results = []
    for row in results["ResultSet"]["Rows"]:
        processed_row = [col.get("VarCharValue", "NULL") for col in row["Data"]]
        processed_results.append(processed_row)
    
    return processed_results[1:]  # Skip header row

def fetch_table_schema(database_name):
    """Fetches table schema and stores nodes and relationships."""
    global node_id_counter, rel_id_counter
    
    query_tables = f"""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = '{database_name}';
    """
    query_id = execute_athena_query(database_name, query_tables)
    tables = get_query_results(query_id)
    
    for table_row in tables:
        table_name = table_row[0]
        
        if table_name not in table_ids:
            table_ids[table_name] = str(node_id_counter)
            node_id_counter += 1
            table_nodes.append({
                ':ID': table_ids[table_name],
                'name:string': table_name,
                'database:string': database_name,
                ':LABEL': 'Table'
            })
        
        query_columns = f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = '{database_name}' AND table_name = '{table_name}';
        """
        query_id = execute_athena_query(database_name, query_columns)
        columns = get_query_results(query_id)
        
        if table_name not in column_ids:
            column_ids[table_name] = {}
        
        for column_info in columns:
            column_name, data_type = column_info
            
            if column_name not in column_ids[table_name]:
                column_ids[table_name][column_name] = str(node_id_counter)
                node_id_counter += 1
                column_nodes.append({
                    ':ID': column_ids[table_name][column_name],
                    'name:string': column_name,
                    'table_name:string': table_name,
                    'database:string': database_name,
                    'data_type:string': data_type,
                    ':LABEL': 'Column'
                })
            
            table_column_rels.append({
                ':ID': str(rel_id_counter),
                ':START_ID': table_ids[table_name],
                ':END_ID': column_ids[table_name][column_name],
                ':TYPE': 'HAS_COLUMN'
            })
            rel_id_counter += 1

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    database_name = event.get("database_name", "pando-db-pg")

    fetch_table_schema(database_name)  # Ensure this function is defined

    # Convert data to DataFrame
    df_nodes = pd.DataFrame(table_nodes + column_nodes)
    df_rels = pd.DataFrame(table_column_rels)

    # **Use in-memory buffer for CSV upload**
    node_csv_buffer = io.StringIO()
    rel_csv_buffer = io.StringIO()

    df_nodes.to_csv(node_csv_buffer, index=False, encoding='utf-8')
    df_rels.to_csv(rel_csv_buffer, index=False, encoding='utf-8')

    # Move cursor to start of buffer
    node_csv_buffer.seek(0)
    rel_csv_buffer.seek(0)

    # Upload CSV to S3 directly
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=f"{S3_TARGET_PATH}updated_nodes.csv",
        Body=node_csv_buffer.getvalue()
    )
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=f"{S3_TARGET_PATH}updated_relationships.csv",
        Body=rel_csv_buffer.getvalue()
    )

    return {
        "statusCode": 200,
        "message": f"Schema extraction completed! Files uploaded to s3://{S3_BUCKET}/{S3_TARGET_PATH}updated_nodes.csv"
    }
