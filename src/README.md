# 護石 seed 復元ツール — ソース構成

## ファイル
- `seedfind2.c` — ネイティブ版の単一ソース (探索コア + スカラ参照実装 + 自己テスト + CLI)。
  ビルド: `gcc -O3 -march=native -fopenmp -o seedfind2 seedfind2.c`
  使い方: `seedfind2 <obs.txt> <カウンタ上限W> <seed_lo> <seed_hi> [--selftest]`
  obs.txt は1行1護石 `id1 lv1 id2 lv2 id3 lv3 sl1 sl2 sl3` (連続錬金・古い順)
- `tables.h` — モデルテーブル (Ptマスター124行 + スキルセグメント)。charm_model_data.json から生成
- `gen_core.py` — seedfind2.c から WASM 用コア `seedfind_core.inc` を切り出す
- `seedfind_api.inc` — WASM export API (sf_set_obs / sf_begin / sf_step / sf_cursor / sf_found_* / sf_compat*)
- `seedfind_wasm.c` — スカラWASM用エントリ (freestanding)。64 seed 同時処理
- `gen_simd.py` — コアを v128 化して `seedfind_core_simd.inc` / `seedfind_api_simd.inc` を生成 (128 seed 同時)
- `seedfind_wasm_simd.c` — SIMD WASM用エントリ
- `build_html.py` — seedfind.wasm / seedfind_simd.wasm / スキル一覧を埋め込んで単一HTMLを生成

## WASM ビルド (ziglang 同梱 clang を使用)
```
python3 -m ziglang cc -target wasm32-freestanding -O3 -nostdlib -Wl,--no-entry -o seedfind.wasm seedfind_wasm.c
python3 -m ziglang cc -target wasm32-freestanding -O3 -msimd128 -nostdlib -Wl,--no-entry -o seedfind_simd.wasm seedfind_wasm_simd.c
```

## 探索アルゴリズム概要
- マスター生成器は xorshift128 変種。seed ごとに初期状態を作り、カウンタ位置ごとに7出力ずつ進める
- 64/128 seed をビットスライスで同時処理 (プレーン = レーンのビット列)
- 2段プリフィルタ: 観測1・2個目について「なり得るPt行 (互換行)」を事前に計算し、
  各位置では第1出力 out1 の剰余 (out1 % セグメント長) が互換行と一致する候補だけを残す。
  2段とも通過した候補だけを抜き出し、スカラ実装で K 個の窓を完全検証する
- カウンタ範囲 [wlo, whi) は「窓の開始位置」の範囲として適用される (範囲外は窓を開始しない)
