#!/usr/bin/env python3
"""
Analyze individual stock and generate CSV trading report
"""

import os
import json
import pandas as pd
import sys
from datetime import datetime
from stock_analyzer import ComprehensiveStockAnalyzer

def analyze_individual_stock(ticker, budget=1600):
    """Analyze individual stock and generate CSV report"""
    
    # Initialize analyzer
    api_key = os.getenv("OPENAI_API_KEY")
    analyzer = ComprehensiveStockAnalyzer(
        api_key=api_key,
        budget=budget,
        max_risk_percent=10
    )
    
    print(f' Analyzing {ticker} with budget ${budget}...')
    
    # Analyze stock
    analysis = analyzer.analyze_stock(ticker)
    
    if 'error' in analysis:
        print(f'❌ Error: {analysis["error"]}')
        sys.exit(1)
    
    # Print formatted analysis
    analyzer.print_analysis(analysis)
    
    # Generate CSV report
    generate_individual_csv_report(analysis, budget)
    
    # Save JSON for reference
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f'../analysis_{ticker}_{timestamp}.json'
    with open(json_filename, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    print(f'✅ JSON analysis saved to {json_filename}')

def generate_individual_csv_report(analysis, budget):
    """Generate CSV report for individual stock analysis"""
    
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
    
    # Create detailed analysis
    detailed_analysis = []
    
    # Technical Analysis
    detailed_analysis.append(f"RSI: {tech.get('rsi', 0):.1f}")
    detailed_analysis.append(f"5-day change: {tech.get('price_change_5d', 0):.1f}%")
    detailed_analysis.append(f"20-day change: {tech.get('price_change_20d', 0):.1f}%")
    detailed_analysis.append(f"Volume ratio: {tech.get('volume_ratio', 1):.1f}x")
    
    # Fundamental Analysis
    if fund.get('pe_ratio', 0) > 0:
        detailed_analysis.append(f"P/E: {fund['pe_ratio']:.1f}")
    if fund.get('return_potential', 0) > 0:
        detailed_analysis.append(f"Analyst target: {fund.get('analyst_target', 0):.2f}")
    
    # Trinity Analysis
    detailed_analysis.append(f"Trinity pattern: {'Yes' if trinity['trinity_signal'] else 'No'}")
    detailed_analysis.append(f"New highs: {trinity['new_highs_count']}")
    
    # Options Analysis
    if analysis['options_analysis']['suitable']:
        opt_count = len(analysis['options_analysis']['recommendations'])
        detailed_analysis.append(f"Options available: {opt_count} suitable strikes")
    
    detailed_text = " | ".join(detailed_analysis)
    
    # Create CSV data
    csv_data = [{
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
        'Volume_Surge': "Yes" if tech.get('volume_surge', False) else "No",
        'Above_SMA20': "Yes" if tech.get('above_sma20', False) else "No",
        'Above_SMA50': "Yes" if tech.get('above_sma50', False) else "No",
        'Detailed_Analysis': detailed_text,
        'Budget_Used': f"${budget}",
        'Analysis_Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }]
    
    # Create DataFrame and save
    df_report = pd.DataFrame(csv_data)
    
    # Save CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f'../trading_report_{ticker}_{timestamp}.csv'
    df_report.to_csv(csv_filename, index=False)
    
    print(f'✅ Trading report saved to {csv_filename}')
    
    # Print summary
    print(f"\n📊 TRADING SUMMARY FOR {ticker}:")
    print(f"Rating: {rating}")
    print(f"Price: {csv_data[0]['Current_Price']}")
    print(f"Potential: {csv_data[0]['Return_Potential']}")
    print(f"Risk Level: {csv_data[0]['Risk_Level']}")
    print(f"Position: {shares} shares (${investment:.0f})")
    print(f"Stop Loss: {csv_data[0]['Stop_Loss']}")
    print(f"Catalyst: {catalyst_text}")

if __name__ == "__main__":
    # Get inputs from environment variables or command line
    ticker = os.getenv('TICKER', 'AAPL').upper()
    budget = float(os.getenv('BUDGET', '1600'))
    
    analyze_individual_stock(ticker, budget)
