#!/usr/bin/env python3
"""
Test script to verify all components of the Stock Analyst App
"""

import requests
import json
import time
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_mcp_servers():
    """Test MCP servers are running and responding."""
    print("Testing MCP Servers...")
    
    servers = [
        ("Finance Server", "http://localhost:8001", {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "get_stock_data",
            "params": {"symbol": "INFY"}
        }),
        ("RSS Server", "http://localhost:8002", {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "get_market_news",
            "params": {"limit": 5}
        }),
        ("Database Server", "http://localhost:8003", {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "analyze_risk",
            "params": {"symbol": "INFY", "period": "1mo"}
        })
    ]
    
    for name, url, payload in servers:
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    print(f"✓ {name}: OK")
                else:
                    print(f"✗ {name}: Error - {data.get('error', 'Unknown error')}")
            else:
                print(f"✗ {name}: HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"✗ {name}: Connection refused (server not running?)")
        except Exception as e:
            print(f"✗ {name}: {str(e)}")

def test_flask_app():
    """Test Flask application endpoints."""
    print("\nTesting Flask Application...")
    
    endpoints = [
        ("Health Check", "http://localhost:5000/health", "GET"),
        ("Dashboard", "http://localhost:5000/", "GET"),
        ("Stock Data", "http://localhost:5000/api/stocks/INFY", "GET"),
        ("Market News", "http://localhost:5000/api/news", "GET"),
    ]
    
    for name, url, method in endpoints:
        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, timeout=10)
                
            if response.status_code == 200:
                print(f"✓ {name}: OK")
            else:
                print(f"✗ {name}: HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"✗ {name}: Connection refused (Flask app not running?)")
        except Exception as e:
            print(f"✗ {name}: {str(e)}")

def test_analysis_pipeline():
    """Test the complete analysis pipeline."""
    print("\nTesting Analysis Pipeline...")
    
    try:
        payload = {
            "stocks": ["INFY", "TCS"]
        }
        
        print("Running analysis (this may take a few minutes)...")
        response = requests.post(
            "http://localhost:5000/analyze",
            json=payload,
            timeout=120  # 2 minutes timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                recommendations = data.get('recommendations', [])
                print(f"✓ Analysis Pipeline: OK ({len(recommendations)} recommendations)")
                
                # Display sample recommendation
                if recommendations:
                    rec = recommendations[0]
                    print(f"  Sample: {rec.get('symbol')} - {rec.get('action')} ({rec.get('confidence', 0)*100:.1f}% confidence)")
            else:
                print(f"✗ Analysis Pipeline: {data.get('message', 'Unknown error')}")
        else:
            print(f"✗ Analysis Pipeline: HTTP {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("✗ Analysis Pipeline: Connection refused")
    except requests.exceptions.Timeout:
        print("✗ Analysis Pipeline: Timeout (this is normal for first run)")
    except Exception as e:
        print(f"✗ Analysis Pipeline: {str(e)}")

def test_database():
    """Test database connectivity."""
    print("\nTesting Database...")
    
    try:
        from models.portfolio import init_db, get_all_recommendations
        
        # Initialize database
        init_db()
        print("✓ Database: Initialization OK")
        
        # Test query
        recommendations = get_all_recommendations(limit=5)
        print(f"✓ Database: Query OK ({len(recommendations)} records)")
        
    except Exception as e:
        print(f"✗ Database: {str(e)}")

def test_aws_bedrock():
    """Test AWS Bedrock connectivity."""
    print("\nTesting AWS Bedrock...")
    
    try:
        import boto3
        from config import Config
        
        client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION
        )
        
        # Test with a simple prompt
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, this is a test. Please respond with 'Test successful'."
                }
            ]
        }
        
        response = client.invoke_model(
            modelId=Config.MODEL_ID,
            body=json.dumps(body),
            contentType='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body.get('content', [{}])[0].get('text', '')
        
        if 'test successful' in content.lower():
            print("✓ AWS Bedrock: OK")
        else:
            print(f"✓ AWS Bedrock: Connected (response: {content[:50]}...)")
            
    except Exception as e:
        print(f"✗ AWS Bedrock: {str(e)}")

def main():
    """Run all tests."""
    print("Stock Analyst App - Component Test Suite")
    print("=" * 50)
    
    # Test components
    test_database()
    test_aws_bedrock()
    test_mcp_servers()
    test_flask_app()
    test_analysis_pipeline()
    
    print("\n" + "=" * 50)
    print("Test Suite Complete!")
    print("\nIf any tests failed, please check:")
    print("1. All servers are running (python start_servers.py)")
    print("2. Flask app is running (python app.py)")
    print("3. AWS credentials are configured correctly")
    print("4. Internet connection is available")
    print("5. Required Python packages are installed")

if __name__ == "__main__":
    main()
