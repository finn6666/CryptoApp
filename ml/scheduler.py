import schedule
import time
import logging
from datetime import datetime
from training_pipeline import CryptoMLPipeline
from weekly_report import WeeklyReportGenerator
import os
import requests
import json

class MLScheduler:
    def __init__(self):
        self.pipeline = CryptoMLPipeline()
        self.weekly_reporter = WeeklyReportGenerator()
        self.data_dir = "/Users/finnbryant/Dev/CryptoApp/data"
        self.model_dir = "/Users/finnbryant/Dev/CryptoApp/models"
        
        # These will be set when scheduler is integrated with main app
        self.gem_detector = None
        self.analyzer = None
        
    def weekly_retrain(self):
        """Weekly retraining job"""
        logging.info(f"Starting weekly retrain at {datetime.now()}")
        
        try:
            # Fetch latest data
            data_file = self.fetch_latest_data()
            
            # Retrain model
            metrics = self.pipeline.train_model(data_file)
            
            # Export updated model
            self.pipeline.export_model(self.model_dir)
            
            # Log success
            logging.info(f"Retraining completed. Metrics: {metrics}")
            
            # Optional: Deploy to Azure (implement based on your setup)
            # self.deploy_to_azure()
            
        except Exception as e:
            logging.error(f"Retraining failed: {str(e)}")
            self.send_alert(f"ML retraining failed: {str(e)}")
    
    def fetch_latest_data(self):
        """Fetch latest crypto data"""
        # This should integrate with your existing crypto data collection
        data_file = f"{self.data_dir}/weekly_training_data.csv"
        
        # Placeholder - replace with actual data fetching logic
        logging.info(f"Fetching latest data to {data_file}")
        
        # You would implement the actual data collection here
        # For now, assume data is already available
        if not os.path.exists(data_file):
            raise FileNotFoundError(f"Training data not found: {data_file}")
            
        return data_file
    
    def send_alert(self, message):
        """Send alert for failed operations"""
        logging.error(f"ALERT: {message}")
    
    def weekly_report_job(self):
        """Generate and send weekly email report"""
        logging.info(f"Starting weekly report generation at {datetime.now()}")
        
        try:
            if not self.gem_detector or not self.analyzer:
                logging.warning("Gem detector or analyzer not initialized for weekly report")
                return
            
            result = self.weekly_reporter.generate_and_send_report(
                self.gem_detector, 
                self.analyzer
            )
            
            if result['success']:
                logging.info(f"Weekly report sent successfully. Opportunities: {result['opportunities_count']}")
            else:
                logging.error(f"Weekly report failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logging.error(f"Weekly report generation failed: {str(e)}")
            self.send_alert(f"Weekly report failed: {str(e)}")
    
    def start_scheduler(self):
        """Start the weekly retraining scheduler and report generation"""
        # Schedule retraining every Sunday at 2 AM
        schedule.every().sunday.at("02:00").do(self.weekly_retrain)
        
        # Schedule weekly report every Monday at 9 AM
        schedule.every().monday.at("09:00").do(self.weekly_report_job)
        
        # For testing, you can also add daily retraining
        # schedule.every().day.at("03:00").do(self.weekly_retrain)
        
        logging.info("ML Scheduler started - Weekly retraining and reports scheduled")
        logging.info("- Model retraining: Every Sunday at 2:00 AM")
        logging.info("- Weekly report: Every Monday at 9:00 AM")
        
        while True:
            schedule.run_pending()
            time.sleep(3600)  # Check every hour

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = MLScheduler()
    scheduler.start_scheduler()
