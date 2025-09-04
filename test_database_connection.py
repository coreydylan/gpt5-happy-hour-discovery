#!/usr/bin/env python3
"""
Test database connection and check actual job status
"""

import os
import sys
import json
import requests
from datetime import datetime

def test_supabase_connection():
    """Test direct Supabase connection"""
    supabase_url = "https://vnnplotrwbtjtopknxgl.supabase.co"
    service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZubnBsb3Ryd2J0anRvcGtueGdsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Njc4NDc1OCwiZXhwIjoyMDcyMzYwNzU4fQ.qFZl7LLGqc9CmpIfPKy8bNyHoexCB_sdre-hc08yIzM"
    
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    print("=== TESTING DATABASE CONNECTION ===")
    
    # Test 1: List tables/health
    try:
        url = f"{supabase_url}/rest/v1/"
        response = requests.get(url, headers=headers)
        print(f"✅ Database connection test: {response.status_code}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Test 2: Check analysis_jobs table
    try:
        url = f"{supabase_url}/rest/v1/analysis_jobs?select=id,status&limit=5"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            jobs = response.json()
            print(f"✅ analysis_jobs table accessible: {len(jobs)} jobs found")
            for job in jobs:
                print(f"   - {job['id']}: {job['status']}")
        else:
            print(f"❌ analysis_jobs table error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ analysis_jobs table test failed: {e}")
    
    # Test 3: Check for specific job
    job_id = "17569531"
    try:
        url = f"{supabase_url}/rest/v1/analysis_jobs?id=eq.{job_id}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            jobs = response.json()
            if jobs:
                print(f"✅ Job {job_id} found in database:")
                print(json.dumps(jobs[0], indent=2))
                return jobs[0]
            else:
                print(f"❌ Job {job_id} NOT found in database")
                
                # Check if any jobs exist at all
                url = f"{supabase_url}/rest/v1/analysis_jobs?select=count"
                count_response = requests.get(url, headers=headers)
                if count_response.status_code == 200:
                    print(f"📊 Total jobs in database: {len(count_response.json())}")
                
        else:
            print(f"❌ Job query error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Job query failed: {e}")
    
    # Test 4: Check venues table
    try:
        url = f"{supabase_url}/rest/v1/venues?select=id,name&limit=3"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            venues = response.json()
            print(f"✅ venues table accessible: {len(venues)} venues found")
            for venue in venues:
                print(f"   - {venue['id']}: {venue['name']}")
        else:
            print(f"❌ venues table error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ venues table test failed: {e}")
    
    return None

def test_supabase_python_client():
    """Test Supabase Python client"""
    try:
        from supabase import create_client, Client
        
        supabase_url = "https://vnnplotrwbtjtopknxgl.supabase.co"
        service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZubnBsb3Ryd2J0anRvcGtueGdsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Njc4NDc1OCwiZXhwIjoyMDcyMzYwNzU4fQ.qFZl7LLGqc9CmpIfPKy8bNyHoexCB_sdre-hc08yIzM"
        
        print("\n=== TESTING PYTHON CLIENT ===")
        
        supabase: Client = create_client(supabase_url, service_key)
        print("✅ Supabase Python client created successfully")
        
        # Test query
        result = supabase.table('analysis_jobs').select('id,status').limit(3).execute()
        print(f"✅ Python client query successful: {len(result.data)} jobs")
        for job in result.data:
            print(f"   - {job['id']}: {job['status']}")
            
        # Test specific job
        job_id = "17569531"
        result = supabase.table('analysis_jobs').select('*').eq('id', job_id).execute()
        if result.data:
            print(f"✅ Job {job_id} found via Python client:")
            return result.data[0]
        else:
            print(f"❌ Job {job_id} not found via Python client")
        
    except ImportError as e:
        print(f"❌ Supabase Python client not available: {e}")
    except Exception as e:
        print(f"❌ Python client test failed: {e}")
    
    return None

def create_test_job():
    """Create a test analysis job to see what happens"""
    supabase_url = "https://vnnplotrwbtjtopknxgl.supabase.co"
    service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZubnBsb3Ryd2J0anRvcGtueGdsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Njc4NDc1OCwiZXhwIjoyMDcyMzYwNzU4fQ.qFZl7LLGqc9CmpIfPKy8bNyHoexCB_sdre-hc08yIzM"
    
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json'
    }
    
    print("\n=== TESTING JOB CREATION ===")
    
    # Create a test job via Lambda API
    lambda_url = "https://uu4pbfcm5rop2dropvwdm3iofe0mbfsi.lambda-url.us-west-2.on.aws"
    
    test_restaurant = {
        "name": "Test Restaurant Debug",
        "address": "123 Test St, Test City, CA 90210",
        "phone": "+15551234567"
    }
    
    try:
        response = requests.post(f"{lambda_url}/api/analyze", 
                               headers={'Content-Type': 'application/json'},
                               json=test_restaurant)
        
        if response.status_code == 200:
            job_data = response.json()
            print(f"✅ Test job created via Lambda: {job_data['job_id']}")
            
            # Wait a moment, then check if it appears in database
            import time
            time.sleep(2)
            
            # Check if job exists in database
            job_id = job_data['job_id']
            url = f"{supabase_url}/rest/v1/analysis_jobs?id=eq.{job_id}"
            db_response = requests.get(url, headers=headers)
            
            if db_response.status_code == 200 and db_response.json():
                print(f"✅ Test job found in database")
                print(json.dumps(db_response.json()[0], indent=2))
            else:
                print(f"❌ Test job NOT found in database after creation")
                print(f"   Database response: {db_response.status_code} - {db_response.text}")
                
        else:
            print(f"❌ Test job creation failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Test job creation error: {e}")

def main():
    print(f"🔍 Database Connection Test")
    print(f"🕐 Current time: {datetime.now().isoformat()}")
    
    # Test 1: Direct HTTP API
    job_data = test_supabase_connection()
    
    # Test 2: Python client (if available)
    python_job_data = test_supabase_python_client()
    
    # Test 3: Create a new job and track it
    create_test_job()
    
    # Summary
    print(f"\n=== ANALYSIS SUMMARY ===")
    if job_data or python_job_data:
        print(f"✅ Job 17569531 exists in the database!")
        print(f"❗ The issue is NOT database connectivity")
        print(f"❗ The issue may be:")
        print(f"   - Agent Lambda functions not properly deployed/configured")
        print(f"   - Pipeline orchestration logic not triggering agents")
        print(f"   - Job processing workflow has a bug")
    else:
        print(f"❌ Job 17569531 does NOT exist in the database")
        print(f"❗ The Lambda function is using fallback mode")
        print(f"❗ Jobs are not being stored in the database at all")

if __name__ == '__main__':
    main()