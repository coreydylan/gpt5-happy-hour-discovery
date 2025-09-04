#!/usr/bin/env python3
"""
Database Maintenance Script for GPT-5 Happy Hour Discovery
Handles routine database maintenance tasks
"""

import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from supabase import create_client, Client
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Install with: pip install supabase psycopg2-binary")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMaintenance:
    """Database maintenance operations"""
    
    def __init__(self):
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')
        self.supabase: Optional[Client] = None
        self.pg_conn = None
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are required")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
    
    def connect(self):
        """Connect to database"""
        try:
            # Supabase client for high-level operations
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            
            # Direct PostgreSQL connection for maintenance operations
            # Extract connection details from Supabase URL
            db_url = self.supabase_url.replace('https://', '')
            db_host = db_url.split('.')[0]
            
            # Note: In production, use proper connection string parsing
            # This is a simplified version for demo
            logger.info("Connected to database successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from database"""
        if self.pg_conn:
            self.pg_conn.close()
            logger.info("Disconnected from database")
    
    def get_table_stats(self) -> List[Dict[str, Any]]:
        """Get table statistics"""
        try:
            result = self.supabase.rpc('analyze_table_stats').execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> str:
        """Clean up old data"""
        try:
            result = self.supabase.rpc('cleanup_old_data', {'days_to_keep': days_to_keep}).execute()
            message = result.data if result.data else "Cleanup completed"
            logger.info(f"Data cleanup: {message}")
            return message
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return f"Cleanup failed: {str(e)}"
    
    def update_statistics(self) -> str:
        """Update table statistics"""
        try:
            result = self.supabase.rpc('update_table_statistics').execute()
            message = result.data if result.data else "Statistics updated"
            logger.info(f"Statistics update: {message}")
            return message
        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
            return f"Statistics update failed: {str(e)}"
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations"""
        try:
            result = self.supabase.rpc('get_optimization_recommendations').execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Failed to get optimization recommendations: {e}")
            return []
    
    def monitor_active_jobs(self) -> List[Dict[str, Any]]:
        """Monitor active jobs"""
        try:
            result = self.supabase.table('active_jobs_summary').select('*').execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Failed to monitor active jobs: {e}")
            return []
    
    def check_database_health(self) -> Dict[str, Any]:
        """Comprehensive database health check"""
        health_report = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'healthy',
            'issues': [],
            'recommendations': [],
            'statistics': {}
        }
        
        try:
            # Check table statistics
            table_stats = self.get_table_stats()
            health_report['statistics']['tables'] = len(table_stats)
            
            # Check active jobs
            active_jobs = self.monitor_active_jobs()
            health_report['statistics']['active_jobs'] = active_jobs
            
            # Check for long-running jobs
            queued_jobs = [job for job in active_jobs if job.get('status') == 'queued']
            if queued_jobs:
                oldest_job = min(queued_jobs, key=lambda x: x.get('oldest_job', ''))
                if oldest_job and oldest_job.get('avg_age_seconds', 0) > 3600:  # 1 hour
                    health_report['issues'].append("Jobs queued for over 1 hour")
                    health_report['status'] = 'warning'
            
            # Get optimization recommendations
            recommendations = self.get_optimization_recommendations()
            health_report['recommendations'] = recommendations
            
            # Check for high priority recommendations
            high_priority = [r for r in recommendations if r.get('priority') == 'High']
            if high_priority:
                health_report['issues'].extend([r.get('recommendation') for r in high_priority])
                health_report['status'] = 'warning'
            
        except Exception as e:
            health_report['status'] = 'error'
            health_report['issues'].append(f"Health check failed: {str(e)}")
        
        return health_report
    
    def run_daily_maintenance(self):
        """Run daily maintenance tasks"""
        logger.info("Starting daily maintenance tasks...")
        
        tasks_completed = []
        tasks_failed = []
        
        try:
            # Update statistics
            result = self.update_statistics()
            tasks_completed.append(f"Statistics: {result}")
        except Exception as e:
            tasks_failed.append(f"Statistics update failed: {str(e)}")
        
        try:
            # Monitor database size and performance
            table_stats = self.get_table_stats()
            total_tables = len(table_stats)
            tasks_completed.append(f"Monitored {total_tables} tables")
        except Exception as e:
            tasks_failed.append(f"Table monitoring failed: {str(e)}")
        
        # Log summary
        logger.info(f"Daily maintenance completed. Success: {len(tasks_completed)}, Failed: {len(tasks_failed)}")
        for task in tasks_completed:
            logger.info(f"✓ {task}")
        for task in tasks_failed:
            logger.error(f"✗ {task}")
    
    def run_weekly_maintenance(self):
        """Run weekly maintenance tasks"""
        logger.info("Starting weekly maintenance tasks...")
        
        tasks_completed = []
        tasks_failed = []
        
        try:
            # Clean up old data
            result = self.cleanup_old_data(90)
            tasks_completed.append(f"Cleanup: {result}")
        except Exception as e:
            tasks_failed.append(f"Data cleanup failed: {str(e)}")
        
        try:
            # Get optimization recommendations
            recommendations = self.get_optimization_recommendations()
            tasks_completed.append(f"Found {len(recommendations)} optimization recommendations")
            
            # Log high-priority recommendations
            for rec in recommendations:
                if rec.get('priority') == 'High':
                    logger.warning(f"HIGH PRIORITY: {rec.get('recommendation')}")
        except Exception as e:
            tasks_failed.append(f"Optimization analysis failed: {str(e)}")
        
        # Log summary
        logger.info(f"Weekly maintenance completed. Success: {len(tasks_completed)}, Failed: {len(tasks_failed)}")
        for task in tasks_completed:
            logger.info(f"✓ {task}")
        for task in tasks_failed:
            logger.error(f"✗ {task}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database maintenance for GPT-5 Happy Hour Discovery')
    parser.add_argument('--mode', choices=['daily', 'weekly', 'health-check'], 
                       default='daily', help='Maintenance mode')
    parser.add_argument('--cleanup-days', type=int, default=90,
                       help='Days of data to keep during cleanup')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        with DatabaseMaintenance() as db:
            if args.mode == 'daily':
                db.run_daily_maintenance()
            elif args.mode == 'weekly':
                db.run_weekly_maintenance()
            elif args.mode == 'health-check':
                health = db.check_database_health()
                print(f"Database Health Status: {health['status']}")
                
                if health['issues']:
                    print("\nIssues Found:")
                    for issue in health['issues']:
                        print(f"  - {issue}")
                
                if health['recommendations']:
                    print(f"\nOptimization Recommendations ({len(health['recommendations'])}):")
                    for rec in health['recommendations']:
                        print(f"  [{rec.get('priority')}] {rec.get('recommendation')}")
                
                if health['statistics'].get('active_jobs'):
                    print("\nActive Jobs:")
                    for job in health['statistics']['active_jobs']:
                        print(f"  {job.get('status')}: {job.get('job_count')} jobs")
    
    except Exception as e:
        logger.error(f"Maintenance failed: {e}")
        sys.exit(1)
    
    logger.info("Maintenance completed successfully")


if __name__ == '__main__':
    main()