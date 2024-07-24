#ifndef __IQ_DATA_H__
#define __IQ_DATA_H__

#include <complex>
#include <cstdint>
#include <memory>
#include <vector>

namespace RCT
{

    /**
     * Complex data format.  IQ data is stored as a complex int16_t, that is,
     * the real and imaginary components are both int16_t.
     */
    typedef std::complex<short> short_cpx;

    /**
     * Data struct containing IQ data and timestamp information.
     */
    struct IQdata
    {

        /**
         * Convenience constructor.
         * @param rx_buffer_size	Size of data buffer.
         * @param time_ms			Timestamp of first sample in ms according to
         *                  		local system clock.
         */
        IQdata(const std::size_t rx_buffer_size, std::uint64_t time_ms = 0);

        /**
         * Copy Constructor
         * @param cpy	IQdata object to copy
         */
        IQdata(const IQdata &cpy);

        /**
         * Destructor - this will deallocate the internal data.
         */
        ~IQdata();

        /**
         * Returns the number of samples this struct contains.
         * @return Number of samples contained.
         */
        std::size_t size();

        /**
         * Data vector.  Data should be in ascending temporal order.
         */
        std::vector<short_cpx> *data;
        /**
         * Timestamp of first sample in ms according to local system clock.
         */
        std::uint64_t time_ms;
    };

    typedef std::shared_ptr<IQdata> IQdataPtr;
} // namespace RCT

#endif