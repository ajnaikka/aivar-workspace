import boto3
import time

# AWS Clients
athena_client = boto3.client("athena")
s3_client = boto3.client("s3")

# S3 bucket where output schema files will be stored
S3_BUCKET = "pando-db-auto-schema"
S3_OUTPUT_LOCATION = "s3://pando-freight-agent/ouput/"

def execute_athena_query(database, query):
    """Executes an Athena query and waits for results."""
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": S3_OUTPUT_LOCATION}
    )
    
    query_execution_id = response["QueryExecutionId"]
    
    # Wait for query to complete
    while True:
        status = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        
        if state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            break
        time.sleep(2)  # Wait before checking again
    
    if state != "SUCCEEDED":
        raise Exception(f"Athena query failed: {state}")
    
    return query_execution_id

def get_query_results(query_execution_id):
    """Fetches Athena query results."""
    results = athena_client.get_query_results(QueryExecutionId=query_execution_id)
    processed_results = []
    for row in results["ResultSet"]["Rows"]:
        processed_row = []
        for col in row["Data"]:
            processed_row.append(col.get("VarCharValue", "NULL"))  # Handle missing values safely
        processed_results.append(processed_row)

    return processed_results[1:]  # Skip header row

def fetch_table_schema(database_name):
    """Fetches table schema and writes to S3."""
    
    # 1. Fetch all tables
    query_tables = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{database_name}';"
    query_id = execute_athena_query(database_name, query_tables)
    tables = get_query_results(query_id)

    for table_row in tables:
        table_name = table_row[0]
        file_name = f"{database_name}_{table_name}.txt"
        content = f"Database: {database_name}\nTable: {database_name}.{table_name}\n"

        # 2. Fetch table description
        # query_desc = f"SELECT comment FROM information_schema.tables WHERE table_schema = '{database_name}' AND table_name = '{table_name}';"
        # query_id = execute_athena_query(database_name, query_desc)
        # table_desc = get_query_results(query_id)
        # table_desc = table_desc[0][0] if table_desc else "No description available"
        table_desc = "No description available"
        content += f"Description: {table_desc}\n\nCOLUMNS:\n========\n\n"

        # 3. Fetch column details
        query_columns = f"""
            SELECT column_name, data_type, comment
            FROM information_schema.columns
            WHERE table_schema = '{database_name}' AND table_name = '{table_name}';
        """
        query_id = execute_athena_query(database_name, query_columns)
        columns = get_query_results(query_id)

        for col_name, col_type, col_desc in columns:
            col_desc = col_desc if col_desc else "No description available"
            content += f"{database_name}.{table_name}.{col_name} | Type: {col_type} | Description: {col_desc}\n\n"

        # 4. Upload file to S3
        s3_client.put_object(Bucket=S3_BUCKET, Key=f"{file_name}", Body=content)
        print(f"Uploaded schema: {file_name} to S3://{S3_BUCKET}/")

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    #database_name = event.get("database_name", "your_database_name")  # Change default DB
    database_name = "pando-db-pg"
    fetch_table_schema(database_name)
    return {"statusCode": 200, "message": "Schema extraction completed!"}
