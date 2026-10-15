//=============================================================================
//  P R O J E C T   I N F O R M A T I O N
//-----------------------------------------------------------------------------
//  Project Name: J02 (FAW-VW MFK DK3)
//  Target system(s): J6
//  Compiler(s): ARM
//=============================================================================

//=============================================================================
/// UDS 0x27 Security Access - FAW-VW 诊断安全防护规范 2.0 算法实现
/// @file    : SecurityAccess_27_J02.cpp
/// @brief   : 按 FAW-VW《General Diagnostic Specification: Diagnostic Security
///            Protection》2.0 实现的 27 服务 seed/key 算法 (App 与 Boot 等级)
///
/// 算法: AES128-CBC (无填充)
///   Input  = Seed(12B, 高位) + Mask(4B, 低位) 拼接为 16B
///   Output = AES128-CBC(Input, AESKey, IV) 加密后的 16B
///   Key    = Output 按 KEY_ORDER_xxx 提取 12B 重排
///
/// 解锁等级 / 子功能 / 长度:
///   App  = Level 1  (0x03 GetSeed / 0x04 CompareKey)  Seed 12B / Key 12B
///   Boot = Level 2  (0x11 GetSeed / 0x12 CompareKey)  Seed 12B / Key 12B
///   Develop (Level 49, 0x61/0x62, 16B/16B) 为内部调试等级, 不在本规范范围内,
///   维持原有 AES-CMAC 实现 (见 ov_dia_0x27_security_access.cpp)
///
/// 验证 (规范 4.2.4 Boot 示例, AESKey2 按字符串 ASCII 字节):
///   Seed=22cb01d0b176e3955d65a202, Mask=9518d8c4
///   Output=cbf89e265fbb40dd031e1254af2f897f, Key=2654cbf8401e5f7faf89bbdd  [PASS]
/// 注意: 规范 4.2.3 App 示例 (Output=9f32e5c752d6b6c4d1014541d823ab41) 用
///   AESKey1="71f9ak515e8d4g3h" 无法复现, 疑似规范示例过期 (Boot 示例可精确
///   复现, 算法理解无误); 实现按规范算法正文执行, 建议与 FAW-VW 确认该示例.
///   按 AESKey1 计算: Seed=853767c8aad4e2e072e4e241, Mask=691b3f23 ->
///   Output=be745462e81f49869550cf6975a4f870, Key=8654701f50be744969e8f895
///
/// 集成说明: 函数签名与 dia_cfg/src/0x27/ov_dia_0x27_security_access.cpp 中
///   DcmDspSecurity 表引用的回调一致 (AppSecurityGetSeed/AppSecurityCompareKey/
///   BootSecurityGetSeed/BootSecurityCompareKey), 可直接替换对应函数体;
///   AttemptCounter 读写函数维持原实现不变.
//=============================================================================

#include <cstring>

#include "basic_types/types.hpp" // for definition of uintxx_t/intxx_t types

#include "idia/service_independent/idia_autosar_includes.hpp"

#include "ov_dia/crypto/AES.hpp" // AESModeOfOperation (MODE_CBC)

#include "Log.h"

// ---------------------------------------------------------------------------
// 长度定义 (对应问卷 DcmDspSecurity 表 SeedSize / KeySize)
// ---------------------------------------------------------------------------
#define DCMAPPL_SECA_SEED_APP_LENGTH 12u
#define DCMAPPL_SECA_KEY_APP_LENGTH 12u

#define DCMAPPL_SECA_SEED_BOOT_LENGTH 12u
#define DCMAPPL_SECA_KEY_BOOT_LENGTH 12u

// AES block = Seed(12B) + Mask(4B)
#define DCMAPPL_SECA_AES_BLOCK_LENGTH 16u

// ---------------------------------------------------------------------------
// 预共享常量 (规范 4.2.1, 字符串按 ASCII 字节使用)
// ---------------------------------------------------------------------------
/// Security access level 1 (App) AES key: "71f9ak515e8d4g3h"
static unsigned char AES_KEY1[16] = {
    '7', '1', 'f', '9', 'a', 'k', '5', '1',
    '5', 'e', '8', 'd', '4', 'g', '3', 'h'};

