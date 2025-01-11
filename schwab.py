import json
import csv
import glob
import os
from datetime import datetime
from typing import List, Dict, Any

def load_exchange_rates(filename: str = 'HistoricalPrices.csv') -> Dict[str, float]:
    """為替レートデータを読み込み、日付をキーとする辞書を返す"""
    exchange_rates = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            last_rate = None
            for row in reader:
                # 日付形式を変換 (MM/DD/YY -> MM/DD/YYYY)
                date_str = row['Date'].strip()
                if len(date_str.split('/')[2]) == 2:
                    month, day, year = date_str.split('/')
                    date_str = f"{month}/{day}/20{year}"
                
                # 終値を為替レートとして使用
                rate = float(row[' Close'])
                exchange_rates[date_str] = rate
                last_rate = rate
    except FileNotFoundError:
        print(f"警告: 為替レートファイル {filename} が見つかりません")
        return {}
    except Exception as e:
        print(f"為替レートファイルの読み込み中にエラーが発生しました: {str(e)}")
        return {}
    
    return exchange_rates

def get_exchange_rate(date: str, rates: Dict[str, float]) -> float:
    """指定された日付の為替レートを取得。ない場合は直前の日付のレートを返す"""
    if not rates:
        return 1.0  # 為替データがない場合はそのまま（1:1）で返す
        
    try:
        # 日付が直接あればその値を返す
        if date in rates:
            return rates[date]
        
        # 日付をdatetimeオブジェクトに変換
        target_date = datetime.strptime(date, '%m/%d/%Y')
        
        # 全ての日付を変換
        dated_rates = {datetime.strptime(d, '%m/%d/%Y'): r for d, r in rates.items()}
        
        # 対象日以前の最も近い日付を探す
        previous_dates = [d for d in dated_rates.keys() if d <= target_date]
        if not previous_dates:
            return list(rates.values())[0]  # データの最初の値を使用
            
        closest_date = max(previous_dates)
        return dated_rates[closest_date]
        
    except Exception as e:
        print(f"為替レート取得中にエラーが発生: {str(e)}")
        return 1.0

