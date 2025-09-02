"""
AWS Lambda Handler for GPT-5 Happy Hour Discovery Orchestrator
Fixed version for Lambda Function URLs (not API Gateway)
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import boto3
from supabase import create_client, Client

# Initialize AWS clients
sqs = boto3.client('sqs')
lambda_client = boto3.client('lambda')

# Initialize Supabase
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

# Configuration
AGENT_FUNCTIONS = {
    'site_agent': os.environ.get('SITE_AGENT_FUNCTION', 'happy-hour-site-agent'),
    'google_agent': os.environ.get('GOOGLE_AGENT_FUNCTION', 'happy-hour-google-agent'),
    'yelp_agent': os.environ.get('YELP_AGENT_FUNCTION', 'happy-hour-yelp-agent'),
    'voice_verify': os.environ.get('VOICE_VERIFY_FUNCTION', 'happy-hour-voice-verify')
}

def lambda_handler(event, context):
    """Main Lambda handler for Function URL requests"""
    
    print(f"Event: {json.dumps(event)}")
    
    # Parse the Lambda Function URL event structure
    request_context = event.get('requestContext', {})
    http = request_context.get('http', {})
    http_method = http.get('method', 'GET')
    path = http.get('path', '/')
    
    # Alternative: check for direct method
    if 'httpMethod' in event:
        http_method = event['httpMethod']
        path = event.get('path', event.get('rawPath', '/'))
    
    # CORS headers for all responses
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Accept'
    }
    
    # Handle OPTIONS for CORS preflight
    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        # Route handling
        if path == '/' and http_method == 'GET':
            return handle_health_check(headers)
        elif path == '/api/analyze' and http_method == 'POST':
            return handle_analyze(event, headers)
        elif path.startswith('/api/job/') and http_method == 'GET':
            job_id = path.split('/')[-1]
            return handle_job_status(job_id, headers)
        elif path == '/api/stats' and http_method == 'GET':
            return handle_stats(headers)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Not found', 'path': path, 'method': http_method})
            }
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
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
            'version': '1.0.1',
            'runtime': 'AWS Lambda',
            'gpt_version': 'GPT-5 Exclusive',
            'database': 'connected' if supabase else 'not connected'
        })
    }

def handle_analyze(event, headers):
    """Handle restaurant analysis request"""
    
    if not supabase:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Database connection not configured'})
        }
    
    try:
        # Parse request body
        body_str = event.get('body', '{}')
        
        # Handle base64 encoding if present
        if event.get('isBase64Encoded', False):
            import base64
            body_str = base64.b64decode(body_str).decode('utf-8')
        
        body = json.loads(body_str)
        
        # Validate required fields
        if not body.get('name'):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Restaurant name is required'})
            }
        
        # Get or create venue
        venue_result = supabase.table('venues').select('id').eq('name', body['name']).execute()
        
        if venue_result.data and len(venue_result.data) > 0:
            venue_id = venue_result.data[0]['id']
        else:
            # Parse address for city and state
            city = None
            state = None
            address = body.get('address')
            if address:
                parts = address.split(',')
                if len(parts) >= 2:
                    city = parts[-2].strip() if len(parts) >= 3 else None
                    if parts[-1].strip():
                        state_zip = parts[-1].strip().split()
                        if state_zip:
                            state = state_zip[0] if len(state_zip) > 0 else None
            
            venue_data = {
                'id': str(uuid.uuid4()),
                'name': body['name'],
                'address': address,
                'city': city,
                'state': state,
                'phone_e164': body.get('phone'),
                'website': body.get('website'),
                'created_at': datetime.utcnow().isoformat()
            }
            
            supabase.table('venues').insert(venue_data).execute()
            venue_id = venue_data['id']
        
        # Create analysis job
        job_id = str(uuid.uuid4())
        job_data = {
            'id': job_id,
            'venue_id': venue_id,
            'status': 'queued',
            'source': 'api',
            'priority': body.get('priority', 5),
            'started_at': datetime.utcnow().isoformat(),
            'cri': {
                'name': body['name'],
                'address': body.get('address'),
                'phone': body.get('phone'),
                'website': body.get('website')
            }
        }
        
        supabase.table('analysis_jobs').insert(job_data).execute()
        
        # Note: Agent invocation would go here in production
        # For now, we're just creating the job record
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'job_id': job_id,
                'venue_id': venue_id,
                'status': 'queued',
                'message': 'Analysis job created successfully',
                'estimated_time_seconds': 45
            })
        }
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Error in handle_analyze: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Error creating analysis job: {str(e)}'})
        }

def handle_job_status(job_id, headers):
    """Get status of an analysis job"""
    
    if not supabase:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Database connection not configured'})
        }
    
    try:
        result = supabase.table('analysis_jobs').select('*').eq('id', job_id).execute()
        
        if not result.data or len(result.data) == 0:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Job not found'})
            }
        
        job = result.data[0]
        
        # Get happy hour data if job is completed
        happy_hour_data = None
        if job['status'] == 'completed' and job['venue_id']:
            hh_result = supabase.table('happy_hour_records').select('*').eq('venue_id', job['venue_id']).execute()
            if hh_result.data and len(hh_result.data) > 0:
                happy_hour_data = hh_result.data[0]
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'job_id': job['id'],
                'status': job['status'],
                'venue_id': job['venue_id'],
                'started_at': job['started_at'],
                'completed_at': job.get('completed_at'),
                'confidence_score': job.get('final_confidence'),
                'happy_hour_data': happy_hour_data,
                'error_message': job.get('error_message')
            })
        }
        
    except Exception as e:
        print(f"Error in handle_job_status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Error fetching job status: {str(e)}'})
        }

def handle_stats(headers):
    """Get system statistics"""
    
    if not supabase:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Database connection not configured'})
        }
    
    try:
        # Get total venues
        venues_result = supabase.table('venues').select('id', count='exact').execute()
        total_venues = venues_result.count if venues_result else 0
        
        # Get total jobs
        jobs_result = supabase.table('analysis_jobs').select('id', count='exact').execute()
        total_jobs = jobs_result.count if jobs_result else 0
        
        # Get jobs by status
        queued_result = supabase.table('analysis_jobs').select('id', count='exact').eq('status', 'queued').execute()
        completed_result = supabase.table('analysis_jobs').select('id', count='exact').eq('status', 'completed').execute()
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'total_venues': total_venues,
                'total_jobs': total_jobs,
                'queued_jobs': queued_result.count if queued_result else 0,
                'completed_jobs': completed_result.count if completed_result else 0,
                'system_status': 'operational',
                'runtime': 'AWS Lambda'
            })
        }
        
    except Exception as e:
        print(f"Error in handle_stats: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Error fetching stats: {str(e)}'})
        }