// seedfind2.c - ビットスライス版 seed 復元 (64 seed 同時処理)
// usage: seedfind2 <obs.txt> <W> <seed_lo> <seed_hi> [--selftest]
// obs.txt: 1行1護石 "id1 lv1 id2 lv2 id3 lv3 sl1 sl2 sl3" (連続錬金・古い順)
#include <stdint.h>
#include "tables.h"

static const int *seg_of(int pt, int *n) {
  switch (pt) {
    case 1: *n = SEG1_N; return &SEG1[0][0];
    case 2: *n = SEG2_N; return &SEG2[0][0];
    case 3: *n = SEG3_N; return &SEG3[0][0];
    case 4: *n = SEG4_N; return &SEG4[0][0];
    case 5: *n = SEG5_N; return &SEG5[0][0];
    case 6: *n = SEG6_N; return &SEG6[0][0];
    case 7: *n = SEG7_N; return &SEG7[0][0];
    case 8: *n = SEG8_N; return &SEG8[0][0];
    case 9: *n = SEG9_N; return &SEG9[0][0];
    case 10: *n = SEG10_N; return &SEG10[0][0];
  }
  *n = 0; return NULL;
}
static const int SEG_LEN_B[4] = {24, 28, 24, 48};
static const int BAND_START[4] = {0, 24, 52, 76};

/* ---------- スカラ参照実装 ---------- */
static void init_state(uint32_t seed, uint32_t s[4]) {
  uint32_t ebx = (seed % 100000000u) ^ 0xAC9365u;
  uint32_t ecx = 0x05491333u, edx = 0, r8 = 0, r9 = 0, r10 = 0x159A55E5u, r11 = 0x1F123BB5u;
  for (int i = 0; i < 100; i++) {
    edx = ecx; r8 = r11; r9 = r10;
    uint32_t r10n = (0x65AC9365u >> (ebx & 3)) ^ ebx;
    r11 = (r10n >> 3) ^ (r10n >> 4);
    ebx = (r10n << 4) ^ (r10n << 3) ^ r11 ^ r10n;
    ecx = ebx ^ (ebx << 15);
    uint32_t r10b = (edx >> 21) ^ edx ^ ecx;
    ecx = (ecx >> 4) ^ r10b;
    r10 = r8; r11 = edx;
  }
  s[0] = r9; s[1] = r8; s[2] = edx; s[3] = ecx;
}
static inline uint32_t step_sc(uint32_t s[4]) {
  uint32_t t = s[0] ^ (s[0] << 15);
  uint32_t nw = s[3] ^ (s[3] >> 21) ^ t ^ (t >> 4);
  s[0] = s[1]; s[1] = s[2]; s[2] = s[3]; s[3] = nw;
  return nw;
}
static inline int band_of(uint32_t g) { uint32_t v = g % 100; return v < 60 ? 0 : v < 87 ? 1 : v < 98 ? 2 : 3; }

typedef struct { int sk[3][2]; int sl[3]; } Obs;
static int meld_matches(const uint32_t st_in[4], const Obs *ob) {
  uint32_t s[4] = {st_in[0], st_in[1], st_in[2], st_in[3]};
  uint32_t o[7];
  for (int i = 0; i < 7; i++) o[i] = step_sc(s);
  int b = band_of(o[1]);
  const int *row = PT[BAND_START[b] + (o[0] % SEG_LEN_B[b])];
  if (row[3] != ob->sl[0] || row[4] != ob->sl[1] || row[5] != ob->sl[2]) return 0;
  int pts[3] = {row[0], row[1], row[2]};
  int chosen[3] = {0, 0, 0};
  for (int k = 0; k < 3; k++) {
    int g0, g1;
    if (!pts[k]) { g0 = 0; g1 = 0; }
    else {
      int n; const int *seg = seg_of(pts[k], &n);
      if (k == 0) { const int *r = seg + 2 * (o[3] % n); g0 = r[0]; g1 = r[1]; }
      else {
        int cnt = 0;
        for (int i = 0; i < n; i++) { int id = seg[2*i], dup = 0; for (int j = 0; j < k; j++) if (chosen[j] == id) dup = 1; if (!dup) cnt++; }
        if (!cnt) { g0 = 0; g1 = 0; }
        else {
          int idx = o[3+k] % cnt, c2 = 0; g0 = 0; g1 = 0;
          for (int i = 0; i < n; i++) { int id = seg[2*i], dup = 0; for (int j = 0; j < k; j++) if (chosen[j] == id) dup = 1; if (dup) continue; if (c2++ == idx) { g0 = id; g1 = seg[2*i+1]; break; } }
        }
      }
    }
    chosen[k] = g0;
    if (g0 != ob->sk[k][0] || g1 != ob->sk[k][1]) return 0;
  }
  return 1;
}
static int window_matches(const uint32_t st[4], const Obs *obs, int K) {
  uint32_t t[4] = {st[0], st[1], st[2], st[3]};
  for (int k = 0; k < K; k++) {
    if (!meld_matches(t, &obs[k])) return 0;
    for (int i = 0; i < 7; i++) step_sc(t);
  }
  return 1;
}

