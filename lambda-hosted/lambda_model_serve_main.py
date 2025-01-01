import json
import logging
from linear_regress_model_handler import LinearRegressModelHandler as lrmh
from auth import AuthVerifier

# Set up logging for CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize API key and model globally
authenticator = AuthVerifier()
model = lrmh(logger)

def authenticate_request(event):
    """
    Extract and validate the JWT token from the Authorization header.

    Args:
        event (dict): The Lambda event object.

    Returns:
        dict: Decoded token payload if validation is successful.
    Raises:
        ValueError: If authentication fails.
    """
    auth_header = event['headers'].get('Authorization', '')
    if not auth_header.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    return authenticator.validate_jwt(token)

def make_prediction(decoded_token, event):
    """
    Handle input data and make prediction.

    Args:
        decoded_token (dict): Decoded token payload.
        event (dict): The Lambda event object.

    Returns:
        dict: Response object for the Lambda function.
    """
    # Check if model is initialized
    if model.model is None:
        return {
            "statusCode": 503,  # Service Unavailable
            "body": json.dumps({"error": "Model is not available. Initialization failed."}),
        }

    # Get input from query parameters
    query_params = event.get("queryStringParameters", {})
    input_data = query_params.get("input")

    if not input_data:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing or invalid input data."}),
        }

    try:
        # Make prediction
        result = model.predict(input_data)
        return {
            "statusCode": 200,
            "body": json.dumps({"prediction": result}),
        }
    except ValueError as e:
        logger.error(f"Input error: {str(e)}")
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "An unexpected error occurred."}),
        }

def handler(event, context):
    """
    AWS Lambda entry point.

    Args:
        event (dict): The Lambda event object.
        context (object): The Lambda context object.

    Returns:
        dict: Response object for the Lambda function.
    """
    # Check if the event is the keep-warm event
    if 'KeepWarmRule' in event.get('detail-type', ''):
        # Log it as an info-level event
        logger.info("Keep warm ping received; this is not an error.")
        
        # You can either return immediately or perform a lightweight action
        return {
            'statusCode': 200,
            'body': "Keep warm ping successful"
        }
    
    try:
        # Authenticate request
        decoded_token = authenticate_request(event)
        logger.info(f"Token validated for user: {decoded_token['sub']}")
    except ValueError as e:
        return {
            "statusCode": 401,
            "body": json.dumps({"Error": str(e)}),
        }

    # Handle business logic
    return make_prediction(decoded_token, event)
