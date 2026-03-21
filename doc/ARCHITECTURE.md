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

ECHOCRAFTのツール群は**2つのレイヤーと1つの可視化カテゴリ**に分類される。

```
Layer1: 信号生成・処理層  (prefix: ec-)
  海洋音響環境の再現と信号処理を担う
  パイプライン内にNDJSONフェーズとバイナリストリーミングフェーズを持つ

Layer2: 分析層           (prefix: eca-)
  生成・取得した信号に対する分析を担う
  stdin/stdout でNDJSONまたはバイナリストリームを扱う

可視化: ファイルベース可視化  (prefix: ecv-)
  保存済みファイル（NDJSON・WAV・JSON）を読み、画像を生成する
  パイプラインには参加しない独立したツール群
```

Layer1・Layer2はパイプで合成可能（出力が次のツールの入力になる）。
ecv-* はパイプラインの終端ではなく、**保存済みファイルから独立して動作する**。
これにより同じデータに対して複数の可視化を並行して生成できる。

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

## 座標系

ECHOCRAFTは2つの座標系を使い分ける。

```
VESSEL_BODY（船体固定座標系）
  パイプライン内の全ツールが使用する座標系。
  アレイ形状の定義、遅延計算、ビームフォーミング、信号の方位指定に使う。

LOCAL_ENU（ワールド座標系）
  可視化ツール（ecv-*）が表示に使用する座標系。
  ヘディング θ を介して VESSEL_BODY から変換する。
```

### VESSEL_BODY（船体固定座標系）

| 軸 | 方向 | 説明 |
|----|------|------|
| x | 艦首（Forward） | 船の進行方向が正 |
| y | 右舷（Starboard） | 右が正、左舷は負 |
| z | 上（Up） | 鉛直上向き |

方位角の定義:
- **Az = 0°**: 艦首（+x方向）
- **Az = 90°**: 右舷（+y方向）
- **回転方向**: 時計回り正（上から見て）

方向ベクトル（平面波到来方向）:
```python
dx = cos(el) * cos(az)   # 艦首成分
dy = cos(el) * sin(az)   # 右舷成分
dz = sin(el)              # 上成分
```

この座標系を使うツール: `ec-source-nb`, `ec-array`, `ec-beamform`, `eca-bearing-level`

### LOCAL_ENU（ワールド座標系）

| 軸 | 方向 | 説明 |
|----|------|------|
| x | 東（East） | 東が正 |
| y | 北（North） | 北が正 |
| z | 上（Up） | 鉛直上向き |

方位角の定義:
- **Az = 0°**: 北（+y方向）
- **Az = 90°**: 東（+x方向）
- **回転方向**: 時計回り正

この座標系を使うツール: `ecv-scene`（表示用）

### 変換

VESSEL_BODY → LOCAL_ENU の変換にはヘディング θ（真北=0°、時計回り正）が必要:

```
真方位 = (相対方位 + ヘディング) mod 360

[East ]   [sin(θ)   cos(θ)] [x_body]
[North] = [cos(θ)  -sin(θ)] [y_body]
```

### array.json の座標系

`array.json` のセンサ位置 `(x, y, z)` は **VESSEL_BODY** で定義する。
x軸方向に並ぶラインアレイは艦首尾方向のアレイを意味する。

### source レコードの方位

`ec-source-nb` の `--az` で指定する方位は **VESSEL_BODY の相対方位**である。
Az=0° は艦首方向、Az=90° は右舷方向からの入射を意味する。

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
| `scenario.json` | 設定ファイルパスの束ね | 複数ツールへの設定パス一括指定 |

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

`rate` は処理周期（Hz）であり、同時に **周波数分解能 Δf** を直接決定する。

```
block_size = sample_rate / rate
Δf = sample_rate / block_size = sample_rate / (sample_rate / rate) = rate
```

すなわち `rate = Δf` である。`rate` を設定する際は以下の2つの観点を考慮する:

1. **周波数分解能**: Δf = rate Hz。対象信号の周波数間隔より十分小さい値を選ぶ
2. **時間分解能**: T_frame = 1 / rate 秒。BTR・LOFAR等の時間軸表示の更新間隔を決定する

`ec-sample` 以降のバイナリストリーミングフェーズの全ツールが `--stream stream.json` で参照する。

#### scenario.json スキーマ

```json
{
  "stream": "stream.json",
  "array": "array.json",
  "ocean": "ocean.json"
}
```

