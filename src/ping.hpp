#ifndef __PING_H__
#define __PING_H__

#include <cstdint>
#include <memory>

namespace RCT
{
    /**
     * Data structure representing a single ping detection.
     */
    struct Ping
    {

        /**
         * Convenience constructor
         *
         * @param	time_ms		time in ms of ping according to local system clock
         * @param	amplitude	amplitude of ping in dB (reference not important)
         * @param	freq		frequency of ping in Hz (reference real world DC)
         */
        Ping(uint64_t time_ms, double amplitude, uint64_t freq)
            : time_ms{time_ms}, amplitude{amplitude}, frequency(freq) {};

        /**
         * Timestamp of ping in ms according to local system clock
         */
        std::uint64_t time_ms;

        /**
         * Relative amplitude of ping in dB
         */
        double amplitude;

        /**
         * Frequency of ping in Hz (real)
         */
        uint64_t frequency;
    };

    typedef std::shared_ptr<Ping> PingPtr;
} // namespace RCT

#endif