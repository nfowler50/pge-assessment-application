import json
import logging

from auth import AuthVerifier

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
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
        authenticator = AuthVerifier(logger = logger)
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"Error": "Failed to initialize authenticator"})
        }

    # Handle the login event
    if event['httpMethod'] == 'POST' and event['path'] == '/login':
        try:
            body = json.loads(event.get("body", "{}"))
            username = body.get("username")
            password = body.get("password")
            
            # Validate credentials
            if not authenticator.validate_credentials(username, password):
                return {
                    "statusCode": 401,
                    "body": json.dumps({"Error": "Bad username or password"})
                }
            
            # Generate JWT
            token = authenticator.generate_jwt(username)
            return {
                "statusCode": 200,
                "body": json.dumps({"access_token": token})
            }
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return {
                "statusCode": 400,
                "body": json.dumps({"Error": "Invalid request"})
            }
    
    # Default response for incorrect path
    return {
        "statusCode": 404,
        "body": json.dumps({"Error": "Not Found"})
    }