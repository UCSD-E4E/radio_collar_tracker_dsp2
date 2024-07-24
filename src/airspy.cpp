#include "airspy.hpp"

#include <iostream>
#include <sys/time.h>
#include <syslog.h>

namespace RCT
{
    int rx_callback(airspy_transfer_t *pTransfer)
    {
        AirSpy *ctx = (AirSpy *)pTransfer->ctx;
        ctx->airspy_rx_callback(pTransfer);
        return 0;
    }

    const char *airspy_strerr(int err)
    {
        switch (err)
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

    AirSpy::AirSpy(double gain, uint64_t rate, uint64_t freq)
        : device(0), _run(false), total_rx_samples(0), sampling_rate(rate)
    {
        int retval;
        uint32_t n_samplerates;
        uint32_t *supported_samplerates = nullptr;
        size_t idx;

        syslog(LOG_DEBUG, "Creating AirSpy\n");

        // Initialize library
        retval = airspy_init();
        if (AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to initialize AirSpy: %s\n", airspy_strerr(retval));
            throw std::runtime_error("Failed to initialize AirSpy");
        }

        // create the handle
        retval = airspy_open(&device);
        if (AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to open AirSpy: %s\n", airspy_strerr(retval));
            std::cerr << "Failed to open AirSpy: " << airspy_strerr(retval) << std::endl;
            throw std::runtime_error("Failed to open AirSpy");
        }

        // set the sample rate
        airspy_get_samplerates(device, &n_samplerates, 0);
        supported_samplerates = new uint32_t[n_samplerates];
        airspy_get_samplerates(device, supported_samplerates, n_samplerates);
        for (idx = 0; idx < n_samplerates; idx++)
        {
            if (rate == supported_samplerates[idx])
            {
                break;
            }
        }
        if (idx == n_samplerates)
        {
            syslog(LOG_ERR, "Sample rate not supported");
            throw std::invalid_argument("Unsupported sample rate");
        }
        delete[] (supported_samplerates);
        retval = airspy_set_samplerate(device, rate);
        if (AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Unable to set sample rate: %s\n", airspy_strerr(retval));
            throw std::runtime_error("Failed to set sample rate");
        }

        // set the RF gain
        if (gain > 14 || gain < 0)
        {
            throw std::runtime_error("Unsupported gain: 0 < gain < 14");
        }
        retval = airspy_set_lna_gain(device, gain);
        if (AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Unable to set RF gain: %s\n", airspy_strerr(retval));
            throw std::runtime_error("Failed to set RF gain");
        }
        retval = airspy_set_mixer_gain(device, 15);
        if (AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Unable to set Mixer Gain: %s\n", airspy_strerr(retval));
            throw std::runtime_error("Failed to set mixer gain");
        }
        retval = airspy_set_vga_gain(device, 15);
        if (AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Unable to set Mixer Gain: %s\n", airspy_strerr(retval));
            throw std::runtime_error("Failed to set mixer gain");
        }

        // Set the center frequency
        retval = airspy_set_freq(device, freq);
        if (AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Unable to set center frequency: %s\n", airspy_strerr(retval));
            throw(std::runtime_error("Failed to set center frequency"));
        }
    }

    AirSpy::~AirSpy()
    {
        int retval;
        retval = airspy_close(this->device);
        if (AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Unable to close airspy: %s\n", airspy_strerr(retval));
        }
        airspy_exit();
    }

    void AirSpy::startStreaming(std::queue<std::complex<double> *> &queue,
                                std::mutex &mutex,
                                std::condition_variable &cond_var)
    {
        int retval;
        struct timeval starttime;

        this->output_queue = &queue;
        this->output_mutex = &mutex;
        this->output_var = &cond_var;

        retval = airspy_set_sample_type(this->device, AIRSPY_SAMPLE_FLOAT32_IQ);
        if (AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to set sample type to F32 IQ: %s\n", airspy_strerr(retval));
            throw(std::runtime_error("Failed to set sample type to F32"));
        }

        gettimeofday(&starttime, NULL);
        retval = airspy_start_rx(this->device, RCT::rx_callback, this);
        if (AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to start receive: %s\n", airspy_strerr(retval));
            throw(std::runtime_error("Failed to start receive"));
        }
        _start_ms = starttime.tv_sec * 1e3 + starttime.tv_usec * 1e-3;
    }

    void AirSpy::stopStreaming()
    {
        int retval;

        retval = airspy_stop_rx(this->device);
        if (AIRSPY_SUCCESS != retval)
        {
            syslog(LOG_ERR, "Failed to stop rx: %s\n", airspy_strerr(retval));
            throw(std::runtime_error("Failed to stop rx"));
        }

        std::cout << "SDR Received " << this->total_rx_samples << " samples, "
                  << (double)this->total_rx_samples / this->sampling_rate << " seconds of data"
                  << std::endl;
    }

    const size_t AirSpy::getStartTime_ms() const
    {
        return this->_start_ms;
    }

    void AirSpy::airspy_rx_callback(airspy_transfer_t *pTransfer)
    {
        size_t nBytesReceived;
        float *pRxBuffer;

        nBytesReceived = pTransfer->sample_count * (sizeof(int16_t)) * 2;
        pRxBuffer = (float *)pTransfer->samples;

        this->total_rx_samples += pTransfer->sample_count;

        std::complex<double> *raw_buffer = new std::complex<double>[pTransfer->sample_count];

        for (size_t idx = 0; idx < pTransfer->sample_count; idx++)
        {
            raw_buffer[idx] = std::complex<double>(pRxBuffer[idx * 2], pRxBuffer[idx * 2 + 1]);
        }

        std::unique_lock<std::mutex> guard(*this->output_mutex);
        this->output_queue->push(raw_buffer);
        guard.unlock();
        output_var->notify_all();
    }

    std::size_t AirSpy::getRxBufferSize(void)
    {
        return 65536;
    }
} // namespace RCT