/* ---------- 互換行 (プリフィルタ用) ---------- */
typedef struct { int seg, r; } Residue;
typedef struct { Residue res[128]; int n; } Compat;
static int seg_contains(int pt, int id, int lv) {
  int n; const int *seg = seg_of(pt, &n);
  for (int i = 0; i < n; i++) if (seg[2*i] == id && seg[2*i+1] == lv) return 1;
  return 0;
}
static void build_compat(const Obs *ob, Compat *c) {
  c->n = 0;
  for (int idx = 0; idx < 124; idx++) {
    const int *row = PT[idx];
    if (row[3] != ob->sl[0] || row[4] != ob->sl[1] || row[5] != ob->sl[2]) continue;
    int band = idx < 24 ? 0 : idx < 52 ? 1 : idx < 76 ? 2 : 3;
    int ok = 1;
    for (int k = 0; k < 3 && ok; k++) {
      int pt = row[k], id = ob->sk[k][0], lv = ob->sk[k][1];
      if (id == 0 && lv == 0) continue;
      if (!pt) ok = 0;
      else if (!seg_contains(pt, id, lv)) ok = 0;
    }
    if (!ok) continue;
    c->res[c->n].seg = SEG_LEN_B[band];
    c->res[c->n].r = idx - BAND_START[band];
    c->n++;
  }
}

