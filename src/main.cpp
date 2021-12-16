#include <pybind11/pybind11.h>

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)

class PingFinder
{
public:
    void start(void)
    {

    }
    void stop(void)
    {

    }
};

namespace py = pybind11;

PYBIND11_MODULE(radio_collar_tracker_dsp2, m) {
    py::class_<PingFinder>(m, "PingFinder")
        .def("start", &PingFinder::start)
        .def("stop", &PingFinder::stop)
    ;
    m.doc() = R"pbdoc(
        Pybind11 example plugin
        -----------------------

        .. currentmodule:: cmake_example

        .. autosummary::
           :toctree: _generate

    )pbdoc";

#ifdef VERSION_INFO
    m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);
#else
    m.attr("__version__") = "dev";
#endif
}