パイプライン上の各ツールは `--stream`, `--array`, `--env` で個別に設定ファイルを受け取る。
`scenario.json` はこれらのパスを1ファイルに束ねるオプションであり、`--scenario scenario.json` で指定する。

設計方針:
- パスは `scenario.json` の配置場所からの相対パスで解決する
- 個別フラグ（`--stream` 等）が指定された場合、scenario の値を上書きする
- 全フィールドは任意。ツールが必要としない設定は省略可能
- ツール内部から暗黙的に設定ファイルを探索しない。`--scenario` は明示的な指定である

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
| `spectrum` | 周波数スペクトル1点 | `freq`, `power_db`, `time` | `time` は秒単位（`block_index / rate`） |
| `bearing` | 方位レベル1点 | `azimuth`, `level_db`, `time` | `time` は秒単位（`block_index / rate`） |
| `scalar` | 単一の分析値 | `key`, `value`, `unit`, `time` | `time` は秒単位（`block_index / rate`） |

`source` レコードは識別子を持たない。下流の `ec-propagate` が `source` レコードの出現順に
`source_id` を採番し、`transfer` レコードに付与する。これにより複数の音源定義ツール
（`ec-source-nb` 等）の出力を結合しても、識別子の衝突が起きない。

#### time フィールド

Layer2の分析ツール（`eca-spectrum`, `eca-bearing-level` 等）が出力するレコードには
`time` フィールド（秒単位）を付与する。値は `block_index / rate` で算出する。
これにより ecv-* の時間軸プロット（BTR, LOFAR等）が時間情報を直接参照できる。

#### 線形振幅の扱い

`spectrum` レコードは `power_db`（dB）のみを保持する。
線形振幅（uPa）が必要な場合は、可視化ツール（ecv-*）側で `10^(power_db/20)` と逆変換する。
dBはパイプライン内の正規表現であり、線形振幅は表示上の都合として可視化ツールの責務とする。

#### NDJSONサンプル

```ndjson
{"type": "source", "freq": 100, "sl": 0, "az": 0, "el": 0}
{"type": "source", "freq": 2000, "sl": -10, "az": -30, "el": 0}
{"type": "noise", "nl": -20}
{"type": "spectrum", "freq": 0.0, "power_db": -10.2, "time": 0.5}
{"type": "spectrum", "freq": 256.0, "power_db": -8.1, "time": 0.5}
{"type": "bearing", "azimuth": 0.0, "level_db": -12.3, "time": 0.5}
{"type": "bearing", "azimuth": 1.0, "level_db": -15.7, "time": 0.5}
{"type": "scalar", "key": "peak_freq", "value": 440.2, "unit": "Hz", "time": 0.5}
{"type": "scalar", "key": "snr", "value": 12.3, "unit": "dB", "time": 0.5}
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
| `ec-beamform` | バイナリストリーム + array.json + stream.json | バイナリストリーム | 遅延和ビームフォーミング（DAS） |
| `ec-beamform-abf` | バイナリストリーム + array.json + stream.json | バイナリストリーム | 適応ビームフォーミング（ABF） |

#### I/O変換

ストリームとファイル間の変換を行う。

| ツール | 入力 | 出力 | 責務 |
|--------|------|------|------|
| `ec-to-wav` | バイナリストリーム + stream.json | WAV | バイナリストリーム → WAV変換 |
| `ec-write` | NDJSON | ファイル | 分析結果の保存 |

#### I/Oルーティング

バイナリストリームのファンアウト（1出力→N入力）を実現する。

| ツール | 入力 | 出力 | 責務 |
|--------|------|------|------|
| `ec-pub` | バイナリストリーム + array.json + stream.json | TCP（トピック） | ストリームをトピックに発行 |
| `ec-sub` | TCP（トピック） | バイナリストリーム | トピックからストリームを受信し stdout に書き出す |

`ec-pub` は stdin からバイナリブロックを読み、localhost TCP 経由で接続された
全サブスクライバにブロック単位でコピーを配信する。`ec-sub` は `ec-pub` が発行した
トピックに接続し、受信したブロックを stdout に書き出す。
`ec-sub` の stdout は通常のパイプラインに接続でき、シェルの合成可能性を維持する。

トピックの発見にはファイルベースのトピックレジストリ（`/tmp/echocraft/{name}.topic`）を使用する。
`ec-pub` がトピックファイルにポート番号を書き、`ec-sub` がそれを読んで接続する。

```bash
# ファンアウト例: 1つのストリームを3つの下流に分配
ec-source-nb ... | ec-noise ... | ec-propagate ... | ec-array ... \
  | ec-sample --stream stream.json --duration 1.0 \
  | ec-pub --stream stream.json --array array.json --topic demo --subscribers 3 &

