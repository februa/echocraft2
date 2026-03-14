# ECHOCRAFT Architecture

## 概要

ECHOCRAFTは海洋音響環境をデジタル上で再現するツール群である。  
Unix哲学に基づき、単一責務を持つ小さなコマンドの集合として設計する。

---

## 設計思想

### Unix哲学の適用

- 各ツールは**1つのことをうまくやる**
- ツール名は**責務（何をするか）**を表す。実装手段（どうやるか）を表してはならない
- ツールはパイプラインで連携できる
- 各ツールの内部実装言語はI/O契約が守られていれば問わない

### フロントエンドとバックエンドの分離

GUIは人間視点における見やすさ・使いやすさを前提とするため、テキストベースで世界を理解するAIとの協調開発と相性が悪い。  
ECHOCRAFTはGUIを持たず、標準入出力とファイルI/Oのみでツール間を連携する。

---

## レイヤー構造

ECHOCRAFTのツール群は**2つのレイヤー**に分類される。

```
Layer1: 信号生成・処理層  (prefix: ec-)
  海洋音響環境の再現と信号処理を担う
  パイプライン内にNDJSONフェーズとバイナリストリーミングフェーズを持つ

Layer2: 分析層           (prefix: eca-)
  生成・取得した信号に対する分析を担う
  stdin/stdout でNDJSONまたはバイナリストリームを扱う
```

### Layer1のパイプラインフェーズ

Layer1のパイプラインは `ec-sample` を境に2つのフェーズに分かれる。

```
NDJSONフェーズ（ec-sample より上流）
  場面定義・伝搬計算の結果をNDJSONで受け渡す
  データ量は軽い（1音源1行のJSONレコード）

バイナリストリーミングフェーズ（ec-sample 以降）
  離散化されたサンプルデータをバイナリ（raw PCM）で受け渡す
  ブロック単位でストリーミングし、全時間分を実体化しない
  ストリームのフォーマット情報は stream.json で各ツールに渡す
```

NDJSONとバイナリは同一パイプ上で混在できないため、`ec-sample` がフォーマット境界となる。
`ec-sample` はNDJSONを読み、バイナリストリームを書き出す。

### データ量の目安

```
全時間分の波形データ（一括保存する場合）
  1000ch × 48kHz × 120sec × 4byte ≒ 23GB
  → 全体をパイプに一括で流すことはしない
  → WAVファイルとして保存する場合は ec-to-wav を使う

ブロック単位の波形データ（ストリーミング時）
  1000ch × 128点 × 4byte ≒ 512KB/ブロック
  → パイプでブロック単位にストリーミング可能

分析結果（Layer2で扱う）
  {"peak_freq": 440.2, "snr_db": 12.3}
  → パイプに乗せられる
```

---

## 入出力フォーマット

### ファイル形式

#### 物理世界の記述

| ファイル | 内容 | 用途 |
|---------|------|------|
| `array.json` | センサの物理配置 | アレイ形状・座標 |
| `ocean.json` | 海洋環境パラメータ | 伝搬モデルへの入力 |

#### 処理系の設定

| ファイル | 内容 | 用途 |
|---------|------|------|
| `stream.json` | ストリームフォーマット定義 | バイナリストリームの解釈に必要なパラメータ |

#### 出力

| ファイル | 内容 | 用途 |
|---------|------|------|
| `*.wav` | マルチチャンネル波形データ | 信号の保存 |

#### array.json スキーマ

```json
{
  "sensors": [
    {"id": 0, "x": 0.0, "y": 0.0, "z": 0.0},
    {"id": 1, "x": 0.1, "y": 0.0, "z": 0.0}
  ]
}
```

#### stream.json スキーマ

```json
{
  "sample_rate": 32768,
  "rate": 256,
  "format": "float32"
}
```

`rate` は処理周期（Hz）。ブロックサイズは `sample_rate / rate` で導出する。
`ec-sample` 以降のバイナリストリーミングフェーズの全ツールが `--stream stream.json` で参照する。

#### ocean.json スキーマ

```json
{
  "sound_speed_profile": [
    {"depth": 0,   "speed": 1520.0},
    {"depth": 100, "speed": 1490.0},
    {"depth": 500, "speed": 1480.0}
  ],
  "bathymetry": {
    "depth": 200.0,
    "bottom_type": "sand"
  },
  "surface": {
    "sea_state": 3
  }
}
```

### NDJSONフォーマット

