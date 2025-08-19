import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # AWS Bedrock Configuration
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')
    MODEL_ID = os.getenv('MODEL_ID', 'arn:aws:bedrock:us-east-2:905418105552:inference-profile/us.anthropic.claude-3-5-sonnet-20240620-v1:0')
    
    # MongoDB Configuration
    MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
    MONGODB_NAME = os.getenv('MONGODB_NAME', 'stock_analyst')
    MONGODB_COLLECTION_RECOMMENDATIONS = 'recommendations'
    MONGODB_COLLECTION_STOCK_DATA = 'stock_data'
    MONGODB_COLLECTION_NEWS_DATA = 'news_data'
    MONGODB_COLLECTION_VOLATILITY_METRICS = 'volatility_metrics'
    MONGODB_COLLECTION_HISTORICAL_PRICES = 'historical_prices'
    MONGODB_COLLECTION_CORRELATION_MATRIX = 'correlation_matrix'
    
    # MCP Server Configuration
    MCP_FINANCE_PORT = int(os.getenv('MCP_FINANCE_PORT', 8001))
    MCP_RSS_PORT = int(os.getenv('MCP_RSS_PORT', 8002))
    MCP_DB_PORT = int(os.getenv('MCP_DB_PORT', 8003))
    
    # API Configuration
    NSE_API_URL = os.getenv('NSE_API_URL', 'https://www.nseindia.com')
    BSE_API_URL = os.getenv('BSE_API_URL', 'https://api.bseindia.com')
    TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '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')
    
    # Application Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Stock Configuration
    DEFAULT_STOCKS = ['INFY', 'TCS', 'RELIANCE', 'HDFCBANK', 'ICICIBANK']
    
    # News RSS Feeds
    RSS_FEEDS = [
        'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
        'https://www.moneycontrol.com/rss/business.xml',
        'https://feeds.feedburner.com/ndtvprofit-latest'
    ]