ec-sub --topic demo | ec-beamform ... | eca-spectrum ... > spectrum.ndjson &
ec-sub --topic demo | eca-bearing-level ... > bearing.ndjson &
ec-sub --topic demo | ec-to-wav ... --output signal.wav &
wait
```

### Layer2: `eca-` （分析・パイプ）

**スペクトル系**

| ツール | 責務 |
|--------|------|
| `eca-spectrum` | 時間領域 → 周波数スペクトル変換 |
| `eca-peak-freq` | ピーク周波数抽出 |
| `eca-snr` | S/N推定 |
| `eca-integrate` | 時系列方向の積分（EMA等） |

**空間系**

| ツール | 入力 | 出力 | 責務 |
|--------|------|------|------|
| `eca-bearing-level` | バイナリストリーム + array.json + stream.json | NDJSON (bearing) | 全方位ビーム掃引 → 方位×レベル算出 |
| `eca-beam-pattern` | — | — | ビームパターン生成 |
| `eca-beamwidth` | — | — | メインローブ半減半角（-3dB幅） |
| `eca-sidelobe-level` | — | — | サイドローブレベル（dB） |

`eca-bearing-level` はバイナリストリームを読み、ブロックごとに指定方位範囲を掃引して
`bearing` レコードを出力する。`eca-spectrum` と同様にバイナリ→NDJSONの変換を担う分析ツール。

### 可視化: `ecv-`（ファイルベース可視化）

ecv-* はパイプラインに参加せず、保存済みファイルを入力として画像を生成する。
パイプラインの処理結果を保存してから、独立して実行する。

**設計方針**

- 入力はファイル（`--input`）。ツールごとに適切なファイル形式（NDJSON・WAV・JSON）を読む
- 出力は画像ファイル（`--output`）。形式は PNG/SVG 等
- パイプラインとは独立しているため、同じデータに対して複数の可視化を並行実行できる
- 線形振幅など表示スケールの変換は ecv-* の責務とする

| ツール | 入力 | 主要オプション | 責務 |
|--------|------|--------------|------|
| `ecv-spectrum` | NDJSON (spectrum) | `--scale linear\|log` | 周波数スペクトル表示（Linear/Log切替） |
| `ecv-bl` | NDJSON (bearing) | — | BL表示（方位×レベル） |
| `ecv-polar` | NDJSON (bearing) | — | 極座標表示（方位×レベル） |
| `ecv-btr` | NDJSON (bearing) | — | BTR表示（方位×時間×レベル、colormap: jet） |
| `ecv-lofar` | NDJSON (spectrum) | — | LOFAR表示（周波数×時間×レベル、colormap: jet） |

**軸定義**

| ツール | x軸 | y軸 | z軸（色） |
|--------|-----|-----|----------|
| `ecv-spectrum` (linear) | Frequency [Hz] (0–fs/2) | Amplitude [uPa] | — |
| `ecv-spectrum` (log) | Frequency [Hz] (0–fs/2) | Level [dB] | — |
| `ecv-bl` | Azimuth [deg] (0–180) | Level [dB/uPa] | — |
| `ecv-polar` | Azimuth [deg] (0–360, polar) | Level [dB/uPa] (radial) | — |
| `ecv-btr` | Azimuth [deg] (0–360) | Time [s] (0–T, inverted) | Level [dB/uPa] (jet) |
| `ecv-lofar` | Frequency [Hz] (0–fs/2) | Time [s] (0–T, inverted) | Level [dB/uPa] (jet) |

BTR・LOFARのy軸（時間）は逆方向（上が古い、下が新しい）とする。

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

### 適応ビームフォーミング（ABF）への差し替え

ビームフォーマを差し替えるだけでパイプラインの他の部分は変更不要。

```bash
ec-source-nb --freq 100,2000,3000 --sl 0,-10,-5 --az 0,-30,90 --el 0,0,0 \
  | ec-noise --nl -20 \
  | ec-propagate --env ocean.json --model plane-wave \
  | ec-array --array array.json \
  | ec-sample --stream stream.json --duration 10 \
  | ec-beamform-abf --array array.json --stream stream.json --method mvdr --reg 1e-3 \
  | eca-spectrum --stream stream.json \
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

### 処理結果の可視化

パイプラインで保存したファイルに対して、ecv-* を独立実行する。

