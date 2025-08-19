#!/usr/bin/env python3
"""
Intelligent Search Agent - Uses Tavily API for advanced stock search and analysis.
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from tavily import TavilyClient
from config import Config

class IntelligentSearchAgent:
    """Agent that uses Tavily API for intelligent stock search and deep analysis."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tavily_client = TavilyClient(api_key=Config.TAVILY_API_KEY)
        
        # Common stock search patterns
        self.stock_patterns = {
            'symbol_extraction': r'\b([A-Z]{2,6}(?:\.[A-Z]{2})?)\b',
            'company_indicators': ['ltd', 'limited', 'inc', 'corporation', 'corp', 'company', 'co'],
            'financial_keywords': ['stock', 'share', 'equity', 'market cap', 'trading', 'nse', 'bse', 'nasdaq']
        }
        
    def search_stock_comprehensive(self, query: str) -> Dict[str, Any]:
        """
        Perform comprehensive stock search using Tavily API.
        
        Args:
            query: Search query (company name, symbol, or description)
            
        Returns:
            Dict containing search results, stock info, and analysis
        """
        try:
            self.logger.info(f"Starting comprehensive search for: {query}")
            
            # Step 1: Basic stock information search
            basic_info = self._search_basic_stock_info(query)
            
            # Step 2: Historical performance and trends
            historical_analysis = self._search_historical_performance(query)
            
            # Step 3: Recent news and market sentiment
            news_sentiment = self._search_stock_news(query)
            
            # Step 4: Financial data and analysis
            financial_analysis = self._search_financial_analysis(query)
            
            # Step 5: Competitor and sector analysis
            sector_analysis = self._search_sector_analysis(query)
            
            # Step 6: Technical analysis and price trends
            technical_analysis = self._search_technical_analysis(query)
            
            # Step 7: Analyst reports and ratings
            analyst_reports = self._search_analyst_reports(query)
            
            # Combine all results
            comprehensive_result = {
                'query': query,
                'timestamp': datetime.now().isoformat(),
                'basic_info': basic_info,
                'historical_analysis': historical_analysis,
                'news_sentiment': news_sentiment,
                'financial_analysis': financial_analysis,
                'sector_analysis': sector_analysis,
                'technical_analysis': technical_analysis,
                'analyst_reports': analyst_reports,
                'search_success': True,
                'data_sources': ['tavily_api', 'web_search', 'financial_sites'],
                'recommendation_confidence': self._calculate_overall_confidence(
                    basic_info, news_sentiment, financial_analysis, historical_analysis
                )
            }
            
            return comprehensive_result
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive stock search: {str(e)}")
            return {
                'query': query,
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'search_success': False,
                'fallback_suggestion': self._suggest_alternative_search(query)
            }
    
    def _search_historical_performance(self, query: str) -> Dict[str, Any]:
        """Search for historical performance and trends."""
        try:
            # Historical performance focused search
            search_query = f"{query} stock price history performance 1 year 3 year 5 year returns charts"
            
            response = self.tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=6,
                include_domains=["moneycontrol.com", "screener.in", "yahoo.com", "google.com"]
            )
            
            return self._extract_historical_data(response, query)
            
        except Exception as e:
            self.logger.error(f"Error in historical search: {str(e)}")
            return {'error': str(e), 'historical_available': False}
    
    def _search_analyst_reports(self, query: str) -> Dict[str, Any]:
        """Search for analyst reports and recommendations."""
        try:
            # Analyst reports focused search
            search_query = f"{query} analyst recommendation buy sell hold target price brokerage reports"
            
            response = self.tavily_client.search(
                query=search_query,
                search_depth="basic",
                max_results=5,
                include_domains=["moneycontrol.com", "economictimes.com", "livemint.com"]
            )
            
            return self._extract_analyst_data(response, query)
            
        except Exception as e:
            self.logger.error(f"Error in analyst reports search: {str(e)}")
            return {'error': str(e), 'analyst_reports_available': False}
    
    def _extract_historical_data(self, response: Dict, query: str) -> Dict[str, Any]:
        """Extract historical performance data from search results."""
        historical_data = {
            'performance_periods': {},
            'key_events': [],
            'volatility_assessment': 'medium',
            'long_term_trend': 'neutral',
            'historical_available': False
        }
        
        try:
            content_corpus = " ".join([res.get('content', '').lower() for res in response.get('results', [])])
            
            period_patterns = {
                '1 Year': r'1\s*year.*?(-?\d[\d,.]*)%',
                '6 Months': r'6\s*months?.*?(-?\d[\d,.]*)%',
                '3 Months': r'3\s*months?.*?(-?\d[\d,.]*)%',
                '1 Month': r'1\s*month?.*?(-?\d[\d,.]*)%',
                'YTD': r'ytd.*?(-?\d[\d,.]*)%',
            }
            for period, pattern in period_patterns.items():
                match = re.search(pattern, content_corpus, re.IGNORECASE)
                if match:
                    historical_data['performance_periods'][period] = f"{match.group(1).replace(',', '')}%"
                    historical_data['historical_available'] = True

            if not historical_data['performance_periods']:
                matches = re.findall(r'(-?\d[\d,.]*)%\s*return', content_corpus, re.IGNORECASE)
                if matches:
                    historical_data['performance_periods']['Unspecified Period'] = f"{matches[0].replace(',', '')}%"
                    historical_data['historical_available'] = True

            if 'high volatility' in content_corpus: historical_data['volatility_assessment'] = 'high'
            if 'low volatility' in content_corpus: historical_data['volatility_assessment'] = 'low'
            if 'strong uptrend' in content_corpus: historical_data['long_term_trend'] = 'positive'
            if 'strong downtrend' in content_corpus: historical_data['long_term_trend'] = 'negative'

            event_keywords = ['split', 'dividend', 'bonus', 'merger', 'acquisition', 'new ceo', 'record high']
            sentences = re.split(r'[.!?]', content_corpus)
            for sentence in sentences:
                if any(kw in sentence for kw in event_keywords):
                    historical_data['key_events'].append(sentence.strip().capitalize())
            
            historical_data['key_events'] = list(set(historical_data['key_events']))[:3]
            if historical_data['key_events']:
                historical_data['historical_available'] = True

        except Exception as e:
            self.logger.error(f"Error extracting historical data: {str(e)}")
            historical_data['error'] = str(e)
        
        return historical_data
    
    def _extract_analyst_data(self, response: Dict, query: str) -> Dict[str, Any]:
        """Extract analyst reports and recommendations."""
        analyst_data = {
            'consensus_rating': 'neutral',
            'target_prices': [],
            'rating_distribution': {'buy': 0, 'hold': 0, 'sell': 0},
            'analyst_reports_available': False
        }
        
        try:
            content_corpus = " ".join([res.get('content', '').lower() for res in response.get('results', [])])
            
            targets = re.findall(r'(?:target price of|tp\s*[:is])\s*rs\.?\s*([\d,]+\.?\d*)', content_corpus, re.IGNORECASE)
            if targets:
                analyst_data['target_prices'] = [f"₹{t.replace(',', '')}" for t in targets][:3]
                analyst_data['analyst_reports_available'] = True

            buy_count = len(re.findall(r'\b(buy|outperform|accumulate)\b', content_corpus, re.IGNORECASE))
            hold_count = len(re.findall(r'\b(hold|neutral|market perform)\b', content_corpus, re.IGNORECASE))
            sell_count = len(re.findall(r'\b(sell|underperform|reduce)\b', content_corpus, re.IGNORECASE))
            
            analyst_data['rating_distribution']['buy'] = buy_count
            analyst_data['rating_distribution']['hold'] = hold_count
            analyst_data['rating_distribution']['sell'] = sell_count

            if buy_count + hold_count + sell_count > 0:
                analyst_data['analyst_reports_available'] = True
                if buy_count > hold_count and buy_count > sell_count:
                    analyst_data['consensus_rating'] = 'buy'
                elif sell_count > buy_count and sell_count > hold_count:
                    analyst_data['consensus_rating'] = 'sell'
                else:
                    analyst_data['consensus_rating'] = 'hold'

        except Exception as e:
            self.logger.error(f"Error extracting analyst data: {str(e)}")
            analyst_data['error'] = str(e)
        
        return analyst_data
    
    def _search_basic_stock_info(self, query: str) -> Dict[str, Any]:
        """Search for basic stock information."""
        try:
            # Enhanced search query for stock basics
            search_query = f"{query} stock price market cap NSE BSE ticker symbol company information"
            
            response = self.tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=5,
                include_domains=["moneycontrol.com", "nseindia.com", "bseindia.com", "yahoo.com", "bloomberg.com"]
            )
            
            return self._extract_basic_info(response, query)
            
        except Exception as e:
            self.logger.error(f"Error in basic stock search: {str(e)}")
            return {'error': str(e), 'data_available': False}
    
    def _search_stock_news(self, query: str) -> Dict[str, Any]:
        """Search for recent stock news and sentiment."""
        try:
            # News-focused search query
            search_query = f"{query} stock news latest updates market performance today 2025"
            
            response = self.tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=8,
                include_domains=["economictimes.com", "livemint.com", "moneycontrol.com", "reuters.com", "bloomberg.com"]
            )
            
            return self._extract_news_sentiment(response, query)
            
        except Exception as e:
            self.logger.error(f"Error in news search: {str(e)}")
            return {'error': str(e), 'news_available': False}
    
    def _search_financial_analysis(self, query: str) -> Dict[str, Any]:
        """Search for financial analysis and metrics."""
        try:
            # Financial analysis focused search
            search_query = f"{query} financial analysis revenue profit margins P/E ratio debt equity quarterly results"
            
            response = self.tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=5,
                include_domains=["moneycontrol.com", "screener.in", "financialexpress.com", "bloomberg.com"]
            )
            
            return self._extract_financial_metrics(response, query)
            
        except Exception as e:
            self.logger.error(f"Error in financial analysis search: {str(e)}")
            return {'error': str(e), 'analysis_available': False}
    
    def _search_sector_analysis(self, query: str) -> Dict[str, Any]:
        """Search for sector and competitor analysis."""
        try:
            # Sector analysis focused search
            search_query = f"{query} sector analysis competitors industry trends market position India"
            
            response = self.tavily_client.search(
                query=search_query,
                search_depth="basic",
                max_results=4
            )
            
            return self._extract_sector_info(response, query)
            
        except Exception as e:
            self.logger.error(f"Error in sector analysis search: {str(e)}")
            return {'error': str(e), 'sector_available': False}
    
    def _search_technical_analysis(self, query: str) -> Dict[str, Any]:
        """Search for technical analysis and price trends."""
        try:
            # Technical analysis focused search
            search_query = f"{query} technical analysis price trend support resistance moving averages chart"
            
            response = self.tavily_client.search(
                query=search_query,
                search_depth="basic",
                max_results=4,
                include_domains=["tradingview.com", "investopedia.com", "moneycontrol.com"]
            )
            
            return self._extract_technical_info(response, query)
            
        except Exception as e:
            self.logger.error(f"Error in technical analysis search: {str(e)}")
            return {'error': str(e), 'technical_available': False}
    
    def _extract_basic_info(self, response: Dict, query: str) -> Dict[str, Any]:
        """Extract basic stock information from search results."""
        basic_info = {
            'company_name': None,
            'ticker_symbol': None,
            'current_price': None,
            'market_cap': None,
            'exchange': None,
            'sector': None,
            'description': None,
            'extracted_from': []
        }
        
        try:
            for result in response.get('results', []):
                content = result.get('content', '').lower()
                title = result.get('title', '').lower()
                url = result.get('url', '')
                
                # Extract ticker symbols
                symbols = re.findall(self.stock_patterns['symbol_extraction'], content.upper())
                if symbols and not basic_info['ticker_symbol']:
                    basic_info['ticker_symbol'] = symbols[0]
                
                # Extract company name (look for patterns before "ltd", "limited", etc.)
                for indicator in self.stock_patterns['company_indicators']:
                    if indicator in content:
                        # Find text before the indicator
                        parts = content.split(indicator)[0].split()
                        if len(parts) >= 2:
                            basic_info['company_name'] = ' '.join(parts[-3:]).title()
                            break
                
                # Extract numeric values (prices, market cap)
                price_matches = re.findall(r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)', content)
                if price_matches and not basic_info['current_price']:
                    basic_info['current_price'] = price_matches[0].replace(',', '')
                
                # Track sources
                basic_info['extracted_from'].append(url)
            
            # Set defaults if not found
            if not basic_info['company_name']:
                basic_info['company_name'] = query.title()
            if not basic_info['ticker_symbol']:
                basic_info['ticker_symbol'] = query.upper()
                
            basic_info['data_available'] = True
            
        except Exception as e:
            self.logger.error(f"Error extracting basic info: {str(e)}")
            basic_info['error'] = str(e)
            basic_info['data_available'] = False
        
        return basic_info
    
    def _extract_news_sentiment(self, response: Dict, query: str) -> Dict[str, Any]:
        """Extract news and sentiment from search results."""
        news_data = {
            'recent_news': [],
            'overall_sentiment': 'neutral',
            'sentiment_score': 0.0,
            'news_count': 0,
            'positive_indicators': [],
            'negative_indicators': [],
            'news_available': True
        }
        
        try:
            positive_words = ['profit', 'growth', 'increase', 'rise', 'gain', 'strong', 'good', 'positive', 'up', 'bull']
            negative_words = ['loss', 'decline', 'fall', 'drop', 'weak', 'negative', 'down', 'bear', 'risk']
            
            sentiment_score = 0
            
            for result in response.get('results', []):
                title = result.get('title', '')
                content = result.get('content', '')
                url = result.get('url', '')
                
                # Basic sentiment analysis
                content_lower = (title + ' ' + content).lower()
                pos_count = sum(1 for word in positive_words if word in content_lower)
                neg_count = sum(1 for word in negative_words if word in content_lower)
                
                # Calculate article sentiment
                article_sentiment = pos_count - neg_count
                sentiment_score += article_sentiment
                
                # Store news item
                news_data['recent_news'].append({
                    'title': title,
                    'content': content[:300] + '...' if len(content) > 300 else content,
                    'url': url,
                    'sentiment': 'positive' if article_sentiment > 0 else 'negative' if article_sentiment < 0 else 'neutral'
                })
                
                # Track sentiment indicators
                if pos_count > 0:
                    news_data['positive_indicators'].extend([word for word in positive_words if word in content_lower])
                if neg_count > 0:
                    news_data['negative_indicators'].extend([word for word in negative_words if word in content_lower])
            
            news_data['news_count'] = len(news_data['recent_news'])
            news_data['sentiment_score'] = sentiment_score
            
            # Determine overall sentiment
            if sentiment_score > 2:
                news_data['overall_sentiment'] = 'positive'
            elif sentiment_score < -2:
                news_data['overall_sentiment'] = 'negative'
            else:
                news_data['overall_sentiment'] = 'neutral'
                
        except Exception as e:
            self.logger.error(f"Error extracting news sentiment: {str(e)}")
            news_data['error'] = str(e)
            news_data['news_available'] = False
        
        return news_data
    
    def _extract_financial_metrics(self, response: Dict, query: str) -> Dict[str, Any]:
        """Extract financial metrics from search results."""
        financial_data = {
            'revenue': None,
            'profit_margin': None,
            'pe_ratio': None,
            'debt_equity': None,
            'roe': None,
            'growth_rate': None,
            'financial_highlights': [],
            'analysis_available': True
        }
        
        try:
            for result in response.get('results', []):
                content = result.get('content', '')
                
                # Extract financial ratios using regex
                pe_matches = re.findall(r'p/e.*?(\d+(?:\.\d+)?)', content.lower())
                if pe_matches and not financial_data['pe_ratio']:
                    financial_data['pe_ratio'] = float(pe_matches[0])
                
                # Extract revenue figures
                revenue_matches = re.findall(r'revenue.*?₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*crore', content.lower())
                if revenue_matches and not financial_data['revenue']:
                    financial_data['revenue'] = revenue_matches[0].replace(',', '')
                
                # Extract growth rates
                growth_matches = re.findall(r'growth.*?(\d+(?:\.\d+)?)%', content.lower())
                if growth_matches and not financial_data['growth_rate']:
                    financial_data['growth_rate'] = float(growth_matches[0])
                
                # Collect financial highlights
                if any(term in content.lower() for term in ['profit', 'revenue', 'earnings', 'financial']):
                    highlight = content[:200] + '...' if len(content) > 200 else content
                    financial_data['financial_highlights'].append(highlight)
                    
        except Exception as e:
            self.logger.error(f"Error extracting financial metrics: {str(e)}")
            financial_data['error'] = str(e)
            financial_data['analysis_available'] = False
        
        return financial_data
    
    def _extract_sector_info(self, response: Dict, query: str) -> Dict[str, Any]:
        """Extract sector and competitor information."""
        sector_data = {
            'sector': None,
            'industry': None,
            'competitors': [],
            'market_position': None,
            'sector_trends': [],
            'sector_available': True
        }
        
        try:
            for result in response.get('results', []):
                content = result.get('content', '').lower()
                
                # Common Indian sectors
                sectors = ['it', 'banking', 'pharmaceutical', 'automotive', 'energy', 'fmcg', 'telecom', 'metal']
                for sector in sectors:
                    if sector in content and not sector_data['sector']:
                        sector_data['sector'] = sector.upper()
                        break
                
                # Extract sector trends
                if any(term in content for term in ['trend', 'outlook', 'growth', 'future']):
                    trend = content[:150] + '...' if len(content) > 150 else content
                    sector_data['sector_trends'].append(trend)
                    
        except Exception as e:
            self.logger.error(f"Error extracting sector info: {str(e)}")
            sector_data['error'] = str(e)
            sector_data['sector_available'] = False
        
        return sector_data
    
    def _extract_technical_info(self, response: Dict, query: str) -> Dict[str, Any]:
        """Extract technical analysis information."""
        technical_data = {
            'trend': 'neutral',
            'support_level': None,
            'resistance_level': None,
            'moving_averages': {},
            'technical_indicators': [],
            'technical_available': True
        }
        
        try:
            for result in response.get('results', []):
                content = result.get('content', '').lower()
                
                # Extract trend indicators
                if any(term in content for term in ['bullish', 'uptrend', 'rising']):
                    technical_data['trend'] = 'bullish'
                elif any(term in content for term in ['bearish', 'downtrend', 'falling']):
                    technical_data['trend'] = 'bearish'
                
                # Extract technical insights
                if any(term in content for term in ['support', 'resistance', 'technical', 'chart']):
                    insight = content[:150] + '...' if len(content) > 150 else content
                    technical_data['technical_indicators'].append(insight)
                    
        except Exception as e:
            self.logger.error(f"Error extracting technical info: {str(e)}")
            technical_data['error'] = str(e)
            technical_data['technical_available'] = False
        
        return technical_data
    
    def _calculate_overall_confidence(self, basic_info: Dict, news_sentiment: Dict, financial_analysis: Dict, historical_analysis: Dict = None) -> float:
        """Calculate overall confidence score for the search results."""
        confidence = 0.0
        
        try:
            # Basic info confidence (20%)
            if basic_info.get('data_available'):
                confidence += 0.2
            
            # News sentiment confidence (30%)
            if news_sentiment.get('news_available'):
                news_count = news_sentiment.get('news_count', 0)
                confidence += min(0.3, news_count * 0.05)
            
            # Financial analysis confidence (25%)
            if financial_analysis.get('analysis_available'):
                confidence += 0.25
            
            # Historical analysis confidence (25%)
            if historical_analysis and historical_analysis.get('historical_available'):
                confidence += 0.25
            
            return min(1.0, confidence)
            
        except Exception:
            return 0.5
    
    def _suggest_alternative_search(self, query: str) -> str:
        """Suggest alternative search terms when search fails."""
        suggestions = [
            f"Try searching with the stock symbol (e.g., 'RELIANCE' instead of 'Reliance Industries')",
            f"Include 'stock' or 'share' in your search: '{query} stock price'",
            f"Try the company's common name: '{query} NSE BSE'",
            f"Search for recent news: '{query} latest news 2025'"
        ]
        
        return suggestions[hash(query) % len(suggestions)]
    
    def quick_stock_lookup(self, query: str) -> Dict[str, Any]:
        """Quick stock lookup for basic information."""
        try:
            search_query = f"{query} stock symbol NSE BSE current price"
            
            response = self.tavily_client.search(
                query=search_query,
                search_depth="basic",
                max_results=3
            )
            
            return {
                'query': query,
                'results': response.get('results', []),
                'quick_lookup': True,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in quick lookup: {str(e)}")
            return {
                'query': query,
                'error': str(e),
                'quick_lookup': False
            }
