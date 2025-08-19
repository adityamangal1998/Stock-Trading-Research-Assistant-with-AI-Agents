import requests
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from config import Config
import yfinance as yf

class RiskAgent:
    """Agent responsible for analyzing volatility and risk metrics using MCP SQL/DB server."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mcp_url = f"http://localhost:{Config.MCP_DB_PORT}"
        self.session = requests.Session()
    
    def analyze_volatility(self, symbol: str, period: str = "1mo") -> Optional[Dict[str, Any]]:
        """
        Analyze volatility and risk metrics for a given symbol.
        
        Args:
            symbol: Stock symbol to analyze
            period: Time period for analysis (1mo, 3mo, 6mo, 1y)
            
        Returns:
            Dictionary containing risk metrics or None if failed
        """
        try:
            self.logger.info(f"Analyzing volatility for {symbol}")
            
            # Try MCP DB server first
            mcp_risk = self._get_risk_from_mcp(symbol, period)
            if mcp_risk:
                return mcp_risk
            
            # Fallback to direct calculation
            return self._calculate_risk_metrics(symbol, period)
            
        except Exception as e:
            self.logger.error(f"Error analyzing volatility for {symbol}: {str(e)}")
            return None
    
    def _get_risk_from_mcp(self, symbol: str, period: str) -> Optional[Dict[str, Any]]:
        """Get risk metrics from MCP DB server."""
        try:
            response = self.session.post(
                self.mcp_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "analyze_risk",
                    "params": {"symbol": symbol, "period": period}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    return data['result']
            
            return None
            
        except Exception as e:
            self.logger.warning(f"MCP DB server call failed for {symbol}: {str(e)}")
            return None
    
    def _calculate_risk_metrics(self, symbol: str, period: str) -> Optional[Dict[str, Any]]:
        """Calculate risk metrics directly using historical data."""
        try:
            # Get historical data
            historical_data = self._get_historical_data(symbol, period)
            if not historical_data:
                return None
            
            df = pd.DataFrame(historical_data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # Calculate daily returns
            df['returns'] = df['close'].pct_change()
            daily_returns = df['returns'].dropna()
            
            if len(daily_returns) < 10:  # Need sufficient data
                return None
            
            # Calculate risk metrics
            risk_metrics = self._compute_risk_metrics(daily_returns, df['close'])
            
            # Add metadata
            risk_metrics.update({
                'symbol': symbol,
                'period': period,
                'data_points': len(daily_returns),
                'start_date': df.index[0].isoformat(),
                'end_date': df.index[-1].isoformat(),
                'analysis_timestamp': datetime.now().isoformat()
            })
            
            return risk_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics for {symbol}: {str(e)}")
            return None
    
    def _get_historical_data(self, symbol: str, period: str) -> Optional[List[Dict]]:
        """Get historical price data."""
        try:
            # Try with .NS suffix first (NSE)
            yf_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                # Try with .BO suffix (BSE)
                yf_symbol = f"{symbol}.BO"
                ticker = yf.Ticker(yf_symbol)
                hist = ticker.history(period=period)
            
            if not hist.empty:
                return [
                    {
                        'date': str(date.date()),
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'close': float(row['Close']),
                        'volume': int(row['Volume'])
                    }
                    for date, row in hist.iterrows()
                ]
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to get historical data for {symbol}: {str(e)}")
            return None
    
    def _compute_risk_metrics(self, returns: pd.Series, prices: pd.Series) -> Dict[str, Any]:
        """Compute comprehensive risk metrics."""
        try:
            # Basic statistics
            mean_return = float(returns.mean())
            std_return = float(returns.std())
            
            # Volatility (annualized)
            volatility = float(std_return * np.sqrt(252))  # 252 trading days
            
            # Value at Risk (VaR) at 95% confidence
            var_95 = float(np.percentile(returns, 5))
            var_99 = float(np.percentile(returns, 1))
            
            # Conditional Value at Risk (CVaR)
            cvar_95 = float(returns[returns <= var_95].mean())
            cvar_99 = float(returns[returns <= var_99].mean())
            
            # Maximum Drawdown
            cumulative_returns = (1 + returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = float(drawdowns.min())
            
            # Sharpe Ratio (assuming risk-free rate of 6% for India)
            risk_free_rate = 0.06 / 252  # Daily risk-free rate
            excess_returns = returns - risk_free_rate
            sharpe_ratio = float(excess_returns.mean() / excess_returns.std()) if excess_returns.std() != 0 else 0
            
            # Beta calculation (using NIFTY as market proxy)
            beta = self._calculate_beta(returns)
            
            # Price-based metrics
            current_price = float(prices.iloc[-1])
            price_52w_high = float(prices.max())
            price_52w_low = float(prices.min())
            
            # Risk classification
            risk_level = self._classify_risk_level(volatility, max_drawdown, var_95)
            
            return {
                'volatility': round(volatility, 4),
                'var_95': round(var_95, 4),
                'var_99': round(var_99, 4),
                'cvar_95': round(cvar_95, 4),
                'cvar_99': round(cvar_99, 4),
                'max_drawdown': round(max_drawdown, 4),
                'sharpe_ratio': round(sharpe_ratio, 4),
                'beta': round(beta, 4) if beta else None,
                'mean_return': round(mean_return, 4),
                'std_return': round(std_return, 4),
                'current_price': current_price,
                'price_52w_high': price_52w_high,
                'price_52w_low': price_52w_low,
                'price_position': round((current_price - price_52w_low) / (price_52w_high - price_52w_low), 4),
                'risk_level': risk_level,
                'upside_potential': round((price_52w_high - current_price) / current_price, 4),
                'downside_risk': round((current_price - price_52w_low) / current_price, 4)
            }
            
        except Exception as e:
            self.logger.error(f"Error computing risk metrics: {str(e)}")
            return {}
    
    def _calculate_beta(self, stock_returns: pd.Series) -> Optional[float]:
        """Calculate beta relative to market (NIFTY)."""
        try:
            # Get NIFTY data for the same period
            nifty_ticker = yf.Ticker("^NSEI")
            nifty_hist = nifty_ticker.history(period="1mo")
            
            if nifty_hist.empty:
                return None
            
            nifty_returns = nifty_hist['Close'].pct_change().dropna()
            
            # Align dates
            common_dates = stock_returns.index.intersection(nifty_returns.index)
            
            if len(common_dates) < 10:
                return None
            
            stock_aligned = stock_returns.loc[common_dates]
            market_aligned = nifty_returns.loc[common_dates]
            
            # Calculate beta
            covariance = np.cov(stock_aligned, market_aligned)[0][1]
            market_variance = np.var(market_aligned)
            
            if market_variance != 0:
                beta = covariance / market_variance
                return float(beta)
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate beta: {str(e)}")
            return None
    
    def _classify_risk_level(self, volatility: float, max_drawdown: float, var_95: float) -> str:
        """Classify risk level based on metrics."""
        try:
            # Define thresholds
            high_vol_threshold = 0.3
            high_drawdown_threshold = -0.2
            high_var_threshold = -0.03
            
            medium_vol_threshold = 0.2
            medium_drawdown_threshold = -0.1
            medium_var_threshold = -0.02
            
            # Count high risk indicators
            high_risk_count = 0
            if volatility > high_vol_threshold:
                high_risk_count += 1
            if max_drawdown < high_drawdown_threshold:
                high_risk_count += 1
            if var_95 < high_var_threshold:
                high_risk_count += 1
            
            # Count medium risk indicators
            medium_risk_count = 0
            if medium_vol_threshold < volatility <= high_vol_threshold:
                medium_risk_count += 1
            if medium_drawdown_threshold < max_drawdown <= high_drawdown_threshold:
                medium_risk_count += 1
            if medium_var_threshold < var_95 <= high_var_threshold:
                medium_risk_count += 1
            
            # Classify
            if high_risk_count >= 2:
                return "HIGH"
            elif high_risk_count >= 1 or medium_risk_count >= 2:
                return "MEDIUM"
            else:
                return "LOW"
                
        except Exception as e:
            self.logger.warning(f"Error classifying risk level: {str(e)}")
            return "MEDIUM"
    
    def analyze_portfolio_risk(self, symbols: List[str], weights: Optional[List[float]] = None) -> Dict[str, Any]:
        """Analyze risk for a portfolio of stocks."""
        try:
            if weights is None:
                weights = [1.0 / len(symbols)] * len(symbols)
            
            if len(weights) != len(symbols):
                raise ValueError("Weights must match number of symbols")
            
            # Get individual risk metrics
            individual_risks = {}
            for symbol in symbols:
                risk_data = self.analyze_volatility(symbol)
                if risk_data:
                    individual_risks[symbol] = risk_data
            
            if not individual_risks:
                return {}
            
            # Calculate portfolio metrics
            portfolio_volatility = self._calculate_portfolio_volatility(symbols, weights)
            
            # Weighted average of individual metrics
            weighted_beta = sum(
                individual_risks[symbol].get('beta', 1.0) * weight
                for symbol, weight in zip(symbols, weights)
                if symbol in individual_risks and individual_risks[symbol].get('beta')
            )
            
            weighted_sharpe = sum(
                individual_risks[symbol].get('sharpe_ratio', 0.0) * weight
                for symbol, weight in zip(symbols, weights)
                if symbol in individual_risks
            )
            
            # Risk level distribution
            risk_levels = [
                individual_risks[symbol].get('risk_level', 'MEDIUM')
                for symbol in symbols if symbol in individual_risks
            ]
            
            risk_distribution = {
                'HIGH': risk_levels.count('HIGH'),
                'MEDIUM': risk_levels.count('MEDIUM'),
                'LOW': risk_levels.count('LOW')
            }
            
            # Overall portfolio risk level
            if risk_distribution['HIGH'] > len(symbols) * 0.3:
                portfolio_risk_level = 'HIGH'
            elif risk_distribution['HIGH'] > 0 or risk_distribution['MEDIUM'] > len(symbols) * 0.5:
                portfolio_risk_level = 'MEDIUM'
            else:
                portfolio_risk_level = 'LOW'
            
            return {
                'portfolio_volatility': round(portfolio_volatility, 4) if portfolio_volatility else None,
                'weighted_beta': round(weighted_beta, 4),
                'weighted_sharpe_ratio': round(weighted_sharpe, 4),
                'portfolio_risk_level': portfolio_risk_level,
                'risk_distribution': risk_distribution,
                'individual_risks': individual_risks,
                'symbols': symbols,
                'weights': weights,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing portfolio risk: {str(e)}")
            return {}
    
    def _calculate_portfolio_volatility(self, symbols: List[str], weights: List[float]) -> Optional[float]:
        """Calculate portfolio volatility considering correlations."""
        try:
            # Get historical returns for all symbols
            returns_data = {}
            
            for symbol in symbols:
                historical = self._get_historical_data(symbol, "1mo")
                if historical:
                    df = pd.DataFrame(historical)
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    returns = df['close'].pct_change().dropna()
                    returns_data[symbol] = returns
            
            if len(returns_data) < 2:
                return None
            
            # Create returns matrix
            returns_df = pd.DataFrame(returns_data)
            
            # Calculate covariance matrix
            cov_matrix = returns_df.cov()
            
            # Annualize
            cov_matrix = cov_matrix * 252
            
            # Calculate portfolio variance
            weights_array = np.array(weights)
            portfolio_variance = np.dot(weights_array.T, np.dot(cov_matrix, weights_array))
            
            # Portfolio volatility
            portfolio_volatility = np.sqrt(portfolio_variance)
            
            return float(portfolio_volatility)
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate portfolio volatility: {str(e)}")
            return None
    
    def get_risk_alerts(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Get risk alerts for symbols that exceed thresholds."""
        try:
            alerts = []
            
            for symbol in symbols:
                risk_data = self.analyze_volatility(symbol)
                if not risk_data:
                    continue
                
                # Check for high volatility
                if risk_data.get('volatility', 0) > 0.4:
                    alerts.append({
                        'symbol': symbol,
                        'type': 'HIGH_VOLATILITY',
                        'message': f"{symbol} showing high volatility: {risk_data['volatility']:.2%}",
                        'severity': 'HIGH',
                        'value': risk_data['volatility']
                    })
                
                # Check for large drawdown
                if risk_data.get('max_drawdown', 0) < -0.25:
                    alerts.append({
                        'symbol': symbol,
                        'type': 'LARGE_DRAWDOWN',
                        'message': f"{symbol} has large max drawdown: {risk_data['max_drawdown']:.2%}",
                        'severity': 'HIGH',
                        'value': risk_data['max_drawdown']
                    })
                
                # Check for extreme VaR
                if risk_data.get('var_95', 0) < -0.05:
                    alerts.append({
                        'symbol': symbol,
                        'type': 'EXTREME_VAR',
                        'message': f"{symbol} has extreme VaR (95%): {risk_data['var_95']:.2%}",
                        'severity': 'MEDIUM',
                        'value': risk_data['var_95']
                    })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error getting risk alerts: {str(e)}")
            return []
