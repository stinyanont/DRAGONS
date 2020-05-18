#!/usr/bin/env python
"""
Tests related to GMOS Long-slit Spectroscopy Arc primitives. `input_files` is a
list of tuples which contains:

 - the input filename,
 - the full-width-at-half-maximum measured using IRAF's splot,
 - the wavelength solution order guessed based on resudials (usually between 2 and 4),
 - the minimum signal to noise for detection, based on splot analysis.

The input data can be cached from the archive and/or processed using the
--force-preprocess-data command line option.

Notes
-----
- The `indirect` argument on `@pytest.mark.parametrize` fixture forces the
  `ad` and `ad_ref` fixtures to be called and the AstroData object returned.

  @bquint:
    It seems that the matching process depends heavily on the FWHM. Because of
    that, the FWHM was measured using `splot` (keys h, c) manually for each
    file. It basically tells how far the KDTreeFitter should look for a match.

    The fitting order was picked up after running the test and analysing the
    shape of the residuals.

    Finally, the min_snr was semi-arbitrary. It had an opposite effect from what
    I, expected. Sometimes, raising this number caused more peaks to be detected.
"""
import glob
import os
from warnings import warn
import tarfile

import numpy as np
import pytest
from matplotlib import pyplot as plt

import astrodata
import geminidr

from geminidr.gmos import primitives_gmos_spect
from gempy.library import astromodels
from gempy.utils import logutils
from recipe_system.testing import reference_ad

try:
    from .plots_gmos_spect_longslit_arcs import PlotGmosSpectLongslitArcs
except ImportError:
    pass

# Test parameters --------------------------------------------------------------
determine_wavelength_solution_parameters = {
    'center': None,
    'nsum': 10,
    'linelist': None,
    'weighting': 'natural',
    'nbright': 0
}

