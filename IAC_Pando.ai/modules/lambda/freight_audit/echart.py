import json
import random
import boto3
from typing import List, Dict, Any, Tuple, Optional, Union

def data_to_echart(data: List[Dict[str, Any]], 
                   use_ai: bool = False, 
                   bedrock_client=None,
                   model_id: str = "anthropic.claude-3-7-sonnet-20250219-v1:0"
                   ) -> Dict[str, Any]:
    """
    Analyzes SQL/table data and converts it to ECharts format with a descriptive title.
    
    Args:
        data: List of dictionaries representing rows of data
        use_ai: Whether to use Claude via Bedrock to determine chart type
        bedrock_client: Pre-configured boto3 bedrock-runtime client
        model_id: Claude model ID for Bedrock
      # chart_hint: Optional user hint about desired chart type
        
    Returns:
        Dictionary containing ECharts configuration
    """
    if not data or not isinstance(data, list) or len(data) == 0:
        raise ValueError("Input must be a non-empty list of data dictionaries")
    
    # Take a sample of data if it's large
    sample_size = min(10, len(data))
    sample_data = random.sample(data, sample_size) if len(data) > sample_size else data
    
    # Clean column names - strip whitespace
    for row in data:
        if isinstance(row, dict):
            clean_row = {}
            for k, v in row.items():
                clean_row[k.strip() if isinstance(k, str) else k] = v
            row.clear()
            row.update(clean_row)
    
    # Determine chart type and get description
    chart_info = {"type": "bar", "description": "", "sub_type": None}
    if use_ai and bedrock_client:
        chart_info = analyze_with_bedrock(sample_data, bedrock_client, model_id)
        print(chart_info)
    else:
        chart_info["type"] = "bar"  # Default fallback
    
    # Format the chart based on the determined type
    chart_config = chart_formatters[chart_info["type"]](data, chart_info.get("sub_type"))
    
    # Add title with description if available
    if chart_info["description"]:
        chart_config["title"] = {"text": chart_info["description"]}
    
    return chart_config

def analyze_with_bedrock(
    sample_data: List[Dict[str, Any]], 
    bedrock_client,
    model_id: str = "anthropic.claude-3-7-sonnet-20250219-v1:0"
) -> Dict[str, str]:
    """
    Uses Claude via AWS Bedrock to analyze data and recommend chart type with description.
    
    Returns:
        Dict with keys 'type', 'description', and 'sub_type'
    """
    # Prepare the prompt for Claude
    chart_options = "line, bar, pie, trend, categorical"
    #hint_text = f"The user has suggested {chart_hint} as the chart type. " if chart_hint else ""
    
    prompt = f"""You are a data visualization expert. Analyze this data sample:
{json.dumps(sample_data, indent=2)}

Based on the structure and content of the data:

1. Recommend the best chart type from: {chart_options}
2. If appropriate, specify a sub-type (e.g., 'stacked' for bar, 'area' for line, etc.)
3. Write a brief one-sentence description of what the chart shows

For reference:
- 'bar' is for comparing discrete categories where precise comparison of individual values is important
- 'line' is for showing continuous data or time series with an emphasis on changes over time
- 'pie' is for showing proportions of a whole, part-to-whole relationships, or percentage distributions
- 'trend' is for showing patterns over time with trend lines and regression analysis
- 'categorical' is for grouped or comparative categorical data

Important guidance:
- When data represents distributions, proportions, or percentages that sum to a meaningful whole, prefer 'pie'
- When data shows two columns with a name/category column and a single value column, 'pie' is often ideal
- When there are fewer than 10 categories and the goal is to show relative proportions, use 'pie'
- When data shows values changing over time (dates, months, years), prefer 'line' or 'trend' charts
- If the data includes time-based columns AND you need to see overall direction/patterns, use 'trend'
- For financial or measurement data tracked over time periods, 'line' or 'trend' is strongly preferred over 'bar'

Time-series detection:
- Look for columns containing dates, months, years, or time periods
- If values are tracked across time periods, this is a time-series and should use 'line' or 'trend'
- For expenses, costs, or values measured over time, 'trend' charts help identify overall patterns

Format your response exactly like this:
TYPE: [your type recommendation]
SUB_TYPE: [optional sub-type]
DESCRIPTION: [your brief description]

Only use the chart types listed above.
"""
    
    # Call Claude via Bedrock
    try:
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
 

        response_body = json.loads(response.get('body').read())
        content = response_body.get('content', [])[0].get('text', '').strip()
        
        # Extract type, sub-type and description
        result = {"type": "bar", "description": "", "sub_type": None}
        
        type_match = content.split("TYPE:", 1)
        if len(type_match) > 1:
            type_line = type_match[1].split("\n", 1)[0].strip().lower()
            # Match against allowed chart types
            for chart_type in ["line", "bar", "pie", "trend", "categorical"]:
                if chart_type in type_line:
                    result["type"] = chart_type
                    break
        
        # Extract sub-type if present
        sub_type_match = content.split("SUB_TYPE:", 1)
        if len(sub_type_match) > 1:
            sub_type_line = sub_type_match[1].split("\n", 1)[0].strip().lower()
            if sub_type_line and sub_type_line != "none" and sub_type_line != "n/a":
                result["sub_type"] = sub_type_line
        
        desc_match = content.split("DESCRIPTION:", 1)
        if len(desc_match) > 1:
            result["description"] = desc_match[1].strip()
            # If there are multiple lines, just take the first one
            if "\n" in result["description"]:
                result["description"] = result["description"].split("\n", 1)[0].strip()
        
        return result
    except Exception as e:
        print(f"Error calling Bedrock API: {e}")
        return {"type": "bar", "description": "", "sub_type": None}

