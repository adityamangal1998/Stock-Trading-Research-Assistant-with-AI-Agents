#!/usr/bin/env python3
"""
MCP Database Server - MongoDB wrapper for historical volatility and risk analysis.
"""

import json
import sys
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson import ObjectId
import yfinance as yf
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

class MCPDatabaseServer:
    """MCP server for MongoDB database operations."""
    
    def __init__(self, mongodb_url: str = None, db_name: str = None):
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.db = None
        
        try:
            # Try to connect to MongoDB
            mongodb_uri = mongodb_url or getattr(Config, 'MONGODB_URI', None)
            db_name = db_name or getattr(Config, 'MONGODB_NAME', 'stock_analysis')
            
            if mongodb_uri:
                self.client = MongoClient(mongodb_uri)
                self.db = self.client[db_name]
                self.init_database()
                self.logger.info("Connected to MongoDB successfully")
            else:
                self.logger.warning("MongoDB URI not configured, running in mock mode")
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            self.logger.warning("Running in mock mode without database")
    
    def init_database(self):
        """Initialize the database with required collections and indexes."""
        if not self.db:
            return
            
        try:
            # Create indexes for historical prices
            self.db.historical_prices.create_index([("symbol", 1), ("date", 1)], unique=True)
            self.db.historical_prices.create_index("symbol")
            self.db.historical_prices.create_index("date")
            
            # Create indexes for volatility metrics
            self.db.volatility_metrics.create_index([("symbol", 1), ("period", 1), ("timestamp", -1)])
            self.db.volatility_metrics.create_index("symbol")
            self.db.volatility_metrics.create_index("timestamp")
            
            # Create indexes for correlation matrix
            self.db.correlation_matrix.create_index([("symbol1", 1), ("symbol2", 1), ("timestamp", -1)])
            self.db.correlation_matrix.create_index("timestamp")
            
            self.logger.info("Database indexes created successfully")
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests."""
        try:
            method = request.get("method")
            params = request.get("params", {})
            
            if method == "analyze_risk":
                symbol = params.get("symbol")
                period = params.get("period", "1mo")
                result = self.analyze_risk(symbol, period)
                
                if result:
                    return {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": result
                    }
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {
                            "code": -32603,
                            "message": f"Failed to analyze risk for {symbol}"
                        }
                    }
            
            elif method == "get_historical_prices":
                symbol = params.get("symbol")
                period = params.get("period", "1mo")
                result = self.get_historical_prices(symbol, period)
                
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": result
                }
            
            elif method == "store_correlation":
                symbols = params.get("symbols", [])
                correlations = params.get("correlations", {})
                result = self.store_correlation_matrix(symbols, correlations)
                
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {"success": result}
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
        
        except Exception as e:
            self.logger.error(f"Error handling request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    def analyze_risk(self, symbol: str, period: str = "1mo") -> Optional[Dict[str, Any]]:
        """Analyze risk metrics for a given symbol."""
        try:
            # Check for recent analysis first (within last hour)
            recent_analysis = self._get_recent_analysis(symbol, period)
            if recent_analysis:
                self.logger.info(f"Using cached risk analysis for {symbol}")
                return recent_analysis
            
            # Get historical data
            df = self._get_historical_data(symbol, period)
            if df is None or df.empty:
                self.logger.warning(f"No data available for {symbol}")
                return None
            
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(df)
            
            # Store the analysis in database
            self._store_risk_analysis(symbol, period, risk_metrics)
            
            return risk_metrics
        
        except Exception as e:
            self.logger.error(f"Error analyzing risk for {symbol}: {e}")
            return None
    
    def get_historical_prices(self, symbol: str, period: str = "1mo") -> Dict[str, Any]:
        """Get historical prices for a symbol."""
        try:
            df = self._get_historical_data(symbol, period)
            if df is None or df.empty:
                return {"error": f"No data available for {symbol}"}
            
            # Convert DataFrame to dictionary format
            data = []
            for index, row in df.iterrows():
                data.append({
                    "date": index.strftime("%Y-%m-%d"),
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": int(row['Volume']) if not pd.isna(row['Volume']) else 0
                })
            
            return {
                "symbol": symbol,
                "period": period,
                "data": data
            }
        
        except Exception as e:
            self.logger.error(f"Error getting historical prices for {symbol}: {e}")
            return {"error": str(e)}
    
    def store_correlation_matrix(self, symbols: List[str], correlations: Dict[str, float]) -> bool:
        """Store correlation matrix in database."""
        if not self.db:
            self.logger.info("Database not available, skipping correlation matrix storage")
            return False
            
        try:
            timestamp = datetime.utcnow()
            
            for symbol_pair, correlation in correlations.items():
                if '_' in symbol_pair:
                    symbol1, symbol2 = symbol_pair.split('_', 1)
                    
                    correlation_doc = {
                        "symbol1": symbol1,
                        "symbol2": symbol2,
                        "correlation": correlation,
                        "timestamp": timestamp
                    }
                    
                    # Upsert correlation data
                    self.db.correlation_matrix.update_one(
                        {"symbol1": symbol1, "symbol2": symbol2},
                        {"$set": correlation_doc},
                        upsert=True
                    )
            
            self.logger.info(f"Stored correlation matrix for {len(symbols)} symbols")
            return True
        
        except Exception as e:
            self.logger.error(f"Error storing correlation matrix: {e}")
            return False
    
    def _get_recent_analysis(self, symbol: str, period: str) -> Optional[Dict[str, Any]]:
        """Check if we have a recent risk analysis for the symbol."""
        if not self.db:
            return None
            
        try:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            analysis = self.db.volatility_metrics.find_one(
                {
                    "symbol": symbol,
                    "period": period,
                    "timestamp": {"$gte": one_hour_ago}
                },
                sort=[("timestamp", -1)]
            )
            
            if analysis:
                # Convert ObjectId to string and remove MongoDB-specific fields
                result = dict(analysis)
                result.pop('_id', None)
                return result
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error checking recent analysis: {e}")
            return None
    
    def _get_historical_data(self, symbol: str, period: str) -> Optional[pd.DataFrame]:
        """Get historical data, from DB first, then API if needed."""
        try:
            # First try to get from database
            df = self._get_data_from_db(symbol, period)
            
            if df is not None and not df.empty:
                # Check if data is recent enough
                last_date = df.index.max()
                days_old = (datetime.now().date() - last_date.date()).days
                
                if days_old <= 1:  # Data is recent
                    self.logger.info(f"Using cached data for {symbol}")
                    return df
            
            # Fetch fresh data from API
            self.logger.info(f"Fetching fresh data for {symbol}")
            fresh_df = self._fetch_data_from_api(symbol, period)
            
            if fresh_df is not None and not fresh_df.empty:
                # Store in database
                self._store_price_data_bulk(symbol, fresh_df)
                return fresh_df
            
            # Return cached data if API fails
            return df
        
        except Exception as e:
            self.logger.error(f"Error getting historical data: {e}")
            return None
    
    def _get_data_from_db(self, symbol: str, period: str) -> Optional[pd.DataFrame]:
        """Get historical data from MongoDB."""
        if not self.db:
            return None
            
        try:
            # Convert period to days for query
            period_map = {
                "1d": 1, "5d": 5, "1mo": 30, "3mo": 90, 
                "6mo": 180, "1y": 365, "2y": 730
            }
            
            days = period_map.get(period, 30)
            start_date = datetime.now() - timedelta(days=days)
            
            cursor = self.db.historical_prices.find(
                {
                    "symbol": symbol,
                    "date": {"$gte": start_date}
                },
                sort=[("date", 1)]
            )
            
            data = []
            for doc in cursor:
                data.append({
                    "Date": doc["date"],
                    "Open": doc.get("open_price", 0),
                    "High": doc.get("high_price", 0),
                    "Low": doc.get("low_price", 0),
                    "Close": doc.get("close_price", 0),
                    "Volume": doc.get("volume", 0)
                })
            
            if data:
                df = pd.DataFrame(data)
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                return df
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error getting data from DB: {e}")
            return None
    
    def _fetch_data_from_api(self, symbol: str, period: str) -> Optional[pd.DataFrame]:
        """Fetch historical data from yfinance API."""
        try:
            # For Indian stocks, append .NS or .BO if not present
            if not symbol.endswith(('.NS', '.BO')):
                if symbol in ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ITC']:
                    symbol_with_suffix = f"{symbol}.NS"
                else:
                    symbol_with_suffix = f"{symbol}.NS"
            else:
                symbol_with_suffix = symbol
            
            ticker = yf.Ticker(symbol_with_suffix)
            df = ticker.history(period=period)
            
            if df.empty:
                self.logger.warning(f"No data returned from API for {symbol}")
                return None
            
            return df
        
        except Exception as e:
            self.logger.error(f"Error fetching data from API: {e}")
            return None
    
    def _store_price_data_bulk(self, symbol: str, df: pd.DataFrame):
        """Store price data in bulk to MongoDB."""
        if not self.db:
            self.logger.info(f"Database not available, skipping bulk storage for {symbol}")
            return
            
        try:
            documents = []
            
            for date, row in df.iterrows():
                doc = {
                    "symbol": symbol,
                    "date": date.to_pydatetime(),
                    "open_price": float(row['Open']),
                    "high_price": float(row['High']),
                    "low_price": float(row['Low']),
                    "close_price": float(row['Close']),
                    "volume": int(row['Volume']) if not pd.isna(row['Volume']) else 0,
                    "timestamp": datetime.utcnow()
                }
                documents.append(doc)
            
            if documents:
                # Use ordered=False to continue on duplicate key errors
                self.db.historical_prices.insert_many(documents, ordered=False)
                self.logger.info(f"Stored {len(documents)} price records for {symbol}")
        
        except Exception as e:
            # Ignore duplicate key errors
            if "duplicate key error" not in str(e).lower():
                self.logger.error(f"Error storing price data: {e}")
    
    def _store_risk_analysis(self, symbol: str, period: str, metrics: Dict[str, Any]):
        """Store risk analysis results in MongoDB."""
        if not self.db:
            self.logger.info(f"Database not available, skipping storage for {symbol}")
            return
            
        try:
            doc = {
                "symbol": symbol,
                "period": period,
                "timestamp": datetime.utcnow(),
                **metrics
            }
            
            self.db.volatility_metrics.insert_one(doc)
            self.logger.info(f"Stored risk analysis for {symbol}")
        
        except Exception as e:
            self.logger.error(f"Error storing risk analysis: {e}")
    
    def _calculate_risk_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics from price data."""
        try:
            # Calculate returns
            df['Returns'] = df['Close'].pct_change()
            returns = df['Returns'].dropna()
            
            if len(returns) < 2:
                return {"error": "Insufficient data for risk calculation"}
            
            # Basic metrics
            volatility = returns.std() * np.sqrt(252)  # Annualized
            mean_return = returns.mean() * 252  # Annualized
            
            # Sharpe ratio (assuming 6% risk-free rate)
            risk_free_rate = 0.06
            sharpe_ratio = (mean_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            # Value at Risk (95% confidence)
            var_95 = np.percentile(returns, 5)
            var_99 = np.percentile(returns, 1)
            
            # Maximum drawdown
            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdown = (cumulative - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # Beta calculation (simplified against a mock market return)
            beta = self._calculate_beta_simplified(returns)
            
            # Risk classification
            risk_level = self._classify_risk(volatility, max_drawdown, var_95)
            
            return {
                "volatility": float(volatility),
                "annualized_return": float(mean_return),
                "sharpe_ratio": float(sharpe_ratio),
                "var_95": float(var_95),
                "var_99": float(var_99),
                "max_drawdown": float(max_drawdown),
                "beta": float(beta) if beta else None,
                "risk_level": risk_level,
                "data_points": len(returns),
                "last_price": float(df['Close'].iloc[-1]),
                "price_change": float(df['Close'].iloc[-1] - df['Close'].iloc[-2]) if len(df) > 1 else 0
            }
        
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return {"error": str(e)}
    
    def _calculate_beta_simplified(self, returns: pd.Series) -> Optional[float]:
        """Calculate a simplified beta using market proxy."""
        try:
            # Using a simple market proxy (could be improved with actual market index)
            market_volatility = 0.20  # Assumed market volatility
            correlation_with_market = 0.7  # Assumed correlation
            
            stock_volatility = returns.std() * np.sqrt(252)
            beta = correlation_with_market * (stock_volatility / market_volatility)
            
            return beta
        
        except Exception as e:
            self.logger.error(f"Error calculating beta: {e}")
            return None
    
    def _classify_risk(self, volatility: float, max_drawdown: float, var_95: float) -> str:
        """Classify risk level based on metrics."""
        try:
            risk_score = 0
            
            # Volatility scoring
            if volatility > 0.40:
                risk_score += 3
            elif volatility > 0.25:
                risk_score += 2
            elif volatility > 0.15:
                risk_score += 1
            
            # Max drawdown scoring
            if max_drawdown < -0.30:
                risk_score += 3
            elif max_drawdown < -0.20:
                risk_score += 2
            elif max_drawdown < -0.10:
                risk_score += 1
            
            # VaR scoring
            if var_95 < -0.05:
                risk_score += 3
            elif var_95 < -0.03:
                risk_score += 2
            elif var_95 < -0.02:
                risk_score += 1
            
            # Classification
            if risk_score >= 7:
                return "Very High"
            elif risk_score >= 5:
                return "High"
            elif risk_score >= 3:
                return "Medium"
            elif risk_score >= 1:
                return "Low"
            else:
                return "Very Low"
        
        except Exception as e:
            self.logger.error(f"Error classifying risk: {e}")
            return "Unknown"

def run_server(port: int = 8003):
    """Run the MCP Database server."""
    try:
        server = MCPDatabaseServer()
        print(f"MCP Database Server starting on port {port}")
        
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json
        
        class MCPHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                try:
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    request = json.loads(post_data.decode('utf-8'))
                    
                    response = server.handle_request(request)
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    response_data = json.dumps(response).encode('utf-8')
                    self.wfile.write(response_data)
                    
                except Exception as e:
                    self.send_error(500, f"Server error: {str(e)}")
            
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'MCP Database Server is running')
            
            def log_message(self, format, *args):
                pass  # Suppress default logging
        
        httpd = HTTPServer(('localhost', port), MCPHandler)
        print(f"MCP Database Server running on http://localhost:{port}")
        httpd.serve_forever()
        
    except Exception as e:
        print(f"Failed to start MCP Database Server: {str(e)}")
        print("Running in mock mode...")
        # In case of error, we can continue without the database server
        import time
        while True:
            time.sleep(1)

def main():
    """Main function to run the MCP server."""
    logging.basicConfig(level=logging.INFO)
    
    # Check if running as HTTP server (with port argument) or stdin/stdout mode
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
            run_server(port)
            return
        except ValueError:
            pass
    
    # Fall back to stdin/stdout mode for compatibility
    server = MCPDatabaseServer()
    
    # Read requests from stdin
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            response = server.handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
        except json.JSONDecodeError:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    main()