input_pars = [

    # Process Arcs: GMOS-N ---
    # (Input File, fwidth, order, min_snr)
    ("N20100115S0346_mosaic.fits", 6., 2, 5.),  # B600:0.500 EEV
    # ("N20130112S0390_mosaic.fits", 3., 2, 5.),  # B600:0.500 E2V
    # ("N20170609S0173_mosaic.fits", 5., 2, 5.),  # B600:0.500 HAM
    # ("N20170403S0452_mosaic.fits", 5., 2, 3.),  # B600:0.590 HAM Full Frame 1x1
    # ("N20170415S0255_mosaic.fits", 5., 3, 3.),  # B600:0.590 HAM Central Spectrum 1x1
    # ("N20171016S0010_mosaic.fits", 5., 2, 5.),  # B600:0.500 HAM, ROI="Central Spectrum", bin=1x2
    # ("N20171016S0127_mosaic.fits", 5., 2, 5.),  # B600:0.500 HAM, ROI="Full Frame", bin=1x2
    # ("N20100307S0236_mosaic.fits", 4., 2, 3.),  # B1200:0.445 EEV
    # ("N20130628S0290_mosaic.fits", 5., 2, 3.),  # B1200:0.420 E2V - Looks Good
    # ("N20170904S0078_mosaic.fits", 3., 3, 3.),  # B1200:0.440 HAM
    # ("N20170627S0116_mosaic.fits", 2.5, 3, 10.),  # B1200:0.520 HAM
    # ("N20100830S0594_mosaic.fits", 2.5, 2, 3.),  # R150:0.500 EEV - todo: is that strong line in the blue real?
    # ("N20100702S0321_mosaic.fits", 2.5, 2, 3.),  # R150:0.700 EEV
    # ("N20130606S0291_mosaic.fits", 5., 2, 3.),  # R150:0.550 E2V
    # ("N20130112S0574_mosaic.fits", 4.5, 3, 3.),  # R150:0.700 E2V
    # ("N20130809S0337_mosaic.fits", 3, 2, 3.),  # R150:0.700 E2V
    # ("N20140408S0218_mosaic.fits", 3, 4, 3.),  # R150:0.700 E2V
    # ("N20180119S0232_mosaic.fits", 5, 2, 10.),  # R150:0.520 HAM - todo: won't pass
    # ("N20180516S0214_mosaic.fits", 3.5, 3, 5.),  # R150:0.610 HAM ROI="Central Spectrum", bin=2x2
    # ("N20171007S0439_mosaic.fits", 3, 2, 10.),  # R150:0.650 HAM
    # ("N20171007S0441_mosaic.fits", 6, 2, 5.),  # R150:0.650 HAM
    # ("N20101212S0213_mosaic.fits", 5.5, 2, 3.),  # R400:0.550 EEV
    # ("N20100202S0214_mosaic.fits", 6, 2, 3.),  # R400:0.700 EEV
    # ("N20130106S0194_mosaic.fits", 6, 2, 3.),  # R400:0.500 E2V
    # ("N20130422S0217_mosaic.fits", 4.5, 3, 3.),  # R400:0.700 E2V
    # ("N20170108S0210_mosaic.fits", 6, 3, 3.),  # R400:0.660 HAM
    # ("N20171113S0135_mosaic.fits", 5.5, 2, 3.),  # R400:0.750 HAM
    # ("N20100427S1276_mosaic.fits", 5.5, 2, 3.),  # R600:0.675 EEV
    # # ("N20180120S0417_mosaic.fits", 8, 3, 5.),  # R600:0.860 HAM - todo: won't pass
    # ("N20100212S0143_mosaic.fits", 5.5, 3, 5.),  # R831:0.450 EEV
    # ("N20100720S0247_mosaic.fits", 3.5, 3, 3.),  # R831:0.850 EEV
    # ("N20130808S0490_mosaic.fits", 4., 3, 5.),  # R831:0.571 E2V
    # ("N20130830S0291_mosaic.fits", 3.5, 3, 5.),  # R831:0.845 E2V
    # # ("N20170910S0009_mosaic.fits", 4.5, 2, 3.),  # R831:0.653 HAM- todo: won't pass
    # ("N20170509S0682_mosaic.fits", 4.5, 3, 3.),  # R831:0.750 HAM
    # ("N20181114S0512_mosaic.fits", 4, 3, 15.),  # R831:0.865 HAM - todo: passes *only* with fwhm=4??
    # # ("N20170416S0058_mosaic.fits", 6., 2, 5.),  # R831:0.865 HAM - todo: won't pass
    # # ("N20170416S0081_mosaic.fits", 4, 2, 3.),  # R831:0.865 HAM - todo: won't pass
    # # ("N20180120S0315_mosaic.fits", 3, 2, 15.),  # R831:0.865 HAM - todo: won't pass
    #
    # # Process Arcs: GMOS-S ---
    # ("S20130218S0126_mosaic.fits", 5., 2, 10),  # B600:0.500 EEV
    # ("S20130111S0278_mosaic.fits", 6, 3, 5.),  # B600:0.520 EEV
    # ("S20130114S0120_mosaic.fits", 3, 2, 5.),  # B600:0.500 EEV
    # ("S20130216S0243_mosaic.fits", 3, 2, 3.),  # B600:0.480 EEV
    # ("S20130608S0182_mosaic.fits", 6, 3, 3.),  # B600:0.500 EEV
    # ("S20131105S0105_mosaic.fits", 3, 2, 5.),  # B600:0.500 EEV
    # ("S20140504S0008_mosaic.fits", 6, 3, 10.),  # B600:0.500 EEV
    # ("S20170103S0152_mosaic.fits", 7, 2, 10.),  # B600:0.600 HAM
    # ("S20170108S0085_mosaic.fits", 5.5, 2, 10.),  # B600:0.500 HAM - todo: detector partially empty
    # ("S20130510S0103_mosaic.fits", 2.5, 2, 5.),  # B1200:0.450 EEV - todo: region without matches
    # ("S20130629S0002_mosaic.fits", 7, 6, 5.),  # B1200:0.525 EEV - todo: order = 6!!
    # ("S20131123S0044_mosaic.fits", 4, 2, 3.),  # B1200:0.595 EEV
    # ("S20170116S0189_mosaic.fits", 5, 2, 3.),  # B1200:0.440 HAM
    # ("S20170103S0149_mosaic.fits", 7, 2, 3.),  # B1200:0.440 HAM
    # ("S20170730S0155_mosaic.fits", 3.5, 2, 3.),  # B1200:0.440 HAM
    # # ("S20171219S0117_mosaic.fits", 4, 2, 3.),  # B1200:0.440 HAM - todo: won't pass
    # ("S20170908S0189_mosaic.fits", 3, 2, 3.),  # B1200:0.550 HAM
    # ("S20131230S0153_mosaic.fits", 3, 2, 10.),  # R150:0.550 EEV
    # ("S20130801S0140_mosaic.fits", 6, 2, 15.),  # R150:0.700 EEV
    # ("S20170430S0060_mosaic.fits", 3, 2, 15.),  # R150:0.717 HAM
    # # ("S20170430S0063_mosaic.fits", 6, 2, 15.),  # R150:0.727 HAM - todo: not stable
    # ("S20171102S0051_mosaic.fits", 6, 2, 5.),   # R150:0.950 HAM
    # ("S20130114S0100_mosaic.fits", 6, 4, 15.),  # R400:0.620 EEV
    # ("S20130217S0073_mosaic.fits", 4, 2, 5.),  # R400:0.800 EEV
    # ("S20170108S0046_mosaic.fits", 3, 2, 3.),  # R400:0.550 HAM
    # ("S20170129S0125_mosaic.fits", 3, 2, 3.),  # R400:0.685 HAM
    # ("S20170703S0199_mosaic.fits", 5, 3, 3.),  # R400:0.800 HAM
    # ("S20170718S0420_mosaic.fits", 5, 2, 3.),  # R400:0.910 HAM
    # ("S20100306S0460_mosaic.fits", 6, 2, 15.),  # R600:0.675 EEV
    # ("S20101218S0139_mosaic.fits", 6, 2, 10.),  # R600:0.675 EEV
    # ("S20110306S0294_mosaic.fits", 6, 2, 5.),  # R600:0.675 EEV
    # ("S20110720S0236_mosaic.fits", 6, 2, 5.),  # R600:0.675 EEV
    # ("S20101221S0090_mosaic.fits", 4, 2, 3.),  # R600:0.690 EEV
    # ("S20120322S0122_mosaic.fits", 5, 2, 3.),  # R600:0.900 EEV
    # ("S20130803S0011_mosaic.fits", 2, 2, 3.),  # R831:0.576 EEV
    # ("S20130414S0040_mosaic.fits", 4, 2, 10.),  # R831:0.845 EEV
    # ("S20170214S0059_mosaic.fits", 2, 2, 10.),  # R831:0.440 HAM - todo: the numbers says it is fine but I can't tell by the plots
    # ("S20170703S0204_mosaic.fits", 3, 2, 3.),  # R831:0.600 HAM
    # ("S20171018S0048_mosaic.fits", 5, 2, 3.)  # R831:0.865 HAM - todo: the numbers says it is fine but I can't tell by the plots
]


