import schedule
import time
import logging
from datetime import datetime
from training_pipeline import CryptoMLPipeline
import os
import requests
import json

class MLScheduler:
    def __init__(self):
        self.pipeline = CryptoMLPipeline()
        self.data_dir = "/Users/finnbryant/Dev/CryptoApp/data"
        self.model_dir = "/Users/finnbryant/Dev/CryptoApp/models"
        
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
        # Implement your preferred alerting method
        # Email, Slack webhook, etc.
    
    def start_scheduler(self):
        """Start the weekly retraining scheduler"""
        # Schedule retraining every Sunday at 2 AM
        schedule.every().sunday.at("02:00").do(self.weekly_retrain)
        
        # For testing, you can also add daily retraining
        # schedule.every().day.at("03:00").do(self.weekly_retrain)
        
        logging.info("ML Scheduler started - Weekly retraining scheduled")
        
        while True:
            schedule.run_pending()
            time.sleep(3600)  # Check every hour

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = MLScheduler()
    scheduler.start_scheduler()