def identify_axes(data: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """
    Identifies the most suitable columns for x and y axes.
    
    Returns:
        Tuple of (x_column, list_of_y_columns)
    """
    keys = list(data[0].keys())
    
    # Analyze each column to determine its type
    column_types = {}
    for key in keys:
        # Skip empty columns
        if all(not row.get(key) for row in data):
            continue
            
        # Check numeric percentage
        try:
            sample = [row[key] for row in data[:min(len(data), 10)] if row.get(key) is not None]
            numeric_count = sum(1 for val in sample if isinstance(val, (int, float)) or 
                              (isinstance(val, str) and val.replace('.', '', 1).replace(',', '', 1).isdigit()))
            numeric_ratio = numeric_count / len(sample) if sample else 0
            
            # Check unique value percentage
            unique_values = set(str(row.get(key, "")) for row in data)
            unique_ratio = len(unique_values) / len(data)
            
            column_types[key] = {
                "numeric_ratio": numeric_ratio,
                "unique_ratio": unique_ratio,
                "key": key
            }
        except:
            column_types[key] = {"numeric_ratio": 0, "unique_ratio": 1, "key": key}
    
    # Sort keys by criteria for x-axis (low numeric ratio, reasonable unique ratio)
    x_candidates = sorted(
        [info for info in column_types.values() if info["unique_ratio"] < 0.9],
        key=lambda x: (x["numeric_ratio"], x["unique_ratio"])
    )
    
    # Sort keys by criteria for y-axis (high numeric ratio)
    y_candidates = sorted(
        [info for info in column_types.values() if info["numeric_ratio"] > 0.7],
        key=lambda x: -x["numeric_ratio"]
    )
    
    # Select best x and y columns
    x_column = x_candidates[0]["key"] if x_candidates else keys[0]
    y_columns = [info["key"] for info in y_candidates] if y_candidates else [k for k in keys if k != x_column]
    
    # If no clear y columns found, take all non-x columns that appear to have useful data
    if not y_columns:
        y_columns = [k for k in keys if k != x_column and any(row.get(k) for row in data)]
    
    return x_column, y_columns[:5]  # Limit to 5 y-columns y_columns[:5]

def identify_value_and_name_columns(data: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Identifies the columns that would be suitable for names/categories and values
    for pie charts and similar visualizations.
    
    Returns:
        Tuple of (name_column, value_column)
    """
    keys = list(data[0].keys())
    
    # Analyze each column to determine its type
    column_types = {}
    for key in keys:
        # Skip empty columns
        if all(not row.get(key) for row in data):
            continue
            
        # Check numeric percentage
        try:
            sample = [row[key] for row in data[:min(len(data), 10)] if row.get(key) is not None]
            numeric_count = sum(1 for val in sample if isinstance(val, (int, float)) or 
                              (isinstance(val, str) and val.replace('.', '', 1).replace(',', '', 1).isdigit()))
            numeric_ratio = numeric_count / len(sample) if sample else 0
            
            # Check unique value percentage
            unique_values = set(str(row.get(key, "")) for row in data)
            unique_ratio = len(unique_values) / len(data)
            
            column_types[key] = {
                "numeric_ratio": numeric_ratio,
                "unique_ratio": unique_ratio,
                "key": key
            }
        except:
            column_types[key] = {"numeric_ratio": 0, "unique_ratio": 1, "key": key}
    
    # Best name column: non-numeric, reasonable uniqueness
    name_candidates = sorted(
        [info for info in column_types.values() if info["numeric_ratio"] < 0.5],
        key=lambda x: (x["unique_ratio"], -len(x["key"]))
    )
    
    # Best value column: highly numeric
    value_candidates = sorted(
        [info for info in column_types.values() if info["numeric_ratio"] > 0.8],
        key=lambda x: -x["numeric_ratio"]
    )
    
    name_column = name_candidates[0]["key"] if name_candidates else keys[0]
    value_column = value_candidates[0]["key"] if value_candidates else [k for k in keys if k != name_column][0]
    
    return name_column, value_column

def format_bar_chart(data: List[Dict[str, Any]], sub_type: str = None) -> Dict[str, Any]:
    """
    Formats data for bar chart.
    
    Args:
        data: List of data dictionaries
        sub_type: Optional sub-type (e.g., 'stacked')
        
    Returns:
        ECharts configuration
    """
    # Identify axes
    x_column, y_columns = identify_axes(data)
    
    # Extract unique x values in order of appearance
    x_values = []
    seen_values = set()
    
    for row in data:
        val = row[x_column]
        val_str = str(val).strip()
        if val_str not in seen_values:
            x_values.append(val_str)
            seen_values.add(val_str)

    print(f"Number of unique x values: {len(x_values)}")
    print(f"X values: {x_values}")
    # Create series data for each y column
    series = []
    for y_col in y_columns:
        # Create a map of x values to y values
        value_map = {}
        for row in data:
            try:
                x_val = str(row[x_column]).strip()
                y_val = row[y_col]
                # Convert to float if possible
                if isinstance(y_val, str):
                    y_val = float(y_val.replace(',', ''))
                else:
                    y_val = float(y_val) if y_val is not None else 0
                value_map[x_val] = y_val
            except (ValueError, TypeError):
                continue
        
        # Generate data array in the order of xValues
        series_data = [value_map.get(x, 0) for x in x_values]
        
        series_config = {
            "name": y_col.strip() if isinstance(y_col, str) else y_col,
            "data": series_data,
            "type": "bar"
        }
        
        # Add stack property if sub_type is stacked
        if sub_type == "stacked":
            series_config["stack"] = "total"
            
        series.append(series_config)
    
    # Build final chart configuration
    chart_config = {
        "xAxis": {
            "type": "category",
            "data": x_values
        },
        "yAxis": {
            "type": "value"
        },
        "series": series,
        "tooltip": {
            "trigger": "axis"
        },
        "legend": {}
    }
    
    return chart_config

def format_line_chart(data: List[Dict[str, Any]], sub_type: str = None) -> Dict[str, Any]:
    """
    Formats data for line chart.
    
    Args:
        data: List of data dictionaries
        sub_type: Optional sub-type (e.g., 'area', 'smooth')
        
    Returns:
        ECharts configuration
    """
    # Identify axes
    x_column, y_columns = identify_axes(data)
    
    # Extract unique x values in order of appearance
    x_values = []
    seen_values = set()
    
    for row in data:
        val = row[x_column]
        val_str = str(val).strip()
        if val_str not in seen_values:
            x_values.append(val_str)
            seen_values.add(val_str)
    
    print(f"Number of unique x values: {len(x_values)}")
    print(f"X values: {x_values}")
    # Create series data for each y column
    series = []
    for y_col in y_columns:
        # Create a map of x values to y values
        value_map = {}
        for row in data:
            try:
                x_val = str(row[x_column]).strip()
                y_val = row[y_col]
                # Convert to float if possible
                if isinstance(y_val, str):
                    y_val = float(y_val.replace(',', ''))
                else:
                    y_val = float(y_val) if y_val is not None else 0
                value_map[x_val] = y_val
            except (ValueError, TypeError):
                continue
        
        # Generate data array in the order of xValues
        series_data = [value_map.get(x, 0) for x in x_values]
        
        series_config = {
            "name": y_col.strip() if isinstance(y_col, str) else y_col,
            "data": series_data,
            "type": "line"
        }
        
        # Add area if sub_type is area
        if sub_type == "area":
            series_config["areaStyle"] = {}
        
        # Add smooth if sub_type is smooth
        if sub_type == "smooth":
            series_config["smooth"] = True
            
        series.append(series_config)
    
    # Build final chart configuration
    chart_config = {
        "xAxis": {
            "type": "category",
            "data": x_values
        },
        "yAxis": {
            "type": "value"
        },
        "series": series,
        "tooltip": {
            "trigger": "axis"
        },
        "legend": {}
    }
    
    return chart_config

def format_pie_chart(data: List[Dict[str, Any]], sub_type: str = None) -> Dict[str, Any]:
    """
    Formats data for pie chart.
    
    Args:
        data: List of data dictionaries
        sub_type: Optional sub-type (e.g., 'doughnut', 'rose')
        
    Returns:
        ECharts configuration
    """
    # Identify name and value columns
    name_column, value_column = identify_value_and_name_columns(data)
    
    # Create pie chart data
    pie_data = []
    for row in data:
        try:
            name = str(row[name_column]).strip()
            value = row[value_column]
            if isinstance(value, str):
                value = float(value.replace(',', ''))
            else:
                value = float(value) if value is not None else 0
                
            pie_data.append({"name": name, "value": value})
        except (ValueError, TypeError):
            continue
    
    # Build series configuration
    series_config = {
        "name": value_column,
        "type": "pie",
        "radius": "55%",
        "data": pie_data,
        "emphasis": {
            "itemStyle": {
                "shadowBlur": 10,
                "shadowOffsetX": 0,
                "shadowColor": "rgba(0, 0, 0, 0.5)"
            }
        }
    }
    
    # Handle sub-types
    if sub_type == "doughnut":
        series_config["radius"] = ["40%", "70%"]
    elif sub_type == "rose":
        series_config["roseType"] = "area"
    
    # Build final chart configuration
    chart_config = {
        "tooltip": {
            "trigger": "item",
            "formatter": "{a} <br/>{b}: {c} ({d}%)"
        },
        "legend": {
            "orient": "vertical",
            "left": 10,
            "data": [row[name_column] for row in data]
        },
        "series": [series_config]
    }
    
    return chart_config

def format_trend_chart(data: List[Dict[str, Any]], sub_type: str = None) -> Dict[str, Any]:
    """
    Formats data for trend chart (line chart with trend line).
    
    Args:
        data: List of data dictionaries
        sub_type: Optional sub-type
        
    Returns:
        ECharts configuration
    """
    # Start with a line chart as the base
    chart_config = format_line_chart(data)
    
    # Identify axes
    x_column, y_columns = identify_axes(data)
    
    # Add trend lines for each series
    for i, series in enumerate(chart_config["series"]):
        # Add a trend line (linear regression) using markLine
        trend_line = {
            "markLine": {
                "silent": True,
                "lineStyle": {
                    "width": 2,
                    "type": "dashed"
                },
                "data": [
                    {"type": "linear", "name": "Trend Line"}
                ]
            }
        }
        
        # Update the series with the trend line
        chart_config["series"][i].update(trend_line)
    
    return chart_config

def format_categorical_chart(data: List[Dict[str, Any]], sub_type: str = None) -> Dict[str, Any]:
    """
    Formats data for categorical bar charts (e.g., grouped categories).
    
    Args:
        data: List of data dictionaries
        sub_type: Optional sub-type
        
    Returns:
        ECharts configuration
    """
    # This is a special type of bar chart with enhanced handling for categories
    # First identify potential category/grouping columns
    keys = list(data[0].keys())
    
    # Try to identify columns suitable for categories and time periods
    # We're looking for columns with low cardinality that could be categories
    column_types = {}
    for key in keys:
        try:
            # Check numeric percentage
            sample = [row[key] for row in data if row.get(key) is not None]
            numeric_count = sum(1 for val in sample if isinstance(val, (int, float)) or 
                              (isinstance(val, str) and val.replace('.', '', 1).replace(',', '', 1).isdigit()))
            numeric_ratio = numeric_count / len(sample) if sample else 0
            
            # Check unique value percentage
            unique_values = set(str(row.get(key, "")) for row in data)
            unique_ratio = len(unique_values) / len(data)
            
            column_types[key] = {
                "numeric_ratio": numeric_ratio,
                "unique_ratio": unique_ratio,
                "unique_count": len(unique_values),
                "key": key
            }
        except:
            column_types[key] = {"numeric_ratio": 0, "unique_ratio": 1, "unique_count": 0, "key": key}
    
    # Find potential category columns - columns with few unique values
    category_candidates = sorted(
        [info for info in column_types.values() if 2 <= info["unique_count"] <= 10],
        key=lambda x: x["unique_count"]
    )
    
    # Find potential time/series columns - could be dates or years
    time_candidates = sorted(
        [info for info in column_types.values() if info["unique_count"] >= 2],
        key=lambda x: (x["unique_ratio"], x["unique_count"])
    )
    
    # Find value columns - numeric columns that aren't categories or time
    value_candidates = sorted(
        [info for info in column_types.values() if info["numeric_ratio"] > 0.8],
        key=lambda x: -x["numeric_ratio"]
    )
    
    # Determine the best columns to use based on the data structure
    if len(category_candidates) >= 1 and len(time_candidates) >= 1:
        # We have both category and time columns - can do a comparative chart
        category_col = category_candidates[0]["key"]
        time_col = time_candidates[0]["key"] if time_candidates[0]["key"] != category_col else time_candidates[1]["key"] if len(time_candidates) > 1 else None
        value_col = value_candidates[0]["key"] if value_candidates else None
        
        # If we have all three column types, create a comparative categorical chart
        if category_col and time_col and value_col:
            return format_comparative_categorical(data, category_col, time_col, value_col)
    
    # Fallback to regular bar chart if we can't identify good categorical structure
    return format_bar_chart(data)

def format_comparative_categorical(data: List[Dict[str, Any]], category_col: str, time_col: str, value_col: str) -> Dict[str, Any]:
    """
    Creates a comparative categorical chart showing categories over time periods.
    
    Args:
        data: List of data dictionaries
        category_col: Column containing categories
        time_col: Column containing time periods
        value_col: Column containing values
        
    Returns:
        ECharts configuration
    """
    # Extract unique categories and time periods
    categories = sorted(list(set(str(row[category_col]).strip() for row in data)))
    time_periods = sorted(list(set(str(row[time_col]).strip() for row in data)))
    
    # Create series for each category
    series = []
    for category in categories:
        category_data = []
        for period in time_periods:
            # Find matching row
            matching_rows = [row for row in data if str(row[category_col]).strip() == category and str(row[time_col]).strip() == period]
            if matching_rows:
                try:
                    value = matching_rows[0][value_col]
                    if isinstance(value, str):
                        value = float(value.replace(',', ''))
                    else:
                        value = float(value) if value is not None else 0
                    category_data.append(value)
                except (ValueError, TypeError):
                    category_data.append(0)
            else:
                category_data.append(0)
        
        series.append({
            "name": category,
            "type": "bar",
            "data": category_data
        })
    
    # Build final chart configuration
    chart_config = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {
                "type": "shadow"
            }
        },
        "legend": {
            "data": categories
        },
        "xAxis": {
            "type": "category",
            "data": time_periods,
            "axisLabel": {
                "rotate": 45 if len(time_periods) > 5 else 0
            }
        },
        "yAxis": {
            "type": "value"
        },
        "series": series
    }
    
    return chart_config

# Dictionary mapping chart types to formatting functions
chart_formatters = {
    "bar": format_bar_chart,
    "line": format_line_chart,
    "pie": format_pie_chart,
    "trend": format_trend_chart,
    "categorical": format_categorical_chart
}