# Tests Definitions ------------------------------------------------------------
@pytest.mark.gmosls
@pytest.mark.preprocessed_data
@pytest.mark.parametrize("ad, fwidth, order, min_snr", input_pars, indirect=True)
def test_reduced_arcs_contain_wavelength_solution_model_with_expected_rms(
        ad, change_working_dir, fwidth, min_snr, order, request):
    """
    Make sure that the WAVECAL model was fitted with an RMS smaller than half of
    the slit size in pixels.

    todo: this test must change with the slit size. While checking that, I found
        out that the `ad[0].slit()` descriptor returns nothing. I could use the
        existing `ad[0].focal_plane_mask()` descriptor for now but it is
        counter-intuitive.
    """
    with change_working_dir():
        logutils.config(file_name='log_rms_{:s}.txt'.format(ad.data_label()))
        p = primitives_gmos_spect.GMOSSpect([ad])
        p.viewer = geminidr.dormantViewer(p, None)

        p.determineWavelengthSolution(
            order=order, min_snr=min_snr, fwidth=fwidth,
            **determine_wavelength_solution_parameters)

        wcalibrated_ad = p.writeOutputs().pop()

    if request.config.getoption("--do-plots"):
        do_plots(wcalibrated_ad)

    table = wcalibrated_ad[0].WAVECAL
    coefficients = table["coefficients"]
    rms = coefficients[table["name"] == "rms"]

    pixel_scale = wcalibrated_ad[0].pixel_scale()  # arcsec / px
    slit_size_in_arcsec = float(wcalibrated_ad[0].focal_plane_mask().replace('arcsec', ''))
    slit_size_in_px = slit_size_in_arcsec / pixel_scale  # px
    dispersion = abs(wcalibrated_ad[0].dispersion(asNanometers=True))  # nm / px

    required_rms = dispersion * slit_size_in_px

    np.testing.assert_array_less(rms, required_rms)


