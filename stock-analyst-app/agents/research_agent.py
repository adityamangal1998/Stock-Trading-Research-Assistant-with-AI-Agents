import requests
import feedparser
import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from config import Config

class ResearchAgent:
    """Agent responsible for gathering and analyzing financial news from MCP RSS server."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mcp_url = f"http://localhost:{Config.MCP_RSS_PORT}"
        self.session = requests.Session()
        
        # RSS feeds for financial news
        self.rss_feeds = Config.RSS_FEEDS
        
        # Keywords for sentiment analysis
        self.positive_keywords = [
            'profit', 'growth', 'gain', 'rise', 'surge', 'bullish', 'positive',
            'upgrade', 'beat', 'strong', 'excellent', 'good', 'buy', 'outperform'
        ]
        
        self.negative_keywords = [
            'loss', 'decline', 'fall', 'drop', 'bearish', 'negative', 'weak',
            'downgrade', 'miss', 'poor', 'bad', 'sell', 'underperform', 'crash'
        ]
    
    def get_market_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get latest market news and perform sentiment analysis.
        
        Args:
            limit: Maximum number of news items to return
            
        Returns:
            List of news dictionaries with sentiment scores
        """
        try:
            self.logger.info("Fetching market news")
            
            # Try MCP server first
            mcp_news = self._get_news_from_mcp(limit)
            if mcp_news:
                return mcp_news
            
            # Fallback to direct RSS parsing
            return self._get_news_from_rss(limit)
            
        except Exception as e:
            self.logger.error(f"Error fetching market news: {str(e)}")
            return []
    
    def _get_news_from_mcp(self, limit: int) -> Optional[List[Dict[str, Any]]]:
        """Get news from MCP RSS server."""
        try:
            response = self.session.post(
                self.mcp_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "get_market_news",
                    "params": {"limit": limit}
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    return data['result']
            
            return None
            
        except Exception as e:
            self.logger.warning(f"MCP RSS server call failed: {str(e)}")
            return None
    
    def _get_news_from_rss(self, limit: int) -> List[Dict[str, Any]]:
        """Get news directly from RSS feeds."""
        try:
            all_news = []
            
            for feed_url in self.rss_feeds:
                try:
                    self.logger.info(f"Parsing RSS feed: {feed_url}")
                    feed = feedparser.parse(feed_url)
                    
                    for entry in feed.entries[:limit//len(self.rss_feeds)]:
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
            self.logger.error(f"Error parsing RSS feeds: {str(e)}")
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
            
            # Common Indian stock symbols pattern
            symbol_patterns = [
                r'\b([A-Z]{3,6})\b',  # 3-6 uppercase letters
                r'\b(NIFTY|SENSEX|BANKNIFTY)\b',  # Index names
            ]
            
            # Known stock symbols to look for
            known_symbols = [
                'INFY', 'TCS', 'RELIANCE', 'HDFCBANK', 'ICICIBANK', 'SBIN',
                'WIPRO', 'BHARTIARTL', 'ITC', 'HINDUNILVR', 'MARUTI', 'BAJFINANCE',
                'KOTAKBANK', 'LT', 'AXISBANK', 'ASIANPAINT', 'NESTLEIND', 'HCLTECH',
                'ULTRACEMCO', 'TATAMOTORS', 'SUNPHARMA', 'ONGC', 'TITAN', 'POWERGRID'
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
    
    def get_stock_specific_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
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
            self.logger.error(f"Error fetching news for {symbol}: {str(e)}")
            return []
    
    def analyze_market_sentiment(self) -> Dict[str, Any]:
        """Analyze overall market sentiment from recent news."""
        try:
            news_items = self.get_market_news(50)
            
            if not news_items:
                return {'overall_sentiment': 0.0, 'confidence': 0.0}
            
            sentiments = [item.get('sentiment', 0.0) for item in news_items]
            
            overall_sentiment = sum(sentiments) / len(sentiments)
            
            # Calculate confidence based on consensus
            positive_count = len([s for s in sentiments if s > 0.1])
            negative_count = len([s for s in sentiments if s < -0.1])
            neutral_count = len(sentiments) - positive_count - negative_count
            
            confidence = (max(positive_count, negative_count) / len(sentiments))
            
            return {
                'overall_sentiment': round(overall_sentiment, 3),
                'confidence': round(confidence, 3),
                'positive_news': positive_count,
                'negative_news': negative_count,
                'neutral_news': neutral_count,
                'total_news': len(news_items),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing market sentiment: {str(e)}")
            return {'overall_sentiment': 0.0, 'confidence': 0.0}
    
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
                    if word not in ['india', 'stock', 'share', 'market', 'company']:
                        word_counts[word] = word_counts.get(word, 0) + 1
            
            # Sort by frequency
            trending = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
            
            return [
                {'topic': word, 'frequency': count}
                for word, count in trending[:limit]
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting trending topics: {str(e)}")
            return []
