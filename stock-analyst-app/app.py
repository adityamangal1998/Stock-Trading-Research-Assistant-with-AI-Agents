from flask import Flask, render_template, request, jsonify
import threading
import time
from datetime import datetime
from config import Config
from agents.orchestrator import Orchestrator
from models.portfolio import init_db, get_all_recommendations, save_recommendation

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
init_db()

# Initialize orchestrator
orchestrator = Orchestrator()

@app.route('/')
def dashboard():
    """Main dashboard showing today's recommendations."""
    try:
        recommendations = get_all_recommendations(limit=10)
        return render_template('index.html', 
                             recommendations=recommendations,
                             current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}")
        return render_template('index.html', 
                             recommendations=[],
                             error="Unable to load recommendations",
                             current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route('/analyze', methods=['POST'])
def analyze():
    """Run orchestrator pipeline and return JSON output."""
    try:
        # Get stocks to analyze from request or use defaults
        data = request.get_json() if request.is_json else {}
        stocks = data.get('stocks', Config.DEFAULT_STOCKS)
        
        # Run analysis
        app.logger.info(f"Starting analysis for stocks: {stocks}")
        results = orchestrator.analyze_portfolio(stocks)
        
        # Save recommendations to database
        for result in results:
            save_recommendation(
                symbol=result.get('symbol'),
                action=result.get('action'),
                reasoning=result.get('reasoning'),
                confidence=result.get('confidence', 0.5),
                metadata=result
            )
        
        return jsonify({
            'status': 'success',
            'recommendations': results,
            'timestamp': datetime.now().isoformat(),
            'analyzed_stocks': stocks
        })
        
    except Exception as e:
        app.logger.error(f"Analysis error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/analyze_deep', methods=['POST'])
def analyze_deep():
    """Run deep analysis using Tavily search and Claude AI."""
    try:
        # Get stock query from request
        data = request.get_json() if request.is_json else {}
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Please provide a stock name, symbol, or description to analyze',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Run deep analysis
        app.logger.info(f"Starting deep analysis for: {query}")
        deep_analysis = orchestrator.analyze_stock_deep(query)
        
        # Extract recommendation for saving to database
        recommendation = deep_analysis.get('comprehensive_recommendation', {})
        if recommendation and recommendation.get('symbol'):
            save_recommendation(
                symbol=recommendation.get('symbol'),
                action=recommendation.get('action'),
                reasoning=recommendation.get('reasoning'),
                confidence=recommendation.get('confidence', 0.5),
                metadata=recommendation.get('metadata', {})
            )
        
        return jsonify({
            'status': 'success',
            'deep_analysis': deep_analysis,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat(),
            'query': query
        })
        
    except Exception as e:
        app.logger.error(f"Deep analysis error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/history')
def history():
    """Show past recommendations from database."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        recommendations = get_all_recommendations(
            limit=per_page,
            offset=(page - 1) * per_page
        )
        
        return jsonify({
            'status': 'success',
            'recommendations': [
                {
                    'id': rec.id,
                    'symbol': rec.symbol,
                    'action': rec.action,
                    'reasoning': rec.reasoning,
                    'confidence': rec.confidence,
                    'timestamp': rec.timestamp.isoformat(),
                    'metadata': rec.metadata
                }
                for rec in recommendations
            ],
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        app.logger.error(f"History error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/stocks/<symbol>')
def get_stock_data(symbol):
    """Get current stock data for a specific symbol."""
    try:
        from agents.data_collector import DataCollectorAgent
        data_collector = DataCollectorAgent()
        stock_data = data_collector.get_stock_data(symbol)
        
        return jsonify({
            'status': 'success',
            'symbol': symbol,
            'data': stock_data
        })
        
    except Exception as e:
        app.logger.error(f"Stock data error for {symbol}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/news')
def get_market_news():
    """Get latest market news."""
    try:
        from agents.research_agent import ResearchAgent
        research_agent = ResearchAgent()
        news = research_agent.get_market_news()
        
        return jsonify({
            'status': 'success',
            'news': news,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"News error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def start_mcp_servers():
    """Start MCP servers in background threads."""
    import subprocess
    import sys
    
    servers = [
        ('finance_server.py', Config.MCP_FINANCE_PORT),
        ('rss_server.py', Config.MCP_RSS_PORT),
        ('db_server.py', Config.MCP_DB_PORT)
    ]
    
    for server_file, port in servers:
        try:
            server_path = f"mcp_servers/{server_file}"
            subprocess.Popen([sys.executable, server_path, str(port)], 
                           cwd=app.root_path)
            app.logger.info(f"Started MCP server: {server_file} on port {port}")
        except Exception as e:
            app.logger.error(f"Failed to start {server_file}: {str(e)}")

if __name__ == '__main__':
    # Start MCP servers
    start_mcp_servers()
    
    # Give servers time to start
    time.sleep(2)
    
    # Start Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=Config.DEBUG
    )
