"""
Portfolio and Stock models for MongoDB collections
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Safe imports with fallbacks
try:
    from pymongo import MongoClient
    from bson import ObjectId
    from config import Config
    MONGO_AVAILABLE = True
    logger.info("MongoDB dependencies available")
except ImportError as e:
    logger.warning(f"MongoDB dependencies not available: {e}")
    MONGO_AVAILABLE = False
    Config = None
    MongoClient = None
    ObjectId = None

# Global database client
db_client = None

def init_db():
    """Initialize the database connection."""
    global db_client
    try:
        if MONGO_AVAILABLE and Config:
            if hasattr(Config, 'MONGODB_URI'):
                db_client = MongoClient(Config.MONGODB_URI)
                # Test connection
                db_client.admin.command('ping')
                logger.info("MongoDB connection established")
            else:
                logger.warning("MONGODB_URI not found in config")
        else:
            logger.warning("MongoDB not available - running in mock mode")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        db_client = None

def get_db():
    """Get database instance."""
    if db_client and MONGO_AVAILABLE and Config:
        return db_client[Config.MONGODB_NAME]
    return None

def save_recommendation(symbol: str, action: str, reasoning: str, 
                       confidence: float = 0.5, metadata: Dict = None) -> Dict[str, Any]:
    """Save a recommendation to the database."""
    try:
        db = get_db()
        if db is None:
            # Return mock data for development
            return {
                'symbol': symbol,
                'action': action,
                'reasoning': reasoning,
                'confidence': confidence,
                'timestamp': datetime.now(timezone.utc),
                '_id': 'mock_id_' + symbol
            }
        
        recommendation = {
            'symbol': symbol,
            'action': action,
            'reasoning': reasoning,
            'confidence': confidence,
            'metadata': metadata or {},
            'timestamp': datetime.now(timezone.utc),
            'created_at': datetime.now(timezone.utc)
        }
        
        result = db.recommendations.insert_one(recommendation)
        recommendation['_id'] = result.inserted_id
        logger.info(f"Saved recommendation for {symbol}: {action}")
        return recommendation
    except Exception as e:
        logger.error(f"Error saving recommendation: {e}")
        # Return mock data on error
        return {
            'symbol': symbol,
            'action': action,
            'reasoning': reasoning,
            'confidence': confidence,
            'timestamp': datetime.now(timezone.utc),
            '_id': 'error_mock_' + symbol
        }

def get_all_recommendations(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Get all recommendations from the database."""
    try:
        db = get_db()
        if db is None:
            # Return mock data for development
            return [
                {
                    'symbol': 'MOCK',
                    'action': 'BUY',
                    'reasoning': 'Mock recommendation for testing',
                    'confidence': 0.8,
                    'timestamp': datetime.now(timezone.utc),
                    '_id': 'mock_rec_1'
                }
            ]
        
        cursor = db.recommendations.find().sort("timestamp", -1).skip(offset).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return []

def get_recommendations_by_symbol(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recommendations for a specific symbol."""
    try:
        db = get_db()
        if db is None:
            return []
        
        cursor = db.recommendations.find({"symbol": symbol}).sort("timestamp", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.error(f"Error getting recommendations for {symbol}: {e}")
        return []

def save_stock_data(symbol: str, price: float, volume: int = None, 
                   change: float = None, change_percent: float = None,
                   source: str = "API", metadata: Dict = None) -> Dict[str, Any]:
    """Save stock data to the database."""
    try:
        db = get_db()
        if db is None:
            # Return mock data for development
            return {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'change': change,
                'change_percent': change_percent,
                'source': source,
                'timestamp': datetime.now(timezone.utc),
                '_id': 'mock_stock_' + symbol
            }
        
        stock_data = {
            'symbol': symbol,
            'price': price,
            'volume': volume,
            'change': change,
            'change_percent': change_percent,
            'source': source,
            'metadata': metadata or {},
            'timestamp': datetime.now(timezone.utc)
        }
        
        result = db.stock_data.insert_one(stock_data)
        stock_data['_id'] = result.inserted_id
        logger.info(f"Saved stock data for {symbol}: ${price}")
        return stock_data
    except Exception as e:
        logger.error(f"Error saving stock data: {e}")
        # Return mock data on error
        return {
            'symbol': symbol,
            'price': price,
            'volume': volume,
            'timestamp': datetime.now(timezone.utc),
            '_id': 'error_stock_' + symbol
        }

def get_stock_history(symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get historical stock data for a symbol."""
    try:
        db = get_db()
        if db is None:
            return []
        
        cursor = db.stock_data.find({"symbol": symbol}).sort("timestamp", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.error(f"Error getting stock history for {symbol}: {e}")
        return []

# Ensure all functions are available for import
__all__ = [
    'init_db',
    'get_db',
    'save_recommendation',
    'get_all_recommendations', 
    'get_recommendations_by_symbol',
    'save_stock_data',
    'get_stock_history'
]