/* ---------- ビットスライス基盤 ---------- */
static void bs_add(const uint64_t *a, int na, const uint64_t *b, int nb, uint64_t *out, int *nout) {
  int n = (na > nb ? na : nb) + 1;
  uint64_t carry = 0;
  for (int i = 0; i < n; i++) {
    uint64_t av = i < na ? a[i] : 0, bv = i < nb ? b[i] : 0;
    out[i] = av ^ bv ^ carry;
    carry = (av & bv) | (carry & (av ^ bv));
  }
  *nout = n;
}
// v (vw planes) に p での条件付き減算を行い mod p にする
static void cond_sub(uint64_t *v, int vw, int p) {
  for (int rep = 0; rep < 2; rep++) {
    uint64_t higher = 0;
    for (int i = (p == 3 ? 2 : 3); i < vw; i++) higher |= v[i];
    uint64_t ge = (p == 3) ? (higher | (v[1] & v[0])) : (higher | (v[0] & v[1] & v[2]));
    if (!ge) return;
    uint64_t sub[8], borrow = 0;
    int sbits = (p == 3) ? 2 : 3;
    for (int i = 0; i < vw; i++) {
      uint64_t sb = i < sbits ? ge : 0;
      sub[i] = v[i] ^ sb ^ borrow;
      borrow = ((~v[i]) & sb) | (borrow & ~(v[i] ^ sb));
    }
    for (int i = 0; i < vw; i++) v[i] = sub[i];
  }
}
static void bs_mod3(const uint64_t *x, uint64_t out[2]) {
  uint64_t cur[16][6]; int cw[16];
  for (int j = 0; j < 16; j++) { cur[j][0] = x[2*j]; cur[j][1] = x[2*j+1]; cw[j] = 2; }
  int cnt = 16;
  while (cnt > 1) {
    int m = 0;
    for (int i = 0; i + 1 < cnt; i += 2) { bs_add(cur[i], cw[i], cur[i+1], cw[i+1], cur[m], &cw[m]); m++; }
    if (cnt & 1) { memcpy(cur[m], cur[cnt-1], sizeof(uint64_t) * cw[cnt-1]); cw[m] = cw[cnt-1]; m++; }
    cnt = m;
  }
  uint64_t v[8]; int vw = cw[0];
  memcpy(v, cur[0], sizeof(uint64_t) * vw);
  for (int rep = 0; rep < 2; rep++) {
    uint64_t hi[8], lo[2], s[9]; int sw;
    for (int i = 0; i < vw - 2; i++) hi[i] = v[i+2];
    lo[0] = v[0]; lo[1] = v[1];
    bs_add(hi, vw - 2, lo, 2, s, &sw);
    memcpy(v, s, sizeof(uint64_t) * sw); vw = sw;
  }
  cond_sub(v, vw, 3);
  out[0] = v[0]; out[1] = v[1];
}
static void bs_mod7(const uint64_t *x, uint64_t out[3]) {
  uint64_t cur[16][8]; int cw[16];
  for (int j = 0; j < 11; j++) {
    cur[j][0] = x[3*j]; cur[j][1] = x[3*j+1]; cur[j][2] = (3*j+2 < 32) ? x[3*j+2] : 0;
    cw[j] = (3*j+2 < 32) ? 3 : 2;
  }
  int cnt = 11;
  while (cnt > 1) {
    int m = 0;
    for (int i = 0; i + 1 < cnt; i += 2) { bs_add(cur[i], cw[i], cur[i+1], cw[i+1], cur[m], &cw[m]); m++; }
    if (cnt & 1) { memcpy(cur[m], cur[cnt-1], sizeof(uint64_t) * cw[cnt-1]); cw[m] = cw[cnt-1]; m++; }
    cnt = m;
  }
  uint64_t v[8]; int vw = cw[0];
  memcpy(v, cur[0], sizeof(uint64_t) * vw);
  for (int rep = 0; rep < 2; rep++) {
    uint64_t hi[8], lo[3], s[9]; int sw;
    for (int i = 0; i < vw - 3; i++) hi[i] = v[i+3];
    lo[0] = v[0]; lo[1] = v[1]; lo[2] = v[2];
    bs_add(hi, vw - 3, lo, 3, s, &sw);
    memcpy(v, s, sizeof(uint64_t) * sw); vw = sw;
  }
  cond_sub(v, vw, 7);
  out[0] = v[0]; out[1] = v[1]; out[2] = v[2];
}
static inline uint64_t eq_const(const uint64_t *pl, int width, int value) {
  uint64_t m = ~0ULL;
  for (int p = 0; p < width; p++) m &= (value >> p) & 1 ? pl[p] : ~pl[p];
  return m;
}
static uint64_t prefilter(const uint64_t *o1, const Compat *c) {
  uint64_t mask = 0, r3[2], r7[3];
  int have3 = 0, have7 = 0;
  for (int i = 0; i < c->n; i++) {
    int seg = c->res[i].seg, r = c->res[i].r;
    uint64_t m;
    if (seg == 24) {
      if (!have3) { bs_mod3(o1, r3); have3 = 1; }
      m = eq_const(o1, 3, r & 7) & eq_const(r3, 2, r % 3);
    } else if (seg == 48) {
      if (!have3) { bs_mod3(o1, r3); have3 = 1; }
      m = eq_const(o1, 4, r & 15) & eq_const(r3, 2, r % 3);
    } else {
      if (!have7) { bs_mod7(o1, r7); have7 = 1; }
      m = eq_const(o1, 2, r & 3) & eq_const(r7, 3, r % 7);
    }
    mask |= m;
  }
  return mask;
}