/// Security access level 2 (Boot) AES key: "86ae5j1ks0fgk2c9"
static unsigned char AES_KEY2[16] = {
    '8', '6', 'a', 'e', '5', 'j', '1', 'k',
    's', '0', 'f', 'g', 'k', '2', 'c', '9'};

/// 初始向量 (Level 1 与 Level 2 相同): "60f5b79md4se6g8h"
static unsigned char AES_IV[16] = {
    '6', '0', 'f', '5', 'b', '7', '9', 'm',
    'd', '4', 's', 'e', '6', 'g', '8', 'h'};

/// ECU 掩码 (4B), 由 OEM 决定并分配给 ECU 供应商, 规范示例值仅供参考
/// TODO: 与 FAW-VW 确认 J02 项目实际分配值后替换
static unsigned char MASK_APP[4] = {0x69u, 0x1bu, 0x3fu, 0x23u};
static unsigned char MASK_BOOT[4] = {0x95u, 0x18u, 0xd8u, 0xc4u};

/// Key 提取顺序 (规范 4.2.3): Key1[i] = Output[KEY_ORDER_APP[i]]
static const uint8_t KEY_ORDER_APP[DCMAPPL_SECA_KEY_APP_LENGTH] = {
    7u, 2u, 15u, 5u, 9u, 0u, 1u, 6u, 11u, 4u, 14u, 8u};

/// Key 提取顺序 (规范 4.2.4): Key2[i] = Output[KEY_ORDER_BOOT[i]]
static const uint8_t KEY_ORDER_BOOT[DCMAPPL_SECA_KEY_BOOT_LENGTH] = {
    3u, 11u, 0u, 1u, 6u, 9u, 4u, 15u, 12u, 14u, 5u, 7u};

/// 当前种子缓存 (requestSeed 生成, sendKey 比对用)
static uint8_t g_seedApp_au8[DCMAPPL_SECA_SEED_APP_LENGTH] = {0x00u};
static uint8_t g_seedBoot_au8[DCMAPPL_SECA_SEED_BOOT_LENGTH] = {0x00u};

/// 伪随机数发生器状态 (LCG + tick 混合; 规范建议 HSM RNG, 与原实现保持一致)
static uint32_t RandomNo_27_u32 = 0x12345678u;

/**
 * @brief Get random number (15-bit), RNG 状态为本文件私有
 * @return uint16 伪随机数
 */
static uint16_t GetRandom27_u16(void)
{
    uint32_t tickValue = 0u;
    GetCounterValue(Rte_TickCounter, &tickValue);
    RandomNo_27_u32 = (RandomNo_27_u32 * 1103515245u) + tickValue;
    return (uint16_t)(((uint16_t)(RandomNo_27_u32 >> 16)) & (uint16_t)0x7fffu);
}

/**
 * @brief 生成 12 字节随机种子, 规避全 0 / 全 FF (规范 4.2.1)
 * @param seed 种子输出缓冲 (12B)
 */
static void GenerateSeed12(uint8_t *seed)
{
    uint8_t i = 0u;
    uint8_t l_zeroCnt_u8 = 0u;
    uint8_t l_ffCnt_u8 = 0u;

    for (i = 0u; i < DCMAPPL_SECA_AES_BLOCK_LENGTH - 4u; i++)
    {
        seed[i] = (uint8_t)GetRandom27_u16();
        if (seed[i] == 0x00u)
        {
            l_zeroCnt_u8++;
        }
        else if (seed[i] == 0xFFu)
        {
            l_ffCnt_u8++;
        }
        else
        {
            /* normal byte */
        }
    }
    /* 规范禁止种子值为全 0 或全 FF: 命中时翻转首字节避开 */
    if ((l_zeroCnt_u8 == DCMAPPL_SECA_AES_BLOCK_LENGTH - 4u)
        || (l_ffCnt_u8 == DCMAPPL_SECA_AES_BLOCK_LENGTH - 4u))
    {
        seed[0] ^= 0x5Au;
    }
}

