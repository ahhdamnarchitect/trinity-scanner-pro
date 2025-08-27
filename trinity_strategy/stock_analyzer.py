import yfinance as yf
import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime, timedelta
import openai
from typing import Dict, List, Optional, Tuple

class ComprehensiveStockAnalyzer:
    def __init__(self, api_key: str = None, budget: float = 1600, max_risk_percent: float = 10):
        """
        Initialize the comprehensive stock analyzer
        
        Args:
            api_key: OpenAI API key (can be set via OPENAI_API_KEY env var)
            budget: Trading budget in dollars
            max_risk_percent: Maximum risk percentage per trade
        """
        self.budget = budget
        self.max_risk = budget * (max_risk_percent / 100)
        
        # Initialize OpenAI client
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = openai.OpenAI(api_key=api_key)
            self.ai_enabled = True
        else:
            print("⚠️ OpenAI API key not found. AI analysis will be disabled.")
            self.ai_enabled = False
    
    def analyze_stock(self, ticker: str) -> Dict:
        """
        Complete analysis of any stock ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing complete analysis
        """
        print(f"�� Analyzing {ticker}...")
        
        try:
            # Get stock data
            stock_data = self.get_stock_data(ticker)
            if not stock_data:
                return {"error": f"Could not retrieve data for {ticker}"}
            
            # Get options chain
            options_data = self.get_options_chain(ticker)
            
            # Technical analysis
            technical = self.technical_analysis(stock_data)
            
            # Fundamental analysis  
            fundamental = self.fundamental_analysis(ticker, stock_data)
            
            # Trinity pattern check
            trinity_status = self.check_trinity_pattern(stock_data)
            
            # Options analysis
            options_analysis = self.analyze_options_chain(options_data, stock_data)
            
            # AI-powered synthesis (if available)
            ai_analysis = None
            if self.ai_enabled:
                ai_analysis = self.get_ai_analysis(ticker, {
                    'technical': technical,
                    'fundamental': fundamental,
                    'trinity': trinity_status,
                    'options': options_analysis
                })
            
            # Combine all analysis
            return self.compile_final_analysis(ticker, technical, fundamental, 
                                             trinity_status, options_analysis, ai_analysis)
        
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}
    
    def get_stock_data(self, ticker: str) -> Optional[Dict]:
        """Get comprehensive stock data"""
        try:
            stock = yf.Ticker(ticker)
            
            # Get basic info first
            info = stock.info
            if not info or 'regularMarketPrice' not in info:
                return None
            
            # Get historical data
            history = stock.history(period='6mo')
            if history.empty:
                return None
            
            return {
                'history': history,
                'info': info,
                'financials': stock.financials,
                'balance_sheet': stock.balance_sheet,
                'cashflow': stock.cashflow,
                'analyst_price_targets': stock.analyst_price_targets,
                'recommendations': stock.recommendations
            }
        except Exception as e:
            print(f"Error getting stock data for {ticker}: {e}")
            return None
    
    def get_options_chain(self, ticker: str) -> Optional[Dict]:
        """Get real-time options chain data"""
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            
            if not expirations:
                return None
            
            options_data = {}
            
            # Get first 4 expirations (or fewer if less available)
            for exp in expirations[:4]:
                try:
                    option_chain = stock.option_chain(exp)
                    options_data[exp] = {
                        'calls': option_chain.calls,
                        'puts': option_chain.puts
                    }
                except Exception as e:
                    print(f"Error getting options for {exp}: {e}")
                    continue
            
            return options_data if options_data else None
            
        except Exception as e:
            print(f"Error getting options chain for {ticker}: {e}")
            return None
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def technical_analysis(self, stock_data: Dict) -> Dict:
        """Perform technical analysis"""
        df = stock_data['history']
        current_price = df['Close'].iloc[-1]
        
        # Calculate indicators
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['SMA_50'] = df['Close'].rolling(50).mean()
        df['RSI'] = self.calculate_rsi(df['Close'])
        
        # Volume analysis
        avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
        recent_volume = df['Volume'].iloc[-5:].mean()
        volume_surge = recent_volume / avg_volume > 1.2 if avg_volume > 0 else False
        
        # Support/Resistance levels
        resistance = df['High'].rolling(20).max().iloc[-1]
        support = df['Low'].rolling(20).min().iloc[-1]
        
        # Price momentum
        price_change_5d = (current_price - df['Close'].iloc[-5]) / df['Close'].iloc[-5] * 100
        price_change_20d = (current_price - df['Close'].iloc[-20]) / df['Close'].iloc[-20] * 100
        
        return {
            'current_price': current_price,
            'resistance': resistance,
            'support': support,
            'volume_surge': volume_surge,
            'rsi': df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 50,
            'above_sma20': current_price > df['SMA_20'].iloc[-1],
            'above_sma50': current_price > df['SMA_50'].iloc[-1],
            'price_change_5d': price_change_5d,
            'price_change_20d': price_change_20d,
            'volume_ratio': recent_volume / avg_volume if avg_volume > 0 else 1
        }
    
    def check_trinity_pattern(self, stock_data: Dict) -> Dict:
        """Check for Trinity Trading System pattern (3 new highs in 24 trading days)"""
        df = stock_data['history']
        
        # Look for 3 new highs in 24 trading days
        lookback_days = 24
        recent_data = df.tail(lookback_days)
        
        if len(recent_data) < lookback_days:
            return {
                'trinity_signal': False,
                'new_highs_count': 0,
                'new_high_dates': [],
                'reason': 'Insufficient data'
            }
        
        # Find new highs
        new_highs = []
        for i, (date, row) in enumerate(recent_data.iterrows()):
            if i > 0:  # Skip first day
                prev_high = recent_data['High'].iloc[:i].max()
                if row['High'] > prev_high:
                    new_highs.append(date.strftime('%Y-%m-%d'))
        
        trinity_signal = len(new_highs) >= 3
        
        return {
            'trinity_signal': trinity_signal,
            'new_highs_count': len(new_highs),
            'new_high_dates': new_highs,
            'lookback_period': f"{lookback_days} trading days"
        }
    
    def fundamental_analysis(self, ticker: str, stock_data: Dict) -> Dict:
        """Perform fundamental analysis"""
        info = stock_data['info']
        
        # Basic metrics
        market_cap = info.get('marketCap', 0)
        pe_ratio = info.get('trailingPE', 0)
        pb_ratio = info.get('priceToBook', 0)
        debt_to_equity = info.get('debtToEquity', 0)
        current_ratio = info.get('currentRatio', 0)
        
        # Growth metrics
        revenue_growth = info.get('revenueGrowth', 0)
        earnings_growth = info.get('earningsGrowth', 0)
        
        # Analyst data
        analyst_target = info.get('targetMeanPrice', 0)
        analyst_rating = info.get('recommendationMean', 'N/A')
        
        # Calculate return potential
        current_price = info.get('regularMarketPrice', 0)
        return_potential = 0
        if analyst_target and current_price:
            return_potential = (analyst_target - current_price) / current_price * 100
        
        return {
            'market_cap': market_cap,
            'pe_ratio': pe_ratio,
            'pb_ratio': pb_ratio,
            'debt_to_equity': debt_to_equity,
            'current_ratio': current_ratio,
            'revenue_growth': revenue_growth,
            'earnings_growth': earnings_growth,
            'analyst_target': analyst_target,
            'analyst_rating': analyst_rating,
            'return_potential': return_potential,
            'current_price': current_price
        }
    
    def analyze_options_chain(self, options_data: Optional[Dict], stock_data: Dict) -> Dict:
        """Analyze options chain for best trades"""
        if not options_data:
            return {'suitable': False, 'reason': 'No options data available'}
        
        current_price = stock_data['history']['Close'].iloc[-1]
        recommendations = []
        
        for exp_date, chains in options_data.items():
            calls = chains['calls']
            
            # Filter for reasonable strikes (90-110% of current price)
            min_strike = current_price * 0.9
            max_strike = current_price * 1.1
            
            filtered_calls = calls[
                (calls['strike'] >= min_strike) & 
                (calls['strike'] <= max_strike) &
                (calls['volume'] > 0) &
                (calls['bid'] > 0.05)
            ]
            
            if not filtered_calls.empty:
                # Find best options based on volume, open interest, bid-ask spread
                for _, option in filtered_calls.iterrows():
                    spread = option['ask'] - option['bid']
                    spread_pct = spread / option['lastPrice'] if option['lastPrice'] > 0 else 1
                    
                    if spread_pct < 0.2:  # Less than 20% spread
                        recommendations.append({
                            'expiration': exp_date,
                            'strike': option['strike'],
                            'last_price': option['lastPrice'],
                            'bid': option['bid'],
                            'ask': option['ask'],
                            'volume': option['volume'],
                            'open_interest': option['openInterest'],
                            'implied_volatility': option['impliedVolatility'],
                            'spread_pct': spread_pct * 100
                        })
        
        # Sort by volume and open interest
        recommendations.sort(key=lambda x: x['volume'] * x['open_interest'], reverse=True)
        
        return {
            'suitable': len(recommendations) > 0,
            'recommendations': recommendations[:5],  # Top 5 options
            'current_stock_price': current_price,
            'total_options_found': len(recommendations)
        }
    
    def get_ai_analysis(self, ticker: str, data_summary: Dict) -> Optional[Dict]:
        """Get AI analysis and recommendations"""
        if not self.ai_enabled:
            return None
            
        try:
            prompt = f"""
            Analyze {ticker} using Edward F. Mrkvicka Jr.'s Trinity Trading System methodology.
            
            TRADING BUDGET: ${self.budget}
            MAX RISK PER TRADE: ${self.max_risk}
            
            DATA SUMMARY:
            {json.dumps(data_summary, default=str, indent=2)}
            
            PROVIDE ANALYSIS FOR:
            1. Trinity Trading System evaluation (resistance breakthrough, return potential)
            2. Position sizing recommendations (stock vs options)
            3. Entry/exit strategy with specific price levels
            4. Risk assessment and stop-loss recommendations
            5. Time horizon expectations
            6. Best options strategy if suitable
            
            RETURN JSON FORMAT:
            {{
                "overall_rating": "STRONG BUY|BUY|HOLD|AVOID",
                "confidence_level": "HIGH|MEDIUM|LOW",
                "return_potential": float,
                "position_recommendation": "STOCK|OPTIONS|MIXED",
                "entry_range": {{"low": float, "high": float}},
                "stop_loss": float,
                "price_targets": [float],
                "risk_level": "LOW|MEDIUM|HIGH",
                "time_horizon": "string",
                "key_reasons": ["string"],
                "warnings": ["string"]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return None
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> Dict:
        """Calculate position sizing based on risk management"""
        risk_per_share = entry_price - stop_loss
        if risk_per_share <= 0:
            return {"shares": 0, "investment": 0, "risk": 0}
        
        max_shares = int(self.max_risk / risk_per_share)
        investment = max_shares * entry_price
        
        return {
            "shares": max_shares,
            "investment": investment,
            "risk": max_shares * risk_per_share
        }
    
    def compile_final_analysis(self, ticker: str, technical: Dict, fundamental: Dict, 
                             trinity: Dict, options: Dict, ai_analysis: Optional[Dict]) -> Dict:
        """Compile final analysis with recommendations"""
        
        # Calculate position sizing
        entry_price = technical['current_price']
        stop_loss = technical['support'] * 0.95  # 5% below support
        position_size = self.calculate_position_size(entry_price, stop_loss)
        
        # Determine overall rating
        rating_factors = []
        
        if trinity['trinity_signal']:
            rating_factors.append("Trinity pattern detected")
        
        if fundamental['return_potential'] >= 50:
            rating_factors.append("High return potential")
        
        if technical['volume_surge']:
            rating_factors.append("Volume surge detected")
        
        if technical['above_sma20'] and technical['above_sma50']:
            rating_factors.append("Above key moving averages")
        
        # Determine overall rating
        if len(rating_factors) >= 3:
            overall_rating = "STRONG BUY"
        elif len(rating_factors) >= 2:
            overall_rating = "BUY"
        elif len(rating_factors) >= 1:
            overall_rating = "HOLD"
        else:
            overall_rating = "AVOID"
        
        # Compile final analysis
        analysis = {
            "ticker": ticker,
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "overall_rating": overall_rating,
            "rating_factors": rating_factors,
            "technical_analysis": technical,
            "fundamental_analysis": fundamental,
            "trinity_analysis": trinity,
            "options_analysis": options,
            "position_sizing": {
                "budget": self.budget,
                "max_risk": self.max_risk,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "position_size": position_size
            },
            "recommendations": {
                "action": "BUY" if overall_rating in ["STRONG BUY", "BUY"] else "HOLD",
                "instrument": "OPTIONS" if options['suitable'] and technical['rsi'] < 70 else "STOCK",
                "time_horizon": "2-4 weeks" if trinity['trinity_signal'] else "1-2 months"
            }
        }
        
        # Add AI analysis if available
        if ai_analysis:
            analysis["ai_analysis"] = ai_analysis
        
        return analysis
    
    def print_analysis(self, analysis: Dict):
        """Print formatted analysis results"""
        if "error" in analysis:
            print(f"❌ {analysis['error']}")
            return
        
        ticker = analysis['ticker']
        rating = analysis['overall_rating']
        
        print(f"\n{'='*60}")
        print(f"📊 COMPREHENSIVE ANALYSIS: {ticker}")
        print(f"{'='*60}")
        
        # Overall rating
        rating_emoji = {"STRONG BUY": "🚀", "BUY": "✅", "HOLD": "⏸️", "AVOID": "❌"}
        print(f"\n🎯 OVERALL RATING: {rating_emoji.get(rating, '❓')} {rating}")
        
        # Key metrics
        tech = analysis['technical_analysis']
        fund = analysis['fundamental_analysis']
        trinity = analysis['trinity_analysis']
        
        print(f"\n💰 CURRENT PRICE: ${tech['current_price']:.2f}")
        print(f"📈 5-DAY CHANGE: {tech['price_change_5d']:.1f}%")
        print(f"📊 20-DAY CHANGE: {tech['price_change_20d']:.1f}%")
        print(f"📊 RSI: {tech['rsi']:.1f}")
        
        # Trinity status
        if trinity['trinity_signal']:
            print(f"�� TRINITY PATTERN: ✅ DETECTED ({trinity['new_highs_count']} new highs)")
        else:
            print(f"�� TRINITY PATTERN: ❌ NOT DETECTED ({trinity['new_highs_count']} new highs)")
        
        # Fundamental highlights
        if fund['return_potential'] > 0:
            print(f"🎯 RETURN POTENTIAL: {fund['return_potential']:.1f}%")
        
        # Position sizing
        pos = analysis['position_sizing']['position_size']
        if pos['shares'] > 0:
            print(f"\n💼 POSITION SIZING:")
            print(f"   Shares: {pos['shares']}")
            print(f"   Investment: ${pos['investment']:.2f}")
            print(f"   Risk: ${pos['risk']:.2f}")
            print(f"   Stop Loss: ${analysis['position_sizing']['stop_loss']:.2f}")
        
        # Options recommendations
        if analysis['options_analysis']['suitable']:
            print(f"\n📋 OPTIONS RECOMMENDATIONS:")
            for i, opt in enumerate(analysis['options_analysis']['recommendations'][:3], 1):
                print(f"   {i}. {opt['expiration']} ${opt['strike']:.0f} Call")
                print(f"      Price: ${opt['last_price']:.2f} | Volume: {opt['volume']}")
        
        # AI analysis
        if 'ai_analysis' in analysis:
            ai = analysis['ai_analysis']
            print(f"\n🤖 AI INSIGHTS:")
            if 'key_reasons' in ai:
                for reason in ai['key_reasons'][:3]:
                    print(f"   • {reason}")
        
        print(f"\n{'='*60}")


def main():
    """Main function for standalone usage"""
    print("🚀 Comprehensive Stock & Options Analyzer")
    print("Based on Mrkvicka's Trinity Trading System")
    print("="*50)
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ OPENAI_API_KEY not found. AI analysis will be disabled.")
    
    # Initialize analyzer
    analyzer = ComprehensiveStockAnalyzer(
        api_key=api_key,
        budget=1600,
        max_risk_percent=10
    )
    
    while True:
        # Get ticker input
        ticker = input("\nEnter stock ticker (or 'quit' to exit): ").upper().strip()
        
        if ticker.lower() in ['quit', 'exit', 'q']:
            break
        
        if not ticker:
            continue
        
        # Analyze stock
        analysis = analyzer.analyze_stock(ticker)
        analyzer.print_analysis(analysis)
        
        # Ask if user wants to save analysis
        save = input("\nSave analysis to file? (y/n): ").lower().strip()
        if save == 'y':
            filename = f"analysis_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            print(f"✅ Analysis saved to {filename}")


if __name__ == "__main__":
    main()
