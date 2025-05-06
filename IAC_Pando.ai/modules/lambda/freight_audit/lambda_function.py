import json
import boto3
from prompt import SQL_GENERATION_PROMT, SQL_CORRECTION_PROMPT , E_CHARTS_GENERATION_PROMPT
import logging
import time
from observability import Observability 
from observability import LocalDestination, FirehoseDestination, ObservabilityMetrics
from datetime import datetime
import math
from gremlin_python.driver import client, serializer
from gremlin_python.driver.protocol import GremlinServerError
import ast
import re
from echart import data_to_echart

REGION = "us-east-1"
FIREHOSE_NAME = "observability_firehose-opensearch-stream"
EXPERIMENT_ID = "freight-audit-project"
INFERENCE_PROFILE_ARN = "arn:aws:bedrock:us-east-1:354602095398:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0"

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Initialize Observability with destinations
firehose_dest = FirehoseDestination("observability_firehose-opensearch-stream")
local_dest = LocalDestination()
bedrock_logs = Observability(
    destinations=[firehose_dest, local_dest],
    experiment_id="test-experiment",
    feature_name="Agent",
    feedback_variables=True
)

# AWS clients
bedrock_client = boto3.client('bedrock-agent-runtime')
bedrock_model_client = boto3.client(service_name="bedrock-runtime")
athena_client = boto3.client("athena")
s3_client = boto3.client("s3")

# Athena settings
DATABASE_NAME = "pando_invoice"
OUTPUT_LOCATION = "s3://pando-freight-agent/ouput/"
SCHEMA_KNOWLEDGE_BASE_ID = "QUXIDJXHOE"
PREV_EXAMPLES_KNOWLEDGE_BASE_ID = "IXTFQ5BLSJ"
SCORE_THRESHOLD = 0.90

@bedrock_logs.watch(capture_input=True, capture_output=True, call_type='freight-audit-AI')
def invoke_model(payload, model_id):
    try:
        start_time = time.time()
        logger.info("Invoking Bedrock model")
        response = bedrock_model_client.invoke_model(
            modelId=model_id,
            body=json.dumps(payload),
            contentType="application/json"
        )
        response_body = response.get("body").read().decode("utf-8")
        response_json = json.loads(response_body)
        
        latency = time.time() - start_time
        response_metadata = {
            "latency": latency,
            "input_tokens": response_json.get("usage", {}).get("input_tokens", 0),
            "output_tokens": response_json.get("usage", {}).get("output_tokens", 0)
        }
        logger.info(f"Model invocation successful, latency: {latency:.2f}s")
        return response_json, response_metadata
    except Exception as e:
        logger.error(f"Error in invoke_model: {str(e)}")
        raise

def write_into_s3(output_json):
    try:
        S3_PREFIX = "freight-audit"
        S3_BUCKET = "pando-ai-observability"
        now = datetime.utcnow()
        partition_path = f"call_type={S3_PREFIX}/year={now.year}/month={now.month}/day={now.day}/data-{now}.json"
        logger.info(f"Writing to S3: s3://{S3_BUCKET}/{partition_path}")
        body = json.dumps(output_json)
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=partition_path,
            Body=body,
            ContentType="application/json"
        )
        logger.info(f"Successfully wrote data to S3: s3://{S3_BUCKET}/{partition_path}")
    except Exception as e:
        logger.error(f"Error in write_into_s3: {str(e)}")
        raise

def sql_generator(prompt):
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "max_tokens": 2000,
        "temperature": 0.0,
        "top_p": 0.5,
        "top_k": 5,
        "stop_sequences": []
    }
    logger.info("Generating SQL with Bedrock model")
    if FIREHOSE_NAME == "local":
        result, metadata, run_id, observation_id = invoke_model(payload, INFERENCE_PROFILE_ARN)
        logger.debug(f"Local mode metadata: {json.dumps(metadata, indent=2)}")
    else:
        result, run_id, observation_id = invoke_model(payload, INFERENCE_PROFILE_ARN)
        logger.info(f"Firehose mode enabled - metadata sent to {FIREHOSE_NAME}")

    response_json, response_metadata = result
    
    try:
        content = json.loads(response_json["content"][0]["text"])
        sql = content["SQL"]
        reasoning = content["Reasoning"]
        logger.info("SQL and reasoning extracted from response")
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Invalid Bedrock response format: {str(e)}")
        raise ValueError(f"Failed to parse Bedrock response: {str(e)}")
    
    output_json = {
        "prompt": prompt,
        "reasoning": reasoning,
        "sql": sql,
        "run_id": run_id,
        "observation_id": observation_id,
        "latency": response_metadata['latency'],
        "input_tokens": response_metadata['input_tokens'],
        "output_tokens": response_metadata['output_tokens']
    }
    logger.debug(f"Generated output JSON: {json.dumps(output_json)}")
    write_into_s3(output_json)
    return sql, reasoning