NDJSONフェーズのツール群はNDJSON（JSON Lines）を標準入出力で受け渡す。
1行1レコードの構造により、`jq`・`grep`・`awk`などUnixツールとの連携が可能。
Layer2の分析結果もNDJSONで出力される。

#### typeフィールド定義

| type | 用途 | 必須フィールド | 備考 |
|------|------|--------------|------|
| `source` | 音源定義 | `freq`, `sl`, `az`, `el` | `source_id` は持たない |
| `noise` | 雑音場定義 | `nl` | |
| `transfer` | 伝搬応答（遅延・損失） | `source_id`, `sensor_id`, `delay`, `loss_db` | `source_id` は `ec-propagate` が出現順で採番 |
| `spectrum` | 周波数スペクトル1点 | `freq`, `power_db` | |
| `scalar` | 単一の分析値 | `key`, `value`, `unit` | |

`source` レコードは識別子を持たない。下流の `ec-propagate` が `source` レコードの出現順に
`source_id` を採番し、`transfer` レコードに付与する。これにより複数の音源定義ツール
（`ec-source-nb` 等）の出力を結合しても、識別子の衝突が起きない。

#### NDJSONサンプル

```ndjson
{"type": "source", "freq": 100, "sl": 0, "az": 0, "el": 0}
{"type": "source", "freq": 2000, "sl": -10, "az": -30, "el": 0}
{"type": "noise", "nl": -20}
{"type": "spectrum", "freq": 0.0, "power_db": -10.2}
{"type": "spectrum", "freq": 1.0, "power_db": -8.1}
{"type": "scalar", "key": "peak_freq", "value": 440.2, "unit": "Hz"}
{"type": "scalar", "key": "snr", "value": 12.3, "unit": "dB"}
```

---

## ツール一覧

### Layer1: `ec-`（信号生成・処理）

#### 場面定義（パイプライン上流・NDJSONフェーズ）

疑似信号パイプラインの起点。海の中に何があるかを宣言する。

| ツール | 入力 | 出力 | 責務 |
|--------|------|------|------|
| `ec-source-nb` | パラメータ | NDJSON | 狭帯域音源定義（周波数・音圧レベル・方位） |
| `ec-noise` | NDJSON + パラメータ | NDJSON | 雑音場定義 |
| `ec-read` | WAV + array.json | バイナリストリーム | 実信号読み込み（実信号パイプラインの起点） |

将来の拡張として `ec-source-bb`（広帯域音源）等を別ツールとして追加する。
信号モデルごとにツールを分離し、個々のツールの肥大化を防ぐ。

#### 物理モデル（NDJSONフェーズ）

場面定義に物理法則を適用する。

| ツール | 入力 | 出力 | 責務 |
|--------|------|------|------|
| `ec-propagate` | NDJSON + ocean.json | NDJSON | 伝搬モデル適用（`source_id` を採番） |

#### 観測・離散化（NDJSONフェーズ → バイナリストリーミングフェーズ）

センサで観測し、連続モデルを離散化する。
`ec-sample` がNDJSON→バイナリのフォーマット境界となる。

| ツール | 入力 | 出力 | 責務 |
|--------|------|------|------|
| `ec-array` | NDJSON + array.json | NDJSON | アレイ応答・センサ特性の畳み込み |
| `ec-sample` | NDJSON + stream.json | バイナリストリーム | 連続モデル → 離散波形生成 |

#### 信号処理（バイナリストリーミングフェーズ）

離散化された信号に処理を適用する。

| ツール | 入力 | 出力 | 責務 |
|--------|------|------|------|
| `ec-beamform` | バイナリストリーム + array.json + stream.json | バイナリストリーム | ビームフォーミング |

#### I/O変換

ストリームとファイル間の変換を行う。

| ツール | 入力 | 出力 | 責務 |
|--------|------|------|------|
| `ec-to-wav` | バイナリストリーム + stream.json | WAV | バイナリストリーム → WAV変換 |
| `ec-write` | NDJSON | ファイル | 分析結果の保存 |

### Layer2: `eca-` （分析・パイプ）

**スペクトル系**

| ツール | 責務 |
|--------|------|
| `eca-spectrum` | 時間領域 → 周波数スペクトル変換 |
| `eca-peak-freq` | ピーク周波数抽出 |
| `eca-snr` | S/N推定 |
| `eca-integrate` | 時系列方向の積分（EMA等） |

**空間系**

| ツール | 責務 |
|--------|------|
| `eca-beam-pattern` | ビームパターン生成 |
| `eca-beamwidth` | メインローブ半減半角（-3dB幅） |
| `eca-sidelobe-level` | サイドローブレベル（dB） |

