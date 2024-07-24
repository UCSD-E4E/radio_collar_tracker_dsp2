#ifndef __SDR_TEST_H__
#define __SDR_TEST_H__

#include "AbstractSDR.hpp"
#include "iq_data.hpp"
// #include "sdr.hpp"
#include <condition_variable>
#include <fstream>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <vector>
namespace RCT
{
    /**
     * Test SDR - this SDR reads pre-recorded data from files.  This expects the
     * files to be named RAW_DATA_%06d_%06d, where the first field is the run
     * number, and the second field is sequential file numbers.  These files
     * must all be located in input_dir (e.g. input_dir/RAW_DATA_000001_000001).
     * This is currently configured to treat the data files as complex int16.
     */
    class SDR_TEST final : public AbstractSDR
    {
    private:
        /**
         * Input directory path
         */
        std::string _input_dir;
        /**
         * Filestream for input files
         */
        std::fstream _stream;
        /**
         * List of all files to read in
         */
        std::vector<std::string> _files;
        /**
         * Size of read buffer in complex samples.
         */
        std::size_t _buffer_size;

        /**
         * Processing thread pointer
         */
        std::thread *_thread;

        /**
         * Sample rate to push data into the queue at
         */
        std::size_t _sampling_freq;

        /**
         * Internal run flag
         */
        volatile bool _run;

        /**
         * Reference to the program's run flag - this is used to notify the
         * program that all data has been read out.
         */
        volatile bool &_p_run;

    public:
        /**
         * Streaming thread method.  This will read data from the data files and
         * output them to the provided queue similar to the way RTT::SDR should.
         * @param o_q Output queue
         * @param o_m Output queue mutex
         * @param o_v Output queue condition variable
         */
        void _process(std::queue<std::complex<double> *> &o_q,
                      std::mutex &o_m,
                      std::condition_variable &o_v);

        /**
         * Constructs a test SDR module pointed at the data in input_dir.  This
         * will read the data from input_dir and set program_run to false when
         * all the data has been read and issued.
         * @param input_dir   Input directory
         * @param program_run Complete flag
         */
        SDR_TEST(std::string input_dir, volatile bool &program_run);
        /**
         * Destructor.
         */
        ~SDR_TEST();

        /**
         * Sets the size of the read and transfer buffers
         * @param buff_size Desired buffer size.
         */
        void setBufferSize(size_t buff_size);

        /**
         * Returns the read and transfer buffer size.
         * @return Buffer size
         */
        int getBufferSize();

        /**
         * Starts the test SDR streaming
         * @param o_q output queue
         * @param o_m output queue mutex
         * @param o_v output queue condition variable
         */
        void startStreaming(std::queue<std::complex<double> *> &o_q,
                            std::mutex &o_m,
                            std::condition_variable &o_v);
        /**
         * Stops the streaming.  This will stop even if not all samples have
         * been issued.
         */
        void stopStreaming();

        /**
         * Gets the timestamp of the first issued sample in ms since Unix epoch.
         * @return first sample timestamp
         */
        const std::size_t getStartTime_ms() const;

        /**
         * Obtains the run number of the run contained in the specified
         * directory
         * @param  input_dir Input directory
         * @return           Run number
         */
        static int getRunNum(const std::string input_dir);

        /**
         * Gets the center frequency of the run in the specified directory
         * @param  input_dir Input directory
         * @return           Center frequency in Hz
         */
        static uint64_t getRxFreq(const std::string input_dir);

        /**
         * Gets the sampling frequency of the run in the specified directory
         * @param  input_dir Input directory
         * @return           Sample frequency in Hz
         */
        static uint64_t getRate(const std::string input_dir);
    };
} // namespace RCT

#endif
