#!/usr/bin/env python3
"""seedfind2.c から WASM 用コア (seedfind_core.inc) を生成する"""
import pathlib
HERE = pathlib.Path(__file__).parent
src = (HERE / 'seedfind2.c').read_text()
core = src[:src.index('/* ---------- セルフテスト ---------- */')]
core = core.replace('''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>''', '#include <stdint.h>')
core = core.replace('''        if (window_matches(st, OBS, Kglob)) {
          #pragma omp critical
          { printf("FOUND seed=%u counter=%ld\\n", base + lane, pos - 1); fflush(stdout); }
          (*found_out)++;
        }''', '''        if (window_matches(st, OBS, Kglob)) {
          if (FOUND_N < 4096) { FOUND_SEEDS[FOUND_N] = base + lane; FOUND_CTS[FOUND_N] = (int32_t)(pos - 1); FOUND_N++; }
          (*found_out)++;
        }''')
core = core.replace('''static Obs OBS[16];
static int Kglob;''', '''static Obs OBS[16];
static int Kglob;
static uint32_t FOUND_SEEDS[4096];
static int32_t FOUND_CTS[4096];
static int FOUND_N;''')
(HERE / 'seedfind_core.inc').write_text(core)
print('seedfind_core.inc regenerated:', len(core), 'bytes')
