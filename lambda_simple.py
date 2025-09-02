import json

def lambda_handler(event, context):
    """Simple Lambda handler for testing"""
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Accept'
    }
    
    # Log the event for debugging
    print(f"Event: {json.dumps(event)}")
    print(f"Context: {context}")
    
    # Try to parse request
    request_context = event.get('requestContext', {})
    http = request_context.get('http', {})
    method = http.get('method', event.get('httpMethod', 'GET'))
    path = http.get('path', event.get('path', event.get('rawPath', '/')))
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'message': 'Hello from GPT-5 Happy Hour Discovery!',
            'method': method,
            'path': path,
            'event_keys': list(event.keys()),
            'working': True
        })
    }