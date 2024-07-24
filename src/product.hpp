#ifndef __PRODUCT_H__
#define __PRODUCT_H__
/**
 * @brief USRP B200mini SDR
 *
 */
#define SDR_TYPE_USRP 1
/**
 * @brief AirSpy SDR
 *
 */
#define SDR_TYPE_AIRSPY 2
/**
 * @brief HackRF SDR
 *
 */
#define SDR_TYPE_HACKRF 3
/**
 * @brief File Reader SDR
 *
 */
#define SDR_TYPE_FILE 4
/**
 * @brief Generator Type SDR
 *
 */
#define SDR_TYPE_GENERATOR 5
/**
 * @brief SDR Active Type selector
 *
 * Must be one of SDR_TYPE_USRP, SDR_TYPE_AIRSPY, SDR_TYPE_HACKRF
 *
 */
#define USE_SDR_TYPE SDR_TYPE_USRP
#endif