#!/usr/bin/env python3
"""seedfind_core.inc から SIMD (v128, 128レーン) 版 seedfind_core_simd.inc を生成"""
import pathlib
HERE = pathlib.Path(__file__).parent
s = (HERE / 'seedfind_core.inc').read_text()

def rep(old, new, cnt=1):
    global s
    assert old in s, 'NOT FOUND: ' + old[:70]
    s = s.replace(old, new, cnt)

# ビットスライス節以降だけを対象にする (スカラ部は触らない)
head, sep, tail = s.partition('/* ---------- ビットスライス基盤 ---------- */')
assert sep
s = tail

def trep(old, new, cnt=1):
    global s
    assert old in s, 'NOT FOUND(tail): ' + old[:70]
    s = s.replace(old, new, cnt)

trep('static void bs_add(const uint64_t *a, int na, const uint64_t *b, int nb, uint64_t *out, int *nout) {',
     'static void bs_add(const v128_t *a, int na, const v128_t *b, int nb, v128_t *out, int *nout) {')
trep('  uint64_t carry = 0;', '  v128_t carry = PL_ZERO;')
trep('    uint64_t av = i < na ? a[i] : 0, bv = i < nb ? b[i] : 0;',
     '    v128_t av = i < na ? a[i] : PL_ZERO, bv = i < nb ? b[i] : PL_ZERO;')
trep('static void cond_sub(uint64_t *v, int vw, int p) {', 'static void cond_sub(v128_t *v, int vw, int p) {')
trep('    uint64_t higher = 0;', '    v128_t higher = PL_ZERO;')
trep('    uint64_t ge = ', '    v128_t ge = ')
trep('    if (!ge) return;', '    if (!wasm_v128_any_true(ge)) return;')
trep('    uint64_t sub[8], borrow = 0;', '    v128_t sub[8], borrow = PL_ZERO;')
trep('      uint64_t sb = i < sbits ? ge : 0;', '      v128_t sb = i < sbits ? ge : PL_ZERO;')
trep('static void bs_mod3(const uint64_t *x, uint64_t out[2]) {', 'static void bs_mod3(const v128_t *x, v128_t out[2]) {')
trep('static void bs_mod7(const uint64_t *x, uint64_t out[3]) {', 'static void bs_mod7(const v128_t *x, v128_t out[3]) {')
trep('  uint64_t cur[16][6]; int cw[16];', '  v128_t cur[16][6]; int cw[16];')
trep('  uint64_t cur[16][8]; int cw[16];', '  v128_t cur[16][8]; int cw[16];')
s = s.replace('  uint64_t v[8]; int vw = cw[0];', '  v128_t v[8]; int vw = cw[0];')
s = s.replace('uint64_t hi[8], lo[2], s[9]; int sw;', 'v128_t hi[8], lo[2], s[9]; int sw;')
s = s.replace('uint64_t hi[8], lo[3], s[9]; int sw;', 'v128_t hi[8], lo[3], s[9]; int sw;')
s = s.replace('sizeof(uint64_t) * cw[cnt-1]', 'sizeof(v128_t) * cw[cnt-1]')
s = s.replace('sizeof(uint64_t) * vw', 'sizeof(v128_t) * vw')
s = s.replace('sizeof(uint64_t) * sw', 'sizeof(v128_t) * sw')
trep('static inline uint64_t eq_const(const uint64_t *pl, int width, int value) {',
     'static inline v128_t eq_const(const v128_t *pl, int width, int value) {')
trep('  uint64_t m = ~0ULL;', '  v128_t m = PL_ALL;')
trep('static uint64_t prefilter(const uint64_t *o1, const Compat *c) {',
     'static v128_t prefilter(const v128_t *o1, const Compat *c) {')
trep('  uint64_t mask = 0, r3[2], r7[3];', '  v128_t mask = PL_ZERO, r3[2], r7[3];')
trep('    uint64_t m;', '    v128_t m;')
trep('static __thread uint64_t ring[RING][32];', 'static v128_t ring[RING][32];')
trep('static __thread int comp_[4], free_;', 'static int comp_[4], free_;')
trep('  const uint64_t *X = ring[comp_[0]], *W = ring[comp_[3]];',
     '  const v128_t *X = ring[comp_[0]], *W = ring[comp_[3]];')