def echart_generator(prompt):
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "max_tokens": 2000,
        "temperature": 0.0,
        "top_p": 0.5,
        "top_k": 5,
        "stop_sequences": []
    }
    logger.info("Generating echart json with Bedrock model")
    if FIREHOSE_NAME == "local":
        result, metadata, run_id, observation_id = invoke_model(payload, INFERENCE_PROFILE_ARN)
        logger.debug(f"Local mode metadata: {json.dumps(metadata, indent=2)}")
    else:
        result, run_id, observation_id = invoke_model(payload, INFERENCE_PROFILE_ARN)
        logger.info(f"Firehose mode enabled - metadata sent to {FIREHOSE_NAME}")
    #print(result)
    response_json, response_metadata = result
    print("echart response_json:",response_json)
    
    try:
        raw_text = response_json["content"][0]["text"]
        #print("raw_text:", raw_text)
        clean_text = re.sub(r"```(?:json)?\n|\n```", "", raw_text)
        #print("clean_text:", clean_text)
        content = json.loads(clean_text)
        #print(content)
        logger.info("echarts json content extracted from response")
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Invalid Bedrock response format: {str(e)}")
        raise ValueError(f"Failed to parse Bedrock response: {str(e)}")
    
    output_json = {
        "prompt": prompt,
        "run_id": run_id,
        "observation_id": observation_id,
        "latency": response_metadata['latency'],
        "input_tokens": response_metadata['input_tokens'],
        "output_tokens": response_metadata['output_tokens']
    }
    logger.debug(f"Generated output JSON: {json.dumps(output_json)}")
    write_into_s3(output_json)
    return content

def syntax_checker(sql):
    query_string = "Explain " + sql
    logger.info(f"Checking syntax for query: {query_string}")
    query_config = {"OutputLocation": OUTPUT_LOCATION}
    query_execution_context = {"Catalog": "AwsDataCatalog"}
    try:
        query_execution = athena_client.start_query_execution(
            QueryString=query_string,
            ResultConfiguration=query_config,
            QueryExecutionContext=query_execution_context,
        )
        execution_id = query_execution["QueryExecutionId"]
        logger.info(f"Syntax check execution ID: {execution_id}")
        time.sleep(3)
        results = athena_client.get_query_execution(QueryExecutionId=execution_id)
        status = results["QueryExecution"]["Status"]
        logger.info(f"Syntax check status: {status['State']}")
        if status["State"] == "SUCCEEDED":
            return "Passed"
        else:
            logger.warning(f"Syntax check failed: {status.get('StateChangeReason', 'No reason provided')}")
            return status["StateChangeReason"]
    except Exception as e:
        logger.error(f"Error in syntax_checker: {str(e)}")
        return str(e)

def execute_query(query_string):
    result_config = {"OutputLocation": OUTPUT_LOCATION}
    query_execution_context = {"Catalog": "AwsDataCatalog"}
    logger.info(f"Executing query: {query_string}")
    query_execution = athena_client.start_query_execution(
        QueryString=query_string,
        ResultConfiguration=result_config,
        QueryExecutionContext=query_execution_context,
    )
    query_execution_id = query_execution["QueryExecutionId"]
    logger.info(f"Query execution ID: {query_execution_id}")
    while True:
        query_status = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        status = query_status["QueryExecution"]["Status"]["State"]
        if status in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            break
        time.sleep(1)
    if status != "SUCCEEDED":
        logger.error(f"Query execution failed with status: {status}")
        return {"status": "Error", "message": f"Query execution failed with status: {status}"}
    results = athena_client.get_query_results(QueryExecutionId=query_execution_id)
    logger.info("Query executed successfully, processing results")
    rows = []
    headers = [col["VarCharValue"] for col in results["ResultSet"]["Rows"][0]["Data"]]
    for row in results["ResultSet"]["Rows"][1:]:
        rows.append({headers[i]: col.get("VarCharValue", "NULL") for i, col in enumerate(row["Data"])})
    return {"database_records": rows}