```bash
# 1. 処理パイプラインでファイルを保存
# スペクトル分析結果
ec-source-nb --freq 100,2000 --sl 0,-10 --az 0,-30 --el 0,0 \
  | ec-noise --nl -20 \
  | ec-propagate --env ocean.json --model plane-wave \
  | ec-array --array array.json \
  | ec-sample --stream stream.json --duration 10 \
  | ec-beamform --array array.json --stream stream.json \
  | eca-spectrum --stream stream.json \
  > spectrum.ndjson

# 方位レベル分析結果
ec-source-nb --freq 100,2000 --sl 0,-10 --az 0,-30 --el 0,0 \
  | ec-noise --nl -20 \
  | ec-propagate --env ocean.json --model plane-wave \
  | ec-array --array array.json \
  | ec-sample --stream stream.json --duration 10 \
  | eca-bearing-level --array array.json --stream stream.json \
  > bearing.ndjson

# 2. 保存済みファイルから可視化（複数並行実行可能）
ecv-spectrum --input spectrum.ndjson --scale log --output spectrum_log.png
ecv-spectrum --input spectrum.ndjson --scale linear --output spectrum_linear.png
ecv-lofar --input spectrum.ndjson --output lofar.png
ecv-bl --input bearing.ndjson --output bl.png
ecv-polar --input bearing.ndjson --output polar.png
ecv-btr --input bearing.ndjson --output btr.png
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
| 無損失 | `lossless` | — （検証・キャリブレーション用） | 実装済み |
| 平面波近似 | `plane-wave` | 低（遠距離・単純環境向け） | 実装済み |
| レイトレーシング | `ray-tracing` | 中（多層音速・マルチパス） | 将来対応 |
| 放物型方程式 | `parabolic-equation` | 高（複雑環境） | 将来対応 |

モデルを追加する際の影響範囲：

- `ec-propagate` 内部：モデル実装を追加
- `ocean.json`：モデル固有パラメータを追記
- **他のツール：変更不要**

---

## ツール分離 vs オプション切り替えの判断基準

同じカテゴリの機能を追加する際、既存ツールにオプション（`--method` 等）を追加するか、
別ツールとして切り出すかの判断基準を以下に定める。

### オプション切り替えが適切な場合（例: `ec-propagate --model`）

- I/Oインターフェースが同一である
- CLIパラメータが共通している（モデル固有の引数が少ない）
- 内部状態の持ち方が同じである（ステートレス同士、ステートフル同士）
- ツール名の責務（何をするか）が同一で、手段（どうやるか）だけが異なる

`ec-propagate` はこの基準を満たす。伝搬モデル（平面波・レイトレーシング等）は
手段の違いであり、「伝搬損失を適用する」という責務は共通している。

### 別ツールとして切り出すべき場合（例: `ec-beamform` vs `ec-beamform-abf`）

以下のいずれかに該当する場合、別ツールにする。

1. **内部状態モデルが本質的に異なる**
   - DAS（遅延和）はブロック間に状態を持たない（ステートレス）
   - ABF（適応ビームフォーミング）は共分散行列の推定が必要で、ブロック間で状態を蓄積する（ステートフル）
   - この差は実装の詳細ではなく、ツールの振る舞いの本質的な違いである

2. **CLIパラメータが大幅に異なる**
   - ABFには正則化パラメータ、スナップショット数、アルゴリズム種別（MVDR/MPDR等）など、DASにはない引数が必要になる
   - 1つのツールに詰め込むと、片方のモード使用時に不要な引数が露出するか、引数の組み合わせ検証が複雑化する

3. **ツールの肥大化を招く**
   - 音源定義（`ec-source-nb` / `ec-source-bb`）と同じ判断基準
   - 信号モデルやアルゴリズムモデルが異なれば別ツールとする

### I/O契約の同一性は分離の障害にならない

`ec-beamform` と `ec-beamform-abf` はI/O契約が同一である
（マルチチャネルバイナリ入力 → 単チャネルバイナリ出力）。
パイプライン上で差し替えるだけで切り替えられる。

```bash
# DAS
... | ec-beamform --array array.json --stream stream.json | ...

# ABF（差し替えるだけ）
... | ec-beamform-abf --array array.json --stream stream.json --method mvdr --reg 1e-3 | ...
```

### 共通処理の共有

ツールを分離しても、共通処理（ステアリング遅延の計算等）は
`lib/common/` に切り出して共有する。ツールの分離はコードの重複を意味しない。

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