@pytest.mark.gmosls
@pytest.mark.preprocessed_data
@pytest.mark.parametrize("ad, fwidth, order, min_snr", input_pars, indirect=True)
def test_regression_determine_wavelength_solution(
        ad, fwidth, order, min_snr, change_working_dir, reference_ad):
    """
    Make sure that the wavelength solution gives same results on different
    runs.
    """
    with change_working_dir():
        logutils.config(file_name='log_regress_{:s}.txt'.format(ad.data_label()))
        p = primitives_gmos_spect.GMOSSpect([ad])
        p.viewer = geminidr.dormantViewer(p, None)

        p.determineWavelengthSolution(
            order=order, min_snr=min_snr, fwidth=fwidth,
            **determine_wavelength_solution_parameters)

        wcalibrated_ad = p.writeOutputs().pop()

    ref_ad = reference_ad(wcalibrated_ad.filename)
    table = wcalibrated_ad[0].WAVECAL
    table_ref = ref_ad[0].WAVECAL

    model = astromodels.dict_to_chebyshev(
        dict(zip(table["name"], table["coefficients"])))

    ref_model = astromodels.dict_to_chebyshev(
        dict(zip(table_ref["name"], table_ref["coefficients"])))

    x = np.arange(wcalibrated_ad[0].shape[1])
    wavelength = model(x)
    ref_wavelength = ref_model(x)

    pixel_scale = wcalibrated_ad[0].pixel_scale()  # arcsec / px
    slit_size_in_arcsec = float(wcalibrated_ad[0].focal_plane_mask().replace('arcsec', ''))
    slit_size_in_px = slit_size_in_arcsec / pixel_scale
    dispersion = abs(wcalibrated_ad[0].dispersion(asNanometers=True))  # nm / px

    tolerance = 0.5 * (slit_size_in_px * dispersion)
    np.testing.assert_allclose(wavelength, ref_wavelength, rtol=tolerance)


# Local Fixtures and Helper Functions ------------------------------------------
@pytest.fixture(scope='function')
def ad(path_to_inputs, request):
    """
    Returns the pre-processed spectrum file.

    Parameters
    ----------
    path_to_inputs : pytest.fixture
        Fixture defined in :mod:`astrodata.testing` with the path to the
        pre-processed input file.
    request : pytest.fixture
        PyTest built-in fixture containing information about parent test.

    Returns
    -------
    AstroData
        Input spectrum processed up to right before the
        `determineWavelengthSolution` primitive.
    """
    filename = request.param
    path = os.path.join(path_to_inputs, filename)

    if os.path.exists(path):
        ad = astrodata.open(path)
    else:
        raise FileNotFoundError(path)

    return ad


@pytest.fixture
def fwidth(request):
    return request.param


@pytest.fixture
def order(request):
    return request.param


