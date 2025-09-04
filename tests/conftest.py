"""Pytest configuration and shared fixtures"""

import os
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import json

# Set test environment variables
os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'test-key'
os.environ['OPENAI_API_KEY'] = 'test-openai-key'
os.environ['ALLOWED_ORIGINS'] = 'http://localhost:3000,https://test.com'


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    with patch('lambda_orchestrator.get_supabase_client') as mock:
        client = Mock()
        
        # Mock table operations
        table = Mock()
        table.select.return_value = table
        table.eq.return_value = table
        table.ilike.return_value = table
        table.limit.return_value = table
        table.insert.return_value = Mock(data=None)
        table.execute.return_value = Mock(data=[], count=0)
        
        client.table.return_value = table
        mock.return_value = client
        yield client


@pytest.fixture
def mock_openai():
    """Mock OpenAI client"""
    with patch('lambda_orchestrator.get_openai_client') as mock:
        client = Mock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_lambda_client():
    """Mock AWS Lambda client"""
    with patch('lambda_orchestrator.lambda_client') as mock:
        mock.invoke.return_value = {'StatusCode': 202}
        yield mock


@pytest.fixture
def sample_api_gateway_event():
    """Sample API Gateway event"""
    return {
        'httpMethod': 'POST',
        'path': '/api/analyze',
        'headers': {
            'Content-Type': 'application/json',
            'Origin': 'http://localhost:3000'
        },
        'body': json.dumps({
            'name': 'Test Restaurant',
            'address': '123 Test St, Test City, CA 90210',
            'phone': '(555) 123-4567'
        }),
        'requestContext': {
            'sourceIp': '127.0.0.1'
        }
    }


@pytest.fixture
def sample_function_url_event():
    """Sample Lambda Function URL event"""
    return {
        'requestContext': {
            'http': {
                'method': 'POST',
                'path': '/api/analyze',
                'sourceIp': '127.0.0.1'
            }
        },
        'headers': {
            'Content-Type': 'application/json',
            'origin': 'http://localhost:3000'
        },
        'body': json.dumps({
            'name': 'Test Restaurant',
            'address': '123 Test St, Test City, CA 90210',
            'phone': '(555) 123-4567'
        })
    }


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.function_name = 'test-function'
    context.function_version = '$LATEST'
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    context.memory_limit_in_mb = 128
    context.remaining_time_in_millis = 30000
    context.aws_request_id = 'test-request-id'
    return context


@pytest.fixture(autouse=True)
def clear_rate_limit_cache():
    """Clear rate limit cache before each test"""
    import lambda_orchestrator
    lambda_orchestrator.RATE_LIMIT_CACHE.clear()
    yield
    lambda_orchestrator.RATE_LIMIT_CACHE.clear()


@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing"""
    with patch('lambda_orchestrator.datetime') as mock_dt:
        mock_dt.utcnow.return_value = datetime(2025, 1, 15, 12, 0, 0)
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.fromtimestamp = datetime.fromtimestamp
        yield mock_dt