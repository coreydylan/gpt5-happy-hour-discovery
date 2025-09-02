"""
AWS Lambda Handler for GPT-5 Happy Hour Discovery Orchestrator
Working version for Lambda Function URLs
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

def lambda_handler(event, context):
    """Main Lambda handler for Function URL requests"""
    
    # Parse Lambda Function URL event
    request_context = event.get('requestContext', {})
    http = request_context.get('http', {})
    method = http.get('method', 'GET')
    path = http.get('path', '/')
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Accept'
    }
    
    # Handle preflight
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        # Route handling
        if path == '/' and method == 'GET':
            return handle_health_check(headers)
        elif path == '/api/analyze' and method == 'POST':
            return handle_analyze_simple(event, headers)
        elif path.startswith('/api/job/') and method == 'GET':
            job_id = path.split('/')[-1]
            return handle_job_status_simple(job_id, headers)
        elif path == '/api/stats' and method == 'GET':
            return handle_stats_simple(headers)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Not found', 
                    'path': path, 
                    'method': method,
                    'available_endpoints': [
                        'GET /',
                        'POST /api/analyze',
                        'GET /api/job/{job_id}',
                        'GET /api/stats'
                    ]
                })
            }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def handle_health_check(headers):
    """Health check endpoint"""
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'status': 'healthy',
            'service': 'Happy Hour Discovery Orchestrator',
            'version': '1.0.2',
            'runtime': 'AWS Lambda',
            'gpt_version': 'GPT-5 Exclusive',
            'database': 'mocked for now'
        })
    }

def handle_analyze_simple(event, headers):
    """Simplified analyze endpoint for testing"""
    
    try:
        # Parse body
        body_str = event.get('body', '{}')
        if event.get('isBase64Encoded', False):
            import base64
            body_str = base64.b64decode(body_str).decode('utf-8')
        
        body = json.loads(body_str) if body_str else {}
        
        if not body.get('name'):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Restaurant name is required'})
            }
        
        # Mock response for now
        job_id = str(uuid.uuid4())
        venue_id = str(uuid.uuid4())
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'job_id': job_id,
                'venue_id': venue_id,
                'status': 'queued',
                'message': 'Analysis job created (mocked for testing)',
                'restaurant_name': body['name'],
                'estimated_time_seconds': 45
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Analysis error: {str(e)}'})
        }

def handle_job_status_simple(job_id, headers):
    """Simplified job status endpoint"""
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'job_id': job_id,
            'status': 'completed',
            'venue_id': str(uuid.uuid4()),
            'started_at': datetime.utcnow().isoformat(),
            'completed_at': datetime.utcnow().isoformat(),
            'confidence_score': 0.85,
            'happy_hour_data': {
                'status': 'active',
                'schedule': {
                    'monday': [{'start': '16:00', 'end': '18:00'}],
                    'friday': [{'start': '15:00', 'end': '19:00'}]
                },
                'offers': [
                    {'type': 'drink', 'description': '$5 draft beers'},
                    {'type': 'food', 'description': 'Half price appetizers'}
                ]
            },
            'message': 'Mock data - system working!'
        })
    }

def handle_stats_simple(headers):
    """Simplified stats endpoint"""
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'total_venues': 42,
            'total_jobs': 128,
            'queued_jobs': 3,
            'completed_jobs': 125,
            'system_status': 'operational',
            'runtime': 'AWS Lambda',
            'message': 'Mock stats - system working!'
        })
    }