import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import glob
import os
import smtplib
import sys
from email.message import EmailMessage

# --- Config ---
TRINITY_WINDOW_DAYS = 24
PRICE_LIMIT = 20
COOLOFF_DAYS = 7  # Days to exclude recently identified Trinity candidates
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ALL_HIGHS_DIR = os.path.join(DATA_DIR, "all_new_highs")
TRINITY_DIR = os.path.join(DATA_DIR, "trinity_candidates")

os.makedirs(ALL_HIGHS_DIR, exist_ok=True)
os.makedirs(TRINITY_DIR, exist_ok=True)

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")


def get_today_highs(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    rows, page = [], 1
    while True:
        r = requests.get(f"{url}&r={1+(page-1)*20}", headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")
        data = soup.select("tr[valign=top]")
        if not data:
            break
        for row in data:
            cells = row.find_all("td")
            if len(cells) > 8:
                try:
                    rows.append({
                        "Ticker": cells[1].text.strip(),
                        "Price": float(cells[8].text)
                    })
                except:
                    continue
        page += 1
        time.sleep(1)
    return pd.DataFrame(rows)


def detect_trinity(all_files, today_df):
    try:
        past_dfs = []
        for f in all_files:
            df = pd.read_csv(f)
            if not df.empty:
                past_dfs.append(df)
        if not past_dfs:
            return today_df.assign(Trinity=False)
        past = pd.concat(past_dfs)
    except Exception as e:
        print("Error reading past files:", e)
        return today_df.assign(Trinity=False)

    past['Date'] = pd.to_datetime(past['Date'])
    cutoff = datetime.now() - timedelta(days=TRINITY_WINDOW_DAYS)
    recent = past[past['Date'] >= cutoff]
    counts = recent.groupby('Ticker').size()
    today_df['Trinity'] = today_df['Ticker'].apply(lambda t: counts.get(t, 0) >= 3)
    return today_df


def find_first_signal_date(ticker, all_files):
    """Find the first date when a ticker appeared in the Trinity window"""
    try:
        past_dfs = []
        for f in all_files:
            df = pd.read_csv(f)
            if not df.empty:
                df['Date'] = pd.to_datetime(df['Date'])
                past_dfs.append(df)
        
        if not past_dfs:
            return None
            
        past = pd.concat(past_dfs)
        ticker_data = past[past['Ticker'] == ticker]
        
        if ticker_data.empty:
            return None
            
        # Sort by date and get the earliest appearance
        ticker_data = ticker_data.sort_values('Date')
        return ticker_data.iloc[0]['Date']
        
    except Exception as e:
        print(f"Error finding first signal date for {ticker}: {e}")
        return None


def get_price_at_date(ticker, target_date, all_files):
    """Get the price of a ticker on a specific date"""
    try:
        for f in all_files:
            df = pd.read_csv(f)
            if not df.empty:
                df['Date'] = pd.to_datetime(df['Date'])
                ticker_data = df[df['Ticker'] == ticker]
                
                if not ticker_data.empty:
                    # Find exact date match or closest date
                    exact_match = ticker_data[ticker_data['Date'] == target_date]
                    if not exact_match.empty:
                        return exact_match.iloc[0]['Price']
                    
                    # If no exact match, find closest date
                    ticker_data['Date_Diff'] = abs(ticker_data['Date'] - target_date)
                    closest = ticker_data.loc[ticker_data['Date_Diff'].idxmin()]
                    return closest['Price']
        
        return None
        
    except Exception as e:
        print(f"Error getting price for {ticker} on {target_date}: {e}")
        return None


def get_recent_trinity_candidates(cooloff_days=COOLOFF_DAYS):
    """Get list of tickers that were Trinity candidates in the last N days"""
    try:
        recent_candidates = set()
        cutoff_date = datetime.now() - timedelta(days=cooloff_days)
        
        trinity_files = glob.glob(os.path.join(TRINITY_DIR, "trinity_candidates_*.csv"))
        
        for file in trinity_files:
            try:
                # Extract date from filename
                basename = os.path.basename(file)
                date_str = basename.split("_")[-1].replace(".csv", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date >= cutoff_date:
                    df = pd.read_csv(file)
                    if not df.empty:
                        recent_candidates.update(df['Ticker'].tolist())
                        
            except Exception as e:
                print(f"Error reading Trinity file {file}: {e}")
                continue
        
        return list(recent_candidates)
        
    except Exception as e:
        print(f"Error getting recent Trinity candidates: {e}")
        return []


def detect_trinity_with_entry_window(all_files, today_df):
    """Enhanced Trinity detection with entry window evaluation and cooloff period"""
    # Apply cooloff period first
    recent_candidates = get_recent_trinity_candidates()
    if recent_candidates:
        print(f"🔄 Excluding {len(recent_candidates)} recent Trinity candidates: {', '.join(recent_candidates)}")
        today_df = today_df[~today_df['Ticker'].isin(recent_candidates)]
    
    # Your existing Trinity detection
    trinity_df = detect_trinity(all_files, today_df)
    
    # Add entry window evaluation for Trinity candidates
    trinity_candidates = trinity_df[trinity_df['Trinity']].copy()
    
    if trinity_candidates.empty:
        return trinity_df.assign(Entry_Status='N/A')
    
    # Initialize Entry_Status column
    trinity_df['Entry_Status'] = 'N/A'
    
    # Evaluate entry timing for each Trinity candidate
    for idx, row in trinity_candidates.iterrows():
        ticker = row['Ticker']
        current_price = row['Price']
        
        # Find when this ticker first appeared in last 24 days
        first_appearance = find_first_signal_date(ticker, all_files)
        
        if first_appearance is None:
            trinity_df.loc[idx, 'Entry_Status'] = 'NO_HISTORY'
            continue
            
        days_since_signal = (datetime.now() - first_appearance).days
        
        # Calculate price move since first signal
        first_price = get_price_at_date(ticker, first_appearance, all_files)
        
        if first_price is None or first_price == 0:
            trinity_df.loc[idx, 'Entry_Status'] = 'PRICE_ERROR'
            continue
            
        price_move_pct = (current_price - first_price) / first_price
        
        # Apply Mrkvicka's entry window rules
        if days_since_signal > 21:
            trinity_df.loc[idx, 'Entry_Status'] = 'EXPIRED'
        elif price_move_pct > 0.20:
            trinity_df.loc[idx, 'Entry_Status'] = 'EXTENDED_MOVE'
        elif days_since_signal > 14 and price_move_pct > 0.15:
            trinity_df.loc[idx, 'Entry_Status'] = 'LATE_STAGE'
        elif days_since_signal > 7 and price_move_pct > 0.10:
            trinity_df.loc[idx, 'Entry_Status'] = 'CAUTION'
        else:
            trinity_df.loc[idx, 'Entry_Status'] = 'GOOD_ENTRY'
        
        # Add additional info for debugging
        trinity_df.loc[idx, 'Days_Since_Signal'] = days_since_signal
        trinity_df.loc[idx, 'Price_Move_Pct'] = round(price_move_pct * 100, 2)
    
    return trinity_df


def send_email(subject, body, attachments=None):
    attachments = attachments or []
    if not (EMAIL_SENDER and EMAIL_PASSWORD and EMAIL_RECEIVER):
        print("❌ Missing email environment variables. Email not sent.")
        return

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    for file in attachments:
        try:
            with open(file, "rb") as f:
                msg.add_attachment(f.read(), maintype="application", subtype="octet-stream", filename=os.path.basename(file))
        except Exception as e:
            print(f"❌ Failed to attach file: {file}", e)

    print("EMAIL_SENDER is set:", EMAIL_SENDER is not None, file=sys.stderr)
    print("EMAIL_PASSWORD is set:", EMAIL_PASSWORD is not None, file=sys.stderr)
    print("EMAIL_RECEIVER is set:", EMAIL_RECEIVER is not None, file=sys.stderr)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print("✅ Email sent successfully.")
    except Exception as e:
        print("❌ Error sending email:", e)


def cleanup_old_files(folder, days_to_keep):
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    for file in glob.glob(os.path.join(folder, "*.csv")):
        try:
            basename = os.path.basename(file)
            date_str = basename.split("_")[-1].replace(".csv", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff_date:
                os.remove(file)
                print(f"🗑️ Deleted old file: {basename}")
        except Exception as e:
            print(f"Error parsing date from {file}: {e}")


def main():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"📅 Running Trinity strategy for: {today_str}")

    nasdaq_url = f"https://finviz.com/screener.ashx?v=111&s=ta_newhigh&f=exch_nasd,sh_price_u{PRICE_LIMIT}&o=-price"
    nyse_url = f"https://finviz.com/screener.ashx?v=111&s=ta_newhigh&f=exch_nyse,sh_price_u{PRICE_LIMIT}&o=-price"

    df_nasdaq = get_today_highs(nasdaq_url)
    df_nyse = get_today_highs(nyse_url)
    df_all = pd.concat([df_nasdaq, df_nyse], ignore_index=True)
    df_all['Date'] = today_str

    # Save daily highs ALWAYS
    all_file = os.path.join(ALL_HIGHS_DIR, f"all_new_highs_{today_str}.csv")
    df_all.to_csv(all_file, index=False)
    print(f"📁 Saved all highs to: {all_file}")

    # Detect Trinity candidates with enhanced logic
    all_past_files = sorted(glob.glob(os.path.join(ALL_HIGHS_DIR, "all_new_highs_*.csv")))
    df_trinity = detect_trinity_with_entry_window(all_past_files, df_all)

    trinity_count = df_trinity['Trinity'].sum()

    subject = f"📈 Trinity Scan Results – {today_str}"

    if trinity_count == 0:
        body = f"No Trinity candidates found today.\n\nTotal highs scanned: {len(df_all)}"
        send_email(subject, body)
    else:
        # Filter for actionable candidates (exclude expired/extended moves)
        actionable_candidates = df_trinity[
            (df_trinity['Trinity']) & 
            (~df_trinity['Entry_Status'].isin(['EXPIRED', 'EXTENDED_MOVE']))
        ]
        
        # Save all Trinity candidates with entry status
        trinity_file = os.path.join(TRINITY_DIR, f"trinity_candidates_{today_str}.csv")
        df_trinity[df_trinity['Trinity']].to_csv(trinity_file, index=False)
        print(f"📁 Saved Trinity candidates to: {trinity_file}")

        # Create detailed email body
        body_parts = [f"{trinity_count} Trinity candidate(s) found"]
        
        if not actionable_candidates.empty:
            body_parts.append(f"\n🎯 {len(actionable_candidates)} actionable candidates:")
            for _, row in actionable_candidates.iterrows():
                status_emoji = {
                    'GOOD_ENTRY': '✅',
                    'CAUTION': '⚠️',
                    'LATE_STAGE': '🟡'
                }.get(row['Entry_Status'], '❓')
                
                body_parts.append(
                    f"{status_emoji} {row['Ticker']} (${row['Price']:.2f}) - "
                    f"{row['Entry_Status']} "
                    f"({row.get('Days_Since_Signal', 'N/A')} days, "
                    f"{row.get('Price_Move_Pct', 'N/A')}% move)"
                )
        
        # Show excluded candidates
        excluded_candidates = df_trinity[
            (df_trinity['Trinity']) & 
            (df_trinity['Entry_Status'].isin(['EXPIRED', 'EXTENDED_MOVE']))
        ]
        
        if not excluded_candidates.empty:
            body_parts.append(f"\n❌ {len(excluded_candidates)} excluded candidates:")
            for _, row in excluded_candidates.iterrows():
                body_parts.append(
                    f"❌ {row['Ticker']} (${row['Price']:.2f}) - "
                    f"{row['Entry_Status']} "
                    f"({row.get('Days_Since_Signal', 'N/A')} days, "
                    f"{row.get('Price_Move_Pct', 'N/A')}% move)"
                )
        
        body_parts.append(f"\nTotal highs scanned: {len(df_all)}")
        body = "\n".join(body_parts)
        
        send_email(subject, body, attachments=[trinity_file])

    # Cleanup old files
    cleanup_old_files(ALL_HIGHS_DIR, days_to_keep=60)
    cleanup_old_files(TRINITY_DIR, days_to_keep=180)


if __name__ == "__main__":
    main()