def load_transaction_data(filename: str) -> List[Dict[str, Any]]:
    """JSONファイルから取引データを読み込む"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            account = os.path.splitext(os.path.basename(filename))[0]
            transactions = data['BrokerageTransactions']
            for trans in transactions:
                trans['Account'] = account
            return transactions
    except Exception as e:
        print(f"ファイル {filename} の読み込み中にエラーが発生しました: {str(e)}")
        return []

def extract_dividend_and_tax(transactions: List[Dict[str, Any]], exchange_rates: Dict[str, float]) -> List[Dict[str, Any]]:
    """配当金、利子と源泉徴収を抽出して整理する"""
    dividend_tax_records = []
    temp_records = {}
    
    for trans in transactions:
        date = trans['Date'].split(' as of ')[0]
        action = trans['Action']
        symbol = trans['Symbol']
        description = trans['Description']
        account = trans.get('Account', 'Unknown')
        amount = float(trans['Amount'].replace('$', '').replace(',', '')) if trans['Amount'] else 0
        
        # 為替レートを取得
        rate = get_exchange_rate(date, exchange_rates)
        
        if action in ['Qualified Dividend', 'Cash Dividend', 'Reinvest Dividend', 'Credit Interest', 
                     'Bond Interest', 'Pr Yr Cash Div', 'Bank Interest'] or \
           (action in ['NRA Tax Adj', 'Pr Yr NRA Tax'] and amount < 0):
            
            key = (date, symbol if symbol else description, account)
            
            if key not in temp_records:
                temp_records[key] = {
                    'date': date,
                    'account': account,
                    'symbol': symbol,
                    'description': description,
                    'gross_amount': 0,
                    'tax': 0,
                    'type': 'Interest' if any(word in action for word in ['Interest', 'Bank']) else 'Dividend',
                    'reinvested': False,
                    'exchange_rate': rate
                }
            
            if action in ['NRA Tax Adj', 'Pr Yr NRA Tax']:
                temp_records[key]['tax'] = abs(amount)
            else:
                temp_records[key]['gross_amount'] = amount
                
            if action == 'Reinvest Dividend':
                temp_records[key]['reinvested'] = True

    for record in temp_records.values():
        if record['gross_amount'] > 0 or record['tax'] > 0:
            rate = record['exchange_rate']
            gross_usd = round(record['gross_amount'], 3)
            tax_usd = round(record['tax'], 3)
            net_usd = round(gross_usd - tax_usd, 3)
            
            gross_jpy = round(record['gross_amount'] * rate)
            tax_jpy = round(record['tax'] * rate)
            net_jpy = round(gross_jpy - tax_jpy)
            
            dividend_tax_records.append({
                'date': record['date'],
                'account': record['account'],
                'symbol': record['symbol'],
                'description': record['description'],
                'type': record['type'],
                'gross_amount_usd': gross_usd,
                'tax_usd': tax_usd,
                'net_amount_usd': net_usd,
                'exchange_rate': rate,
                'gross_amount_jpy': gross_jpy,
                'tax_jpy': tax_jpy,
                'net_amount_jpy': net_jpy,
                'reinvested': 'Yes' if record['reinvested'] else 'No'
            })
    
    dividend_tax_records.sort(key=lambda x: datetime.strptime(x['date'], '%m/%d/%Y'))
    
    return dividend_tax_records

def write_to_csv(records: List[Dict[str, Any]], filename: str = 'dividend_tax_history.csv'):
    """レコードをCSVファイルに出力する"""
    fieldnames = ['date', 'account', 'symbol', 'description', 'type', 
                 'gross_amount_usd', 'tax_usd', 'net_amount_usd',
                 'exchange_rate', 'gross_amount_jpy', 'tax_jpy', 'net_amount_jpy',
                 'reinvested']
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

def print_summary(records: List[Dict[str, Any]]):
    """集計結果を表示する"""
    print("\n=== 集計結果 ===")
    
    account_summary = {}
    for record in records:
        account = record['account']
        if account not in account_summary:
            account_summary[account] = {
                'dividend_usd': 0,
                'interest_usd': 0,
                'tax_usd': 0,
                'dividend_jpy': 0,
                'interest_jpy': 0,
                'tax_jpy': 0
            }
        
        if record['type'] == 'Dividend':
            account_summary[account]['dividend_usd'] += record['gross_amount_usd']
            account_summary[account]['dividend_jpy'] += record['gross_amount_jpy']
        else:
            account_summary[account]['interest_usd'] += record['gross_amount_usd']
            account_summary[account]['interest_jpy'] += record['gross_amount_jpy']
        account_summary[account]['tax_usd'] += record['tax_usd']
        account_summary[account]['tax_jpy'] += record['tax_jpy']
    
    for account, summary in account_summary.items():
        print(f"\nアカウント: {account}")
        print(f"配当金合計: ${round(summary['dividend_usd'], 3):,.3f} (¥{round(summary['dividend_jpy']):,})")
        print(f"利子合計: ${round(summary['interest_usd'], 3):,.3f} (¥{round(summary['interest_jpy']):,})")
        print(f"源泉徴収合計: ${round(summary['tax_usd'], 3):,.3f} (¥{round(summary['tax_jpy']):,})")
        net_usd = round(summary['dividend_usd'] + summary['interest_usd'] - summary['tax_usd'], 3)
        net_jpy = round(summary['dividend_jpy'] + summary['interest_jpy'] - summary['tax_jpy'])
        print(f"手取り合計: ${net_usd:,.3f} (¥{net_jpy:,})")
    
    total_dividend_usd = round(sum(summary['dividend_usd'] for summary in account_summary.values()), 3)
    total_interest_usd = round(sum(summary['interest_usd'] for summary in account_summary.values()), 3)
    total_tax_usd = round(sum(summary['tax_usd'] for summary in account_summary.values()), 3)
    total_dividend_jpy = round(sum(summary['dividend_jpy'] for summary in account_summary.values()))
    total_interest_jpy = round(sum(summary['interest_jpy'] for summary in account_summary.values()))
    total_tax_jpy = round(sum(summary['tax_jpy'] for summary in account_summary.values()))
    
    print("\n=== 総合計 ===")
    print(f"配当金合計: ${total_dividend_usd:,.3f} (¥{total_dividend_jpy:,})")
    print(f"利子合計: ${total_interest_usd:,.3f} (¥{total_interest_jpy:,})")
    print(f"源泉徴収合計: ${total_tax_usd:,.3f} (¥{total_tax_jpy:,})")
    net_total_usd = round(total_dividend_usd + total_interest_usd - total_tax_usd, 3)
    net_total_jpy = round(total_dividend_jpy + total_interest_jpy - total_tax_jpy)
    print(f"手取り合計: ${net_total_usd:,.3f} (¥{net_total_jpy:,})")

def main():
    try:
        # 為替レートの読み込み
        exchange_rates = load_exchange_rates()
        if not exchange_rates:
            print("警告: 為替レートデータが読み込めませんでした。USD金額のみで処理を継続します。")
        
        # JSONファイルのパターンを指定
        json_files = glob.glob('*.json')
        
        if not json_files:
            print("処理対象のJSONファイルが見つかりませんでした。")
            return
        
        # 全てのファイルから取引データを読み込む
        all_transactions = []
        for file in json_files:
            print(f"ファイル {file} を処理中...")
            transactions = load_transaction_data(file)
            all_transactions.extend(transactions)
        
        # 配当と税金の記録を抽出
        dividend_tax_records = extract_dividend_and_tax(all_transactions, exchange_rates)
        
        # CSVファイルに出力
        output_filename = 'dividend_tax_history.csv'
        write_to_csv(dividend_tax_records, output_filename)
        
        # 集計結果を表示
        print(f"\n{len(json_files)}個のファイルから{len(dividend_tax_records)}件のレコードを処理しました。")
        print(f"結果は {output_filename} に出力されました。")
        
        # 詳細な集計を表示
        print_summary(dividend_tax_records)
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main()
