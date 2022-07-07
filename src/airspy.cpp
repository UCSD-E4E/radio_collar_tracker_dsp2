#include "airspy.hpp"

#include <syslog.h>
#include <iostream>

namespace RCT{
    const char* airspy_strerr(int err)
    {
        switch(err)
        {
            case AIRSPY_SUCCESS:
                return "AIRSPY_SUCCESS";
            case AIRSPY_TRUE:
                return "AIRSPY_TRUE";
            case AIRSPY_ERROR_INVALID_PARAM:
                return "AIRSPY_ERROR_INVALID_PARAM";
            case AIRSPY_ERROR_NOT_FOUND:
                return "AIRSPY_ERROR_NOT_FOUND";
            case AIRSPY_ERROR_BUSY:
                return "AIRSPY_ERROR_BUSY";
            case AIRSPY_ERROR_NO_MEM:
                return "AIRSPY_ERROR_NO_MEM";
            case AIRSPY_ERROR_LIBUSB:
                return "AIRSPY_ERROR_LIBUSB";
            case AIRSPY_ERROR_THREAD:
                return "AIRSPY_ERROR_THREAD";
            case AIRSPY_ERROR_STREAMING_THREAD_ERR:
                return "AIRSPY_ERROR_STREAMING_THREAD_ERR";
            case AIRSPY_ERROR_STREAMING_STOPPED:
                return "AIRSPY_ERROR_STREAMING_STOPPED";
            case AIRSPY_ERROR_OTHER:
                return "AIRSPY_ERROR_OTHER";
            default:
                return "AIRSPY UNKNOWN ERROR";
        }
    }

    AirSpy::AirSpy(double gain, uint64_t rate, uint64_t freq) :
        device(0)
    {   
        int retval;
        uint32_t n_samplerates;
        uint32_t* supported_samplerates = nullptr;
        size_t idx;

        syslog(LOG_DEBUG, "Creating AirSpy\n");
        
        // Initialize library
        retval = airspy_init();
        if(AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to initialize AirSpy: %s\n", airspy_strerr(retval));
            throw std::runtime_error("Failed to initialize AirSpy");

        }

        // create the handle
        retval = airspy_open(&device);
        if(AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to open AirSpy: %s\n", airspy_strerr(retval));
            std::cerr << "Failed to open AirSpy: " << airspy_strerr(retval) << std::endl;
            throw std::runtime_error("Failed to open AirSpy");
        }

        // set the sample rate
        airspy_get_samplerates(device, &n_samplerates, 0);
        supported_samplerates = new uint32_t[n_samplerates];
        airspy_get_samplerates(device, supported_samplerates, n_samplerates);
        for(idx = 0; idx < n_samplerates; idx++)
        {
            if(rate == supported_samplerates[idx])
            {
                break;
            }
        }
        if(idx == n_samplerates)
        {
            syslog(LOG_ERR, "Sample rate not supported");
            throw std::invalid_argument("Unsupported sample rate");
        }
        delete[](supported_samplerates);
        retval = airspy_set_samplerate(device, rate);
        if(AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Unable to set sample rate: %s\n", airspy_strerr(retval));
            throw std::runtime_error("Failed to set sample rate");
        }

        // set the RF gain
        retval = airspy_set_lna_gain(device, gain);
        if(AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Unable to set RF gain: %s\n", airspy_strerr(retval));
            throw std::runtime_error("Failed to set RF gain");
        }

        // Set the center frequency
        retval = airspy_set_freq(device, freq);
        if(AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Unable to set center frequency: %s\n", airspy_strerr(retval));
            throw(std::runtime_error("Failed to set center frequency"));
        }
    }

    AirSpy::~AirSpy(){
        airspy_exit();
    }

    void AirSpy::startStreaming(std::queue<std::complex<double>*>& queue, 
        std::mutex& mutex, std::condition_variable& cond_var)
    {
        
    }

    void AirSpy::stopStreaming()
    {

    }

    const size_t AirSpy::getStartTime_ms() const{
        return 0;
    }
}