import json
import boto3
from prompt import SQL_GENERATION_PROMT , SQL_CORRECTION_PROMPT
import logging
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#logger.addHandler(logging.StreamHandler())

bedrock_client = boto3.client('bedrock-agent-runtime')
bedrock_model_client = boto3.client(service_name="bedrock-runtime")
athena_client = boto3.client("athena")
s3_client = boto3.client("s3")

# Athena settings
DATABASE_NAME = "pando_test"
#OUTPUT_BUCKET = "s3://pando-email-usecase/athena_output/"
OUTPUT_LOCATION = f"s3://pando-freight-agent/ouput/"
SCHEMA_KNOWLEDGE_BASE_ID ="QUXIDJXHOE"
PREV_EXAMPLES_KNOWLEDGE_BASE_ID = "IXTFQ5BLSJ"
SCORE_THRESHOLD = 0.90
MODEL_ID = "anthropic.claude-3-7-sonnet-20250219-v1:0"
INFERENCE_PROFILE_ARN = "arn:aws:bedrock:us-east-1:354602095398:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0"

def syntax_checker(sql):
    query_string="Explain  "+sql
    print(f"Executing: {query_string}")
    query_config = {"OutputLocation": f"s3://pando-freight-agent/ouput/"}
    query_execution_context = {
        "Catalog": "AwsDataCatalog",
        "Database": "pando_test"
    }
    try :
        print(" I am checking the syntax here")
        query_execution = athena_client.start_query_execution(
            QueryString=query_string,
            ResultConfiguration=query_config,
            QueryExecutionContext=query_execution_context,
        )
        execution_id = query_execution["QueryExecutionId"]
        print(f"execution_id: {execution_id}")
        time.sleep(3)
        results = athena_client.get_query_execution(QueryExecutionId=execution_id)
        # print(f"results: {results}")
        status=results['QueryExecution']['Status']
        print("Status :",status)
        if status['State']=='SUCCEEDED':
            return "Passed"
        else:  
            print(results['QueryExecution']['Status']['StateChangeReason'])
            errmsg=results['QueryExecution']['Status']['StateChangeReason']
            return errmsg
        # return results
    except Exception as e:
        print("Error in exception")
        msg = str(e)
        print(msg)

def execute_query(query_string):
        # print("Inside execute query", query_string)
        # result_folder='athena_output'
        result_config = {"OutputLocation": f"s3://pando-freight-agent/ouput/"}
        query_execution_context = {
            "Catalog": "AwsDataCatalog",
            "Database": "pando_test"
        }
        print(f"Executing: {query_string}")
        query_execution = athena_client.start_query_execution(
            QueryString=query_string,
            ResultConfiguration=result_config,
            QueryExecutionContext=query_execution_context,
        )
        query_execution_id = query_execution["QueryExecutionId"]
        # Wait for the query to complete
        while True:
            query_status = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            status = query_status["QueryExecution"]["Status"]["State"]

            if status in ["SUCCEEDED", "FAILED", "CANCELLED"]:
                break
            time.sleep(1)  # Wait before checking again

        if status != "SUCCEEDED":
            return {"status": "Error", "message": f"Query execution failed with status: {status}"}

        # Get query results
        results = athena_client.get_query_results(QueryExecutionId=query_execution_id)

        # Extract and format results
        rows = []
        headers = [col["VarCharValue"] for col in results["ResultSet"]["Rows"][0]["Data"]]  # First row is headers

        for row in results["ResultSet"]["Rows"][1:]:  # Skip header row
            rows.append({headers[i]: col.get("VarCharValue", "NULL") for i, col in enumerate(row["Data"])})

        response_data = {
            "database_records": rows
        }

        return response_data

def sql_generator(prompt):
    # Call Bedrock to generate SQL
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.0,
            "top_p": 0.5,
            "top_k": 5,
            "stop_sequences": []
        }

        response = bedrock_model_client.invoke_model(
            modelId=INFERENCE_PROFILE_ARN,
            body=json.dumps(payload),
            contentType="application/json"
        )

        # Extract and print the generated SQL
        response_body = response.get("body").read().decode("utf-8")
        response_json = json.loads(response_body)
        sql = json.loads(response_json["content"][0]['text'])['SQL']
        print('sql:',sql)
        Reasoning = json.loads(response_json["content"][0]['text'])['Reasoning']
        print('Reasoning:',Reasoning)
        return sql, Reasoning



def lambda_handler(event, context):
    try:
        # Extract required parameters from event
        client_id = event.get("client_id")
        user_id = event.get("user_id")
        query_text = event.get("query")

        # Validate inputs
        if not client_id or not user_id or not query_text:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing client_id, user_id, or query"})
            }

        # Call Bedrock Agent to retrieve knowledge base data for database schema
        response = bedrock_client.retrieve(
            knowledgeBaseId=SCHEMA_KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query_text}
        )

        # Extract retrieved information for database schema
        retrieved_data = response.get("retrievalResults", [])
        # Format response
        schema_filtered = [item["content"]["text"] for item in retrieved_data]
        #print(schema_filtered)

        # Call Bedrock Agent to retrieve knowledge base data for Prev user queries
        response = bedrock_client.retrieve(
            knowledgeBaseId=PREV_EXAMPLES_KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query_text}
        )

        # Extract retrieved information for database schema for Prev user queries
        retrieved_data = response.get("retrievalResults", [])
        #print(retrieved_data)

        # Format response
        prev_example_filtered = [{"score": item["score"], "content": item["content"]["text"]} for item in retrieved_data if float(item["score"]) >= SCORE_THRESHOLD  ]
        top3_prev_examples = sorted(prev_example_filtered, key=lambda x: x["score"], reverse=True)[:3]
        #print("top3_prev_examples:",top3_prev_examples)

        sql_gen_prompt = SQL_GENERATION_PROMT.format(schema=schema_filtered, prev_examples=top3_prev_examples, user_query=query_text, client_id=client_id, user_id=user_id)

        attempt = 0
        max_attempts = 3
        prompt = sql_gen_prompt
        error_messages=[]
        while attempt < max_attempts:
            logger.info(f'Sql Generation attempt Count: {attempt+1}')
            try:
                logger.info(f'we are in Try block to generate the sql and count is :{attempt+1}')
                generated_sql, reasoning = sql_generator(prompt)
                syntaxcheckmsg = syntax_checker(generated_sql)
                if syntaxcheckmsg=='Passed':
                    logger.info(f'syntax checked for query passed in attempt number :{attempt+1}')
                    return_records = execute_query(generated_sql)
                    return{
                        'statusCode': 200,
                        'body': json.dumps({
                                "SQL": generated_sql,
                                "Reasoning": reasoning,
                                "Records": return_records['database_records']
                        })   
                    }
                    
                else:
                    prompt = SQL_CORRECTION_PROMPT.format(prompt=prompt,syntaxcheckmsg=syntaxcheckmsg,sqlgenerated=generated_sql)
                    attempt += 1
            except Exception as e:
                print(e)
                logger.error('FAILED')
                msg = str(e)
                error_messages.append(msg)
                attempt += 1

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

