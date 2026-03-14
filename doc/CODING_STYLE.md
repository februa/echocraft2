# ECHOCRAFT Coding Style

言語ごとのコーディング規約を定める。
言語共通のルールを先に示し、言語固有の規約を後述する。

---

## 共通規約

### ログ

- ログはstderrに出力する（stdoutはデータパスとして予約）
- ログレベル: `--verbose` フラグでDEBUGに切り替え可能とする
- パイプラインの動作を妨げないために、ログは絶対にstdoutに出さない

### エラー処理

- 想定外の入力には明確なエラーメッセージをstderrに出力し、非ゼロの終了コードで終了する
- 例外を握りつぶさない
- パイプの途中でエラーが起きた場合、下流に不正なデータを流さない

### 命名規則

- ツール名: `ec-source-nb`（ケバブケース）
- ツールのディレクトリ・モジュール名: `ec_source_nb`（スネークケース、言語の慣習に従う）
- 定数: UPPER_SNAKE_CASE
- 非公開メンバ: 言語の慣習に従う（Python: `_prefix`, C++: `private`セクション）

### テスト

- 各ツールの `tests/` ディレクトリにテストを配置する
- テストデータはリポジトリ内に配置し、外部依存しない
- CIでの自動実行を前提とする
- テストの種類:
  - 単体テスト: 内部ロジックの検証
  - I/Oテスト: NDJSON/バイナリの入出力契約の検証
  - パイプラインテスト: 他ツールとの結合時の動作検証

---

## Python

### バージョン・ツール

- Python 3.10以上を対象とする
- フォーマッタ: ruff format
- リンタ: ruff check
- テストフレームワーク: pytest

### 型・ドキュメント

- 型ヒントを必須とする（関数シグネチャ、クラス属性）
- docstringはGoogle styleとする

### ファイル構成

- 1ファイル1クラスを基本とする（ユーティリティ関数は例外）
- エントリポイント: `ec-source-nb` → `ec_source_nb/main.py`

### 命名規則

- クラス: PascalCase
- 関数・変数: snake_case
- 定数: UPPER_SNAKE_CASE
- 非公開メンバ: `_prefix`

### ログ

- 標準ライブラリの `logging` を使用する
- ハンドラは `logging.StreamHandler(sys.stderr)` とする

### エラー処理

- バリデーションエラーは `ValueError` を送出する
- `main()` でキャッチし、stderrにメッセージを出力して `sys.exit(1)` する
- `except Exception` での握りつぶしは禁止

---

## C++（将来対応）

具体的な規約はC++ツール初回実装時に追記する。以下は方針のみ。

### 方針

- C++17以上を対象とする
- ビルドシステム: CMake
- 型安全を最大限に活用する（`const`修飾、`std::optional`、`std::variant`）
- メモリ管理: スマートポインタを優先する（`std::unique_ptr`, `std::shared_ptr`）

### 命名規則（予定）

- クラス: PascalCase
- 関数・変数: snake_case
- 定数: UPPER_SNAKE_CASE
- 名前空間: `echocraft::`