def get_titan_embedding(query):
    bedrock = boto3.client(service_name='bedrock-runtime')
    payload = {"inputText": query}
    logger.info(f"Generating Titan embedding for query: {query}")
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload)
    )
    response_body = json.loads(response["body"].read().decode("utf-8"))
    logger.info("Titan embedding generated successfully")
    return response_body["embedding"]

def cosine_similarity(vec1, vec2):
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_vec1 = math.sqrt(sum(a * a for a in vec1))
    norm_vec2 = math.sqrt(sum(b * b for b in vec2))
    similarity = dot_product / (norm_vec1 * norm_vec2) if norm_vec1 and norm_vec2 else 0.0
    logger.debug(f"Computed cosine similarity: {similarity}")
    return similarity

def get_embedding_by_query(gremlin_client, query_text):
    """Fetch embedding for the Concept node based on the query description."""
    gremlin_query = f"""
    g.V().hasLabel('Concept').has('query', '{query_text}').valueMap('query', 'embedding')
    """
    logger.debug(f"Executing Gremlin query: {gremlin_query}")
    result = gremlin_client.submit(gremlin_query).all().result()
    
    if result:
        #logger.debug(f"Query result: {result}")
        concept_data = result[0]
        embedding = concept_data.get('embedding', None)
        if embedding and embedding[0]:
            # Convert string embedding to list
            try:
                embedding_list = ast.literal_eval(embedding[0])
                return embedding_list
            except (ValueError, SyntaxError) as e:
                logger.error(f"Failed to parse embedding for {query_text}: {str(e)}")
                return None
    logger.info(f"No results found for query: {query_text}")
    return None

