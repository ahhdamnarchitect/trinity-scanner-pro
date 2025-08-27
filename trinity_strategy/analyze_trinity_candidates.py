#!/usr/bin/env python3
"""
Analyze Trinity candidates with comprehensive stock and options analysis
"""

import os
import json
import pandas as pd
from datetime import datetime
from stock_analyzer import ComprehensiveStockAnalyzer

def analyze_trinity_candidates():
    """Analyze all current Trinity candidates with comprehensive analysis"""
    
    # Initialize analyzer
    api_key = os.getenv("OPENAI_API_KEY")
    analyzer = ComprehensiveStockAnalyzer(
        api_key=api_key,
        budget=1600,
        max_risk_percent=10
    )
    
    # Find Trinity candidate files
    trinity_dir = os.path.join(os.path.dirname(__file__), "data", "trinity_candidates")
    trinity_files = []
    
    if os.path.exists(trinity_dir):
        for file in os.listdir(trinity_dir):
            if file.startswith("trinity_candidates_") and file.endswith(".csv"):
                trinity_files.append(os.path.join(trinity_dir, file))
    
    if not trinity_files:
        print("❌ No Trinity candidate files found")
        return
    
    # Get most recent Trinity candidates
    latest_file = max(trinity_files, key=os.path.getctime)
    print(f"📁 Analyzing candidates from: {os.path.basename(latest_file)}")
    
    # Read Trinity candidates
    df = pd.read_csv(latest_file)
    tickers = df['Ticker'].tolist()
    
    print(f"�� Found {len(tickers)} Trinity candidates to analyze")
    
    # Analyze each candidate
    results = []
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Analyzing {ticker}...")
        
        analysis = analyzer.analyze_stock(ticker)
        if "error" not in analysis:
            results.append(analysis)
            
            # Print summary
            rating = analysis['overall_rating']
            price = analysis['technical_analysis']['current_price']
            trinity = analysis['trinity_analysis']['trinity_signal']
            
            print(f"   Rating: {rating} | Price: ${price:.2f} | Trinity: {'✅' if trinity else '❌'}")
    
    # Save comprehensive analysis
    if results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_analysis_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n✅ Comprehensive analysis saved to {filename}")
        
        # Print summary
        print(f"\n📊 ANALYSIS SUMMARY:")
        print(f"Total candidates analyzed: {len(results)}")
        
        ratings = [r['overall_rating'] for r in results]
        for rating in ['STRONG BUY', 'BUY', 'HOLD', 'AVOID']:
            count = ratings.count(rating)
            if count > 0:
                print(f"{rating}: {count}")
    
    else:
        print("❌ No successful analyses completed")

if __name__ == "__main__":
    analyze_trinity_candidates()