@pytest.fixture
def min_snr(request):
    return request.param


def do_plots(ad):
    """
    Generate diagnostic plots.

    Parameters
    ----------
    ad : astrodata
    """
    output_dir = ("./plots/geminidr/gmos/"
                  "test_gmos_spect_ls_determine_wavelength_solution")
    os.makedirs(output_dir, exist_ok=True)

    name, _ = os.path.splitext(ad.filename)
    grating = ad.disperser(pretty=True)
    bin_x = ad.detector_x_bin()
    bin_y = ad.detector_y_bin()
    central_wavelength = ad.central_wavelength() * 1e9  # in nanometers

    package_dir = os.path.dirname(primitives_gmos_spect.__file__)
    arc_table = os.path.join(package_dir, "lookups", "CuAr_GMOS.dat")
    arc_lines = np.loadtxt(arc_table, usecols=[0]) / 10.0

    for ext_num, ext in enumerate(ad):

        if not hasattr(ext, "WAVECAL"):
            continue

        peaks = ext.WAVECAL["peaks"] - 1  # ToDo: Refactor peaks to be 0-indexed
        wavelengths = ext.WAVECAL["wavelengths"]

        wavecal_model = astromodels.dict_to_chebyshev(
            dict(zip(ext.WAVECAL["name"], ext.WAVECAL["coefficients"])))

        middle = ext.data.shape[0] // 2
        sum_size = 10
        r1 = middle - sum_size // 2
        r2 = middle + sum_size // 2

        mask = np.round(np.average(ext.mask[r1:r2], axis=0)).astype(int)
        data = np.ma.masked_where(mask > 0, np.sum(ext.data[r1:r2], axis=0))
        data = (data - data.min()) / data.ptp()

        # -- Plot lines --
        fig, ax = plt.subplots(
            dpi=150, num="{:s}_{:d}_{:s}_{:.0f}".format(
                name, ext_num, grating, central_wavelength))

        w = wavecal_model(np.arange(data.size))

        arcs = [ax.vlines(line, 0, 1, color="k", alpha=0.25) for line in arc_lines]
        wavs = [ax.vlines(peak, 0, 1, color="r", ls="--", alpha=0.25)
                for peak in wavecal_model(peaks)]

        plot, = ax.plot(w, data, "k-", lw=0.75)

        ax.legend((plot, arcs[0], wavs[0]),
                  ("Normalized Data", "Reference Lines", "Matched Lines"))

        x0, x1 = wavecal_model([0, data.size])
        ax.grid(alpha=0.1)
        ax.set_xlim(x0, x1)
        ax.set_xlabel("Wavelength [nm]")
        ax.set_ylabel("Normalized intensity")
        ax.set_title("Wavelength Calibrated Spectrum for\n"
                     "{:s}\n obtained with {:s} at {:.0f} nm".format(
                        name, grating, central_wavelength))

        if x0 > x1:
            ax.invert_xaxis()

        fig_name = os.path.join(output_dir, "{:s}_{:d}_{:s}_{:.0f}.png".format(
            name, ext_num, grating, central_wavelength))

        fig.savefig(fig_name)
        del fig, ax

        # -- Plot non-linear components ---
        fig, ax = plt.subplots(
            dpi=150, num="{:s}_{:d}_{:s}_{:.0f}_non_linear_comps".format(
                name, ext_num, grating, central_wavelength))

        non_linear_model = wavecal_model.copy()
        _ = [setattr(non_linear_model, "c{}".format(k), 0) for k in [0, 1]]
        residuals = wavelengths - wavecal_model(peaks)

        p = np.linspace(min(peaks), max(peaks), 1000)
        ax.plot(wavecal_model(p), non_linear_model(p),
                "C0-", label="Generic Representation")
        ax.plot(wavecal_model(peaks), non_linear_model(peaks) + residuals,
                "ko", label="Non linear components and residuals")

        ax.legend()
        ax.grid(alpha=0.25)
        ax.set_xlabel("Wavelength [nm]")
        ax.set_title("Non-linear components for\n"
                     "{:s} obtained with {:s} at {:.0f}".format(
                        name, grating, central_wavelength))

        fig_name = os.path.join(
            output_dir, "{:s}_{:d}_{:s}_{:.0f}_non_linear_comps.png".format(
                name, ext_num, grating, central_wavelength))

        fig.savefig(fig_name)
        del fig, ax

        # -- Plot Wavelength Solution Residuals ---
        fig, ax = plt.subplots(
            dpi=150, num="{:s}_{:d}_{:s}_{:.0f}_residuals".format(
                name, ext_num, grating, central_wavelength))

        ax.plot(wavelengths, wavelengths - wavecal_model(peaks), "ko")

        ax.grid(alpha=0.25)
        ax.set_xlabel("Wavelength [nm]")
        ax.set_ylabel("Residuum [nm]")
        ax.set_title("Wavelength Calibrated Residuum for\n"
                     "{:s} obtained with {:s} at {:.0f}".format(
                        name, grating, central_wavelength))

        fig_name = os.path.join(
            output_dir, "{:s}_{:d}_{:s}_{:.0f}_residuals.png".format(
                name, ext_num, grating, central_wavelength))

        fig.savefig(fig_name)

    # -- Create artifacts ---
    if "BUILD_ID" in os.environ:
        branch_name = os.environ["BRANCH_NAME"].replace("/", "_")
        build_number = int(os.environ["BUILD_NUMBER"])

        tar_name = os.path.join(output_dir, "plots_{:s}_b{:03d}.tar.gz".format(
            branch_name, build_number))

        with tarfile.open(tar_name, "w:gz") as tar:
            for _file in glob.glob(os.path.join(output_dir, "*.png")):
                tar.add(name=_file, arcname=os.path.basename(_file))

        target_dir = "./plots/"
        target_file = os.path.join(target_dir, os.path.basename(tar_name))

        os.makedirs(target_dir, exist_ok=True)
        os.rename(tar_name, target_file)