def get_neptune_output(input_query):
    neptune_endpoint = "wss://db-neptune-1.cluster-ro-cpu28yegypjp.us-east-1.neptune.amazonaws.com:8182/gremlin"
    
    try:
        gremlin_client = client.Client(
            neptune_endpoint,
            'g',
            username="",
            password="",
            message_serializer=serializer.GraphSONSerializersV2d0()
        )

        input_embedding = get_titan_embedding(input_query)
        
        # Fetch all Concept node queries
        concept_query = "g.V().hasLabel('Concept').values('query')"
        logger.debug(f"Fetching all concept queries with: {concept_query}")
        concept_queries = gremlin_client.submit(concept_query).all().result()
        
        if not concept_queries:
            logger.warning("No Concept nodes found in Neptune")
            return {
                'statusCode': 404,
                'body': json.dumps({'message': 'No Concept nodes found in Neptune'})
            }
        
        logger.info(f"Found {len(concept_queries)} concept queries")
        
        # Find matching concept
        matched_concept = None
        highest_similarity = 0.0
        
        for concept in concept_queries:
            stored_embedding = get_embedding_by_query(gremlin_client, concept)
            if stored_embedding:
                similarity = cosine_similarity(input_embedding, stored_embedding)
                logger.debug(f"Similarity between '{input_query}' and '{concept}': {similarity}")
                
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    if similarity >= 0.90:
                        matched_concept = concept
                        logger.info(f"Found match: '{concept}' with similarity {similarity}")
                        break
        
        if not matched_concept:
            logger.info(f"No match found. Highest similarity was {highest_similarity}")
            return {
                'statusCode': 404,
                'body': json.dumps({'message': f'No matching Concept node found with similarity >= 0.90. Highest similarity: {highest_similarity}'})
            }
        
        # Rest of the Lambda function remains the same
        query = f"""
        g.V().hasLabel('Concept').has('query', '{matched_concept}')
        .as('concept')
        .out().hasLabel('Table').as('table')
        .project('concept', 'table', 'columns')
        .by(valueMap(true))
        .by(valueMap(true))
        .by(out().hasLabel('Column').valueMap(true).fold())
        """
        
        logger.debug(f"Executing detail query: {query}")
        result = gremlin_client.submit(query).all().result()
        
        if not result:
            logger.warning(f"No tables/columns found for concept: {matched_concept}")
            return {
                'statusCode': 404,
                'body': json.dumps({'message': 'No matching Concept node or connected Tables found'})
            }
        
        output = []
        DATABASE_NAME = "pando_invoice"
        
        for entry in result:
            table = entry['table']
            table_name = table['name'][0]
            columns = entry['columns']
            
            table_output = [
                f"Database: {DATABASE_NAME}",
                f"Table: {DATABASE_NAME}.{table_name}",
                "Description:",
                "COLUMNS:",
                "========"
            ]
            
            for column in columns:
                column_name = column['name'][0]
                table_output.append(f"{DATABASE_NAME}.{table_name}.{column_name} | Type:  | Description: ")
            
            output.append("\n".join(table_output))
        
        final_output = "\n\n".join(output)
        logger.info(f"Neptune output generated: {final_output}")
        return final_output
    finally:
        if 'gremlin_client' in locals():
            gremlin_client.close()

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    try:
        if "body" in event:
            try:
                body = json.loads(event["body"])
                logger.info("Parsed request body from API Gateway")
            except json.JSONDecodeError:
                logger.error("Invalid JSON format in request body")
                return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON format"})}
        else:
            body = event
            logger.info("Processing direct invocation event")

        client_id = body.get("client_id")
        user_id = body.get("user_id")
        query_text = body.get("query")

        if not client_id or not user_id or not query_text:
            logger.error("Missing required parameters: client_id, user_id, or query")
            return {"statusCode": 400, "body": json.dumps({"error": "Missing client_id, user_id, or query"})}

        logger.info("Fetching Neptune output")
        neptune_output = get_neptune_output(query_text)
        
        logger.info("Retrieving schema from knowledge base")
        response = bedrock_client.retrieve(
            knowledgeBaseId=SCHEMA_KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query_text}
        )
        schema_filtered = [item["content"]["text"] for item in response.get("retrievalResults", [])]

        logger.info("Retrieving previous examples from knowledge base")
        response = bedrock_client.retrieve(
            knowledgeBaseId=PREV_EXAMPLES_KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query_text}
        )
        prev_example_filtered = [{"score": item["score"], "content": item["content"]["text"]} 
                                for item in response.get("retrievalResults", []) 
                                if float(item["score"]) >= SCORE_THRESHOLD]
        top3_prev_examples = sorted(prev_example_filtered, key=lambda x: x["score"], reverse=True)[:3]

        sql_gen_prompt = SQL_GENERATION_PROMT.format(
            schema=schema_filtered, prev_examples=top3_prev_examples, 
            user_query=query_text, client_id=client_id, user_id=user_id, neptune_output=neptune_output
        )
        
        attempt = 0
        max_attempts = 3
        prompt = sql_gen_prompt
        error_messages = []
        while attempt < max_attempts:
            logger.info(f"SQL generation attempt {attempt + 1} of {max_attempts}")
            try:
                generated_sql, reasoning = sql_generator(prompt)
                syntaxcheckmsg = syntax_checker(generated_sql)
                if syntaxcheckmsg == "Passed":
                    logger.info("Syntax check passed, executing query")
                    return_records = execute_query(generated_sql)
                    logger.info("Query executed successfully, returning response")
                    #echart_prompt = E_CHARTS_GENERATION_PROMPT.format(records=return_records)
                    #return_echarts=echart_generator(echart_prompt)
                    if len(return_records["database_records"]) >= 3:    
                        chart_config = data_to_echart(
                            return_records["database_records"],
                            use_ai=True,
                            bedrock_client=bedrock_model_client,
                            model_id=INFERENCE_PROFILE_ARN
                            )
                        logger.info("Echarts executed successfully, returning response")
                    else:
                        chart_config = "Not enough records to generate echart"
                        logger.info("Not enough records to generate echart")
                    
                    return {
                        "statusCode": 200,
                        "body": json.dumps({
                            "SQL": generated_sql,
                            "Reasoning": reasoning,
                            "Records": return_records["database_records"],
                            "Echarts" : chart_config
                        })
                    }
                else:
                    logger.warning(f"Syntax check failed: {syntaxcheckmsg}")
                    prompt = SQL_CORRECTION_PROMPT.format(
                        prompt=prompt, syntaxcheckmsg=syntaxcheckmsg, sqlgenerated=generated_sql
                    )
                    attempt += 1
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                error_messages.append(str(e))
                attempt += 1
        logger.error(f"Failed after {max_attempts} attempts: {error_messages}")
        return {"statusCode": 500, "body": json.dumps({"error": "Failed after max attempts", "details": error_messages})}
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}