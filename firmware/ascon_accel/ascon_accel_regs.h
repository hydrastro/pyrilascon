#ifndef ASCON_ACCEL_REGS_H
#define ASCON_ACCEL_REGS_H

#include <stdint.h>

/* Generated from ascon_arch/register_map.py. Do not edit manually. */
#define ASCON_ACCEL_ABI_VERSION 1u

/* Register offsets, byte-addressed. */
#define ASCON_REG_CONTROL           0x00u
#define ASCON_REG_STATUS            0x04u
#define ASCON_REG_MODE              0x08u
#define ASCON_REG_CAPABILITIES      0x0Cu
#define ASCON_REG_AD_LEN            0x10u
#define ASCON_REG_TEXT_LEN          0x14u
#define ASCON_REG_OUT_LEN           0x18u
#define ASCON_REG_CUSTOM_LEN        0x1Cu
#define ASCON_REG_KEY0              0x20u
#define ASCON_REG_KEY1              0x24u
#define ASCON_REG_KEY2              0x28u
#define ASCON_REG_KEY3              0x2Cu
#define ASCON_REG_NONCE0            0x30u
#define ASCON_REG_NONCE1            0x34u
#define ASCON_REG_NONCE2            0x38u
#define ASCON_REG_NONCE3            0x3Cu
#define ASCON_REG_DATA_IN           0x40u
#define ASCON_REG_DATA_IN_CTRL      0x44u
#define ASCON_REG_DATA_OUT          0x48u
#define ASCON_REG_DATA_OUT_CTRL     0x4Cu
#define ASCON_REG_TAG0              0x60u
#define ASCON_REG_TAG1              0x64u
#define ASCON_REG_TAG2              0x68u
#define ASCON_REG_TAG3              0x6Cu
#define ASCON_REG_CYCLE_COUNT_LO    0x70u
#define ASCON_REG_CYCLE_COUNT_HI    0x74u
#define ASCON_REG_ERROR_CODE        0x78u
#define ASCON_REG_ABI_VERSION       0x7Cu

/* CONTROL bits. */
#define ASCON_CONTROL_START          (1u << 0)
#define ASCON_CONTROL_DECRYPT        (1u << 1)
#define ASCON_CONTROL_HASH           (1u << 2)
#define ASCON_CONTROL_XOF            (1u << 3)
#define ASCON_CONTROL_CXOF           (1u << 4)
#define ASCON_CONTROL_CLEAR          (1u << 8)
#define ASCON_CONTROL_IRQ_ENABLE     (1u << 16)

/* STATUS bits. */
#define ASCON_STATUS_BUSY            (1u << 0)
#define ASCON_STATUS_DONE            (1u << 1)
#define ASCON_STATUS_TAG_VALID       (1u << 2)
#define ASCON_STATUS_ERROR           (1u << 3)
#define ASCON_STATUS_IN_READY        (1u << 4)
#define ASCON_STATUS_OUT_VALID       (1u << 5)

/* DATA_IN_CTRL / DATA_OUT_CTRL bits. */
#define ASCON_DATA_LAST              (1u << 0)
#define ASCON_DATA_VALID             (1u << 1)
#define ASCON_DATA_AD                (1u << 2)
#define ASCON_DATA_TEXT              (1u << 3)
#define ASCON_DATA_CUSTOM            (1u << 4)
#define ASCON_DATA_KEEP_SHIFT   8u
#define ASCON_DATA_KEEP_MASK    0xFu

/* MODE values. */
#define ASCON_MODE_AEAD128     0u
#define ASCON_MODE_AEAD128A    1u
#define ASCON_MODE_AEAD128PQ   2u
#define ASCON_MODE_HASH        3u
#define ASCON_MODE_HASHA       4u
#define ASCON_MODE_XOF         5u
#define ASCON_MODE_XOFA        6u
#define ASCON_MODE_CXOF128     7u

/* CAPABILITIES bits. */
#define ASCON_CAP_AEAD128                (1u << 0)
#define ASCON_CAP_AEAD128A               (1u << 1)
#define ASCON_CAP_AEAD128PQ              (1u << 2)
#define ASCON_CAP_HASH                   (1u << 3)
#define ASCON_CAP_HASHA                  (1u << 4)
#define ASCON_CAP_XOF                    (1u << 5)
#define ASCON_CAP_XOFA                   (1u << 6)
#define ASCON_CAP_CXOF128                (1u << 7)
#define ASCON_CAP_DECRYPT_BUFFERED       (1u << 16)
#define ASCON_CAP_CONSTTIME_TAG_COMPARE  (1u << 17)
#define ASCON_CAP_RAND_COUNTER_HARDENING (1u << 18)
#define ASCON_CAP_FAULT_DETECTION        (1u << 19)
#define ASCON_CAP_STREAMING_BYTEMASK     (1u << 20)
#define ASCON_CAP_CYCLE_COUNTER          (1u << 21)

/* ERROR_CODE values. */
#define ASCON_ERROR_NONE               0u
#define ASCON_ERROR_UNSUPPORTED_MODE   1u
#define ASCON_ERROR_BAD_LENGTH         2u
#define ASCON_ERROR_STREAM_PROTOCOL    3u
#define ASCON_ERROR_TAG_INVALID        4u
#define ASCON_ERROR_FAULT_DETECTED     5u

#endif
