# Schwab Dividend Tax Calculator

シュワブ証券の配当金と源泉徴収税に関する計算と集計を行うツールです。

## 機能

- 複数アカウントの配当金データを一括処理
- 為替レートの自動適用（WSJのヒストリカルデータを使用）
- 以下の形式でのレポート出力：
  - 取引詳細CSV（dividend_tax_history.csv）
  - シンボル別サマリーCSV（dividend_tax_summary_by_symbol.csv）
  - コンソール出力（アカウント別集計と総合計）

## 必要条件

- Python 3.9以上

## インストール

```bash
# リポジトリのクローン
git clone https://github.com/yourusername/schwab-dividend-calculator.git
cd schwab-dividend-calculator

# パッケージのインストール
pip install -e .

# データディレクトリの作成
mkdir -p data
```

## 使い方

1. シュワブ証券から取引履歴をダウンロード：
   - シュワブのウェブサイトにログイン
   - History & Statements > Investment Income > Show Details
   - Export to JSONを選択（年ごと）
   - ダウンロードしたJSONファイルを作業ディレクトリに配置

2. WSJから為替レートデータをダウンロード：
   - https://www.wsj.com/market-data/quotes/fx/USDJPY/historical-prices にアクセス
   - "Download Historical Data"をクリック
   - CSVをダウンロードし、`data/HistoricalPrices.csv`として保存
   ```bash
   # ディレクトリ構造の例
   schwab-dividend-calculator/
   ├── data/
   │   └── HistoricalPrices.csv  # WSJからダウンロードしたデータ
   ├── src/
   │   └── schwab/
   └── ...
   ```
   - 為替レートファイルがない場合は、デフォルトレート（150円）が使用されます

3. プログラムの実行：

```bash
python -m schwab.main
```


## 出力ファイル

### dividend_tax_history.csv
取引ごとの詳細情報を含むCSVファイル：
- 日付
- アカウント
- シンボル
- 説明
- 種類（配当/利子）
- 総額（USD/JPY）
- 源泉徴収額（USD/JPY）
- 手取り額（USD/JPY）
- 再投資フラグ

### dividend_tax_summary_by_symbol.csv
シンボル（銘柄）ごとの集計情報：
- シンボル
- 説明
- 種類（配当/利子）
- 総額（USD/JPY）
- 源泉徴収額（USD/JPY）
- 手取り額（USD/JPY）
- 取引回数

## 注意事項

- 全ての金額はUSDとJPYの両方で計算されます
- 為替レートは取引日に基づいて適用されます
- 米国源泉徴収税（NRA Tax）が自動的に計算されます
- 再投資配当も正しく処理されます

## 開発者向け情報

### プロジェクト構造

```
schwab/
├── __init__.py
├── main.py
├── constants.py
├── models/
│   ├── __init__.py
│   └── dividend.py
├── processors/
│   ├── __init__.py
│   ├── exchange_rate.py
│   └── transaction.py
└── writers/
    ├── __init__.py
    ├── base.py
    ├── console.py
    ├── csv_report.py
    └── symbol_summary.py
```

### 新しいレポート形式の追加

1. `writers/base.py`の`ReportWriter`クラスを継承
2. `write`メソッドを実装
3. `main.py`の`writers`リストに新しいライターを追加

例：
```python
class NewReportWriter(ReportWriter):
    def write(self, records: List[DividendRecord]) -> None:
        # 新しい出力形式の実装
        pass
```

## ライセンス

MIT License

## 貢献

1. Forkを作成
2. 新しいブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -am 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成