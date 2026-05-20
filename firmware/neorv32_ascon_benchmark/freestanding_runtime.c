#include <stddef.h>
#include <stdint.h>

void *memset(void *dst, int value, size_t len) {
  uint8_t *out = (uint8_t *)dst;
  for (size_t i = 0u; i < len; ++i) {
    out[i] = (uint8_t)value;
  }
  return dst;
}

void *memcpy(void *dst, const void *src, size_t len) {
  uint8_t *out = (uint8_t *)dst;
  const uint8_t *in = (const uint8_t *)src;
  for (size_t i = 0u; i < len; ++i) {
    out[i] = in[i];
  }
  return dst;
}

void *memmove(void *dst, const void *src, size_t len) {
  uint8_t *out = (uint8_t *)dst;
  const uint8_t *in = (const uint8_t *)src;
  if (out == in || len == 0u) {
    return dst;
  }
  if (out < in) {
    for (size_t i = 0u; i < len; ++i) {
      out[i] = in[i];
    }
  } else {
    for (size_t i = len; i > 0u; --i) {
      out[i - 1u] = in[i - 1u];
    }
  }
  return dst;
}

int memcmp(const void *a, const void *b, size_t len) {
  const uint8_t *pa = (const uint8_t *)a;
  const uint8_t *pb = (const uint8_t *)b;
  for (size_t i = 0u; i < len; ++i) {
    if (pa[i] != pb[i]) {
      return (int)pa[i] - (int)pb[i];
    }
  }
  return 0;
}

void abort(void) {
  for (;;) {
    __asm__ volatile ("nop");
  }
}

size_t strlen(const char *s) {
  size_t n = 0u;
  while (s[n] != '\0') {
    ++n;
  }
  return n;
}

/* Minimal ctype table for NEORV32 UART printf parsing when libc is absent.
 * Newlib's ctype macros index this table as _ctype_[c + 1].  We only need
 * digit classification for width parsing; all other classes may remain zero.
 */
unsigned char _ctype_[257] = {
  ['0' + 1] = 0x04,
  ['1' + 1] = 0x04,
  ['2' + 1] = 0x04,
  ['3' + 1] = 0x04,
  ['4' + 1] = 0x04,
  ['5' + 1] = 0x04,
  ['6' + 1] = 0x04,
  ['7' + 1] = 0x04,
  ['8' + 1] = 0x04,
  ['9' + 1] = 0x04,
};

typedef union {
  uint64_t u64;
  struct {
    uint32_t lo;
    uint32_t hi;
  } w;
} u64_parts_t;

uint64_t __ashldi3(uint64_t value, int shift) {
  u64_parts_t in;
  u64_parts_t out;
  unsigned int s = (unsigned int)shift & 63u;
  in.u64 = value;
  if (s == 0u) {
    return value;
  }
  if (s < 32u) {
    out.w.lo = in.w.lo << s;
    out.w.hi = (in.w.hi << s) | (in.w.lo >> (32u - s));
  } else {
    out.w.lo = 0u;
    out.w.hi = in.w.lo << (s - 32u);
  }
  return out.u64;
}

uint64_t __lshrdi3(uint64_t value, int shift) {
  u64_parts_t in;
  u64_parts_t out;
  unsigned int s = (unsigned int)shift & 63u;
  in.u64 = value;
  if (s == 0u) {
    return value;
  }
  if (s < 32u) {
    out.w.lo = (in.w.lo >> s) | (in.w.hi << (32u - s));
    out.w.hi = in.w.hi >> s;
  } else {
    out.w.lo = in.w.hi >> (s - 32u);
    out.w.hi = 0u;
  }
  return out.u64;
}

static uint32_t udivmod32(uint32_t num, uint32_t den, uint32_t *rem_out) {
  uint32_t q = 0u;
  uint32_t r = 0u;
  if (den == 0u) {
    if (rem_out != 0) {
      *rem_out = num;
    }
    return UINT32_MAX;
  }
  for (int i = 31; i >= 0; --i) {
    r = (uint32_t)((r << 1u) | ((num >> (unsigned int)i) & 1u));
    if (r >= den) {
      r -= den;
      q |= (uint32_t)(1u << (unsigned int)i);
    }
  }
  if (rem_out != 0) {
    *rem_out = r;
  }
  return q;
}

uint32_t __udivsi3(uint32_t num, uint32_t den) {
  return udivmod32(num, den, 0);
}

uint32_t __umodsi3(uint32_t num, uint32_t den) {
  uint32_t rem = 0u;
  (void)udivmod32(num, den, &rem);
  return rem;
}

int32_t __divsi3(int32_t num, int32_t den) {
  uint32_t neg = 0u;
  uint32_t unum;
  uint32_t uden;
  uint32_t q;
  if (num < 0) {
    unum = (uint32_t)(-num);
    neg ^= 1u;
  } else {
    unum = (uint32_t)num;
  }
  if (den < 0) {
    uden = (uint32_t)(-den);
    neg ^= 1u;
  } else {
    uden = (uint32_t)den;
  }
  q = udivmod32(unum, uden, 0);
  return neg ? -(int32_t)q : (int32_t)q;
}

int32_t __modsi3(int32_t num, int32_t den) {
  uint32_t rem = 0u;
  uint32_t unum = (num < 0) ? (uint32_t)(-num) : (uint32_t)num;
  uint32_t uden = (den < 0) ? (uint32_t)(-den) : (uint32_t)den;
  (void)udivmod32(unum, uden, &rem);
  return (num < 0) ? -(int32_t)rem : (int32_t)rem;
}

