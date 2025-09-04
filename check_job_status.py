#!/usr/bin/env python3
"""
Direct job status check for GPT-5 Happy Hour Discovery System
"""

import os
import sys
import json
import requests
from datetime import datetime

def check_job_via_lambda(job_id):
    """Check job status via Lambda Function URL"""
    lambda_url = "https://uu4pbfcm5rop2dropvwdm3iofe0mbfsi.lambda-url.us-west-2.on.aws"
    
    try:
        response = requests.get(f"{lambda_url}/api/job/{job_id}", 
                              headers={'Content-Type': 'application/json'})
        
        print(f"Lambda Response Status: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error response: {response.text}")
            return None
    except Exception as e:
        print(f"Error calling Lambda: {e}")
        return None

def check_job_via_supabase_direct(job_id):
    """Check job status directly via Supabase REST API"""
    supabase_url = "https://vnnplotrwbtjtopknxgl.supabase.co"
    
    # You'll need the service key for this to work
    service_key = os.environ.get('SUPABASE_SERVICE_KEY')
    if not service_key:
        print("SUPABASE_SERVICE_KEY not set - skipping direct Supabase check")
        return None
    
    try:
        headers = {
            'apikey': service_key,
            'Authorization': f'Bearer {service_key}',
            'Content-Type': 'application/json'
        }
        
        # Check analysis_jobs table
        url = f"{supabase_url}/rest/v1/analysis_jobs?id=eq.{job_id}"
        response = requests.get(url, headers=headers)
        
        print(f"Supabase Response Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            return data[0] if data else None
        else:
            print(f"Supabase error: {response.text}")
            return None
    except Exception as e:
        print(f"Error calling Supabase: {e}")
        return None

def check_system_stats():
    """Check overall system statistics"""
    lambda_url = "https://uu4pbfcm5rop2dropvwdm3iofe0mbfsi.lambda-url.us-west-2.on.aws"
    
    try:
        response = requests.get(f"{lambda_url}/api/stats", 
                              headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Stats error: {response.text}")
            return None
    except Exception as e:
        print(f"Error getting stats: {e}")
        return None

def analyze_job_status(job_data, job_id):
    """Analyze why a job might be stuck"""
    print(f"\n=== JOB STATUS ANALYSIS ===")
    
    if not job_data:
        print(f"❌ Job {job_id} NOT FOUND")
        return
    
    status = job_data.get('status', 'unknown')
    created_at = job_data.get('created_at', job_data.get('started_at'))
    
    print(f"📋 Job ID: {job_id}")
    print(f"📊 Status: {status}")
    print(f"🕐 Created: {created_at}")
    
    if created_at:
        try:
            # Parse timestamp and calculate age
            created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            age_seconds = (datetime.now(created_time.tzinfo) - created_time).total_seconds()
            age_minutes = int(age_seconds // 60)
            
            print(f"⏰ Age: {age_minutes} minutes ({age_seconds:.1f} seconds)")
            
            if status == 'queued':
                if age_minutes > 60:
                    print(f"🚨 WARNING: Job has been queued for {age_minutes} minutes!")
                    print("   This suggests the processing pipeline may be stuck")
                elif age_minutes > 15:
                    print(f"⚠️  Job has been queued for {age_minutes} minutes")
                    print("   Normal processing time is ~1-2 minutes")
                else:
                    print(f"✅ Job age is within normal range")
        except Exception as e:
            print(f"❌ Error parsing timestamp: {e}")
    
    # Check for additional fields
    venue_id = job_data.get('venue_id')
    error_message = job_data.get('error_message')
    
    if venue_id:
        print(f"🏢 Venue ID: {venue_id}")
    
    if error_message:
        print(f"❌ Error: {error_message}")
    
    # Provide recommendations
    print(f"\n=== RECOMMENDATIONS ===")
    
    if status == 'queued' and age_minutes > 10:
        print("1. Check if the agent Lambda functions are deployed and working")
        print("2. Verify the orchestrator is triggering agent functions correctly")
        print("3. Check CloudWatch logs for the orchestrator Lambda")
        print("4. Verify database connection is working properly")
    elif status == 'queued':
        print("1. Job is recently queued - may start processing soon")
        print("2. Normal processing time is 1-2 minutes for GPT-5 analysis")
    elif status == 'completed':
        print("✅ Job completed successfully!")
    elif status == 'failed':
        print("❌ Job failed - check error_message and CloudWatch logs")

def main():
    job_id = "17569531"
    
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
    
    print(f"🔍 Checking status of job ID: {job_id}")
    print(f"🕐 Current time: {datetime.now().isoformat()}")
    
    # Check via Lambda first (this is how the frontend calls it)
    print(f"\n=== CHECKING VIA LAMBDA FUNCTION ===")
    lambda_result = check_job_via_lambda(job_id)
    
    if lambda_result:
        print("✅ Lambda Function Response:")
        print(json.dumps(lambda_result, indent=2))
        
        analyze_job_status(lambda_result, job_id)
    else:
        print("❌ Failed to get job status via Lambda")
    
    # Try direct Supabase if service key is available
    print(f"\n=== CHECKING VIA SUPABASE DIRECT ===")
    supabase_result = check_job_via_supabase_direct(job_id)
    
    if supabase_result:
        print("✅ Direct Supabase Response:")
        print(json.dumps(supabase_result, indent=2))
    else:
        print("❌ Could not check via direct Supabase (may need service key)")
    
    # Check system overall health
    print(f"\n=== SYSTEM HEALTH CHECK ===")
    stats = check_system_stats()
    
    if stats:
        print(f"🔧 System Status: {stats.get('system_status', 'unknown')}")
        print(f"📊 Total Jobs: {stats.get('total_jobs', 'unknown')}")
        print(f"⏳ Queued Jobs: {stats.get('queued_jobs', 'unknown')}")
        print(f"🏃 Running Jobs: {stats.get('running_jobs', 'unknown')}")
        print(f"✅ Completed Jobs: {stats.get('completed_jobs', 'unknown')}")
        print(f"❌ Failed Jobs: {stats.get('failed_jobs', 'unknown')}")
        print(f"🔗 Database: {stats.get('database', 'unknown')}")
        
        if stats.get('database') == 'fallback':
            print("⚠️  WARNING: System is running in fallback mode (database connection issues)")
            print("   This means jobs may not be processing properly!")
    
    print(f"\n=== TROUBLESHOOTING STEPS ===")
    print("1. Check AWS CloudWatch logs for the orchestrator Lambda function")
    print("2. Verify the agent Lambda functions are deployed and callable")
    print("3. Check Supabase database connectivity and credentials")
    print("4. Verify the GPT-5 API key is properly configured")
    print("5. Check if there are any AWS Lambda quota or timeout issues")

if __name__ == '__main__':
    main()