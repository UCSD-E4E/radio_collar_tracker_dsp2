#ifndef __UTILS_HPP__
#define __UTILS_HPP__

#include <queue>
namespace RCT
{
    template <class T>
    void updated_hwm(std::queue<T>& queue, std::size_t& hwm)
    {
        if(queue.size() > hwm)
        {
            hwm = queue.size();
        }
    }
}
#endif