trep('  uint64_t *NW = ring[free_];', '  v128_t *NW = ring[free_];')
trep('  uint64_t T[32];', '  v128_t T[32];')
# scatter / extract / const_planes を丸ごと差し替え
trep('''static void scatter(uint64_t *pl, const uint32_t *vals) {
  for (int p = 0; p < 32; p++) pl[p] = 0;
  for (int i = 0; i < 64; i++) {
    uint32_t v = vals[i];
    while (v) { int p = __builtin_ctz(v); pl[p] |= 1ULL << i; v &= v - 1; }
  }
}''', '''static void scatter(v128_t *pl, const uint32_t *vals) {
  uint64_t tmp[64];
  for (int p = 0; p < 64; p++) tmp[p] = 0;
  for (int i = 0; i < 128; i++) {
    uint32_t v = vals[i];
    while (v) { int p = __builtin_ctz(v); tmp[2*p + (i >> 6)] |= 1ULL << (i & 63); v &= v - 1; }
  }
  for (int p = 0; p < 32; p++) pl[p] = wasm_v128_load(&tmp[2*p]);
}''')
trep('''static uint32_t extract(const uint64_t *pl, int lane) {
  uint32_t v = 0;
  for (int p = 0; p < 32; p++) v |= (uint32_t)((pl[p] >> lane) & 1) << p;
  return v;
}''', '''static uint32_t extract(const v128_t *pl, int lane) {
  uint32_t v = 0;
  int half = lane >> 6, bit = lane & 63;
  for (int p = 0; p < 32; p++) { uint64_t w = half ? (uint64_t)wasm_i64x2_extract_lane(pl[p], 1) : (uint64_t)wasm_i64x2_extract_lane(pl[p], 0); v |= (uint32_t)((w >> bit) & 1) << p; }
  return v;
}''')
trep('static void const_planes(uint64_t *pl, uint32_t c) {', 'static void const_planes(v128_t *pl, uint32_t c) {')
trep('pl[p] = (c >> p) & 1 ? ~0ULL : 0;', 'pl[p] = (c >> p) & 1 ? PL_ALL : PL_ZERO;')
trep('  uint64_t E[32], C[32], D[32], R8[32], R9[32], R10[32], R11[32];',
     '  v128_t E[32], C[32], D[32], R8[32], R9[32], R10[32], R11[32];')
trep('  uint32_t ev[64];', '  uint32_t ev[128];')
trep('for (int i = 0; i < 64; i++) ev[i] = (base + i) ^ 0xAC9365u;',
     'for (int i = 0; i < 128; i++) ev[i] = (base + i) ^ 0xAC9365u;')
trep('  uint64_t R10N[32], R11N[32], EN[32], C1[32], R10B[32], CN[32];',
     '  v128_t R10N[32], R11N[32], EN[32], C1[32], R10B[32], CN[32];')
trep('    uint64_t e0 = E[0], e1 = E[1];', '    v128_t e0 = E[0], e1 = E[1];')
trep('    uint64_t mk[4] = ', '    v128_t mk[4] = ')
trep('      uint64_t cp = 0;', '      v128_t cp = PL_ZERO;')
# プレーン式中の `: 0)` を一括で PL_ZERO 化 (この節内は全てプレーン式)
s = s.replace(': 0)', ': PL_ZERO)')
# scan_batch
trep('''  uint64_t lane_mask = 0;
  for (int i = 0; i < 64; i++) if (base + i < hi && base + i < 100000000u) lane_mask |= 1ULL << i;
  uint64_t pending = 0;''', '''  uint64_t lm[2] = {0, 0};
  for (int i = 0; i < 128; i++) if (base + i < hi && base + i < 100000000u) lm[i >> 6] |= 1ULL << (i & 63);
  v128_t lane_mask = wasm_v128_load(lm);
  v128_t pending = PL_ZERO;''')
trep('    const uint64_t *o1 = ring[o1_idx];', '    const v128_t *o1 = ring[o1_idx];')
trep('''    if (pending) {
      uint64_t m2 = prefilter(o1, &COMPAT1) & pending;
      while (m2) {
        int lane = __builtin_ctzll(m2);
        m2 &= m2 - 1;''', '''    if (wasm_v128_any_true(pending)) {
      v128_t m2v = prefilter(o1, &COMPAT1) & pending;
      uint64_t m2w[2] = {(uint64_t)wasm_i64x2_extract_lane(m2v, 0), (uint64_t)wasm_i64x2_extract_lane(m2v, 1)};
      for (int half = 0; half < 2; half++) {
        uint64_t m2 = m2w[half];
        while (m2) {
        int lane = half * 64 + __builtin_ctzll(m2);
        m2 &= m2 - 1;''')
trep('''        if (window_matches(st, OBS, Kglob)) {
          if (FOUND_N < 4096) { FOUND_SEEDS[FOUND_N] = base + lane; FOUND_CTS[FOUND_N] = (int32_t)(pos - 1); FOUND_N++; }
          (*found_out)++;
        }
      }
    }''', '''        if (window_matches(st, OBS, Kglob)) {
          if (FOUND_N < 4096) { FOUND_SEEDS[FOUND_N] = base + lane; FOUND_CTS[FOUND_N] = (int32_t)(pos - 1); FOUND_N++; }
          (*found_out)++;
        }
        }
      }
    }''')
trep('    else pending = 0;', '    else pending = PL_ZERO;')

preamble = '''#include <wasm_simd128.h>
#define PL_ALL (wasm_i64x2_splat(-1))
#define PL_ZERO (wasm_i64x2_splat(0))
'''
out = head + sep + '\n' + preamble + s
(HERE / 'seedfind_core_simd.inc').write_text(out)
# SIMD 用 API (バッチ = 128 seed)
api = (HERE / 'seedfind_api.inc').read_text().replace('SC_CUR += 64;', 'SC_CUR += 128;')
(HERE / 'seedfind_api_simd.inc').write_text(api)
print('simd core + api generated')
