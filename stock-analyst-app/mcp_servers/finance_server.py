#!/usr/bin/env python3
"""
MCP Finance Server - Wraps NSE/BSE stock API for the stock analysis system.
"""

import json
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import yfinance as yf
import requests

class MCPFinanceServer:
    """MCP server for financial data operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        
        # Symbol mapping for common company names to ticker symbols
        self.symbol_map = {
            # Company names to ticker symbols
            'suzlon energy': 'SUZLON',
            'suzlon': 'SUZLON',
            'reliance industries': 'RELIANCE',
            'reliance': 'RELIANCE',
            'tata consultancy services': 'TCS',
            'tcs': 'TCS',
            'infosys': 'INFY',
            'infy': 'INFY',
            'hdfc bank': 'HDFCBANK',
            'hdfcbank': 'HDFCBANK',
            'icici bank': 'ICICIBANK',
            'icicibank': 'ICICIBANK',
            'state bank of india': 'SBIN',
            'sbin': 'SBIN',
            'wipro': 'WIPRO',
            'bharti airtel': 'BHARTIARTL',
            'airtel': 'BHARTIARTL',
            'itc': 'ITC',
            'larsen toubro': 'LT',
            'l&t': 'LT',
            'mahindra': 'M&M',
            'tata motors': 'TATAMOTORS',
            'asian paints': 'ASIANPAINT',
            'bajaj finance': 'BAJFINANCE',
            'maruti suzuki': 'MARUTI',
            'hindustan unilever': 'HINDUNILVR',
            'kotak mahindra bank': 'KOTAKBANK',
        }
        
        # Advanced symbol search alternatives
        self.symbol_alternatives = {
            'SUZLON': ['SUZLON.NS', 'SUZLON.BO', '532667.BO'],  # BSE code for Suzlon
            'RELIANCE': ['RELIANCE.NS', 'RELIANCE.BO', '500325.BO'],
            'TCS': ['TCS.NS', 'TCS.BO', '532540.BO'],
            'INFY': ['INFY.NS', 'INFY.BO', '500209.BO'],
            'HDFCBANK': ['HDFCBANK.NS', 'HDFCBANK.BO', '500180.BO'],
            'ICICIBANK': ['ICICIBANK.NS', 'ICICIBANK.BO', '532174.BO'],
        }
        
        # NSE headers
        self.nse_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request."""
        try:
            method = request.get('method')
            params = request.get('params', {})
            request_id = request.get('id')
            
            if method == 'get_stock_data':
                result = self.get_stock_data(params.get('symbol'))
            elif method == 'get_market_indices':
                result = self.get_market_indices()
            elif method == 'get_sector_data':
                result = self.get_sector_data(params.get('sector'))
            elif method == 'get_historical_data':
                result = self.get_historical_data(
                    params.get('symbol'),
                    params.get('period', '1mo')
                )
            else:
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {
                        'code': -32601,
                        'message': f'Method not found: {method}'
                    }
                }
            
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': result
            }
            
        except Exception as e:
            self.logger.error(f"Error handling request: {str(e)}")
            return {
                'jsonrpc': '2.0',
                'id': request.get('id'),
                'error': {
                    'code': -32603,
                    'message': f'Internal error: {str(e)}'
                }
            }
    
    def get_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive stock data for a symbol."""
        try:
            # Normalize symbol using symbol map
            normalized_symbol = self._normalize_symbol(symbol)
            self.logger.info(f"Normalized '{symbol}' to '{normalized_symbol}'")
            
            # Try yfinance first
            yf_data = self._get_yfinance_data(normalized_symbol)
            if yf_data:
                return yf_data
            
            # Fallback to NSE API
            nse_data = self._get_nse_data(normalized_symbol)
            if nse_data:
                return nse_data
            
            self.logger.warning(f"Could not fetch data for {symbol} (normalized: {normalized_symbol})")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting stock data for {symbol}: {str(e)}")
            return None
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol using the symbol map."""
        # Convert to lowercase for lookup
        symbol_lower = symbol.lower().strip()
        
        # Check if it's in our mapping
        if symbol_lower in self.symbol_map:
            return self.symbol_map[symbol_lower]
        
        # If not found, return the original symbol (in uppercase)
        return symbol.upper().strip()
    
    def _get_yfinance_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get data using yfinance with advanced symbol search."""
        try:
            # Get list of symbols to try
            symbols_to_try = []
            
            # Check if we have alternatives for this symbol
            if symbol in self.symbol_alternatives:
                symbols_to_try = self.symbol_alternatives[symbol]
            else:
                # Default NSE and BSE symbols
                symbols_to_try = [f"{symbol}.NS", f"{symbol}.BO"]
            
            last_error = None
            
            # Try each symbol variant until one works
            for yf_symbol in symbols_to_try:
                try:
                    self.logger.info(f"Trying symbol: {yf_symbol}")
                    ticker = yf.Ticker(yf_symbol)
                    
                    # Get basic info first
                    info = ticker.info
                    if not info or info.get('regularMarketPrice') is None:
                        self.logger.warning(f"No market price data for {yf_symbol}")
                        continue
                    
                    # Get historical data
                    hist = ticker.history(period="1mo")  # Try 1 month instead of 5 days
                    
                    if not hist.empty:
                        self.logger.info(f"Successfully fetched data for {yf_symbol}")
                        
                        # Calculate additional metrics
                        current_price = hist['Close'].iloc[-1] if not hist.empty else info.get('regularMarketPrice', 0)
                        price_change = hist['Close'].iloc[-1] - hist['Close'].iloc[-2] if len(hist) > 1 else 0
                        price_change_percent = (price_change / hist['Close'].iloc[-2] * 100) if len(hist) > 1 and hist['Close'].iloc[-2] != 0 else 0
                        volatility = hist['Close'].pct_change().std() * (252 ** 0.5) if len(hist) > 5 else 0.2  # Annualized volatility
                        
                        return {
                            'symbol': symbol,
                            'yf_symbol': yf_symbol,
                            'current_price': float(current_price),
                            'price_change': float(price_change),
                            'price_change_percent': float(price_change_percent),
                            'volume': int(hist['Volume'].iloc[-1]) if not hist.empty and 'Volume' in hist.columns else 0,
                            'market_cap': info.get('marketCap', 0),
                            'volatility': float(volatility),
                            'company_name': info.get('shortName', symbol),
                            'sector': info.get('sector', 'Unknown'),
                            'industry': info.get('industry', 'Unknown'),
                            'last_updated': datetime.now().isoformat(),
                            'source': 'yfinance',
                            'data_quality': 'real' if not hist.empty else 'info_only'
                        }
                    
                except Exception as e:
                    last_error = str(e)
                    self.logger.warning(f"Failed to get data for {yf_symbol}: {str(e)}")
                    continue
            
            # If all attempts failed, return mock data with warning
            self.logger.warning(f"All symbol variants failed for {symbol}. Last error: {last_error}")
            return self._generate_mock_data(symbol, f"No data available - {last_error}")
            
        except Exception as e:
            self.logger.error(f"Error in _get_yfinance_data for {symbol}: {str(e)}")
            return self._generate_mock_data(symbol, f"Data fetch error: {str(e)}")
    
    def _generate_mock_data(self, symbol: str, reason: str) -> Dict[str, Any]:
        """Generate mock data when real data is not available."""
        import random
        
        base_price = random.uniform(10, 500)
        price_change = random.uniform(-5, 5)
        
        return {
            'symbol': symbol,
            'yf_symbol': f"{symbol}.NS",
            'current_price': round(base_price, 2),
            'price_change': round(price_change, 2),
            'price_change_percent': round(price_change / base_price * 100, 2),
            'volume': random.randint(10000, 1000000),
            'market_cap': random.randint(1000000000, 100000000000),
            'volatility': round(random.uniform(0.15, 0.45), 3),
            'company_name': symbol.title(),
            'sector': 'Energy' if 'suzlon' in symbol.lower() else 'Technology',
            'industry': 'Renewable Energy' if 'suzlon' in symbol.lower() else 'Software',
            'last_updated': datetime.now().isoformat(),
            'source': 'mock',
            'data_quality': 'mock',
            'warning': reason
        }

    def _get_nse_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get data from NSE API."""
        try:
            url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
            response = self.session.get(url, headers=self.nse_headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'priceInfo' in data:
                    price_info = data['priceInfo']
                    
                    return {
                        "symbol": symbol,
                        "price": float(price_info.get('lastPrice', 0)),
                        "open": float(price_info.get('open', 0)),
                        "high": float(price_info.get('intraDayHighLow', {}).get('max', 0)),
                        "low": float(price_info.get('intraDayHighLow', {}).get('min', 0)),
                        "change": float(price_info.get('change', 0)),
                        "change_percent": float(price_info.get('pChange', 0)),
                        "volume": int(data.get('securityInfo', {}).get('totalTradedVolume', 0)),
                        "source": "nse",
                        "timestamp": datetime.now().isoformat(),
                        "currency": "INR"
                    }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"NSE API failed for {symbol}: {str(e)}")
            return None
    
    def get_market_indices(self) -> Dict[str, Any]:
        """Get major market indices."""
        try:
            indices = {
                'NIFTY 50': '^NSEI',
                'NIFTY BANK': '^NSEBANK',
                'SENSEX': '^BSESN'
            }
            
            indices_data = {}
            
            for name, symbol in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="2d")
                    
                    if not hist.empty:
                        latest = hist.iloc[-1]
                        previous = hist.iloc[-2] if len(hist) > 1 else latest
                        
                        indices_data[name] = {
                            "symbol": symbol,
                            "name": name,
                            "price": float(latest['Close']),
                            "open": float(latest['Open']),
                            "high": float(latest['High']),
                            "low": float(latest['Low']),
                            "volume": int(latest['Volume']),
                            "change": float(latest['Close'] - previous['Close']),
                            "change_percent": float((latest['Close'] - previous['Close']) / previous['Close'] * 100),
                            "timestamp": datetime.now().isoformat()
                        }
                except Exception as e:
                    self.logger.warning(f"Failed to get data for {name}: {str(e)}")
                    continue
            
            return indices_data
            
        except Exception as e:
            self.logger.error(f"Error getting market indices: {str(e)}")
            return {}
    
    def get_sector_data(self, sector: str) -> Dict[str, Any]:
        """Get sector-wise stock data."""
        try:
            sector_stocks = {
                'IT': ['INFY.NS', 'TCS.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS'],
                'BANKING': ['HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'AXISBANK.NS'],
                'AUTO': ['MARUTI.NS', 'TATAMOTORS.NS', 'BAJAJ-AUTO.NS', 'M&M.NS'],
                'PHARMA': ['SUNPHARMA.NS', 'DRREDDY.NS', 'CIPLA.NS', 'LUPIN.NS']
            }
            
            stocks = sector_stocks.get(sector.upper(), [])
            sector_data = {}
            
            for stock_symbol in stocks:
                try:
                    clean_symbol = stock_symbol.replace('.NS', '')
                    data = self.get_stock_data(clean_symbol)
                    if data:
                        sector_data[clean_symbol] = data
                except Exception as e:
                    self.logger.warning(f"Failed to get data for {stock_symbol}: {str(e)}")
                    continue
            
            return {
                'sector': sector,
                'stocks': sector_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting sector data for {sector}: {str(e)}")
            return {}
    
    def get_historical_data(self, symbol: str, period: str = "1mo") -> Optional[Dict[str, Any]]:
        """Get historical stock data."""
        try:
            yf_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                # Try BSE
                yf_symbol = f"{symbol}.BO"
                ticker = yf.Ticker(yf_symbol)
                hist = ticker.history(period=period)
            
            if not hist.empty:
                return {
                    "symbol": symbol,
                    "period": period,
                    "data": [
                        {
                            "date": str(date.date()),
                            "open": float(row['Open']),
                            "high": float(row['High']),
                            "low": float(row['Low']),
                            "close": float(row['Close']),
                            "volume": int(row['Volume'])
                        }
                        for date, row in hist.iterrows()
                    ],
                    "source": "yfinance",
                    "timestamp": datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return None

def run_server(port: int = 8001):
    """Run the MCP Finance server."""
    server = MCPFinanceServer()
    
    print(f"MCP Finance Server starting on port {port}")
    
    try:
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
                    
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    
                    error_response = {
                        'jsonrpc': '2.0',
                        'id': None,
                        'error': {
                            'code': -32603,
                            'message': f'Server error: {str(e)}'
                        }
                    }
                    
                    self.wfile.write(json.dumps(error_response).encode('utf-8'))
            
            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
        
        httpd = HTTPServer(('localhost', port), MCPHandler)
        print(f"MCP Finance Server running on http://localhost:{port}")
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\nMCP Finance Server stopped.")
    except Exception as e:
        print(f"Server error: {str(e)}")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    run_server(port)
