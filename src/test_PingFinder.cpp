#include "sdr_record.hpp"

#include <unistd.h>

int main()
{
    std::unique_ptr<RCT::PingFinder> pf = RCT::PingFinder::create();
    pf->gain = 14.0;
    pf->sampling_rate = 2500000;
    pf->center_frequency = 173500000;
    pf->run_num = 1;
    pf->enable_test_data = false;
    pf->output_dir = ".";
    pf->ping_width_ms = 25;
    pf->ping_min_snr = 25;
    pf->ping_max_len_mult = 1.5;
    pf->ping_min_len_mult = 0.5;
    pf->target_frequencies.insert(pf->target_frequencies.begin(), 173964000);
    pf->target_frequencies.insert(pf->target_frequencies.begin(), 173900000);

    pf->start();

    sleep(8);

    pf->stop();
    
    return 0;
}