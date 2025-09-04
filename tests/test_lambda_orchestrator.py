"""Test suite for lambda_orchestrator.py"""

import pytest
import json
from unittest.mock import Mock, patch
from lambda_orchestrator import (
    lambda_handler, 
    parse_request_event, 
    get_client_ip, 
    check_rate_limit,
    create_response,
    handle_health_check,
    parse_address,
    parse_query_string
)


class TestLambdaHandler:
    """Test cases for the main lambda_handler function"""
    
    def test_health_check_api_gateway(self, lambda_context, mock_supabase, mock_openai):
        """Test health check endpoint with API Gateway event"""
        event = {
            'httpMethod': 'GET',
            'path': '/',
            'headers': {},
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'healthy'
        assert body['service'] == 'Happy Hour Discovery Orchestrator'
        assert body['gpt_version'] == 'GPT-5 Exclusive'
    
    def test_health_check_function_url(self, lambda_context, mock_supabase, mock_openai):
        """Test health check endpoint with Function URL event"""
        event = {
            'requestContext': {
                'http': {
                    'method': 'GET',
                    'path': '/',
                    'sourceIp': '127.0.0.1'
                }
            },
            'headers': {}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'healthy'
    
    def test_cors_preflight(self, lambda_context):
        """Test CORS preflight OPTIONS request"""
        event = {
            'httpMethod': 'OPTIONS',
            'path': '/api/analyze',
            'headers': {'Origin': 'http://localhost:3000'},
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
    
    def test_not_found(self, lambda_context):
        """Test 404 for unknown endpoints"""
        event = {
            'httpMethod': 'GET',
            'path': '/unknown',
            'headers': {},
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'Not found' in body['error']
    
    def test_rate_limiting(self, lambda_context):
        """Test rate limiting functionality"""
        event = {
            'httpMethod': 'GET',
            'path': '/',
            'headers': {},
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        # Make requests up to the limit
        with patch('lambda_orchestrator.MAX_REQUESTS_PER_MINUTE', 2):
            # First request should succeed
            response1 = lambda_handler(event, lambda_context)
            assert response1['statusCode'] == 200
            
            # Second request should succeed
            response2 = lambda_handler(event, lambda_context)
            assert response2['statusCode'] == 200
            
            # Third request should be rate limited
            response3 = lambda_handler(event, lambda_context)
            assert response3['statusCode'] == 429


class TestAnalyzeEndpoint:
    """Test cases for the /api/analyze endpoint"""
    
    def test_analyze_success(self, sample_api_gateway_event, lambda_context, 
                           mock_supabase, mock_lambda_client):
        """Test successful analysis request"""
        response = lambda_handler(sample_api_gateway_event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'job_id' in body
        assert body['status'] == 'queued'
        assert body['restaurant_name'] == 'Test Restaurant'
    
    def test_analyze_missing_name(self, lambda_context):
        """Test analyze request without restaurant name"""
        event = {
            'httpMethod': 'POST',
            'path': '/api/analyze',
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({}),
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Restaurant name is required' in body['error']
    
    def test_analyze_invalid_json(self, lambda_context):
        """Test analyze request with invalid JSON"""
        event = {
            'httpMethod': 'POST',
            'path': '/api/analyze',
            'headers': {'Content-Type': 'application/json'},
            'body': 'invalid json',
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid JSON' in body['error']
    
    def test_analyze_empty_body(self, lambda_context):
        """Test analyze request with empty body"""
        event = {
            'httpMethod': 'POST',
            'path': '/api/analyze',
            'headers': {'Content-Type': 'application/json'},
            'body': '',
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 400


class TestJobStatusEndpoint:
    """Test cases for the /api/job/{job_id} endpoint"""
    
    def test_job_status_queued(self, lambda_context, mock_datetime):
        """Test job status for queued job"""
        job_id = f"{int(mock_datetime.utcnow().timestamp())}-test-uuid"
        
        event = {
            'httpMethod': 'GET',
            'path': f'/api/job/{job_id}',
            'headers': {},
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'queued'
        assert body['job_id'] == job_id
    
    def test_job_status_completed(self, lambda_context):
        """Test job status for completed job (old timestamp)"""
        import time
        old_timestamp = int(time.time()) - 60  # 1 minute ago
        job_id = f"{old_timestamp}-test-uuid"
        
        event = {
            'httpMethod': 'GET',
            'path': f'/api/job/{job_id}',
            'headers': {},
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'completed'
        assert 'happy_hour_data' in body
    
    def test_job_status_empty_id(self, lambda_context):
        """Test job status with empty job ID"""
        event = {
            'httpMethod': 'GET',
            'path': '/api/job/',
            'headers': {},
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 404  # Not found due to routing


class TestRestaurantSearch:
    """Test cases for the /api/restaurants/search endpoint"""
    
    def test_restaurant_search_success(self, lambda_context, mock_supabase):
        """Test successful restaurant search"""
        mock_supabase.table().select().ilike().limit().execute.return_value = Mock(
            data=[
                {
                    'id': 'test-id',
                    'name': 'Test Restaurant',
                    'address': '123 Test St',
                    'phone_e164': '(555) 123-4567',
                    'city': 'Test City',
                    'state': 'CA',
                    'business_type': 'restaurant'
                }
            ]
        )
        
        event = {
            'httpMethod': 'GET',
            'path': '/api/restaurants/search',
            'rawQueryString': 'query=test&limit=10',
            'headers': {},
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['restaurants']) > 0
        assert body['query'] == 'test'
    
    def test_restaurant_search_missing_query(self, lambda_context):
        """Test restaurant search without query parameter"""
        event = {
            'httpMethod': 'GET',
            'path': '/api/restaurants/search',
            'rawQueryString': '',
            'headers': {},
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 400


class TestUtilityFunctions:
    """Test cases for utility functions"""
    
    def test_parse_request_event_api_gateway(self):
        """Test parsing API Gateway event format"""
        event = {
            'httpMethod': 'POST',
            'path': '/api/test',
            'queryStringParameters': {'param1': 'value1'}
        }
        
        method, path, query_string = parse_request_event(event)
        
        assert method == 'POST'
        assert path == '/api/test'
        assert 'param1=value1' in query_string
    
    def test_parse_request_event_function_url(self):
        """Test parsing Function URL event format"""
        event = {
            'requestContext': {
                'http': {
                    'method': 'GET',
                    'path': '/api/test'
                }
            },
            'rawQueryString': 'param1=value1'
        }
        
        method, path, query_string = parse_request_event(event)
        
        assert method == 'GET'
        assert path == '/api/test'
        assert query_string == 'param1=value1'
    
    def test_get_client_ip_function_url(self):
        """Test extracting client IP from Function URL event"""
        event = {
            'requestContext': {
                'http': {
                    'sourceIp': '192.168.1.1'
                }
            }
        }
        
        ip = get_client_ip(event)
        assert ip == '192.168.1.1'
    
    def test_get_client_ip_api_gateway(self):
        """Test extracting client IP from API Gateway event"""
        event = {
            'requestContext': {
                'sourceIp': '10.0.0.1'
            }
        }
        
        ip = get_client_ip(event)
        assert ip == '10.0.0.1'
    
    def test_get_client_ip_header_fallback(self):
        """Test extracting client IP from headers"""
        event = {
            'headers': {
                'X-Forwarded-For': '203.0.113.1, 70.41.3.18'
            }
        }
        
        ip = get_client_ip(event)
        assert ip == '203.0.113.1'
    
    def test_check_rate_limit(self):
        """Test rate limiting logic"""
        # First request should pass
        assert check_rate_limit('127.0.0.1') is True
        
        # Multiple requests within limit should pass
        for _ in range(59):  # Assuming MAX_REQUESTS_PER_MINUTE = 60
            assert check_rate_limit('127.0.0.1') is True
        
        # Request over limit should fail
        with patch('lambda_orchestrator.MAX_REQUESTS_PER_MINUTE', 60):
            assert check_rate_limit('127.0.0.1') is False
    
    def test_create_response(self):
        """Test response creation utility"""
        response = create_response(200, {'test': 'data'})
        
        assert response['statusCode'] == 200
        assert 'Content-Type' in response['headers']
        assert json.loads(response['body'])['test'] == 'data'
    
    def test_parse_address(self):
        """Test address parsing utility"""
        address = '123 Main St, Los Angeles, CA 90210'
        city, state = parse_address(address)
        
        assert city == 'Los Angeles'
        assert state == 'CA'
    
    def test_parse_address_invalid(self):
        """Test address parsing with invalid input"""
        city, state = parse_address('')
        assert city is None
        assert state is None
        
        city, state = parse_address('Invalid Address')
        assert city is None
        assert state is None
    
    def test_parse_query_string(self):
        """Test query string parsing"""
        query_string = 'param1=value1&param2=value%20with%20spaces'
        params = parse_query_string(query_string)
        
        assert params['param1'] == 'value1'
        assert params['param2'] == 'value with spaces'
    
    def test_parse_query_string_empty(self):
        """Test query string parsing with empty input"""
        params = parse_query_string('')
        assert params == {}


class TestErrorHandling:
    """Test cases for error handling"""
    
    def test_handle_exception_in_lambda_handler(self, lambda_context):
        """Test exception handling in lambda_handler"""
        event = {
            'httpMethod': 'GET',
            'path': '/',
            'headers': {},
            'requestContext': {'sourceIp': '127.0.0.1'}
        }
        
        # Mock an exception in the handler
        with patch('lambda_orchestrator.parse_request_event', side_effect=Exception('Test error')):
            response = lambda_handler(event, lambda_context)
            
            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert 'Internal server error' in body['error']