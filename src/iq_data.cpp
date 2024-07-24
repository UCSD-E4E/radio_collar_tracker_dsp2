#include "iq_data.hpp"

#include <vector>

namespace RCT
{
    IQdata::IQdata(const std::size_t rx_buffer_size, std::uint64_t time_ms) : time_ms(time_ms)
    {
        data = new std::vector<std::complex<short>>(rx_buffer_size);
    }

    IQdata::~IQdata()
    {
        delete data;
    }

    IQdata::IQdata(const IQdata &cpy)
    {
        data = new std::vector<std::complex<short>>(*cpy.data);
        time_ms = cpy.time_ms;
    }

    std::size_t IQdata::size()
    {
        return data->size();
    }
} // namespace RCT