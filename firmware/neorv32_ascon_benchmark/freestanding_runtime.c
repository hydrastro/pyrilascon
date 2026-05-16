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
