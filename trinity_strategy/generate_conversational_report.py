#!/usr/bin/env python3
"""
Generate conversational trading report in Mrkvicka's format
"""

import os
import json
import pandas as pd
from datetime import datetime
from stock_analyzer import ComprehensiveStockAnalyzer

def generate_conversational_report():
    """Generate conversational trading report for Trinity candidates"""
    
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
    
    # Generate conversational report
    generate_conversational_output(results, latest_file)

def generate_conversational_output(analyses, source_file):
    """Generate conversational report in Mrkvicka's format"""
    
    # Extract date from source file
    basename = os.path.basename(source_file)
    date_str = basename.split("_")[-1].replace(".csv", "")
    
    # Sort by rating priority
    rating_priority = {'STRONG BUY': 1, 'BUY': 2, 'HOLD': 3, 'AVOID': 4}
    analyses.sort(key=lambda x: rating_priority.get(x['overall_rating'], 5))
    
    # Separate into categories
    strong_buys = [a for a in analyses if a['overall_rating'] == 'STRONG BUY']
    buys = [a for a in analyses if a['overall_rating'] == 'BUY']
    holds = [a for a in analyses if a['overall_rating'] == 'HOLD']
    avoids = [a for a in analyses if a['overall_rating'] == 'AVOID']
    
    # Generate conversational report
    report_lines = []
    
    # Header
    report_lines.append(f"Based on my analysis of the {len(analyses)} Trinity candidates from {date_str}, here are the best trades according to Mrkvicka's methodology:")
    report_lines.append("")
    report_lines.append(f"🎯 TOP TRINITY PICKS - {date_str.upper()}")
    report_lines.append("")
    
    # Strong Buys
    if strong_buys:
        for i, analysis in enumerate(strong_buys[:5], 1):  # Top 5
            report_lines.extend(generate_stock_entry(analysis, i, "STRONG BUY"))
            report_lines.append("")
    
    # Buys
    if buys:
        for i, analysis in enumerate(buys[:3], len(strong_buys) + 1):  # Top 3
            report_lines.extend(generate_stock_entry(analysis, i, "BUY"))
            report_lines.append("")
    
    # Avoid section
    if avoids:
        report_lines.append("❌ AVOID THESE:")
        avoid_tickers = [a['ticker'] for a in avoids]
        report_lines.append(f"{', '.join(avoid_tickers)} - Insufficient volume/data for Trinity analysis")
        report_lines.append("")
    
    # Summary
    report_lines.append(f"📊 SUMMARY:")
    report_lines.append(f"• STRONG BUY: {len(strong_buys)}")
    report_lines.append(f"• BUY: {len(buys)}")
    report_lines.append(f"• HOLD: {len(holds)}")
    report_lines.append(f"• AVOID: {len(avoids)}")
    report_lines.append("")
    report_lines.append("💡 Remember: Always use proper position sizing and stop losses!")
    
    # Save conversational report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"trinity_conversational_report_{date_str}_{timestamp}.txt"
    
    with open(report_filename, 'w') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\n✅ Conversational report saved to: {report_filename}")
    
    # Print to console
    print("\n" + "="*80)
    print('\n'.join(report_lines))
    print("="*80)

