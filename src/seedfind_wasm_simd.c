// seedfind_wasm_simd.c - WASM SIMD (128レーン) 用エントリ
#include <stddef.h>
#include <stdint.h>
void *memcpy(void *d, const void *s, size_t n) { unsigned char *dd = d; const unsigned char *ss = s; for (size_t i = 0; i < n; i++) dd[i] = ss[i]; return d; }
void *memset(void *d, int v, size_t n) { unsigned char *dd = d; for (size_t i = 0; i < n; i++) dd[i] = (unsigned char)v; return d; }
void *memmove(void *d, const void *s, size_t n) { unsigned char *dd = d; const unsigned char *ss = s; if (dd < ss) { for (size_t i = 0; i < n; i++) dd[i] = ss[i]; } else { for (size_t i = n; i > 0; i--) dd[i-1] = ss[i-1]; } return d; }
#include "seedfind_core_simd.inc"
#include "seedfind_api_simd.inc"
