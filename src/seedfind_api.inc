
/* ---------- WASM API ---------- */
static uint32_t SC_LO, SC_HI, SC_CUR;
static long SC_WLO, SC_WHI;
__attribute__((export_name("sf_set_obs"))) void sf_set_obs(int idx, int i1, int l1, int i2, int l2, int i3, int l3, int s1, int s2, int s3) {
  OBS[idx].sk[0][0] = i1; OBS[idx].sk[0][1] = l1;
  OBS[idx].sk[1][0] = i2; OBS[idx].sk[1][1] = l2;
  OBS[idx].sk[2][0] = i3; OBS[idx].sk[2][1] = l3;
  OBS[idx].sl[0] = s1; OBS[idx].sl[1] = s2; OBS[idx].sl[2] = s3;
}
__attribute__((export_name("sf_begin"))) void sf_begin(int K, int wlo, int whi, uint32_t lo, uint32_t hi) {
  Kglob = K;
  build_compat(&OBS[0], &COMPAT0);
  build_compat(&OBS[1], &COMPAT1);
  SC_WLO = wlo; SC_WHI = whi; SC_LO = lo; SC_HI = hi; SC_CUR = lo;
  FOUND_N = 0;
}
// 最大 max_batches バッチ処理。完了したら 0、継続中は 1 を返す
__attribute__((export_name("sf_step"))) int sf_step(int max_batches) {
  long done = 0;
  while (SC_CUR < SC_HI && done < max_batches) {
    long fc = 0;
    scan_batch(SC_CUR, SC_WLO, SC_WHI, SC_HI, &fc);
    SC_CUR += 64;
    done++;
  }
  return SC_CUR < SC_HI ? 1 : 0;
}
__attribute__((export_name("sf_cursor"))) uint32_t sf_cursor(void) { return SC_CUR; }
__attribute__((export_name("sf_found_count"))) int sf_found_count(void) { return FOUND_N; }
__attribute__((export_name("sf_found_seed"))) uint32_t sf_found_seed(int i) { return FOUND_SEEDS[i]; }
__attribute__((export_name("sf_found_counter"))) int sf_found_counter(int i) { return FOUND_CTS[i]; }
__attribute__((export_name("sf_compat0"))) int sf_compat0(void) { return COMPAT0.n; }
__attribute__((export_name("sf_compat1"))) int sf_compat1(void) { return COMPAT1.n; }
