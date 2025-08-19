import boto3
import json
import logging
from typing import List, Dict, Any
from config import Config
from agents.data_collector import DataCollectorAgent
from agents.research_agent import ResearchAgent
from agents.risk_agent import RiskAgent
from agents.intelligent_search_agent import IntelligentSearchAgent
from datetime import datetime

class Orchestrator:
    """Main orchestrator agent that coordinates all other agents and uses Claude Sonnet 3.5 for final recommendations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.bedrock_client = self._init_bedrock_client()
        self.data_collector = DataCollectorAgent()
        self.research_agent = ResearchAgent()
        self.risk_agent = RiskAgent()
        self.intelligent_search = IntelligentSearchAgent()
    
    def _init_bedrock_client(self):
        """Initialize AWS Bedrock client."""
        try:
            return boto3.client(
                'bedrock-runtime',
                aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
                region_name=Config.AWS_REGION
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise
    
    def analyze_portfolio(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Main analysis pipeline that coordinates all agents and generates recommendations.
        
        Args:
            symbols: List of stock symbols to analyze
            
        Returns:
            List of recommendation dictionaries
        """
        try:
            self.logger.info(f"Starting portfolio analysis for: {symbols}")
            
            # Collect data from all agents
            stock_data = self._collect_stock_data(symbols)
            news_data = self._collect_news_data(symbols)
            risk_data = self._collect_risk_data(symbols)
            
            # Generate recommendations using Claude Sonnet 3.5
            recommendations = self._generate_recommendations(stock_data, news_data, risk_data)
            
            self.logger.info(f"Generated {len(recommendations)} recommendations")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Portfolio analysis failed: {str(e)}")
            raise
    
    def _collect_stock_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Collect stock data for all symbols."""
        try:
            stock_data = {}
            for symbol in symbols:
                data = self.data_collector.get_stock_data(symbol)
                if data:
                    stock_data[symbol] = data
                    self.logger.info(f"Collected data for {symbol}")
            return stock_data
        except Exception as e:
            self.logger.error(f"Failed to collect stock data: {str(e)}")
            return {}
    
    def _collect_news_data(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Collect news data related to symbols."""
        try:
            news_data = self.research_agent.get_market_news()
            # Filter news relevant to our symbols
            relevant_news = []
            for news_item in news_data:
                if any(symbol.lower() in news_item.get('title', '').lower() or 
                      symbol.lower() in news_item.get('content', '').lower() 
                      for symbol in symbols):
                    relevant_news.append(news_item)
            
            self.logger.info(f"Collected {len(relevant_news)} relevant news items")
            return relevant_news
        except Exception as e:
            self.logger.error(f"Failed to collect news data: {str(e)}")
            return []
    
    def _collect_risk_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Collect risk analysis data for all symbols."""
        try:
            risk_data = {}
            for symbol in symbols:
                risk_metrics = self.risk_agent.analyze_volatility(symbol)
                if risk_metrics:
                    risk_data[symbol] = risk_metrics
                    self.logger.info(f"Collected risk data for {symbol}")
            return risk_data
        except Exception as e:
            self.logger.error(f"Failed to collect risk data: {str(e)}")
            return {}
    
    def _generate_recommendations(self, stock_data: Dict, news_data: List, risk_data: Dict) -> List[Dict[str, Any]]:
        """Generate recommendations using Claude Sonnet 3.5 via AWS Bedrock."""
        try:
            # Prepare input data for Claude
            analysis_input = {
                "stock_data": stock_data,
                "news_data": news_data,
                "risk_data": risk_data,
                "timestamp": str(boto3.Session().region_name)
            }
            
            # Create prompt for Claude
            prompt = self._create_analysis_prompt(analysis_input)
            
            # Call Claude Sonnet 3.5 via Bedrock
            response = self._call_claude(prompt)
            
            # Parse and validate response
            recommendations = self._parse_claude_response(response)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {str(e)}")
            # Return fallback recommendations
            return self._generate_fallback_recommendations(stock_data)
    
    def _create_analysis_prompt(self, analysis_input: Dict) -> str:
        """Create a comprehensive prompt for Claude analysis."""
        prompt = f"""
You are an expert stock market analyst. Analyze the following data and provide investment recommendations.

