import requests
import json
import logging
import yfinance as yf
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from config import Config

class DataCollectorAgent:
    """Agent responsible for collecting live stock data from NSE/BSE via MCP Finance API server."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mcp_url = f"http://localhost:{Config.MCP_FINANCE_PORT}"
        self.session = requests.Session()
        
        # Headers for NSE API
        self.nse_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    
    def get_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive stock data for a given symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'INFY', 'TCS')
            
        Returns:
            Dictionary containing stock data or None if failed
        """
        try:
            self.logger.info(f"Fetching stock data for {symbol}")
            
            # Try MCP server first
            mcp_data = self._get_data_from_mcp(symbol)
            if mcp_data:
                return mcp_data
            
            # Fallback to direct APIs
            yf_data = self._get_data_from_yfinance(symbol)
            if yf_data:
                return yf_data
            
            # Fallback to NSE API
            nse_data = self._get_data_from_nse(symbol)
            if nse_data:
                return nse_data
            
            self.logger.warning(f"Could not fetch data for {symbol}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching stock data for {symbol}: {str(e)}")
            return None
    
    def _get_data_from_mcp(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get data from MCP Finance server."""
        try:
            response = self.session.post(
                self.mcp_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "get_stock_data",
                    "params": {"symbol": symbol}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    return data['result']
            
            return None
            
        except Exception as e:
            self.logger.warning(f"MCP server call failed for {symbol}: {str(e)}")
            return None
    
    def _get_data_from_yfinance(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get data using yfinance library."""
        try:
            # Add .NS for NSE stocks or .BO for BSE stocks
            yf_symbol = f"{symbol}.NS"
            
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            hist = ticker.history(period="5d")
            
            if hist.empty:
                # Try BSE
                yf_symbol = f"{symbol}.BO"
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                hist = ticker.history(period="5d")
            
            if not hist.empty:
                latest = hist.iloc[-1]
                previous = hist.iloc[-2] if len(hist) > 1 else latest
                
                return {
                    "symbol": symbol,
                    "price": float(latest['Close']),
                    "open": float(latest['Open']),
                    "high": float(latest['High']),
                    "low": float(latest['Low']),
                    "volume": int(latest['Volume']),
                    "change": float(latest['Close'] - previous['Close']),
                    "change_percent": float((latest['Close'] - previous['Close']) / previous['Close'] * 100),
                    "market_cap": info.get('marketCap'),
                    "pe_ratio": info.get('trailingPE'),
                    "source": "yfinance",
                    "timestamp": datetime.now().isoformat(),
                    "currency": info.get('currency', 'INR')
                }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"YFinance call failed for {symbol}: {str(e)}")
            return None
    
    def _get_data_from_nse(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get data directly from NSE API."""
        try:
            # NSE API endpoint
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
            self.logger.warning(f"NSE API call failed for {symbol}: {str(e)}")
            return None
    
    def get_market_indices(self) -> Dict[str, Any]:
        """Get major market indices data."""
        try:
            indices = ['NIFTY', 'SENSEX', 'BANKNIFTY']
            indices_data = {}
            
            for index in indices:
                data = self.get_stock_data(index)
                if data:
                    indices_data[index] = data
            
            return indices_data
            
        except Exception as e:
            self.logger.error(f"Error fetching market indices: {str(e)}")
            return {}
    
    def get_sector_data(self, sector: str) -> Dict[str, Any]:
        """Get sector-wise stock data."""
        try:
            # Define sector stocks
            sector_stocks = {
                'IT': ['INFY', 'TCS', 'WIPRO', 'HCLTECH', 'TECHM'],
                'BANKING': ['HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK', 'AXISBANK'],
                'AUTO': ['MARUTI', 'HYUNDAI', 'TATAMOTORS', 'BAJAJ-AUTO', 'M&M'],
                'PHARMA': ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'LUPIN', 'BIOCON']
            }
            
            stocks = sector_stocks.get(sector.upper(), [])
            sector_data = {}
            
            for stock in stocks:
                data = self.get_stock_data(stock)
                if data:
                    sector_data[stock] = data
            
            return sector_data
            
        except Exception as e:
            self.logger.error(f"Error fetching sector data for {sector}: {str(e)}")
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
            self.logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None
    
    def get_multiple_stocks(self, symbols: list) -> Dict[str, Any]:
        """Get data for multiple stocks efficiently."""
        try:
            stocks_data = {}
            
            for symbol in symbols:
                data = self.get_stock_data(symbol)
                if data:
                    stocks_data[symbol] = data
                    self.logger.info(f"Successfully fetched data for {symbol}")
                else:
                    self.logger.warning(f"Failed to fetch data for {symbol}")
            
            return stocks_data
            
        except Exception as e:
            self.logger.error(f"Error fetching multiple stocks data: {str(e)}")
            return {}
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if a stock symbol exists and is tradeable."""
        try:
            data = self.get_stock_data(symbol)
            return data is not None and data.get('price', 0) > 0
        except:
            return False