/**
 * @brief FAW-VW 2.0 seed to key 算法 (AES128-CBC 无填充 + 字节重排)
 * @param aesKey 16B AES 密钥 (AES_KEY1 / AES_KEY2)
 * @param mask   4B ECU 掩码 (OEM 分配)
 * @param seed   12B 种子
 * @param order  12B Key 提取顺序 (KEY_ORDER_APP / KEY_ORDER_BOOT)
 * @param key    12B 密钥输出
 */
static void SeedToKeyFawvw(const unsigned char aesKey[16],
                           const unsigned char mask[4],
                           const uint8_t seed[12],
                           const uint8_t order[12],
                           uint8_t key[12])
{
    unsigned char l_input_au8[DCMAPPL_SECA_AES_BLOCK_LENGTH] = {0u};
    unsigned char l_output_au8[DCMAPPL_SECA_AES_BLOCK_LENGTH] = {0u};
    AESModeOfOperation l_aes;

    /* Input = Seed (12B, MSB) + Mask (4B, LSB) */
    memcpy(l_input_au8, seed, DCMAPPL_SECA_AES_BLOCK_LENGTH - 4u);
    memcpy(&l_input_au8[DCMAPPL_SECA_AES_BLOCK_LENGTH - 4u], mask, 4u);

    l_aes.set_mode(MODE_CBC);
    l_aes.set_key(const_cast<unsigned char *>(aesKey));
    l_aes.set_iv(AES_IV);
    (void)l_aes.Encrypt(l_input_au8, DCMAPPL_SECA_AES_BLOCK_LENGTH, l_output_au8);

    for (uint8_t i = 0u; i < DCMAPPL_SECA_KEY_APP_LENGTH; i++)
    {
        key[i] = l_output_au8[order[i]];
    }
}

/**
 * @brief Application level security access seed generation (Level 1, 0x03)
 *        每次收到 requestSeed 生成新的 12B 随机种子
 */
Std_ReturnType AppSecurityGetSeed(Dcm_SecLevelType SecLevel_u8, uint32 Seedlen_u32,
                                  uint32 AccDataRecsize_u32, uint8 *SecurityAccessDataRecord,
                                  uint8 *Seed, Dcm_OpStatusType OpStatus,
                                  Dcm_NegativeResponseCodeType *ErrorCode)
{
    (void)SecLevel_u8;
    (void)Seedlen_u32;
    (void)AccDataRecsize_u32;
    (void)SecurityAccessDataRecord;
    (void)OpStatus;

    Std_ReturnType ret_value = (Std_ReturnType)E_OK;

    GenerateSeed12(g_seedApp_au8);
    memcpy(Seed, g_seedApp_au8, DCMAPPL_SECA_SEED_APP_LENGTH);
    *ErrorCode = idia::E_POSITIVE_RESPONSE;

    LogSync("[AppSecurityGetSeed] SEED: %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x\r\n",
            g_seedApp_au8[0], g_seedApp_au8[1], g_seedApp_au8[2], g_seedApp_au8[3],
            g_seedApp_au8[4], g_seedApp_au8[5], g_seedApp_au8[6], g_seedApp_au8[7],
            g_seedApp_au8[8], g_seedApp_au8[9], g_seedApp_au8[10], g_seedApp_au8[11]);

    return (ret_value);
}

/**
 * @brief Boot level security access seed generation (Level 2, 0x11)
 *        每次收到 requestSeed 生成新的 12B 随机种子
 */
