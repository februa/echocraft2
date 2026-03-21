# ECHOCRAFT Design Guide

ツール実装時のクラス設計・コード構造の指針を定める。
言語共通の原則を先に示し、言語固有の実装パターンを後述する。

---

## 設計原則

### 1. I/Oとドメインロジックの分離

各ツールは「入力 → 変換 → 出力」のフィルタである。
ドメインロジック（変換）はI/O（入力・出力）を知らない。

```
main.py（I/O層）
  引数のパース、stdin/stdoutの接続、エラーハンドリング

domain class（ドメイン層）
  純粋な計算。ファイルやストリームへの参照を持たない
```

これにより:
- ドメインロジックのテストにI/Oのモックが不要になる
- 同じドメインロジックを異なるI/O（パイプ、ファイル、テスト）で再利用できる

### 2. レコードの不変性

パイプラインを流れるデータは不変（immutable）とする。
ツールは入力レコードを書き換えず、新しいレコードを生成して出力する。

```
入力: {"type": "source", "freq": 100, ...}
  ↓ ec-propagate
出力: {"type": "transfer", "source_id": 0, "delay": 0.001, ...}
```

入力の `source` レコードを変更するのではなく、新しい `transfer` レコードを生成する。

### 3. 依存方向の制約

```
tool → lib/common   OK（ツールが共有ライブラリを使う）
lib/common → tool   NG（共有ライブラリがツール固有の知識を持つ）
tool → tool          NG（ツール間の直接依存。パイプで連携する）
```

`lib/common/` にはI/O契約の実装（NDJSONパーサ等）とユーティリティのみ置く。
具体的には: `ndjson.py`（パーサ・ライタ）、`stream.py`（StreamConfig）、
`record.py`（レコードバリデーション）、`scenario.py`（ScenarioConfig）、`log.py`（ログ設定）。
ドメインロジックは各ツール内に閉じる。

### 4. クラスの分類

各ツールのクラスは以下の2種類に分類される。

**データクラス**: NDJSONレコードに対応する値の入れ物。不変。ロジックを持たない（シリアライズ用メソッドは例外）。

**ドメインクラス**: 変換の責務を持つ。入力データから出力データを生成する。I/Oを知らない。

### 5. エントリポイントの責務

`main.py` は以下だけを行う:
- 引数のパース
- I/Oストリームの接続（stdin/stdout/ファイル）
- ドメインクラスの生成と実行
- エラーハンドリングと終了コードの設定
- ログの初期化

`main.py` にドメインロジックを書かない。

---

## 言語別実装パターン

### Python

#### データクラス → dataclass (frozen)

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class SourceRecord:
    """狭帯域音源の定義レコード。"""
    freq: float
    sl: float
    az: float
    el: float
    type: str = field(default="source", init=False)

    def to_dict(self) -> dict:
        """NDJSON出力用の辞書に変換する。"""
        return {
            "type": self.type,
            "freq": self.freq,
            "sl": self.sl,
            "az": self.az,
            "el": self.el,
        }
```

`frozen=True` により生成後の書き換えを禁止する。

#### ドメインクラス → 純粋なクラス

```python
class NarrowbandSource:
    """狭帯域音源を生成するドメインクラス。"""

    def __init__(self, freq: float, sl: float, az: float, el: float) -> None:
        self._validate(freq, sl, az, el)
        self._record = SourceRecord(freq=freq, sl=sl, az=az, el=el)

    def to_record(self) -> SourceRecord:
        """音源レコードを返す。"""
        return self._record

    @staticmethod
    def _validate(freq: float, sl: float, az: float, el: float) -> None:
        if freq <= 0:
            raise ValueError(f"freq must be positive, got {freq}")
```

I/O（stdout, ファイル）への参照を持たない。

#### エントリポイント → main.py

```python
import sys
import argparse
from common.ndjson import NdjsonWriter
from common.logging import setup_logging
from ec_source_nb.source import NarrowbandSource

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Narrowband source definition")
    parser.add_argument("--freq", type=str, required=True)
    parser.add_argument("--sl", type=str, required=True)
    parser.add_argument("--az", type=str, required=True)
    parser.add_argument("--el", type=str, required=True)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(verbose=args.verbose)

    freqs = [float(f) for f in args.freq.split(",")]
    sls = [float(s) for s in args.sl.split(",")]
    azs = [float(a) for a in args.az.split(",")]
    els = [float(e) for e in args.el.split(",")]

    writer = NdjsonWriter(sys.stdout)
    for freq, sl, az, el in zip(freqs, sls, azs, els, strict=True):
        source = NarrowbandSource(freq=freq, sl=sl, az=az, el=el)
        writer.write(source.to_record().to_dict())

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

`parse_args` に `argv` を注入可能にすることで、テストからCLI引数を差し替えられる。

#### テストの構造

```python
# tests/test_source.py
from ec_source_nb.source import NarrowbandSource

class TestNarrowbandSource:
    """ドメインロジックのテスト。I/O不要。"""

    def test_to_record(self):
        source = NarrowbandSource(freq=100.0, sl=0.0, az=0.0, el=0.0)
        record = source.to_record()
        assert record.freq == 100.0
        assert record.type == "source"

    def test_negative_freq_raises(self):
        with pytest.raises(ValueError):
            NarrowbandSource(freq=-1.0, sl=0.0, az=0.0, el=0.0)
```

```python
# tests/test_main.py
import json
from io import StringIO
from ec_source_nb.main import main

class TestMain:
    """I/O統合テスト。"""

    def test_single_source_output(self, capsys):
        main(["--freq", "100", "--sl", "0", "--az", "0", "--el", "0"])
        output = capsys.readouterr().out
        record = json.loads(output.strip())
        assert record["type"] == "source"
        assert record["freq"] == 100.0
```

### C++（将来対応）

C++実装時も同じ原則に従う。

- データクラス → `struct` + `const` メンバ
- ドメインクラス → 純粋なクラス（I/O非依存）
- エントリポイント → `main.cpp`（引数パース + I/O接続）
- 不変性 → `const` 修飾 + コピーによる新レコード生成

具体的な実装パターンはC++ツール初回実装時に追記する。
