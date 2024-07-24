#include "dspv3.hpp"
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
    pf->target_frequencies.insert(pf->target_frequencies.begin(), 173500000 + 1000);
    pf->sdr_type = 5;

    // pf->target_frequencies.insert(pf->target_frequencies.begin(), 173900000);

    // RCT::DSP *dsp_object = new RCT::DSP_V3{
    //     pf->sampling_rate,
    //     pf->center_frequency,
    //     pf->target_frequencies,
    //     pf->ping_width_ms,
    //     pf->ping_min_snr,
    //     pf->ping_max_len_mult,
    //     pf->ping_min_len_mult,
    //     1024,   // This probably isn't the right value!
    //     16};

    // pf->set_dsp_object(*dsp_object);

    pf->start();

    sleep(8);

    pf->stop();

    return 0;
}