# -- Recipe to create pre-processed data ---------------------------------------
def create_inputs_recipe():
    """
    Creates input data for tests using pre-processed standard star and its
    calibration files.

    The raw files will be downloaded and saved inside the path stored in the
    `$DRAGONS_TEST/raw_inputs` directory. Processed files will be stored inside
    a new folder called "dragons_test_inputs". The sub-directory structure
    should reflect the one returned by the `path_to_inputs` fixture.
    """
    import os
    from astrodata.testing import download_from_archive

    root_path = os.path.join("./dragons_test_inputs/")
    module_path = "geminidr/gmos/test_gmos_spect_ls_determine_wavelength_solution/"
    path = os.path.join(root_path, module_path, "inputs")

    os.makedirs(path, exist_ok=True)
    os.chdir(path)
    print('Current working directory:\n    {:s}'.format(os.getcwd()))

    for filename, _, _, _ in input_pars:
        print('Downloading files...')
        basename = filename.split("_")[0] + ".fits"
        sci_path = download_from_archive(basename)
        sci_ad = astrodata.open(sci_path)
        data_label = sci_ad.data_label()

        print('Reducing pre-processed data:')
        logutils.config(file_name='log_{}.txt'.format(data_label))
        p = primitives_gmos_spect.GMOSSpect([sci_ad])
        p.prepare()
        p.addDQ(static_bpm=None)
        p.addVAR(read_noise=True)
        p.overscanCorrect()
        p.ADUToElectrons()
        p.addVAR(poisson_noise=True)
        p.mosaicDetectors()
        p.makeIRAFCompatible()

        processed_ad = p.writeOutputs().pop()
        print('Wrote pre-processed file to:\n'
              '    {:s}'.format(processed_ad.filename))


if __name__ == '__main__':
    import sys

    if "--create-inputs" in sys.argv[1:]:
        create_inputs_recipe()
    else:
        pytest.main()