/* -----------------------------------------------------------------------
 * 64-bit math helpers used by gcc's libgcc.
 * Required because we link with -nodefaultlibs to avoid the soft-float
 * vs double-float multilib mismatch from nixpkgs newlib/libgcc.
 * ----------------------------------------------------------------------- */

/* Helper: 32x32 -> 64 multiply, using shift-add only (no widening multiplies).
 * Returns a*b zero-extended to 64 bits. */
static uint64_t mul32_64(uint32_t a, uint32_t b) {
  uint64_t acc = 0u;
  uint64_t x = (uint64_t)a;
  while (b != 0u) {
    if (b & 1u) acc += x;
    x += x;        /* x *= 2, plain 64-bit add, no multiply */
    b >>= 1u;
  }
  return acc;
}

uint64_t __muldi3(uint64_t a, uint64_t b) {
  /* 64x64 -> low-64 multiplication.
   *
   *   a*b = (a_hi*2^32 + a_lo) * (b_hi*2^32 + b_lo)
   *       = a_lo*b_lo + (a_lo*b_hi + a_hi*b_lo) * 2^32  (high*2^64 dropped)
   *
   * All sub-multiplies are 32x32 done with shift-add (mul32_64), so we
   * never trigger __mulsidi3 / __mulsi3 / __muldi3 from libgcc. */
  uint32_t a_lo = (uint32_t)a;
  uint32_t a_hi = (uint32_t)(a >> 32);
  uint32_t b_lo = (uint32_t)b;
  uint32_t b_hi = (uint32_t)(b >> 32);
  uint64_t ll = mul32_64(a_lo, b_lo);
  uint64_t lh = mul32_64(a_lo, b_hi);
  uint64_t hl = mul32_64(a_hi, b_lo);
  return ll + ((lh + hl) << 32);
}

/* Full 128-bit product: returns the low 64 bits when both inputs are 64-bit.
 * gcc generates calls to __multi3 in some configurations even when only
 * 64x64 -> 64 is needed; alias it to __muldi3. */
uint64_t __multi3(uint64_t a, uint64_t b) {
  return __muldi3(a, b);
}

/* Unsigned 64/64 -> (quotient, remainder).
 * Bit-by-bit non-restoring division; portable and small. */
static uint64_t udivmoddi4(uint64_t num, uint64_t den, uint64_t *rem_out) {
  uint64_t q = 0u;
  uint64_t r = 0u;
  if (den == 0u) {
    if (rem_out) *rem_out = num;
    return ~(uint64_t)0u;
  }
  for (int i = 63; i >= 0; --i) {
    r = (r << 1) | ((num >> i) & 1u);
    if (r >= den) {
      r -= den;
      q |= ((uint64_t)1u << i);
    }
  }
  if (rem_out) *rem_out = r;
  return q;
}

uint64_t __udivdi3(uint64_t num, uint64_t den) {
  return udivmoddi4(num, den, 0);
}

uint64_t __umoddi3(uint64_t num, uint64_t den) {
  uint64_t r = 0u;
  (void)udivmoddi4(num, den, &r);
  return r;
}

int64_t __divdi3(int64_t num, int64_t den) {
  int neg = 0;
  uint64_t un = (num < 0) ? (neg ^= 1, (uint64_t)(-num)) : (uint64_t)num;
  uint64_t ud = (den < 0) ? (neg ^= 1, (uint64_t)(-den)) : (uint64_t)den;
  uint64_t q = udivmoddi4(un, ud, 0);
  return neg ? -(int64_t)q : (int64_t)q;
}

int64_t __moddi3(int64_t num, int64_t den) {
  uint64_t r = 0u;
  uint64_t un = (num < 0) ? (uint64_t)(-num) : (uint64_t)num;
  uint64_t ud = (den < 0) ? (uint64_t)(-den) : (uint64_t)den;
  (void)udivmoddi4(un, ud, &r);
  return (num < 0) ? -(int64_t)r : (int64_t)r;
}

/* Count leading zeros — naive bit-by-bit. */
int __clzsi2(uint32_t v) {
  int n = 0;
  if (v == 0u) return 32;
  while ((v & 0x80000000u) == 0u) { v <<= 1; ++n; }
  return n;
}

int __clzdi2(uint64_t v) {
  uint32_t hi = (uint32_t)(v >> 32);
  if (hi) return __clzsi2(hi);
  return 32 + __clzsi2((uint32_t)v);
}

/* gcc may emit __ashrdi3 (arithmetic right shift) on signed 64-bit code. */
int64_t __ashrdi3(int64_t value, int shift) {
  unsigned int s = (unsigned int)shift & 63u;
  if (s == 0u) return value;
  if (s < 32u) {
    int32_t hi = (int32_t)(value >> 32);
    uint32_t lo = (uint32_t)(value);
    uint32_t new_lo = (lo >> s) | ((uint32_t)hi << (32u - s));
    int32_t  new_hi = hi >> s;
    return ((int64_t)new_hi << 32) | (int64_t)new_lo;
  } else {
    int32_t hi = (int32_t)(value >> 32);
    int32_t new_lo = hi >> (s - 32u);
    int32_t new_hi = hi >> 31;     /* sign-extend */
    return ((int64_t)new_hi << 32) | (uint32_t)new_lo;
  }
}