/* ---------- ビットスライス状態 (リング) ---------- */
#define RING 20
static __thread uint64_t ring[RING][32];
static __thread int comp_[4], free_;
static void bs_step(void) {
  const uint64_t *X = ring[comp_[0]], *W = ring[comp_[3]];
  uint64_t *NW = ring[free_];
  uint64_t T[32];
  for (int p = 0; p < 32; p++) T[p] = X[p] ^ (p >= 15 ? X[p-15] : 0);
  for (int p = 0; p < 32; p++)
    NW[p] = W[p] ^ (p + 21 < 32 ? W[p+21] : 0) ^ T[p] ^ (p + 4 < 32 ? T[p+4] : 0);
  int nw = free_;
  free_ = (free_ + 1) % RING;
  comp_[0] = comp_[1]; comp_[1] = comp_[2]; comp_[2] = comp_[3]; comp_[3] = nw;
}
static void scatter(uint64_t *pl, const uint32_t *vals) {
  for (int p = 0; p < 32; p++) pl[p] = 0;
  for (int i = 0; i < 64; i++) {
    uint32_t v = vals[i];
    while (v) { int p = __builtin_ctz(v); pl[p] |= 1ULL << i; v &= v - 1; }
  }
}
static uint32_t extract(const uint64_t *pl, int lane) {
  uint32_t v = 0;
  for (int p = 0; p < 32; p++) v |= (uint32_t)((pl[p] >> lane) & 1) << p;
  return v;
}
static void const_planes(uint64_t *pl, uint32_t c) {
  for (int p = 0; p < 32; p++) pl[p] = (c >> p) & 1 ? ~0ULL : 0;
}
static void bs_init(uint32_t base) {
  uint64_t E[32], C[32], D[32], R8[32], R9[32], R10[32], R11[32];
  uint32_t ev[64];
  for (int i = 0; i < 64; i++) ev[i] = (base + i) ^ 0xAC9365u;
  scatter(E, ev);
  const_planes(C, 0x05491333u);
  const_planes(D, 0);
  const_planes(R8, 0); const_planes(R9, 0);
  const_planes(R10, 0x159A55E5u);
  const_planes(R11, 0x1F123BB5u);
  uint64_t R10N[32], R11N[32], EN[32], C1[32], R10B[32], CN[32];
  uint32_t CK[4];
  for (int k = 0; k < 4; k++) CK[k] = 0x65AC9365u >> k;
  for (int it = 0; it < 100; it++) {
    memcpy(D, C, sizeof(D));
    memcpy(R8, R11, sizeof(R8));
    memcpy(R9, R10, sizeof(R9));
    uint64_t e0 = E[0], e1 = E[1];
    uint64_t mk[4] = {~e0 & ~e1, e0 & ~e1, ~e0 & e1, e0 & e1};
    for (int p = 0; p < 32; p++) {
      uint64_t cp = 0;
      for (int k = 0; k < 4; k++) if ((CK[k] >> p) & 1) cp |= mk[k];
      R10N[p] = cp ^ E[p];
    }
    for (int p = 0; p < 32; p++) R11N[p] = (p + 3 < 32 ? R10N[p+3] : 0) ^ (p + 4 < 32 ? R10N[p+4] : 0);
    for (int p = 0; p < 32; p++) EN[p] = (p >= 4 ? R10N[p-4] : 0) ^ (p >= 3 ? R10N[p-3] : 0) ^ R11N[p] ^ R10N[p];
    for (int p = 0; p < 32; p++) C1[p] = EN[p] ^ (p >= 15 ? EN[p-15] : 0);
    for (int p = 0; p < 32; p++) R10B[p] = (p + 21 < 32 ? D[p+21] : 0) ^ D[p] ^ C1[p];
    for (int p = 0; p < 32; p++) CN[p] = (p + 4 < 32 ? C1[p+4] : 0) ^ R10B[p];
    memcpy(R10, R8, sizeof(R10));
    memcpy(R11, D, sizeof(R11));
    memcpy(E, EN, sizeof(E));
    memcpy(C, CN, sizeof(C));
  }
  memcpy(ring[0], R9, sizeof(ring[0]));
  memcpy(ring[1], R8, sizeof(ring[1]));
  memcpy(ring[2], D, sizeof(ring[2]));
  memcpy(ring[3], C, sizeof(ring[3]));
  comp_[0] = 0; comp_[1] = 1; comp_[2] = 2; comp_[3] = 3;
  free_ = 4;
}

/* ---------- スキャン ---------- */
static Obs OBS[16];
static int Kglob;
static uint32_t FOUND_SEEDS[4096];
static int32_t FOUND_CTS[4096];
static int FOUND_N;
static Compat COMPAT0, COMPAT1;
static long FOUND_CNT;

static void scan_batch(uint32_t base, long wlo, long whi, uint32_t hi, long *found_out) {
  bs_init(base);
  uint64_t lane_mask = 0;
  for (int i = 0; i < 64; i++) if (base + i < hi && base + i < 100000000u) lane_mask |= 1ULL << i;
  uint64_t pending = 0;
  int snap_prev[4] = {0, 0, 0, 0};
  long total = whi + Kglob - 1;
  for (long pos = 0; pos < total; pos++) {
    int snap_cur[4] = {comp_[0], comp_[1], comp_[2], comp_[3]};
    bs_step();
    int o1_idx = comp_[3];
    for (int i = 0; i < 6; i++) bs_step();
    const uint64_t *o1 = ring[o1_idx];
    if (pending) {
      uint64_t m2 = prefilter(o1, &COMPAT1) & pending;
      while (m2) {
        int lane = __builtin_ctzll(m2);
        m2 &= m2 - 1;
        uint32_t st[4];
        for (int c = 0; c < 4; c++) st[c] = extract(ring[snap_prev[c]], lane);
        if (window_matches(st, OBS, Kglob)) {
          if (FOUND_N < 4096) { FOUND_SEEDS[FOUND_N] = base + lane; FOUND_CTS[FOUND_N] = (int32_t)(pos - 1); FOUND_N++; }
          (*found_out)++;
        }
      }
    }
    if (pos >= wlo && pos < whi) pending = prefilter(o1, &COMPAT0) & lane_mask;
    else pending = 0;
    memcpy(snap_prev, snap_cur, sizeof(snap_cur));
  }
}

