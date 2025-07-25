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
    today_df['Trinity'] = today_df['Ticker'].apply(lambda t: counts.get(t, 0) >= 2)
    return today_df


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

    # Save daily highs
    all_file = os.path.join(ALL_HIGHS_DIR, f"all_new_highs_{today_str}.csv")
    df_all.to_csv(all_file, index=False)
    print(f"📁 Saved all highs to: {all_file}")

    # Detect Trinity candidates
    all_past_files = sorted(glob.glob(os.path.join(ALL_HIGHS_DIR, "all_new_highs_*.csv")))
    df_trinity = detect_trinity(all_past_files, df_all)

    trinity_file = os.path.join(TRINITY_DIR, f"trinity_candidates_{today_str}.csv")
    df_trinity[df_trinity['Trinity']].to_csv(trinity_file, index=False)
    print(f"📁 Saved Trinity candidates to: {trinity_file}")

    trinity_count = df_trinity['Trinity'].sum()
    subject = f"📈 Trinity Scan Results – {today_str}"

    if trinity_count == 0:
        body = f"No Trinity candidates found today.\n\nTotal highs scanned: {len(df_all)}"
        send_email(subject, body)
    else:
        tickers = ", ".join(df_trinity[df_trinity['Trinity']]['Ticker'].tolist())
        body = f"{trinity_count} Trinity candidate(s) found: {tickers}\n\nSee attached file for details."
        send_email(subject, body, attachments=[trinity_file])

    # Cleanup old files
    cleanup_old_files(ALL_HIGHS_DIR, days_to_keep=60)
    cleanup_old_files(TRINITY_DIR, days_to_keep=180)


if __name__ == "__main__":
    main()
