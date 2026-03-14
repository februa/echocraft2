# CLAUDE.md

このファイルはClaudeがECHOCRAFTプロジェクトで作業する際の指針を定める。

---

## 開発環境

- OS: Windows
- シェル: Git Bash（パイプラインのバイナリストリーミングを正しく扱うため）
- エディタ: Neovim
- 実装言語: Python（初期実装）
- テスト: pytest
- パッケージ管理: pip + requirements.txt

---

## 設計原則

### Claudeへの必須要求

- 実装より先にARCHITECTURE.mdとの設計整合性を確認すること
- エラーに対して「とりあえず動くコード」を作らないこと
- 不明点は仮定を明示した上で提案すること
- UI変更は必ず設計意図を言語化すること
- 「普通こうする」「一般的には」を理由に設計を壊さないこと
- ユーザの提案が設計を壊す場合、理由を説明して却下すること

### 設計思想

- Unix哲学に従う（ARCHITECTURE.md参照）
- クラス設計・責務分離はDESIGN.mdに従う
- プロトタイプでもクラス設計・責務分離を重視する
- API・ログ・エクスポートは最初から設計に含める
- デバッグ・テスト駆動を最初から設計に含める
- フロントエンドとバックエンドは明確に区別する

---

## ディレクトリ構成

```
root/
  tools/                        # ツールごとに独立したディレクトリ
    ec_source_nb/               #   Python実装の例
      pyproject.toml            #     ツール単体のパッケージ定義
      ec_source_nb/             #     ソースコード
        __init__.py
        main.py                 #       エントリポイント
      tests/                    #     ツール固有のテスト
    ec_beamform/                #   将来C++実装の例
      CMakeLists.txt
      src/
      tests/

  lib/                          # ツール間共有ライブラリ
    common/
      __init__.py
      ndjson.py                 #   NDJSONパーサ・ライタ
      stream.py                 #   stream.jsonローダ
      logging.py                #   ログ設定ヘルパー

  bin/                          # ラッパースクリプト（言語を隠蔽）
    ec-source-nb                #   #!/bin/bash → exec python -m ec_source_nb "$@"

  configs/                      # 設定ファイルのサンプル
    stream.json
    array.json
    ocean.json

  Makefile                      # 全ツールのビルド・インストールを束ねる
  requirements.txt              # Python全体の依存（開発用）
```

### 設計方針

- ツール1つ = `tools/` 配下の1ディレクトリ。言語固有のビルド定義はツール内に閉じる
- `bin/` のラッパースクリプトにより、呼び出し側は実装言語を意識しない
- `lib/common/` にツール間で共有するコード（NDJSONパーサ、stream.jsonローダ等）を置く
- テストは各ツールの `tests/` に配置する。`pytest tools/*/tests/` で一括実行可能
- `Makefile` が各ツールの言語に応じたビルドコマンドを呼び分ける

---

## コーディング規約

CODING_STYLE.md を参照。言語共通のルールと言語別の規約を定義している。

---

## Git運用

- ブランチ命名: `feature/ツール名`, `fix/概要`, `docs/概要`
- コミットメッセージ: 英語、動詞で始める（例: "Add ec-source-nb initial implementation"）
- mainへの直接pushは禁止
