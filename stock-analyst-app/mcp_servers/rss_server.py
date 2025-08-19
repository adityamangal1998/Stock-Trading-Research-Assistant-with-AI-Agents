#!/usr/bin/env python3
"""
MCP RSS Server - Wraps financial news RSS feeds for the stock analysis system.
"""

import json
import sys
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import feedparser
import requests
from bs4 import BeautifulSoup

class MCPRSSServer:
    """MCP server for RSS news operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        
        # RSS feeds
        self.rss_feeds = [
            'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
            'https://www.moneycontrol.com/rss/business.xml',
            'https://feeds.feedburner.com/ndtvprofit-latest',
            'https://www.business-standard.com/rss/markets-106.rss',
            'https://www.livemint.com/rss/markets'
        ]
        
        # Sentiment keywords
        self.positive_keywords = [
            'profit', 'growth', 'gain', 'rise', 'surge', 'bullish', 'positive',
            'upgrade', 'beat', 'strong', 'excellent', 'good', 'buy', 'outperform'
        ]
        
        self.negative_keywords = [
            'loss', 'decline', 'fall', 'drop', 'bearish', 'negative', 'weak',
            'downgrade', 'miss', 'poor', 'bad', 'sell', 'underperform', 'crash'
        ]
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request."""
        try:
            method = request.get('method')
            params = request.get('params', {})
            request_id = request.get('id')
            
            if method == 'get_market_news':
                result = self.get_market_news(params.get('limit', 20))
            elif method == 'get_stock_news':
                result = self.get_stock_news(
                    params.get('symbol'),
                    params.get('limit', 10)
                )
            elif method == 'analyze_sentiment':
                result = self.analyze_sentiment(params.get('text', ''))
            elif method == 'get_trending_topics':
                result = self.get_trending_topics(params.get('limit', 10))
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
    
    def get_market_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get latest market news from RSS feeds."""
        try:
            all_news = []
            
            for feed_url in self.rss_feeds:
                try:
                    self.logger.info(f"Parsing RSS feed: {feed_url}")
                    feed = feedparser.parse(feed_url)
                    
                    for entry in feed.entries[:limit//len(self.rss_feeds) + 2]:
                        news_item = self._parse_news_entry(entry, feed_url)
                        if news_item:
                            all_news.append(news_item)
                            
                except Exception as e:
                    self.logger.warning(f"Failed to parse RSS feed {feed_url}: {str(e)}")
                    continue
            
            # Sort by published date and limit
            all_news.sort(key=lambda x: x.get('published_date', ''), reverse=True)
            return all_news[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting market news: {str(e)}")
            return []
    
    def _parse_news_entry(self, entry, source_url: str) -> Optional[Dict[str, Any]]:
        """Parse a single news entry from RSS feed."""
        try:
            # Extract basic information
            title = entry.get('title', '').strip()
            summary = entry.get('summary', '').strip()
            link = entry.get('link', '').strip()
            
            # Parse published date
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_date = datetime(*entry.published_parsed[:6])
            
            # Get full content if available
            content = self._extract_content(entry)
            
            # Extract related stock symbols
            symbols = self._extract_stock_symbols(title + ' ' + summary + ' ' + content)
            
            # Calculate sentiment score
            sentiment = self._calculate_sentiment(title + ' ' + summary + ' ' + content)
            
            return {
                'title': title,
                'summary': summary,
                'content': content,
                'url': link,
                'source': self._get_source_name(source_url),
                'published_date': published_date.isoformat() if published_date else None,
                'symbols': symbols,
                'sentiment': sentiment,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to parse news entry: {str(e)}")
            return None
    
    def _extract_content(self, entry) -> str:
        """Extract full content from news entry."""
        try:
            content = ''
            
            # Try different content fields
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].value if isinstance(entry.content, list) else entry.content
            elif hasattr(entry, 'description'):
                content = entry.description
            elif hasattr(entry, 'summary'):
                content = entry.summary
            
            # Clean HTML tags
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                content = soup.get_text(strip=True)
            
            return content[:1000]  # Limit content length
            
        except Exception as e:
            self.logger.warning(f"Failed to extract content: {str(e)}")
            return ''
    
    def _extract_stock_symbols(self, text: str) -> List[str]:
        """Extract stock symbols mentioned in the text."""
        try:
            symbols = []
            
            # Known stock symbols to look for
            known_symbols = [
                'INFY', 'TCS', 'RELIANCE', 'HDFCBANK', 'ICICIBANK', 'SBIN',
                'WIPRO', 'BHARTIARTL', 'ITC', 'HINDUNILVR', 'MARUTI', 'BAJFINANCE',
                'KOTAKBANK', 'LT', 'AXISBANK', 'ASIANPAINT', 'NESTLEIND', 'HCLTECH',
                'ULTRACEMCO', 'TATAMOTORS', 'SUNPHARMA', 'ONGC', 'TITAN', 'POWERGRID',
                'NIFTY', 'SENSEX', 'BANKNIFTY'
            ]
            
            text_upper = text.upper()
            
            for symbol in known_symbols:
                if symbol in text_upper:
                    symbols.append(symbol)
            
            return list(set(symbols))  # Remove duplicates
            
        except Exception as e:
            self.logger.warning(f"Failed to extract stock symbols: {str(e)}")
            return []
    
    def _calculate_sentiment(self, text: str) -> float:
        """Calculate sentiment score for the text (-1.0 to 1.0)."""
        try:
            text_lower = text.lower()
            
            positive_count = sum(1 for word in self.positive_keywords if word in text_lower)
            negative_count = sum(1 for word in self.negative_keywords if word in text_lower)
            
            total_words = len(text.split())
            
            if total_words == 0:
                return 0.0
            
            # Calculate sentiment score
            sentiment_score = (positive_count - negative_count) / max(total_words / 10, 1)
            
            # Normalize to -1.0 to 1.0 range
            sentiment_score = max(-1.0, min(1.0, sentiment_score))
            
            return round(sentiment_score, 3)
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate sentiment: {str(e)}")
            return 0.0
    
    def _get_source_name(self, url: str) -> str:
        """Extract source name from URL."""
        try:
            if 'economictimes' in url:
                return 'Economic Times'
            elif 'moneycontrol' in url:
                return 'MoneyControl'
            elif 'ndtv' in url:
                return 'NDTV Profit'
            elif 'business-standard' in url:
                return 'Business Standard'
            elif 'livemint' in url:
                return 'LiveMint'
            else:
                return 'Unknown'
        except:
            return 'Unknown'
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get news specific to a particular stock symbol."""
        try:
            all_news = self.get_market_news(limit * 3)  # Get more to filter
            
            stock_news = []
            for news in all_news:
                if (symbol.upper() in news.get('symbols', []) or 
                    symbol.lower() in news.get('title', '').lower() or
                    symbol.lower() in news.get('content', '').lower()):
                    stock_news.append(news)
                    
                if len(stock_news) >= limit:
                    break
            
            return stock_news
            
        except Exception as e:
            self.logger.error(f"Error getting stock news for {symbol}: {str(e)}")
            return []
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of given text."""
        try:
            sentiment_score = self._calculate_sentiment(text)
            
            # Classify sentiment
            if sentiment_score > 0.1:
                sentiment_label = 'POSITIVE'
            elif sentiment_score < -0.1:
                sentiment_label = 'NEGATIVE'
            else:
                sentiment_label = 'NEUTRAL'
            
            return {
                'text': text[:200] + '...' if len(text) > 200 else text,
                'sentiment_score': sentiment_score,
                'sentiment_label': sentiment_label,
                'confidence': abs(sentiment_score),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                'sentiment_score': 0.0,
                'sentiment_label': 'NEUTRAL',
                'confidence': 0.0
            }
    
    def get_trending_topics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending topics from recent news."""
        try:
            news_items = self.get_market_news(100)
            
            # Extract keywords from titles
            word_counts = {}
            
            for news in news_items:
                title = news.get('title', '').lower()
                words = re.findall(r'\b[a-zA-Z]{4,}\b', title)
                
                for word in words:
                    if word not in ['india', 'stock', 'share', 'market', 'company', 'news']:
                        word_counts[word] = word_counts.get(word, 0) + 1
            
            # Sort by frequency
            trending = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
            
            return [
                {
                    'topic': word,
                    'frequency': count,
                    'sentiment': self._get_topic_sentiment(word, news_items)
                }
                for word, count in trending[:limit]
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting trending topics: {str(e)}")
            return []
    
    def _get_topic_sentiment(self, topic: str, news_items: List[Dict]) -> float:
        """Get average sentiment for a topic."""
        try:
            topic_sentiments = []
            
            for news in news_items:
                if topic.lower() in news.get('title', '').lower():
                    topic_sentiments.append(news.get('sentiment', 0.0))
            
            if topic_sentiments:
                return round(sum(topic_sentiments) / len(topic_sentiments), 3)
            
            return 0.0
            
        except:
            return 0.0

def run_server(port: int = 8002):
    """Run the MCP RSS server."""
    server = MCPRSSServer()
    
    print(f"MCP RSS Server starting on port {port}")
    
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
        print(f"MCP RSS Server running on http://localhost:{port}")
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\nMCP RSS Server stopped.")
    except Exception as e:
        print(f"Server error: {str(e)}")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8002
    run_server(port)
