#!/usr/bin/env python3
"""
MongoDB Setup Script for Stock Analyst App
"""

import subprocess
import sys
import os
from pathlib import Path

def install_mongodb():
    """Instructions for installing MongoDB on Windows."""
    print("MongoDB Installation Instructions for Windows:")
    print("=" * 50)
    print("1. Download MongoDB Community Server from: https://www.mongodb.com/try/download/community")
    print("2. Run the installer and follow the setup wizard")
    print("3. Choose 'Complete' installation")
    print("4. Install MongoDB as a Windows Service")
    print("5. Install MongoDB Compass (GUI) if desired")
    print("\nAlternatively, you can use MongoDB Atlas (cloud):")
    print("1. Sign up at: https://www.mongodb.com/atlas")
    print("2. Create a free cluster")
    print("3. Get your connection string")
    print("4. Update .env file with your connection string")

def setup_environment():
    """Setup environment variables for MongoDB."""
    env_file = Path(".env")
    
    print("\nSetting up environment variables...")
    
    # Default MongoDB settings
    env_content = """# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_NAME=stock_analyst

# AWS Bedrock Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# Application Settings
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here

# MCP Server Ports
FINANCE_SERVER_PORT=8001
RSS_SERVER_PORT=8002
DB_SERVER_PORT=8003
"""
    
    if not env_file.exists():
        with open(env_file, 'w') as f:
            f.write(env_content)
        print(f"Created {env_file} with default MongoDB settings")
    else:
        print(f"{env_file} already exists. Please verify MongoDB settings:")
        print("MONGODB_URL=mongodb://localhost:27017")
        print("MONGODB_NAME=stock_analyst")

def install_python_packages():
    """Install required Python packages."""
    print("\nInstalling Python packages...")
    
    packages = [
        "pymongo>=4.6.0",
        "motor>=3.3.0",
        "flask==2.3.3",
        "boto3==1.34.0",
        "requests==2.31.0",
        "feedparser==6.0.11",
        "pandas>=2.2.0",
        "numpy>=1.26.0",
        "matplotlib>=3.8.0",
        "python-dotenv==1.0.0",
        "yfinance>=0.2.32",
        "beautifulsoup4==4.12.2",
        "lxml>=4.9.3",
        "schedule==1.2.0"
    ]
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except subprocess.CalledProcessError as e:
            print(f"Error installing {package}: {e}")

def test_mongodb_connection():
    """Test MongoDB connection."""
    try:
        from pymongo import MongoClient
        from config import Config
        
        print("\nTesting MongoDB connection...")
        client = MongoClient(Config.MONGODB_URL, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful!")
        
        # Test database access
        db = client[Config.MONGODB_NAME]
        db.test.insert_one({"test": "connection"})
        db.test.delete_one({"test": "connection"})
        print("✅ Database operations successful!")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure MongoDB is running (check Windows Services)")
        print("2. Verify the MONGODB_URL in your .env file")
        print("3. Check firewall settings")
        return False

def create_sample_data():
    """Create sample data in MongoDB."""
    try:
        from models.portfolio import (
            save_recommendation, save_stock_data, save_news_data
        )
        from datetime import datetime
        
        print("\nCreating sample data...")
        
        # Sample recommendations
        save_recommendation("RELIANCE", "BUY", "Strong fundamentals and growth prospects", 0.85)
        save_recommendation("TCS", "HOLD", "Stable but fairly valued", 0.65)
        save_recommendation("INFY", "BUY", "Good quarterly results", 0.75)
        
        # Sample stock data
        save_stock_data("RELIANCE", 2450.50, 1000000, 25.30, 1.04)
        save_stock_data("TCS", 3520.75, 500000, -15.25, -0.43)
        save_stock_data("INFY", 1680.20, 750000, 12.80, 0.77)
        
        # Sample news
        save_news_data(
            "Market rallies on positive earnings",
            "Indian stock markets gained today...",
            "https://example.com/news1",
            "Financial Express",
            0.7,
            ["RELIANCE", "TCS", "INFY"]
        )
        
        print("✅ Sample data created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return False

def main():
    """Main setup function."""
    print("Stock Analyst App - MongoDB Setup")
    print("=" * 40)
    
    # Step 1: MongoDB installation instructions
    install_mongodb()
    
    # Step 2: Setup environment
    setup_environment()
    
    # Step 3: Install packages
    response = input("\nInstall Python packages? (y/n): ").lower()
    if response in ['y', 'yes']:
        install_python_packages()
    
    # Step 4: Test connection
    response = input("\nTest MongoDB connection? (y/n): ").lower()
    if response in ['y', 'yes']:
        if test_mongodb_connection():
            # Step 5: Create sample data
            response = input("\nCreate sample data? (y/n): ").lower()
            if response in ['y', 'yes']:
                create_sample_data()
    
    print("\n" + "=" * 40)
    print("Setup complete!")
    print("\nNext steps:")
    print("1. Make sure MongoDB is running")
    print("2. Update your .env file with correct settings")
    print("3. Run: python app.py")
    print("4. Visit: http://localhost:5000")

if __name__ == "__main__":
    main()
