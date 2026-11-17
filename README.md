# マカ錬金 未来視（オフライン版） / Melding Pot Future Vision (Offline)

モンスターハンターワイルズの「マカ錬金」で、これから出現する護石を予測するツールです。
単一の HTML ファイルだけで動作し、通信は一切行いません。ゲーム本体や MOD は不要です。

A fan-made, offline predictor for Monster Hunter Wilds talisman melding (Maka / Melding Pot).
It runs as a single HTML file with no network access. No game mod is required.

## 使い方 / Usage

そのままブラウザで開くだけで使えます（GitHub Pages で公開されている場合はその URL を開くだけ）。

### 予測する

1. 「基準seed」と「現在のカウンタ」を入力します
   - 基準seed はセーブデータごとに決まっている値で、公開ツール **Gogma Seed Finder** が表示する基準seed と同じものです
   - 基準seed が分からない場合は、下記の「基準seed・カウンタ位置の特定」で、実際に錬金した護石の記録から割り出せます
2. 「予測する」を押すと、これから出る護石が順番に一覧表示されます（次に錬金する1個目が、そのカウンタ値の結果です）

### seed・カウンタが分からないとき

「基準seed・カウンタ位置の特定」に、直近で連続して錬金した護石3件を古い順に入力すると、基準seed が入力されていればカウンタ位置を、未入力なら基準seedを特定できます（基準seedの特定にはスロットの入力が必要です）。見つかった値はそのまま予測にセットできます。

### 探す・登録する

- スキル条件・スロット条件・レア度（レア5〜8）で絞り込みができます
- 「条件に一致する護石を検索」で、一覧の範囲より先（最大で現在カウンタから 1,000 万件先まで）を検索できます
- 気になる護石は ☆ でお気に入りに登録できます

## 特徴

- **完全オフライン**: 単一 HTML ファイル、外部通信なし。入力した seed・カウンタ・お気に入りはブラウザ内（localStorage）にだけ保存されます
- **3言語対応**: 日本語 / English / 簡体中文（画面右上のボタンで切替）
- 予測モデルは実測データで検証済みです

## ファイル構成

- `index.html` — ツール本体（このファイル1つで動作します）
- `src/` — seed 特定エンジン（WASM）のソースコード。構成とビルド方法は `src/README.md` を参照
- `LICENSE` — MIT ライセンス

## ライセンス / License

MIT License — Copyright (c) 2026 fujima

## 免責 / Disclaimer

本ツールはファンメイドの非公式ツールであり、CAPCOM とは一切関係ありません。
「モンスターハンターワイルズ」「MONSTER HUNTER WILDS」は株式会社カプコンの商標または登録商標です。

This is an unofficial fan-made tool and is not affiliated with CAPCOM.
MONSTER HUNTER WILDS is a trademark of CAPCOM CO., LTD.
