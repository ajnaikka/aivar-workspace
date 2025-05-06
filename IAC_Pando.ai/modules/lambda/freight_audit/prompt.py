import pytz
import json
import time
import boto3
import logging
#import requests
import asyncio
from uuid import uuid4
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, List, Union, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d - %(message)s"
)


class LoggingDestination(ABC):
    """Abstract base class for logging destinations."""

    @abstractmethod
    def send_log(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send log data to the destination."""
        pass


class FirehoseDestination(LoggingDestination):
    """Amazon Kinesis Data Firehose logging destination."""

    def __init__(self, delivery_stream_name: str):
        """Initialize Firehose destination with stream name."""
        self.__delivery_stream_name = delivery_stream_name
        self.__client = boto3.client('firehose')

    def send_log(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send log data to Firehose."""
        response = self.__client.put_record(
            DeliveryStreamName=self.__delivery_stream_name,
            Record={'Data': json.dumps(data)})
        return response


# class NewRelicDestination(LoggingDestination):
#     """New Relic logging destination."""

#     def __init__(self, api_key: str):
#         """Initialize New Relic destination with API key."""
#         self.__api_key = api_key
#         self.__url = "https://log-api.newrelic.com/log/v1"

#     def send_log(self, data: Dict[str, Any]) -> Dict[str, Any]:
#         """Send log data to New Relic."""
#         headers = {
#             "Content-Type": "application/json",
#             "Api-Key": self.__api_key,
#         }

#         payload = json.dumps([{
#             "message": data,
#             "attributes": data,
#             "timestamp": int(time.time() * 1000),
#         }])

#         response = requests.post(self.__url, headers=headers, data=payload)

#         return {"status_code": response.status_code, "text": response.text}


class LocalDestination(LoggingDestination):
    """Local logging destination for testing."""

    def send_log(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Log data locally."""
        logging.info("Local log: %s", json.dumps(data, default=str))
        return {"status": "success", "destination": "local"}


class ObservabilityMetrics:
    """Class for collecting and processing metrics."""

    def __init__(self):
        """Initialize metrics collection."""
        self.__metrics = {
            "latency": {},
            "memory": {},
            "cpu": {},
            "requests": 0,
            "errors": 0,
            "custom": {}
        }

    def track_latency(self, name: str, duration: float):
        """Track latency metric."""
        if name not in self.__metrics["latency"]:
            self.__metrics["latency"][name] = []
        self.__metrics["latency"][name].append(duration)

    def track_memory(self, usage: float):
        """Track memory usage."""
        timestamp = time.time()
        self.__metrics["memory"][timestamp] = usage

    def track_cpu(self, usage: float):
        """Track CPU usage."""
        timestamp = time.time()
        self.__metrics["cpu"][timestamp] = usage

    def increment_requests(self):
        """Increment request counter."""
        self.__metrics["requests"] += 1

    def increment_errors(self):
        """Increment error counter."""
        self.__metrics["errors"] += 1

    def add_custom_metric(self, name: str, value: Any):
        """Add custom metric."""
        if name not in self.__metrics["custom"]:
            self.__metrics["custom"][name] = []
        self.__metrics["custom"][name].append(value)

    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        return self.__metrics

    def reset_metrics(self):
        """Reset all metrics."""
        self.__metrics = {
            "latency": {},
            "memory": {},
            "cpu": {},
            "requests": 0,
            "errors": 0,
            "custom": {}
        }


class Observability:
    """Class for logging and tracing API interactions with multiple destinations."""

    VALID_FEATURE_NAMES = {"None", "Agent", "KB", "InvokeModel"}

    def __init__(
        self,
        destinations: List[LoggingDestination],
        experiment_id: Optional[str] = None,
        default_call_type: str = "Agent",
        feature_name: Optional[str] = None,
        feedback_variables: bool = True,
    ):
        """
        Initialize observability with logging and monitoring.
        
        Args:
            destinations: List of logging destinations
            experiment_id: Optional experiment identifier
            default_call_type: Default type of call to log
            feature_name: Feature being used (Agent, KB, etc.)
            feedback_variables: Whether to include feedback variables
        """
        self.__destinations = destinations
        self.__experiment_id = experiment_id
        self.__default_call_type = default_call_type
        self.__feedback_variables = feedback_variables
        self.__step_counter = 0
        self.__metrics = ObservabilityMetrics()

        # Validate feature name
        if feature_name and feature_name not in self.VALID_FEATURE_NAMES:
            raise ValueError(
                f"Invalid feature_name '{feature_name}'. "
                f"Valid values: {', '.join(self.VALID_FEATURE_NAMES)}")
        self.__feature_name = feature_name

        logging.info("Observability initialized with feature_name: %s",
                     feature_name)

    @staticmethod
    def __find_keys(dictionary: Any, key: str, path=None) -> list:
        """Recursively find all occurrences of a key in a nested dictionary."""
        if path is None:
            path = []
        results = []

        if isinstance(dictionary, dict):
            for k, v in dictionary.items():
                new_path = path + [k]
                if k == key:
                    results.append((new_path, v))
                else:
                    results.extend(Observability.__find_keys(v, key, new_path))
        elif isinstance(dictionary, list):
            for i, item in enumerate(dictionary):
                results.extend(Observability.__find_keys(
                    item, key, path + [i]))

        return results

    def __extract_session_id(self, log_data: Dict[str, Any]) -> str:
        """
        Extract session ID from log data.
        
        Args:
            log_data: The log data to extract from
            
        Returns:
            Session ID or a new UUID if not found
        """
        if not log_data:
            return str(uuid4())

        if self.__feature_name == "Agent":
            session_id_paths = self.__find_keys(
                log_data, 'x-amz-bedrock-agent-session-id')
        else:
            session_id_paths = self.__find_keys(log_data, 'sessionId')

        if session_id_paths:
            path, session_id = session_id_paths[0]
            return session_id

        return str(uuid4())

    def __handle_agent_feature(self, output_data, request_start_time):
        """
        Process agent feature data, including step counting and latency calculation.
        
        Args:
            output_data: The output data to process
            request_start_time: The start time of the request
            
        Returns:
            Processed output data with latency and step information
        """
        prev_trace_time = None

        for data in output_data:
            if isinstance(data, dict) and 'trace' in data:
                self.__process_trace_data(data, 'trace', prev_trace_time,
                                          request_start_time)
                prev_trace_time = data['trace'].get('start_trace_time')

            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        if 'start_trace_time' in item:
                            self.__process_item_data(item, prev_trace_time,
                                                     request_start_time)
                            prev_trace_time = item.get('start_trace_time')

                        elif 'trace' in item:
                            self.__process_trace_data(item, 'trace',
                                                      prev_trace_time,
                                                      request_start_time)
                            prev_trace_time = item['trace'].get(
                                'start_trace_time')

        return output_data

    def __process_trace_data(self, data, key, prev_time, request_start_time):
        """Process trace data to add latency and step information."""
        trace = data[key]
        if 'start_trace_time' in trace:
            self.__validate_trace_time(trace['start_trace_time'])

            latency = self.__calculate_latency(trace['start_trace_time'],
                                               prev_time, request_start_time)

            trace['latency'] = latency
            trace['step_number'] = self.__step_counter

            # Track latency in metrics
            self.__metrics.track_latency(f"step_{self.__step_counter}",
                                         latency)

            self.__step_counter += 1
            data[key] = trace

    def __process_item_data(self, item, prev_time, request_start_time):
        """Process item data to add latency and step information."""
        self.__validate_trace_time(item['start_trace_time'])

        latency = self.__calculate_latency(item['start_trace_time'], prev_time,
                                           request_start_time)

        item['latency'] = latency
        item['step_number'] = self.__step_counter

        # Track latency in metrics
        self.__metrics.track_latency(f"step_{self.__step_counter}", latency)

        self.__step_counter += 1

    @staticmethod
    def __validate_trace_time(trace_time):
        """Validate that trace time is a float."""
        if not isinstance(trace_time, float):
            raise ValueError(
                "The key 'start_trace_time' should be a time.time() object.")

    @staticmethod
    def __calculate_latency(current_time, prev_time, request_start_time):
        """Calculate latency between trace times."""
        if prev_time is None:
            return current_time - request_start_time
        return current_time - prev_time

    def watch(self,
              capture_input: bool = True,
              capture_output: bool = True,
              call_type: Optional[str] = None):
        """
        Decorator to track API calls and log execution metadata.
        
        Args:
            capture_input: Whether to capture function input
            capture_output: Whether to capture function output
            call_type: Type of call being made
            
        Returns:
            Decorated function
        """

        def wrapper(func: Callable):

            async def async_inner(*args, **kwargs):
                """Handle async functions."""
                return await self.__process_function(func, args, kwargs,
                                                     capture_input,
                                                     capture_output, call_type,
                                                     True)

            def sync_inner(*args, **kwargs):
                """Handle synchronous functions."""
                return self.__process_function(func, args, kwargs,
                                               capture_input, capture_output,
                                               call_type, False)

            return async_inner if asyncio.iscoroutinefunction(
                func) else sync_inner

        return wrapper

    async def __process_async_function(self, func, args, kwargs, capture_input,
                                       capture_output, call_type):
        """Process async function execution and log results."""
        # Start timing
        request_start_time = time.time()

        # Capture input if requested
        input_data = args if capture_input and args else None
        input_log = input_data[0] if input_data else None

        # Generate observation metadata
        observation_id = str(uuid4())
        obs_timestamp = datetime.now(timezone.utc).isoformat()
        start_time = time.time()

        # Increment request counter
        self.__metrics.increment_requests()

        # Execute the function
        try:
            result = await func(*args, **kwargs)
        except Exception as e:
            logging.error("Error in async function %s: %s", func.__name__,
                          str(e))
            self.__metrics.increment_errors()
            raise

        # Capture output and calculate duration
        output_data = result if capture_output else None
        end_time = time.time()
        duration = end_time - start_time

        # Track function latency
        self.__metrics.track_latency(func.__name__, duration)

        # Begin logging
        logging_start_time = time.time()

        # Process agent feature if needed
        if self.__feature_name == "Agent" and output_data is not None:
            output_data = self.__handle_agent_feature(output_data,
                                                      request_start_time)
            run_id = self.__extract_session_id(output_data[0])
        else:
            run_id = self.__extract_session_id(input_log)

        # Prepare metadata
        metadata = self.__prepare_metadata(run_id, observation_id,
                                           obs_timestamp, start_time, end_time,
                                           duration, input_log, output_data,
                                           call_type)

        # Add metrics to metadata
        metadata['metrics'] = self.__metrics.get_metrics()

        # Add additional metadata if provided
        additional_metadata = kwargs.get('additional_metadata', {})
        if additional_metadata:
            metadata.update(additional_metadata)

        user_prompt = kwargs.get('user_prompt', {})
        if user_prompt:
            metadata.update(user_prompt)

        # Calculate logging duration
        logging_end_time = time.time()
        logging_duration = logging_end_time - logging_start_time
        metadata['logging_duration'] = logging_duration

        # Send to all destinations
        for destination in self.__destinations:
            try:
                destination.send_log(metadata)
            except Exception as e:
                logging.error("Failed to send log to destination: %s", str(e))

        # Return result with additional data if needed
        if self.__feedback_variables:
            return result, run_id, observation_id
        return result

    def __process_function(self, func, args, kwargs, capture_input,
                           capture_output, call_type, is_async):
        """Process function execution and log results."""
        # Start timing
        request_start_time = time.time()

        # Capture input if requested
        input_data = args if capture_input and args else None
        input_log = input_data[0] if input_data else None

        # Generate observation metadata
        observation_id = str(uuid4())
        obs_timestamp = datetime.now(timezone.utc).isoformat()
        start_time = time.time()

        # Increment request counter
        self.__metrics.increment_requests()

        # Execute the function
        try:
            if is_async:
                result = asyncio.run(func(*args, **kwargs))
            else:
                result = func(*args, **kwargs)
        except Exception as e:
            logging.error("Error in function %s: %s", func.__name__, str(e))
            self.__metrics.increment_errors()
            raise

        # Capture output and calculate duration
        output_data = result if capture_output else None
        end_time = time.time()
        duration = end_time - start_time

        # Track function latency
        self.__metrics.track_latency(func.__name__, duration)

        # Begin logging
        logging_start_time = time.time()

        # Process agent feature if needed
        if self.__feature_name == "Agent" and output_data is not None:
            output_data = self.__handle_agent_feature(output_data,
                                                      request_start_time)
            run_id = self.__extract_session_id(output_data[0])
        else:
            run_id = self.__extract_session_id(input_log)

        # Prepare metadata
        metadata = self.__prepare_metadata(run_id, observation_id,
                                           obs_timestamp, start_time, end_time,
                                           duration, input_log, output_data,
                                           call_type)

        # Add metrics to metadata
        metadata['metrics'] = self.__metrics.get_metrics()

        # Add additional metadata if provided
        additional_metadata = kwargs.get('additional_metadata', {})
        if additional_metadata:
            metadata.update(additional_metadata)

        user_prompt = kwargs.get('user_prompt', {})
        if user_prompt:
            metadata.update(user_prompt)

        # Calculate logging duration
        logging_end_time = time.time()
        logging_duration = logging_end_time - logging_start_time
        metadata['logging_duration'] = logging_duration

        # Send to all destinations
        for destination in self.__destinations:
            try:
                destination.send_log(metadata)
            except Exception as e:
                logging.error("Failed to send log to destination: %s", str(e))

        # Return result with additional data if needed
        if self.__feedback_variables:
            return result, run_id, observation_id
        return result

    def __prepare_metadata(self, run_id, observation_id, obs_timestamp,
                           start_time, end_time, duration, input_log,
                           output_data, call_type):
        """Prepare metadata for logging."""
        return {
            'experiment_id':
            self.__experiment_id,
            'run_id':
            run_id,
            'observation_id':
            observation_id,
            'obs_timestamp':
            obs_timestamp,
            'start_time':
            datetime.fromtimestamp(start_time, tz=pytz.utc).isoformat(),
            'end_time':
            datetime.fromtimestamp(end_time, tz=pytz.utc).isoformat(),
            'duration':
            duration,
            'input_log':
            input_log,
            'output_log':
            output_data,
            'call_type':
            call_type or self.__default_call_type,
            'feature_name':
            self.__feature_name,
            'feedback_enabled':
            self.__feedback_variables
        }

    def add_custom_metric(self, name: str, value: Any):
        """Add a custom metric to be included in logs."""
        self.__metrics.add_custom_metric(name, value)

    def track_memory(self, usage: float):
        """Track memory usage."""
        self.__metrics.track_memory(usage)

    def track_cpu(self, usage: float):
        """Track CPU usage in metrics."""
        self.__metrics.track_cpu(usage)

    def reset_metrics(self):
        """Reset all collected metrics."""
        self.__metrics.reset_metrics()

    def get_metrics(self):
        """Get all collected metrics."""
        return self.__metrics.get_metrics()


# Example usage with multiple destinations
firehose_dest = FirehoseDestination("your-firehose-stream")
#newrelic_dest = NewRelicDestination("your-newrelic-api-key")
local_dest = LocalDestination()

# Initialize with multiple destinations
obs = Observability(destinations=[firehose_dest, local_dest],
                    experiment_id="test-experiment",
                    feature_name="Agent",
                    feedback_variables=True)


# Decorate a function to track its execution
@obs.watch(capture_input=True, capture_output=True)
def example_function(input_data):
    # Track custom metrics during execution
    obs.add_custom_metric("input_length", len(str(input_data)))

    # Track resource usage
    obs.track_cpu(0.5)  # Example CPU usage
    obs.track_memory(128.5)  # Example memory usage in MB

    # Function logic
    result = {"response": f"Processed {input_data}"}
    return result


# Call the decorated function
#result = example_function("test input")