Std_ReturnType BootSecurityGetSeed(Dcm_SecLevelType SecLevel_u8, uint32 Seedlen_u32,
                                   uint32 AccDataRecsize_u32, uint8 *SecurityAccessDataRecord,
                                   uint8 *Seed, Dcm_OpStatusType OpStatus,
                                   Dcm_NegativeResponseCodeType *ErrorCode)
{
    (void)SecLevel_u8;
    (void)Seedlen_u32;
    (void)AccDataRecsize_u32;
    (void)SecurityAccessDataRecord;
    (void)OpStatus;

    Std_ReturnType ret_value = (Std_ReturnType)E_OK;

    GenerateSeed12(g_seedBoot_au8);
    memcpy(Seed, g_seedBoot_au8, DCMAPPL_SECA_SEED_BOOT_LENGTH);
    *ErrorCode = idia::E_POSITIVE_RESPONSE;

    LogSync("[BootSecurityGetSeed] SEED: %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x\r\n",
            g_seedBoot_au8[0], g_seedBoot_au8[1], g_seedBoot_au8[2], g_seedBoot_au8[3],
            g_seedBoot_au8[4], g_seedBoot_au8[5], g_seedBoot_au8[6], g_seedBoot_au8[7],
            g_seedBoot_au8[8], g_seedBoot_au8[9], g_seedBoot_au8[10], g_seedBoot_au8[11]);

    return (ret_value);
}

/**
 * @brief Application level key comparison (Level 1, 0x04)
 */
Std_ReturnType AppSecurityCompareKey(uint32 KeyLen_32, const uint8 *Key,
                                     Dcm_OpStatusType OpStatus,
                                     Dcm_NegativeResponseCodeType *ErrorCode)
{
    (void)OpStatus;

    Std_ReturnType Ret = (Std_ReturnType)DCM_E_COMPARE_KEY_FAILED;
    uint8_t l_keyCalculate_au8[DCMAPPL_SECA_KEY_APP_LENGTH] = {0u};

    if (KeyLen_32 != DCMAPPL_SECA_KEY_APP_LENGTH)
    {
        *ErrorCode = idia::E_SUB_FUNCTION_NOT_SUPPORTED;
        return (Std_ReturnType)DCM_RES_POS_NOT_OK;
    }

    SeedToKeyFawvw(AES_KEY1, MASK_APP, g_seedApp_au8, KEY_ORDER_APP, l_keyCalculate_au8);
    LogSync("[AppSecurityCompareKey] KeyCalc: %02x... KeyRecv: %02x...\r\n",
            l_keyCalculate_au8[0], Key[0]);

    if (memcmp(Key, l_keyCalculate_au8, DCMAPPL_SECA_KEY_APP_LENGTH) == 0)
    {
        *ErrorCode = DCM_RES_POS_OK;
        Ret = (Std_ReturnType)E_OK;
    }

    return Ret;
}

/**
 * @brief Boot level key comparison (Level 2, 0x12)
 */
Std_ReturnType BootSecurityCompareKey(uint32 KeyLen_32, const uint8 *Key,
                                      Dcm_OpStatusType OpStatus,
                                      Dcm_NegativeResponseCodeType *ErrorCode)
{
    (void)OpStatus;

    Std_ReturnType Ret = (Std_ReturnType)DCM_E_COMPARE_KEY_FAILED;
    uint8_t l_keyCalculate_au8[DCMAPPL_SECA_KEY_BOOT_LENGTH] = {0u};

    if (KeyLen_32 != DCMAPPL_SECA_KEY_BOOT_LENGTH)
    {
        *ErrorCode = idia::E_SUB_FUNCTION_NOT_SUPPORTED;
        return (Std_ReturnType)DCM_RES_POS_NOT_OK;
    }

    SeedToKeyFawvw(AES_KEY2, MASK_BOOT, g_seedBoot_au8, KEY_ORDER_BOOT, l_keyCalculate_au8);
    LogSync("[BootSecurityCompareKey] KeyCalc: %02x... KeyRecv: %02x...\r\n",
            l_keyCalculate_au8[0], Key[0]);

    if (memcmp(Key, l_keyCalculate_au8, DCMAPPL_SECA_KEY_BOOT_LENGTH) == 0)
    {
        *ErrorCode = DCM_RES_POS_OK;
        Ret = (Std_ReturnType)E_OK;
    }

    return Ret;
}
