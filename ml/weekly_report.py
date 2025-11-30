"""
Weekly Email Report System for Crypto Investment Opportunities
Sends top 3 opportunities via email, avoiding duplicates from previous week
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

class WeeklyReportGenerator:
    def __init__(self, data_dir=None):
        # Get project root dynamically
        if data_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, 'data')
        
        self.data_dir = data_dir
        self.history_file = os.path.join(data_dir, "weekly_report_history.json")
        self.logger = logging.getLogger(__name__)
        
        # Email configuration from environment variables
        self.email_from = os.getenv('REPORT_EMAIL_FROM', '')
        self.email_to = os.getenv('REPORT_EMAIL_TO', '')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        
    def load_previous_recommendations(self) -> List[str]:
        """Load symbols from last week's report"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
                    # Get symbols from last week (within 7 days)
                    one_week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                    recent_symbols = []
                    for entry in history.get('reports', []):
                        if entry['timestamp'] > one_week_ago:
                            recent_symbols.extend(entry['symbols'])
                    return recent_symbols
        except Exception as e:
            self.logger.error(f"Error loading previous recommendations: {e}")
        return []
    
    def save_report_history(self, symbols: List[str]):
        """Save this week's recommended symbols"""
        try:
            history = {'reports': []}
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            
            # Add new report
            history['reports'].append({
                'timestamp': datetime.now().isoformat(),
                'symbols': symbols
            })
            
            # Keep only last 4 weeks of history
            four_weeks_ago = (datetime.now() - timedelta(days=28)).isoformat()
            history['reports'] = [
                r for r in history['reports'] 
                if r['timestamp'] > four_weeks_ago
            ]
            
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving report history: {e}")
    
    def get_top_opportunities(self, gem_detector, analyzer, count=3) -> List[Dict]:
        """Get top opportunities excluding previous week's recommendations"""
        try:
            previous_symbols = self.load_previous_recommendations()
            self.logger.info(f"Excluding {len(previous_symbols)} symbols from last week: {previous_symbols}")
            
            # Get hidden gems
            gems = []
            if gem_detector and hasattr(gem_detector, 'scan_for_hidden_gems'):
                result = gem_detector.scan_for_hidden_gems(limit=20, min_probability=0.65)
                gems = result.get('hidden_gems', [])
            
            # Filter out previous week's recommendations
            filtered_gems = [
                gem for gem in gems 
                if gem['symbol'] not in previous_symbols
            ]
            
            # Get analyzer data for additional context
            if analyzer:
                analyzed_coins = analyzer.get_coins()
                # Enhance gems with analyzer data
                for gem in filtered_gems:
                    for coin in analyzed_coins:
                        if coin['symbol'] == gem['symbol']:
                            gem['analyzer_score'] = coin.get('score', 0)
                            gem['status'] = coin.get('status', 'unknown')
                            break
            
            # Sort by gem_score and take top count
            top_opportunities = sorted(
                filtered_gems, 
                key=lambda x: x.get('gem_score', 0), 
                reverse=True
            )[:count]
            
            return top_opportunities
            
        except Exception as e:
            self.logger.error(f"Error getting top opportunities: {e}")
            return []
    
    def generate_email_html(self, opportunities: List[Dict]) -> str:
        """Generate HTML email content"""
        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }
                .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; }
                h1 { color: #667eea; border-bottom: 3px solid #f6d55c; padding-bottom: 10px; }
                .opportunity { background-color: #f9f9f9; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #f6d55c; }
                .symbol { font-size: 24px; font-weight: bold; color: #333; }
                .score { background: linear-gradient(135deg, #f6d55c, #764ba2); color: white; padding: 5px 15px; border-radius: 15px; display: inline-block; margin: 10px 0; }
                .metric { margin: 8px 0; }
                .label { font-weight: bold; color: #666; }
                .recommendation { background-color: #e6f7ff; padding: 15px; border-radius: 5px; margin-top: 10px; }
                .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #888; font-size: 12px; text-align: center; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>💎 Weekly Crypto Opportunities Report</h1>
                <p><strong>Report Date:</strong> {date}</p>
                <p>Here are your top 3 cryptocurrency investment opportunities for this week:</p>
        """.format(date=datetime.now().strftime("%B %d, %Y"))
        
        if not opportunities:
            html += """
                <div class="opportunity">
                    <p>No new opportunities found this week that weren't recommended last week.</p>
                    <p>The market may be consolidating, or previous recommendations remain the best options.</p>
                </div>
            """
        else:
            for i, opp in enumerate(opportunities, 1):
                gem_score = round(opp.get('gem_score', 0))
                probability = round(opp.get('gem_probability', 0) * 100, 1)
                price = opp.get('price', 'N/A')
                risk = opp.get('risk_level', 'Unknown')
                
                # Calculate estimated valuation
                current_market_cap = opp.get('market_cap', 0)
                estimated_potential = gem_score / 100  # Simple estimation
                estimated_price = price * (1 + estimated_potential) if isinstance(price, (int, float)) else None
                
                html += f"""
                <div class="opportunity">
                    <div class="symbol">#{i} {opp['symbol']} - {opp['name']}</div>
                    <div class="score">💎 Gem Score: {gem_score}%</div>
                    
                    <div class="metric">
                        <span class="label">Current Price:</span> ${price if isinstance(price, str) else f'{price:.8f}'}
                    </div>
                    <div class="metric">
                        <span class="label">Market Cap Rank:</span> #{opp.get('market_cap_rank', 'N/A')}
                    </div>
                    <div class="metric">
                        <span class="label">Gem Probability:</span> {probability}%
                    </div>
                    <div class="metric">
                        <span class="label">Risk Level:</span> {risk}
                    </div>
                    
                    {f'<div class="metric"><span class="label">Estimated Price Potential:</span> ${estimated_price:.8f} ({int(estimated_potential * 100)}% increase potential)</div>' if estimated_price else ''}
                    
                    <div class="recommendation">
                        <strong>Analysis:</strong><br>
                        {opp.get('recommendation', 'Strong potential for growth based on technical indicators and market position.')}
                    </div>
                    
                    {'<div style="margin-top: 10px;"><strong>Key Strengths:</strong><ul>' + ''.join([f'<li>{s}</li>' for s in opp.get('key_strengths', [])[:3]]) + '</ul></div>' if opp.get('key_strengths') else ''}
                </div>
                """
        
        html += """
                <div class="footer">
                    <p>This report is generated automatically by your Crypto Investment Dashboard.</p>
                    <p>Always conduct your own research before making investment decisions.</p>
                    <p><em>Past performance does not guarantee future results.</em></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_email(self, html_content: str) -> bool:
        """Send email report"""
        try:
            if not all([self.email_from, self.email_to, self.smtp_password]):
                self.logger.warning("Email credentials not configured. Set environment variables: REPORT_EMAIL_FROM, REPORT_EMAIL_TO, SMTP_PASSWORD")
                return False
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"💎 Weekly Crypto Opportunities - {datetime.now().strftime('%B %d, %Y')}"
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_from, self.smtp_password)
                server.send_message(msg)
            
            self.logger.info(f"Weekly report sent successfully to {self.email_to}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False
    
    def generate_and_send_report(self, gem_detector, analyzer) -> Dict:
        """Main method to generate and send weekly report"""
        try:
            self.logger.info("Generating weekly report...")
            
            # Get top opportunities
            opportunities = self.get_top_opportunities(gem_detector, analyzer, count=3)
            
            # Generate email
            html_content = self.generate_email_html(opportunities)
            
            # Send email
            success = self.send_email(html_content)
            
            if success:
                # Save symbols to history
                symbols = [opp['symbol'] for opp in opportunities]
                self.save_report_history(symbols)
                
                return {
                    'success': True,
                    'opportunities_count': len(opportunities),
                    'symbols': symbols,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to send email - check credentials',
                    'opportunities_count': len(opportunities)
                }
                
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
weekly_reporter = WeeklyReportGenerator()