---

## パイプライン例

### 疑似信号生成 → ビームフォーミング → 分析（ブロックストリーミング）

生成から分析まで一本のパイプで接続する。WAVの実体化は不要。

```bash
ec-source-nb --freq 100,2000,3000 --sl 0,-10,-5 --az 0,-30,90 --el 0,0,0 \
  | ec-noise --nl -20 \
  | ec-propagate --env ocean.json --model plane-wave \
  | ec-array --array array.json \
  | ec-sample --stream stream.json --duration 10 \
  | ec-beamform --array array.json --stream stream.json \
  | eca-spectrum --stream stream.json \
  | eca-integrate --method ema --alpha 0.1 \
  | eca-peak-freq \
  | eca-snr \
  > result.ndjson
```

### WAV保存が必要な場合

`ec-to-wav` でストリームをファイルに書き出す。

```bash
ec-source-nb --freq 100,2000,3000 --sl 0,-10,-5 --az 0,-30,90 --el 0,0,0 \
  | ec-noise --nl -20 \
  | ec-propagate --env ocean.json --model plane-wave \
  | ec-array --array array.json \
  | ec-sample --stream stream.json --duration 10 \
  | ec-to-wav --stream stream.json --output signal.wav
```

### 複数音源定義ツールの結合

異なる信号モデルの音源を結合してパイプラインに流す。

```bash
{ ec-source-nb --freq 100 --sl 0 --az 0 --el 0
  ec-source-nb --freq 2000 --sl -10 --az -30 --el 0
} | ec-noise --nl -20 \
  | ec-propagate --env ocean.json --model plane-wave \
  | ec-array --array array.json \
  | ec-sample --stream stream.json --duration 10 \
  | ec-beamform --array array.json --stream stream.json \
  > /dev/null
```

### 実信号分析

```bash
ec-read signal.wav --array array.json --stream stream.json \
  | eca-spectrum --stream stream.json \
  | eca-peak-freq \
  > result.ndjson
```

### jqとの連携例（NDJSONフェーズ）

```bash
ec-source-nb --freq 100,2000,3000 --sl 0,-10,-5 --az 0,-30,90 --el 0,0,0 \
  | ec-noise --nl -20 \
  | ec-propagate --env ocean.json --model plane-wave \
  | jq 'select(.type == "transfer")'
```

---

## 伝搬モデルの切り替え設計

`ec-propagate` は `--model` オプションで伝搬モデルを切り替えられる。  
**I/Oインターフェースは固定**し、内部モデルのみ切り替わる。

| モデル | オプション値 | 精度 | 実装状況 |
|--------|------------|------|---------|
| 平面波近似 | `plane-wave` | 低（遠距離・単純環境向け） | 初期実装 |
| レイトレーシング | `ray-tracing` | 中（多層音速・マルチパス） | 将来対応 |
| 放物型方程式 | `parabolic-equation` | 高（複雑環境） | 将来対応 |

モデルを追加する際の影響範囲：

- `ec-propagate` 内部：モデル実装を追加
- `ocean.json`：モデル固有パラメータを追記
- **他のツール：変更不要**

---

## 実装言語に関する制約と指針

ECHOCRAFTはI/O契約（NDJSON / WAV / JSON）が守られていれば実装言語を問わない。  
ただし言語によってI/Oの扱いに差があるため、以下の制約を設ける。

### 言語別I/O対応

| 言語 | Layer1 | Layer2 | stdin/stdout |
|------|--------|--------|-------------|
| C++ | ○ | ○ | ネイティブ対応 |
| Python | ○ | ○ | ネイティブ対応 |
| MATLAB | ○ | 非推奨 | 扱いにくい |

### MATLABを使用する場合の指針

MATLABはstdin/stdoutの操作が他言語と比べて扱いにくいため、Layer2での使用は非推奨とする。  
MATLABでLayer2ツール群を実装する場合は、**Layer2の全ツールをMATLABで統一**し、パイプラインをファイルI/Oで代替すること。

```bash
# MATLABによるLayer2代替例
ec-read signal.wav array.json > tmp.ndjson
matlab -batch "eca_spectrum('tmp.ndjson', 'spec.ndjson')"
matlab -batch "eca_peak_freq('spec.ndjson', 'result.ndjson')"
```

### 混在禁止ルール

MATLABツールとC++/PythonツールをLayer2で混在させてはならない。  
混在が必要な場合は、変換器（`ec-to-wav`等）を明示的に挟み、I/O境界を明確にすること。