def generate_stock_entry(analysis, rank, rating):
    """Generate conversational entry for a single stock"""
    
    ticker = analysis['ticker']
    tech = analysis['technical_analysis']
    fund = analysis['fundamental_analysis']
    trinity = analysis['trinity_analysis']
    pos = analysis['position_sizing']
    
    # Get company name
    company_name = analysis.get('info', {}).get('longName', ticker)
    
    lines = []
    
    # Header
    lines.append(f"{rank}. {ticker} ({company_name}) - {rating}")
    lines.append("")
    
    # Key metrics
    current_price = tech['current_price']
    price_change_5d = tech.get('price_change_5d', 0)
    rsi = tech.get('rsi', 0)
    return_potential = fund.get('return_potential', 0)
    
    lines.append(f"💰 Current Price: ${current_price:.2f} ({price_change_5d:+.1f}% 5-day)")
    lines.append(f"📊 RSI: {rsi:.1f} | Return Potential: {return_potential:.1f}%")
    
    # Catalysts
    catalysts = []
    if trinity['trinity_signal']:
        catalysts.append("Trinity pattern confirmed")
    if fund.get('revenue_growth', 0) > 0.1:
        catalysts.append(f"{fund['revenue_growth']*100:.1f}% revenue growth")
    if tech.get('volume_surge', False):
        catalysts.append("Volume surge detected")
    if fund.get('earnings_growth', 0) > 0.1:
        catalysts.append(f"{fund['earnings_growth']*100:.1f}% earnings growth")
    
    if catalysts:
        lines.append(f"�� Catalysts: {' | '.join(catalysts)}")
    
    # Position sizing
    shares = pos['position_size']['shares']
    investment = pos['position_size']['investment']
    stop_loss = pos['stop_loss']
    
    lines.append(f"�� Position: {shares} shares (${investment:.0f}) | Stop: ${stop_loss:.2f}")
    
    # Options info with specific strikes
    if analysis['options_analysis']['suitable']:
        opt_count = len(analysis['options_analysis']['recommendations'])
        lines.append(f"📈 Options: {opt_count} suitable strikes available")
        
        # Add top 3 options recommendations
        if analysis['options_analysis']['recommendations']:
            lines.append("   Top strikes:")
            for i, opt in enumerate(analysis['options_analysis']['recommendations'][:3], 1):
                lines.append(f"   {i}. {opt['expiration']} ${opt['strike']:.0f} Call - ${opt['last_price']:.2f} (Vol: {opt['volume']})")
    
    # Risk assessment
    risk_level = "Medium"
    if fund.get('debt_to_equity', 0) > 1.0:
        risk_level = "High"
    elif tech.get('rsi', 50) > 70:
        risk_level = "Medium-High"
    elif tech.get('rsi', 50) < 30:
        risk_level = "Low"
    
    lines.append(f"⚠️ Risk Level: {risk_level}")
    
    # Why it's perfect for Trinity
    reasons = []
    if trinity['trinity_signal']:
        reasons.append("Major catalyst + breakthrough pattern")
    if return_potential > 50:
        reasons.append(f"{return_potential:.0f}%+ upside potential")
    if tech.get('volume_surge', False):
        reasons.append("strong volume confirmation")
    
    if reasons:
        lines.append(f"🎯 Why it's perfect for Trinity: {' + '.join(reasons)}")
    
    return lines

def generate_individual_conversational_report(ticker, budget=1600):
    """Generate conversational report for individual stock"""
    
    # Initialize analyzer
    api_key = os.getenv("OPENAI_API_KEY")
    analyzer = ComprehensiveStockAnalyzer(
        api_key=api_key,
        budget=budget,
        max_risk_percent=10
    )
    
    print(f'�� Analyzing {ticker} with budget ${budget}...')
    
    # Analyze stock
    analysis = analyzer.analyze_stock(ticker)
    
    if 'error' in analysis:
        print(f'❌ Error: {analysis["error"]}')
        return
    
    # Print formatted analysis
    analyzer.print_analysis(analysis)
    
    # Generate conversational report
    report_lines = []
    report_lines.append(f"📊 INDIVIDUAL STOCK ANALYSIS: {ticker}")
    report_lines.append("="*60)
    report_lines.append("")
    
    # Add the stock entry
    stock_lines = generate_stock_entry(analysis, 1, analysis['overall_rating'])
    report_lines.extend(stock_lines)
    
    # Add AI insights if available
    if 'ai_analysis' in analysis:
        ai = analysis['ai_analysis']
        report_lines.append("")
        report_lines.append("🤖 AI INSIGHTS:")
        if 'key_reasons' in ai:
            for reason in ai['key_reasons'][:3]:
                report_lines.append(f"• {reason}")
        if 'warnings' in ai:
            report_lines.append("")
            report_lines.append("⚠️ WARNINGS:")
            for warning in ai['warnings'][:2]:
                report_lines.append(f"• {warning}")
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"individual_analysis_{ticker}_{timestamp}.txt"
    
    with open(report_filename, 'w') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\n✅ Conversational report saved to: {report_filename}")
    
    # Print to console
    print("\n" + "="*60)
    print('\n'.join(report_lines))
    print("="*60)

if __name__ == "__main__":
    generate_conversational_report()