STOCK DATA:
{json.dumps(analysis_input.get('stock_data', {}), indent=2)}

NEWS DATA:
{json.dumps(analysis_input.get('news_data', []), indent=2)}

RISK DATA:
{json.dumps(analysis_input.get('risk_data', {}), indent=2)}

Please provide recommendations in the following JSON format for each stock:
{{
    "recommendations": [
        {{
            "symbol": "SYMBOL",
            "action": "BUY|SELL|HOLD",
            "reasoning": "Detailed explanation of the recommendation",
            "confidence": 0.8,
            "target_price": 1000.0,
            "risk_level": "LOW|MEDIUM|HIGH",
            "time_horizon": "SHORT|MEDIUM|LONG"
        }}
    ]
}}

Consider the following factors:
1. Current stock price trends and technical indicators
2. Market sentiment from news analysis
3. Volatility and risk metrics
4. Overall market conditions
5. Company fundamentals (if available)

Provide clear, actionable recommendations with confidence scores between 0.0 and 1.0.
"""
        return prompt
    
    def _call_claude(self, prompt: str) -> str:
        """Call Claude Sonnet 3.5 via AWS Bedrock."""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=Config.MODEL_ID,
                body=json.dumps(body),
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            return response_body.get('content', [{}])[0].get('text', '')
            
        except Exception as e:
            self.logger.error(f"Claude API call failed: {str(e)}")
            raise
    
    def _parse_claude_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse Claude's response and extract recommendations."""
        try:
            # Find JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[start_idx:end_idx]
            parsed_response = json.loads(json_str)
            
            recommendations = parsed_response.get('recommendations', [])
            
            # Validate and clean recommendations
            valid_recommendations = []
            for rec in recommendations:
                if self._validate_recommendation(rec):
                    valid_recommendations.append(rec)
            
            return valid_recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to parse Claude response: {str(e)}")
            self.logger.error(f"Raw response: {response}")
            raise
    
    def _validate_recommendation(self, recommendation: Dict) -> bool:
        """Validate a single recommendation."""
        required_fields = ['symbol', 'action', 'reasoning']
        
        for field in required_fields:
            if field not in recommendation:
                return False
        
        # Validate action
        valid_actions = ['BUY', 'SELL', 'HOLD']
        if recommendation['action'] not in valid_actions:
            return False
        
        # Validate confidence if present
        if 'confidence' in recommendation:
            confidence = recommendation['confidence']
            if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                recommendation['confidence'] = 0.5
        
        return True
    
    def _generate_fallback_recommendations(self, stock_data: Dict) -> List[Dict[str, Any]]:
        """Generate basic fallback recommendations when Claude fails."""
        recommendations = []
        
        for symbol, data in stock_data.items():
            # Simple logic based on price change
            change_percent = data.get('change_percent', 0)
            current_price = data.get('current_price', 0)
            volume = data.get('volume', 0)
            
            # Determine action based on price movement
            if change_percent > 2:
                action = "BUY"
                reasoning = f"{symbol} shows positive price momentum with a {change_percent:.2f}% increase today and trading near its daily high."
                confidence = min(0.6, 0.3 + (change_percent / 10))
            elif change_percent < -2:
                action = "SELL"
                reasoning = f"{symbol} shows negative price momentum with a {change_percent:.2f}% decline today, indicating potential weakness."
                confidence = min(0.6, 0.3 + (abs(change_percent) / 10))
            else:
                action = "HOLD"
                reasoning = f"{symbol} shows neutral price movement with {change_percent:.2f}% change, suggesting consolidation phase."
                confidence = 0.4
            
            # Determine risk level based on volatility proxy
            if abs(change_percent) > 5:
                risk_level = "HIGH"
            elif abs(change_percent) > 2:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            # Create enhanced metadata
            metadata = {
                "current_price": current_price,
                "price_change": data.get('change', 0),
                "price_change_percent": change_percent,
                "volume": volume,
                "risk_level": risk_level,
                "volatility": abs(change_percent) / 100,  # Simple volatility proxy
                "company_name": data.get('company_name', symbol),
                "sector": data.get('sector', 'Unknown'),
                "analysis_type": "Fallback Analysis"
            }
            
            recommendations.append({
                "symbol": symbol,
                "action": action,
                "reasoning": reasoning,
                "confidence": confidence,
                "risk_level": risk_level,
                "time_horizon": "SHORT",
                "metadata": metadata
            })
        
        self.logger.warning("Using fallback recommendations due to Claude failure")
        return recommendations
    
    def analyze_stock_deep(self, query: str) -> Dict[str, Any]:
        """
        Perform deep analysis of a stock using Tavily search and Claude analysis.
        
        Args:
            query: Stock name, symbol, or description
            
        Returns:
            Comprehensive analysis with recommendations
        """
        try:
            self.logger.info(f"Starting deep analysis for: {query}")
            
            # Step 1: Use Tavily for comprehensive search
            search_results = self.intelligent_search.search_stock_comprehensive(query)
            
            if not search_results.get('search_success'):
                self.logger.warning(f"Tavily search failed for {query}")
                return self._generate_fallback_deep_analysis(query, search_results.get('error'))
            
            # Step 2: Extract key information for Claude analysis
            analysis_data = self._prepare_deep_analysis_data(search_results)
            
            # Step 3: Use Claude for sophisticated analysis
            claude_analysis = self._get_claude_deep_analysis(analysis_data)
            
            # Step 4: Combine Tavily search with Claude insights
            deep_analysis = {
                'query': query,
                'timestamp': datetime.now().isoformat(),
                'search_results': search_results,
                'claude_analysis': claude_analysis,
                'comprehensive_recommendation': self._generate_comprehensive_recommendation(
                    search_results, claude_analysis
                ),
                'analysis_type': 'deep_tavily_claude',
                'confidence_score': search_results.get('recommendation_confidence', 0.5),
                'data_sources': ['tavily_api', 'claude_sonnet_3.5', 'web_search']
            }
            
            self.logger.info(f"Deep analysis completed for {query}")
            return deep_analysis
            
        except Exception as e:
            self.logger.error(f"Error in deep stock analysis: {str(e)}")
            return self._generate_fallback_deep_analysis(query, str(e))
    
    def _prepare_deep_analysis_data(self, search_results: Dict) -> Dict[str, Any]:
        """Prepare data from Tavily search for Claude analysis."""
        try:
            basic_info = search_results.get('basic_info', {})
            news_sentiment = search_results.get('news_sentiment', {})
            financial_analysis = search_results.get('financial_analysis', {})
            sector_analysis = search_results.get('sector_analysis', {})
            technical_analysis = search_results.get('technical_analysis', {})
            historical_analysis = search_results.get('historical_analysis', {})
            analyst_reports = search_results.get('analyst_reports', {})
            
            analysis_data = {
                'company_name': basic_info.get('company_name', 'Unknown'),
                'ticker_symbol': basic_info.get('ticker_symbol', 'Unknown'),
                'sector': basic_info.get('sector') or sector_analysis.get('sector', 'Unknown'),
                'current_price': basic_info.get('current_price'),
                'market_cap': basic_info.get('market_cap'),
                
                # Financial metrics
                'financial_metrics': {
                    'pe_ratio': financial_analysis.get('pe_ratio'),
                    'revenue': financial_analysis.get('revenue'),
                    'growth_rate': financial_analysis.get('growth_rate'),
                    'profit_margin': financial_analysis.get('profit_margin')
                },
                
                # Historical performance
                'historical_performance': {
                    'performance_periods': historical_analysis.get('performance_periods', {}),
                    'volatility_assessment': historical_analysis.get('volatility_assessment', 'medium'),
                    'long_term_trend': historical_analysis.get('long_term_trend', 'neutral'),
                    'key_events': historical_analysis.get('key_events', [])[:3]
                },
                
                # Market sentiment
                'market_sentiment': {
                    'overall_sentiment': news_sentiment.get('overall_sentiment', 'neutral'),
                    'sentiment_score': news_sentiment.get('sentiment_score', 0),
                    'news_count': news_sentiment.get('news_count', 0),
                    'positive_indicators': news_sentiment.get('positive_indicators', []),
                    'negative_indicators': news_sentiment.get('negative_indicators', [])
                },
                
                # Analyst recommendations
                'analyst_consensus': {
                    'consensus_rating': analyst_reports.get('consensus_rating', 'neutral'),
                    'target_prices': analyst_reports.get('target_prices', [])[:3],
                    'rating_distribution': analyst_reports.get('rating_distribution', {})
                },
                
                # Technical indicators
                'technical_indicators': {
                    'trend': technical_analysis.get('trend', 'neutral'),
                    'support_level': technical_analysis.get('support_level'),
                    'resistance_level': technical_analysis.get('resistance_level')
                },
                
                # Recent news highlights
                'recent_news': news_sentiment.get('recent_news', [])[:3],  # Top 3 news items
                
                # Financial highlights
                'financial_highlights': financial_analysis.get('financial_highlights', [])[:2]
            }
            
            return analysis_data
            
        except Exception as e:
            self.logger.error(f"Error preparing analysis data: {str(e)}")
            return {'error': str(e)}
    
    def _get_claude_deep_analysis(self, analysis_data: Dict) -> Dict[str, Any]:
        """Get sophisticated analysis from Claude Sonnet 3.5."""
        try:
            prompt = f"""
You are a senior financial analyst providing comprehensive stock analysis. Analyze the following data and provide detailed, actionable insights:

COMPANY INFORMATION:
- Company: {analysis_data.get('company_name')}
- Symbol: {analysis_data.get('ticker_symbol')}
- Sector: {analysis_data.get('sector')}
- Current Price: ₹{analysis_data.get('current_price', 'N/A')}

FINANCIAL METRICS:
- P/E Ratio: {analysis_data.get('financial_metrics', {}).get('pe_ratio', 'N/A')}
- Revenue: ₹{analysis_data.get('financial_metrics', {}).get('revenue', 'N/A')} Cr
- Growth Rate: {analysis_data.get('financial_metrics', {}).get('growth_rate', 'N/A')}%
- Profit Margin: {analysis_data.get('financial_metrics', {}).get('profit_margin', 'N/A')}%

HISTORICAL PERFORMANCE:
- Performance Periods: {json.dumps(analysis_data.get('historical_performance', {}).get('performance_periods', {}), indent=2)}
- Volatility Assessment: {analysis_data.get('historical_performance', {}).get('volatility_assessment', 'medium')}
- Long-term Trend: {analysis_data.get('historical_performance', {}).get('long_term_trend', 'neutral')}
- Key Historical Events: {json.dumps(analysis_data.get('historical_performance', {}).get('key_events', []), indent=2)}

ANALYST CONSENSUS:
- Consensus Rating: {analysis_data.get('analyst_consensus', {}).get('consensus_rating', 'neutral')}
- Target Prices: {json.dumps(analysis_data.get('analyst_consensus', {}).get('target_prices', []), indent=2)}
- Rating Distribution: {json.dumps(analysis_data.get('analyst_consensus', {}).get('rating_distribution', {}), indent=2)}

MARKET SENTIMENT:
- Overall Sentiment: {analysis_data.get('market_sentiment', {}).get('overall_sentiment')}
- News Count: {analysis_data.get('market_sentiment', {}).get('news_count')}
- Sentiment Score: {analysis_data.get('market_sentiment', {}).get('sentiment_score')}
- Positive Indicators: {', '.join(analysis_data.get('market_sentiment', {}).get('positive_indicators', [])[:5])}
- Negative Indicators: {', '.join(analysis_data.get('market_sentiment', {}).get('negative_indicators', [])[:5])}

TECHNICAL ANALYSIS:
- Current Trend: {analysis_data.get('technical_indicators', {}).get('trend')}
- Support Level: {analysis_data.get('technical_indicators', {}).get('support_level', 'N/A')}
- Resistance Level: {analysis_data.get('technical_indicators', {}).get('resistance_level', 'N/A')}

RECENT NEWS ANALYSIS:
{json.dumps(analysis_data.get('recent_news', []), indent=2)}

FINANCIAL HIGHLIGHTS:
{json.dumps(analysis_data.get('financial_highlights', []), indent=2)}

Based on this comprehensive analysis, provide a structured investment recommendation with the following format:

{{
    "investment_decision": "BUY/HOLD/SELL",
    "confidence_percentage": 85,
    "risk_level": "LOW/MEDIUM/HIGH",
    "investment_horizon": {{
        "short_term": "1-3 months",
        "medium_term": "6-12 months", 
        "long_term": "1-3 years"
    }},
    "price_targets": {{
        "current_price": 45.20,
        "target_3_months": 52.00,
        "target_6_months": 58.00,
        "target_1_year": 65.00,
        "stop_loss": 38.00
    }},
    "investment_thesis": {{
        "bull_case": ["Point 1", "Point 2", "Point 3"],
        "bear_case": ["Risk 1", "Risk 2", "Risk 3"],
        "neutral_factors": ["Factor 1", "Factor 2"]
    }},
    "action_plan": {{
        "immediate_action": "What to do now",
        "hold_strategy": "When and why to hold",
        "exit_strategy": "When and how to sell",
        "portfolio_allocation": "5-10% of portfolio"
    }},
    "key_catalysts": {{
        "positive_catalysts": ["Catalyst 1", "Catalyst 2"],
        "negative_risks": ["Risk 1", "Risk 2"],
        "upcoming_events": ["Event 1", "Event 2"]
    }},
    "detailed_reasoning": "Comprehensive 3-4 paragraph analysis explaining the recommendation",
    "monitor_metrics": ["Key metrics to track"],
    "review_frequency": "Weekly/Monthly",
    "last_updated": "2025-08-20"
}}

Provide specific, actionable advice with clear price targets and timeframes. Consider both fundamental and technical analysis, market sentiment, sector trends, historical performance patterns, and analyst consensus.
"""

            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 3000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            response = self.bedrock_client.invoke_model(
                body=json.dumps(body),
                modelId=Config.MODEL_ID,
                contentType='application/json',
                accept='application/json'
            )

            response_body = json.loads(response['body'].read())
            claude_response = response_body['content'][0]['text']
            
            # Try to parse as JSON, fallback to text parsing
            try:
                analysis = json.loads(claude_response)
                # Ensure all required fields are present
                analysis = self._validate_and_enhance_analysis(analysis)
            except json.JSONDecodeError:
                analysis = self._parse_claude_structured_response(claude_response)
            
            return analysis

        except Exception as e:
            self.logger.error(f"Error getting Claude analysis: {str(e)}")
            return self._generate_fallback_structured_analysis(analysis_data)
    
    def _validate_and_enhance_analysis(self, analysis: Dict) -> Dict:
        """Validate and enhance the Claude analysis with defaults."""
        default_analysis = {
            "investment_decision": "HOLD",
            "confidence_percentage": 50,
            "risk_level": "MEDIUM",
            "investment_horizon": {
                "short_term": "1-3 months",
                "medium_term": "6-12 months", 
                "long_term": "1-3 years"
            },
            "price_targets": {
                "current_price": 0.0,
                "target_3_months": 0.0,
                "target_6_months": 0.0,
                "target_1_year": 0.0,
                "stop_loss": 0.0
            },
            "investment_thesis": {
                "bull_case": ["Analysis in progress"],
                "bear_case": ["Analysis in progress"],
                "neutral_factors": ["Market conditions"]
            },
            "action_plan": {
                "immediate_action": "Monitor market conditions",
                "hold_strategy": "Maintain position with regular review",
                "exit_strategy": "Exit if fundamentals change",
                "portfolio_allocation": "3-5% of portfolio"
            },
            "key_catalysts": {
                "positive_catalysts": ["Market recovery"],
                "negative_risks": ["Market volatility"],
                "upcoming_events": ["Quarterly results"]
            },
            "detailed_reasoning": "Analysis based on available data",
            "monitor_metrics": ["Price", "Volume", "News"],
            "review_frequency": "Monthly",
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        }
        
        # Merge with defaults for missing fields
        for key, default_value in default_analysis.items():
            if key not in analysis:
                analysis[key] = default_value
            elif isinstance(default_value, dict) and isinstance(analysis[key], dict):
                for sub_key, sub_default in default_value.items():
                    if sub_key not in analysis[key]:
                        analysis[key][sub_key] = sub_default
        
        return analysis
    
    def _parse_claude_structured_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude response when JSON parsing fails."""
        analysis = {
            "investment_decision": "HOLD",
            "confidence_percentage": 50,
            "risk_level": "MEDIUM",
            "detailed_reasoning": response_text,
        }
        
        text_lower = response_text.lower()
        
        # Extract investment decision
        if 'strong buy' in text_lower or 'buy' in text_lower:
            analysis['investment_decision'] = 'BUY'
        elif 'sell' in text_lower:
            analysis['investment_decision'] = 'SELL'
            
        # Extract confidence
        import re
        confidence_match = re.search(r'confidence.*?(\d+)%?', text_lower)
        if confidence_match:
            analysis['confidence_percentage'] = int(confidence_match.group(1))
            
        # Extract risk level
        if 'high risk' in text_lower:
            analysis['risk_level'] = 'HIGH'
        elif 'low risk' in text_lower:
            analysis['risk_level'] = 'LOW'
        
        # Add default structured fields
        return self._validate_and_enhance_analysis(analysis)
    
    def _generate_fallback_structured_analysis(self, analysis_data: Dict) -> Dict[str, Any]:
        """Generate fallback structured analysis when Claude fails."""
        current_price = analysis_data.get('current_price', 50.0)
        if isinstance(current_price, str):
            try:
                current_price = float(current_price.replace(',', ''))
            except:
                current_price = 50.0
        
        return {
            "investment_decision": "HOLD",
            "confidence_percentage": 40,
            "risk_level": "MEDIUM",
            "investment_horizon": {
                "short_term": "1-3 months",
                "medium_term": "6-12 months", 
                "long_term": "1-3 years"
            },
            "price_targets": {
                "current_price": current_price,
                "target_3_months": current_price * 1.10,
                "target_6_months": current_price * 1.15,
                "target_1_year": current_price * 1.20,
                "stop_loss": current_price * 0.85
            },
            "investment_thesis": {
                "bull_case": ["Market conditions improving", "Sector fundamentals stable"],
                "bear_case": ["Market volatility", "Sector headwinds"],
                "neutral_factors": ["Mixed signals from analysis"]
            },
            "action_plan": {
                "immediate_action": "Monitor price action and volume",
                "hold_strategy": "Hold if price stays above support levels",
                "exit_strategy": "Consider exit if stops loss is hit",
                "portfolio_allocation": "3-5% of portfolio"
            },
            "key_catalysts": {
                "positive_catalysts": ["Earnings improvement", "Sector recovery"],
                "negative_risks": ["Market correction", "Company-specific risks"],
                "upcoming_events": ["Quarterly results", "Sector news"]
            },
            "detailed_reasoning": f"Fallback analysis for {analysis_data.get('company_name', 'the company')}. Limited data available for comprehensive analysis. Recommend careful monitoring of market conditions and company fundamentals.",
            "monitor_metrics": ["Stock price", "Trading volume", "News sentiment", "Sector performance"],
            "review_frequency": "Weekly",
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        }
    
    def _parse_claude_text_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude response when JSON parsing fails."""
        analysis = {
            'recommendation': 'HOLD',
            'confidence': 50,
            'risk_level': 'MEDIUM',
            'reasoning': response_text,
            'key_strengths': [],
            'key_risks': [],
            'time_horizon': 'MEDIUM'
        }
        
        text_lower = response_text.lower()
        
        # Extract recommendation
        if 'buy' in text_lower:
            analysis['recommendation'] = 'BUY'
        elif 'sell' in text_lower:
            analysis['recommendation'] = 'SELL'
            
        # Extract confidence
        import re
        confidence_match = re.search(r'confidence.*?(\d+)%?', text_lower)
        if confidence_match:
            analysis['confidence'] = int(confidence_match.group(1))
            
        # Extract risk level
        if 'high risk' in text_lower:
            analysis['risk_level'] = 'HIGH'
        elif 'low risk' in text_lower:
            analysis['risk_level'] = 'LOW'
            
        return analysis
    
    def _generate_comprehensive_recommendation(self, search_results: Dict, claude_analysis: Dict) -> Dict[str, Any]:
        """Generate final comprehensive recommendation combining all data."""
        try:
            # Get basic info
            basic_info = search_results.get('basic_info', {})
            news_sentiment = search_results.get('news_sentiment', {})
            
            # Combine Claude recommendation with search data
            recommendation = {
                'symbol': basic_info.get('ticker_symbol', 'Unknown'),
                'company_name': basic_info.get('company_name', 'Unknown'),
                'action': claude_analysis.get('recommendation', 'HOLD'),
                'confidence': claude_analysis.get('confidence', 50) / 100,
                'risk_level': claude_analysis.get('risk_level', 'MEDIUM'),
                'time_horizon': claude_analysis.get('time_horizon', 'MEDIUM'),
                'price_target': claude_analysis.get('price_target'),
                
                # Enhanced reasoning combining all sources
                'reasoning': self._create_enhanced_reasoning(search_results, claude_analysis),
                
                # Metadata with comprehensive information
                'metadata': {
                    'current_price': basic_info.get('current_price'),
                    'sector': basic_info.get('sector'),
                    'market_sentiment': news_sentiment.get('overall_sentiment'),
                    'news_count': news_sentiment.get('news_count', 0),
                    'analysis_depth': 'comprehensive',
                    'data_sources': ['tavily_search', 'claude_analysis'],
                    'key_strengths': claude_analysis.get('key_strengths', []),
                    'key_risks': claude_analysis.get('key_risks', []),
                    'financial_highlights': search_results.get('financial_analysis', {}).get('financial_highlights', [])
                },
                
                'timestamp': datetime.now().isoformat()
            }
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive recommendation: {str(e)}")
            return {
                'symbol': 'Unknown',
                'action': 'HOLD',
                'confidence': 0.5,
                'reasoning': f"Error generating recommendation: {str(e)}",
                'metadata': {'error': str(e)}
            }
    
    def _create_enhanced_reasoning(self, search_results: Dict, claude_analysis: Dict) -> str:
        """Create enhanced reasoning combining Tavily search and Claude analysis."""
        try:
            basic_info = search_results.get('basic_info', {})
            news_sentiment = search_results.get('news_sentiment', {})
            claude_reasoning = claude_analysis.get('reasoning', '')
            
            company_name = basic_info.get('company_name', 'the company')
            sentiment = news_sentiment.get('overall_sentiment', 'neutral')
            news_count = news_sentiment.get('news_count', 0)
            
            enhanced_reasoning = f"""
COMPREHENSIVE ANALYSIS FOR {company_name.upper()}:

CLAUDE AI ASSESSMENT: {claude_reasoning}

MARKET INTELLIGENCE: Based on {news_count} recent news articles, market sentiment is {sentiment}. 
"""
            
            # Add sentiment details
            if news_sentiment.get('positive_indicators'):
                enhanced_reasoning += f"Positive indicators include: {', '.join(news_sentiment['positive_indicators'][:3])}. "
            
            if news_sentiment.get('negative_indicators'):
                enhanced_reasoning += f"Risk factors include: {', '.join(news_sentiment['negative_indicators'][:3])}. "
            
            # Add financial highlights
            financial_highlights = search_results.get('financial_analysis', {}).get('financial_highlights', [])
            if financial_highlights:
                enhanced_reasoning += f"\n\nFINANCIAL INSIGHTS: {financial_highlights[0][:200]}..."
            
            # Add technical analysis
            technical_trend = search_results.get('technical_analysis', {}).get('trend', 'neutral')
            enhanced_reasoning += f"\n\nTECHNICAL OUTLOOK: Current trend is {technical_trend}."
            
            enhanced_reasoning += f"\n\nRECOMMENDATION CONFIDENCE: {claude_analysis.get('confidence', 50)}% based on comprehensive multi-source analysis."
            
            return enhanced_reasoning.strip()
            
        except Exception as e:
            return f"Enhanced analysis failed: {str(e)}"
    
    def _generate_fallback_deep_analysis(self, query: str, error: str) -> Dict[str, Any]:
        """Generate fallback analysis when Tavily search fails."""
        return {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'error': error,
            'analysis_type': 'fallback',
            'comprehensive_recommendation': {
                'symbol': query.upper(),
                'action': 'HOLD',
                'confidence': 0.3,
                'reasoning': f"Deep analysis unavailable for {query}. Error: {error}. Please try with a different stock symbol or company name.",
                'metadata': {
                    'analysis_depth': 'fallback',
                    'error': error,
                    'suggestion': 'Try searching with exact stock symbol (e.g., RELIANCE, TCS, INFY)'
                }
            },
            'search_success': False
        }
