#!/usr/bin/env python3
"""
Generate trading report in CSV format with Mrkvicka's methodology analysis
"""

import os
import json
import pandas as pd
from datetime import datetime
from stock_analyzer import ComprehensiveStockAnalyzer

def generate_trading_report():
    """Generate comprehensive trading report for Trinity candidates"""
    
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
    
    if not results:
        print("❌ No successful analyses completed")
        return
    
    # Generate CSV report
    generate_csv_report(results, latest_file)

def generate_csv_report(analyses, source_file):
    """Generate CSV report in Mrkvicka's format"""
    
    # Extract date from source file
    basename = os.path.basename(source_file)
    date_str = basename.split("_")[-1].replace(".csv", "")
    
    # Prepare data for CSV
    csv_data = []
    
    for analysis in analyses:
        ticker = analysis['ticker']
        rating = analysis['overall_rating']
        tech = analysis['technical_analysis']
        fund = analysis['fundamental_analysis']
        trinity = analysis['trinity_analysis']
        pos = analysis['position_sizing']
        
        # Determine risk level
        risk_level = "Low"
        if fund.get('debt_to_equity', 0) > 1.0:
            risk_level = "High"
        elif tech.get('rsi', 50) > 70:
            risk_level = "Medium-High"
        elif tech.get('rsi', 50) < 30:
            risk_level = "Low"
        
        # Get company name
        company_name = analysis.get('info', {}).get('longName', ticker)
        
        # Create catalyst/reason
        catalysts = []
        if trinity['trinity_signal']:
            catalysts.append("Trinity pattern confirmed")
        if fund.get('return_potential', 0) > 50:
            catalysts.append(f"{fund['return_potential']:.1f}% upside potential")
        if tech.get('volume_surge', False):
            catalysts.append("Volume surge")
        if fund.get('revenue_growth', 0) > 0.1:
            catalysts.append(f"{fund['revenue_growth']*100:.1f}% revenue growth")
        
        catalyst_text = " | ".join(catalysts) if catalysts else "Technical breakout"
        
        # Options availability
        options_available = "Yes" if analysis['options_analysis']['suitable'] else "No"
        
        # Position sizing
        shares = pos['position_size']['shares']
        investment = pos['position_size']['investment']
        risk_amount = pos['position_size']['risk']
        
        csv_data.append({
            'Rank': '',
            'Ticker': ticker,
            'Company': company_name,
            'Rating': rating,
            'Current_Price': f"${tech['current_price']:.2f}",
            'Price_Change_5d': f"{tech.get('price_change_5d', 0):.1f}%",
            'RSI': f"{tech.get('rsi', 0):.1f}",
            'Return_Potential': f"{fund.get('return_potential', 0):.1f}%",
            'Risk_Level': risk_level,
            'Catalyst': catalyst_text,
            'Options_Available': options_available,
            'Shares_Recommended': shares,
            'Investment_Amount': f"${investment:.0f}",
            'Risk_Amount': f"${risk_amount:.0f}",
            'Stop_Loss': f"${pos['stop_loss']:.2f}",
            'Trinity_Pattern': "Yes" if trinity['trinity_signal'] else "No",
            'New_Highs_Count': trinity['new_highs_count'],
            'Days_Since_Signal': analysis.get('Days_Since_Signal', 'N/A'),
            'Volume_Surge': "Yes" if tech.get('volume_surge', False) else "No",
            'Above_SMA20': "Yes" if tech.get('above_sma20', False) else "No",
            'Above_SMA50': "Yes" if tech.get('above_sma50', False) else "No"
        })
    
    # Sort by rating priority
    rating_priority = {'STRONG BUY': 1, 'BUY': 2, 'HOLD': 3, 'AVOID': 4}
    csv_data.sort(key=lambda x: rating_priority.get(x['Rating'], 5))
    
    # Add ranking
    for i, row in enumerate(csv_data, 1):
        row['Rank'] = i
    
    # Create DataFrame and save
    df_report = pd.DataFrame(csv_data)
    
    # Save detailed CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"trinity_trading_report_{date_str}_{timestamp}.csv"
    df_report.to_csv(csv_filename, index=False)
    
    # Save summary CSV (top picks only)
    top_picks = df_report[df_report['Rating'].isin(['STRONG BUY', 'BUY'])].copy()
    summary_filename = f"trinity_top_picks_{date_str}_{timestamp}.csv"
    top_picks.to_csv(summary_filename, index=False)
    
    print(f"\n✅ Trading report saved:")
    print(f"   📊 Full report: {csv_filename}")
    print(f"   🎯 Top picks: {summary_filename}")
    
    # Print summary
    print(f"\n📊 ANALYSIS SUMMARY:")
    print(f"Total candidates analyzed: {len(csv_data)}")
    
    ratings = [r['Rating'] for r in csv_data]
    for rating in ['STRONG BUY', 'BUY', 'HOLD', 'AVOID']:
        count = ratings.count(rating)
        if count > 0:
            print(f"{rating}: {count}")
    
    if not top_picks.empty:
        print(f"\n🎯 TOP PICKS ({len(top_picks)}):")
        for _, row in top_picks.head(5).iterrows():
            print(f"{row['Rank']}. {row['Ticker']} ({row['Company']}) - {row['Rating']}")
            print(f"   Price: {row['Current_Price']} | Potential: {row['Return_Potential']} | Risk: {row['Risk_Level']}")

if __name__ == "__main__":
    generate_trading_report()
