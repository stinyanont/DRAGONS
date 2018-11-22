import numpy as np
import math
from astropy.modeling import fitting, models, FittableModel, Parameter
from astropy.modeling.fitting import (_validate_model,
                                      _fitter_to_model_params,
                                      _model_to_fit_params, Fitter,
                                      _convert_input)
from astropy.wcs import WCS

from scipy import optimize, spatial
from datetime import datetime

from matplotlib import pyplot as plt

from gempy.gemini import gemini_tools as gt
from ..utils import logutils

##############################################################################
class MatchBox(object):
    """
    A class to hold two sets of coordinates that have a one-to-one
    correspondence, and the transformations that go between them.
    """
    def __init__(self, input_coords, output_coords, forward_model=None,
                 backward_model=None, fitter=fitting.LinearLSQFitter,
                 domain=None, **kwargs):
        super(MatchBox, self).__init__(**kwargs)
        self._input_coords = list(input_coords)
        self._output_coords = list(output_coords)
        try:
            self._ndim = len(self._input_coords[0])
        except TypeError:
            self._ndim = 1
        self.validate_coords()
        self._forward_model = forward_model
        self._backward_model = backward_model
        self._fitter = fitter
        self._domain = domain

    def validate_coords(self, input_coords=None, output_coords=None):
        """Confirm that the two sets of coordinates are compatible"""
        if input_coords is None:
            input_coords = self._input_coords
        if output_coords is None:
            output_coords = self._output_coords
        if len(input_coords) != len(output_coords):
            raise ValueError("Coordinate lists have different lengths")
        try:
            for coord in input_coords+output_coords:
                try:
                    assert len(coord) == self._ndim
                except TypeError:
                    assert self._ndim == 1
        except AssertionError:
            raise ValueError("Incompatible elements in one or both coordinate lists")

    @property
    def input_coords(self):
        return self._input_coords

    @property
    def output_coords(self):
        return self._output_coords

    @property
    def forward(self):
        """Compute the forward transformation"""
        return self._forward_model

    @forward.setter
    def forward(self, model):
        if isinstance(model, FittableModel):
            self._forward_model = model
        else:
            raise ValueError("Model is not Fittable")

    @property
    def backward(self):
        """Compute the backward transformation"""
        return self._backward_model

    @backward.setter
    def backward(self, model):
        if isinstance(model, FittableModel):
            self._backward_model = model
        else:
            raise ValueError("Model is not Fittable")

    def _fit(self, model, input_coords, output_coords):
        """Fits a model to input and output coordinates after repackaging
        them in the correct format"""
        fit = self._fitter()
        prepared_input = np.array(input_coords).T
        prepared_output = np.array(output_coords).T
        if len(prepared_input) == 1:
            prepared_input = (prepared_input,)
            prepared_output = (prepared_output,)
        return fit(model, prepared_input, prepared_output)

    def fit_forward(self, model=None, coords=None, set_inverse=True):
        """
        Fit the forward (input->output) model.

        Parameters
        ----------
        model: FittableModel
            initial model guess (if None, use the _forward_model)
        coords: array-like
            if not None, fit the backward-transformed version of these coords
            to these coords (_backward_model must not be None)
        set_inverse: bool
            set the inverse (backward) model too, if possible?
        """
        if model is None:
            model = self._forward_model
        if model is None:
            raise ValueError("No forward model specified")
        if coords is None:
            coords = self._input_coords
            out_coords = self._output_coords
        else:
            if self._backward_model is None:
                raise ValueError("A backward model must exist to map specific coords")
            out_coords = self.backward(coords)
        fitted_model = self._fit(model, coords, out_coords)
        self._forward_model = fitted_model
        if set_inverse:
            try:
                self._backward_model = fitted_model.inverse
            except NotImplementedError:
                pass

    def fit_backward(self, model=None, coords=None, set_inverse=True):
        """
        Fit the backward (output->input) model. If this has an inverse, set the
        forward_model to its inverse.

        Parameters
        ----------
        model: FittableModel
            initial model guess (if None, use the _backward_model)
        coords: array-like
            if not None, fit the forward-transformed version of these coords
            to these coords (_forward_model must not be None)
        set_inverse: bool
            set the inverse (forward) model too, if possible?
        """
        if model is None:
            model = self._backward_model
        if model is None:
            raise ValueError("No backward model specified")
        if coords is None:
            coords = self._output_coords
            out_coords = self._input_coords
        else:
            if self._forward_model is None:
                raise ValueError("A forward model must exist to map specific coords")
            out_coords = self.forward(coords)
        fitted_model = self._fit(model, coords, out_coords)
        self._backward_model = fitted_model
        if set_inverse:
            try:
                self._forward_model = fitted_model.inverse
            except NotImplementedError:
                pass

    def add_coords(self, input_coords, output_coords):
        """
        Add coordinates to the input and output coordinate lists

        Parameters
        ----------
        input_coords: array-like/value
            New input coordinates
        output_coords: array-like/value
            New output coordinates
        """
        try:  # Replace value with single-element list
            len(input_coords)
        except TypeError:
            input_coords = [input_coords]
            output_coords = [output_coords]
        self.validate_coords(input_coords, output_coords)
        self._input_coords.extend(input_coords)
        self._output_coords.extend(output_coords)

    def __delitem__(self, index):
        del self._input_coords[index]
        del self._output_coords[index]

    def sort(self, by_output=False, reverse=False):
        """
        Sort the coordinate lists, either by input or output.

        Parameters
        ----------
        by_output: bool
            If set, sort by the output coords rather than input coords
        reverse: bool
            If set, put the largest elements at the start of the list
        """
        ordered = zip(*sorted(zip(self._input_coords, self._output_coords),
                                  reverse=reverse, key=lambda x: x[1 if by_output else 0]))
        self._input_coords, self._output_coords = ordered

    @property
    def residuals(self):
        """
        Return the residuals of the fit
        """
        try:
            len(self._input_coords[0])
        except TypeError:
            return self._output_coords - self.forward(self._input_coords)
        else:
            return list(c1[i]-c2[i] for c1, c2 in zip(self._output_coords,
                                                      self.forward(self._input_coords))
                        for i in range(self._ndim))

    @property
    def rms_input(self):
        """
        Return the rms of the fit in input units
        """
        return self._rms(self._input_coords, self.backward(self._output_coords))

    @property
    def rms_output(self):
        """
        Return the rms of the fit in output units
        """
        return self._rms(self._output_coords, self.forward(self._input_coords))

    def _rms(self, coords1, coords2):
        try:
            len(coords1[0])
        except TypeError:
            return np.std(coords1 - coords2)
        else:
            return list(np.std([c1[i]-c2[i] for c1,c2 in zip(coords1,coords2)])
                        for i in range(self._ndim))

##############################################################################

class Chebyshev1DMatchBox(MatchBox):
    """
    A MatchBox that specifically has Chebyshev1D transformations, and provides
    additional plotting methods for analysis.
    """
    def __init__(self, input_coords, output_coords, forward_model=None,
                 backward_model=None, fitter=fitting.LinearLSQFitter,
                 **kwargs):
        if not isinstance(forward_model, models.Chebyshev1D):
            raise ValueError("forward_model is not a Chebyshev1D instance")
        if (backward_model is not None and
                not isinstance(backward_model, models.Chebyshev1D)):
            raise ValueError("backward_model is not a Chebyshev1D instance")
        super(Chebyshev1DMatchBox, self).__init__(input_coords, output_coords,
                                                  forward_model=forward_model,
                                                  backward_model=backward_model,
                                                  fitter=fitter, **kwargs)

    def display_fit(self, remove_orders=1, axes=None, show=False):
        """
        Plot the fit

        Parameters
        ----------
        remove_orders: int
            Only show the fit's orders above this value (so the default value
            of 1 removes the linear component)
        axes: None/Axes object
            axes for plotting (None => create new figure)
        show: bool
            call plt.show() method at end?
        """
        if axes is None:
            fig, axes = plt.subplots()

        model = self.forward.copy()
        if not (remove_orders is None or remove_orders < 0):
            for i in range(0, remove_orders+1):
                setattr(model, 'c{}'.format(i), 0)

        limits = self._forward_model.domain or (min(self._input_coords), max(self._input_coords))
        x = np.linspace(limits[0], limits[1], 1000)
        axes.plot(self.forward(x), model(x))
        axes.plot(self.forward(self._input_coords), model(self._input_coords)+self.residuals, 'ko')

        if show:
            plt.show()

##############################################################################

class Pix2Sky(FittableModel):
    """
    Wrapper to make an astropy.WCS object act like an astropy.modeling.Model
    object, including having an inverse.
    """
    def __init__(self, wcs, x_offset=0.0, y_offset=0.0, factor=1.0, angle=0.0,
                 direction=1, factor_scale=1.0, angle_scale=1.0, **kwargs):
        self._wcs = wcs.deepcopy()
        self._direction = direction
        self._factor_scale = float(factor_scale)
        self._angle_scale = float(angle_scale)
        super(Pix2Sky, self).__init__(x_offset, y_offset, factor, angle,
                                      **kwargs)

    inputs = ('x','y')
    outputs = ('x','y')
    x_offset = Parameter()
    y_offset = Parameter()
    factor = Parameter()
    angle = Parameter()

    def evaluate(self, x, y, x_offset, y_offset, factor, angle):
        # x_offset and y_offset are actually arrays in the Model
        #temp_wcs = self.wcs(x_offset[0], y_offset[0], factor, angle)
        temp_wcs = self.wcs
        return temp_wcs.all_pix2world(x, y, 1) if self._direction>0 \
            else temp_wcs.all_world2pix(x, y, 1)

    @property
    def inverse(self):
        inv = self.copy()
        inv._direction = -self._direction
        return inv

    @property
    def wcs(self):
        """Return the WCS modified by the translation/scaling/rotation"""
        wcs = self._wcs.deepcopy()
        x_offset = self.x_offset.value
        y_offset = self.y_offset.value
        angle = self.angle.value
        factor = self.factor.value
        wcs.wcs.crpix += np.array([x_offset, y_offset])
        if factor != self._factor_scale:
            wcs.wcs.cd *= factor / self._factor_scale
        if angle != 0.0:
            m = models.Rotation2D(angle / self._angle_scale)
            wcs.wcs.cd = m(*wcs.wcs.cd)
        return wcs


class Shift2D(FittableModel):
    """2D translation"""
    inputs = ('x', 'y')
    outputs = ('x', 'y')
    x_offset = Parameter(default=0.0)
    y_offset = Parameter(default=0.0)

    @property
    def inverse(self):
        inv = self.copy()
        inv.x_offset = -self.x_offset
        inv.y_offset = -self.y_offset
        return inv

    @staticmethod
    def evaluate(x, y, x_offset, y_offset):
        return x+x_offset, y+y_offset

class Scale2D(FittableModel):
    """ 2D scaling. A "factor_scale" is included here because the minimization
    routines use the same absolute tolerance in all parameters, so we need to
    engineer the parameters such that a 0.01 change in this parameter has the
    same sort of effect in positions as a 0.01 change in a shift."""
    def __init__(self, factor=1.0, factor_scale=1.0, **kwargs):
        self._factor_scale = factor_scale
        super(Scale2D, self).__init__(factor, **kwargs)

    inputs = ('x', 'y')
    outputs = ('x', 'y')
    factor = Parameter(default=1.0)

    @property
    def inverse(self):
        inv = self.copy()
        inv.factor = self._factor_scale**2/self.factor
        return inv

    def evaluate(self, x, y, factor):
        return x*factor/self._factor_scale, y*factor/self._factor_scale

class Rotate2D(FittableModel):
    """Rotation; Rotation2D isn't fittable. The parameter scaling mechanism
    is also included here (see Scale2D)"""
    def __init__(self, angle=0.0, angle_scale=1.0, **kwargs):
        self._angle_scale = angle_scale
        super(Rotate2D, self).__init__(angle, **kwargs)

    inputs = ('x', 'y')
    outputs = ('x', 'y')
    angle = Parameter(default=0.0, getter=np.rad2deg, setter=np.deg2rad)

    @property
    def inverse(self):
        inv = self.copy()
        inv.angle = -self.angle
        return inv

    def evaluate(self, x, y, angle):
        if x.shape != y.shape:
            raise ValueError("Expected input arrays to have the same shape")
        orig_shape = x.shape or (1,)
        inarr = np.array([x.flatten(), y.flatten()])
        s, c = math.sin(angle/self._angle_scale), math.cos(angle/self._angle_scale)
        x, y = np.dot(np.array([[c, -s], [s, c]], dtype=np.float64), inarr)
        x.shape = y.shape = orig_shape
        return x, y

##############################################################################

def _landstat(landscape, updated_model, in_coords):
    """
    Compute the statistic for transforming coordinates onto an existing
    "landscape" of "mountains" representing source positions. Since the
    landscape is an array and therefore pixellated, the precision is limited.

    Parameters
    ----------
    landscape: nD array
        synthetic image representing locations of sources in reference plane
    updated_model: Model
        transformation (input -> reference) being investigated
    in_coords: nD array
        input coordinates

    Returns
    -------
    float:
        statistic representing quality of fit to be minimized
    """
    def _element_if_in_bounds(arr, index):
        try:
            return arr[index]
        except IndexError:
            return 0

    out_coords = updated_model(*in_coords)
    if len(in_coords) == 1:
        out_coords = (out_coords,)
    out_coords2 = tuple((coords-0.5).astype(int) for coords in out_coords)
    sum = np.sum(_element_if_in_bounds(landscape, coord[::-1]) for coord in zip(*out_coords2))
    ################################################################################
    # This stuff replaces the above 3 lines if speed doesn't hold up
    #    sum = np.sum(landscape[i] for i in out_coords if i>=0 and i<len(landscape))
    #elif len(in_coords) == 2:
    #    xt, yt = out_coords
    #    sum = np.sum(landscape[iy,ix] for ix,iy in zip((xt-0.5).astype(int),
    #                                                   (yt-0.5).astype(int))
    #                  if ix>=0 and iy>=0 and ix<landscape.shape[1]
    #                                     and iy<landscape.shape[0])
    ################################################################################
    return -sum  # to minimize

class BruteLandscapeFitter(Fitter):
    """
    Fitter class that employs brute-force optimization to map a set of input
    coordinates onto a set of reference coordinates by cross-correlation
    over a "landscape" of "mountains" representing the reference coords
    """
    def __init__(self):
        super(BruteLandscapeFitter, self).__init__(optimize.brute,
                                              statistic=_landstat)

    @staticmethod
    def mklandscape(coords, sigma, maxsig, landshape):
        """
        Populates an array with Gaussian mountains at specified coordinates.
        Used to allow rapid goodness-of-fit calculations for cross-correlation.

        Parameters
        ----------
        coords: 2xN float array
            coordinates of sources
        sigma: float
            standard deviation of Gaussian in pixels
        maxsig: float
            extent (in standard deviations) of each Gaussian
        landshape: 2-tuple
            shape of array

        Returns
        -------
        float array:
            the "landscape", populated by "mountains"
        """
        # Turn 1D arrays into tuples to allow iteration over axes
        try:
            iter(coords[0])
        except TypeError:
            coords = (coords,)

        landscape = np.zeros(landshape)
        hw = int(maxsig * sigma)
        grid = np.meshgrid(*[np.arange(0, hw*2+1)]*landscape.ndim)
        rsq = np.sum((ax - hw)**2 for ax in grid)
        mountain = np.exp(-0.5 * rsq / (sigma * sigma))

        # Place a mountain onto the landscape for each coord in coords
        # Need to crop at edges if mountain extends beyond landscape
        for coord in zip(*coords):
            lslice = []
            mslice = []
            for pos, length in zip(coord[::-1], landshape):
                l1, l2 = int(pos-0.5)-hw, int(pos-0.5)+hw+1
                m1, m2 = 0, hw*2+1
                if l2 < 0 or l1 >= length:
                    break
                if l1 < 0:
                    m1 -= l1
                    l1 = 0
                if l2 > length:
                    m2 -= (l2 - length)
                    l2 = length
                lslice.append(slice(l1, l2))
                mslice.append(slice(m1, m2))
            else:
                landscape[tuple(lslice)] += mountain[tuple(mslice)]
        return landscape

    def __call__(self, model, in_coords, ref_coords, sigma=5.0, maxsig=4.0,
                 landscape=None, **kwargs):
        model_copy = _validate_model(model, ['bounds', 'fixed'])

        # Turn 1D arrays into tuples to allow iteration over axes
        try:
            iter(in_coords[0])
        except TypeError:
            in_coords = (in_coords,)
        try:
            iter(ref_coords[0])
        except TypeError:
            ref_coords = (ref_coords,)

        if landscape is None:
            landshape = tuple(int(max(np.max(inco), np.max(refco)))
                              for inco, refco in zip(in_coords, ref_coords))
            landscape = self.mklandscape(ref_coords, sigma, maxsig, landshape)

        farg = (model_copy,) + _convert_input(in_coords, landscape)
        p0, _ = _model_to_fit_params(model_copy)

        # TODO: Use the name of the parameter to infer the step size
        ranges = []
        for p in model_copy.param_names:
            bounds = model_copy.bounds[p]
            try:
                diff = np.diff(bounds)[0]
            except TypeError:
                pass
            else:
                # We don't check that the value of a fixed param is within bounds
                if diff > 0 and not model_copy.fixed[p]:
                    ranges.append(slice(*(bounds+(min(0.5*sigma, 0.1*diff),))))
                    continue
            ranges.append((getattr(model_copy, p).value,) * 2)

        # Ns=1 limits the fitting along an axis where the range is not a slice
        # object: this is those were the bounds are equal (i.e. fixed param)
        fitted_params = self._opt_method(self.objective_function, ranges,
                                         farg, Ns=1, finish=None, **kwargs)
        _fitter_to_model_params(model_copy, fitted_params)
        return model_copy

def _kdstat(tree, updated_model, in_coords, sigma, maxsig, k):
    """
    Compute the statistic for transforming coordinates onto a set of reference
    coordinates. This uses mathematical calulations and is not pixellated like
    the landscape-array methods.

    Parameters
    ----------
    tree: KDTree
        a KDTree made from the reference coordinates
    updated_model: Model
        transformation (input -> reference) being investigated
    x, y: float arrays
        input x, y coordinates
    sigma: float
        standard deviation of Gaussian (in pixels) used to represent each source
    maxsig: float
        maximum number of standard deviations of Gaussian extent

    Returns
    -------
    float:
        statistic representing quality of fit to be minimized
    """
    f = 0.5/(sigma*sigma)
    maxsep = maxsig*sigma
    out_coords = updated_model(*in_coords)
    if len(in_coords) == 1:
        out_coords = (out_coords,)
    dist, idx = tree.query(list(zip(*out_coords)), k=k, distance_upper_bound=maxsep)
    if k > 1:
        sum = np.sum(np.exp(-f*d*d) for dd in dist for d in dd)
    else:
        sum = np.sum(np.exp(-f*d*d) for d in dist)
    return -sum  # to minimize

class KDTreeFitter(Fitter):
    """
    Fitter class that uses minimization (the method can be passed as a
    parameter to the instance) to determine the transformation to map a set
    of input coordinates to a set of reference coordinates.
    """
    def __init__(self):
        self.statistic = None
        self.niter = None
        super(KDTreeFitter, self).__init__(optimize.minimize,
                                           statistic=_kdstat)

    def __call__(self, model, in_coords, ref_coords, sigma=5.0, maxsig=4.0,
                 k=5, **kwargs):
        model_copy = _validate_model(model, ['bounds', 'fixed'])

        # Turn 1D arrays into tuples to allow iteration over axes
        try:
            iter(in_coords[0])
        except TypeError:
            in_coords = (in_coords,)
        try:
            iter(ref_coords[0])
        except TypeError:
            ref_coords = (ref_coords,)

        # Starting simplex step size is set to be 5% of parameter values
        # Need to ensure this is larger than the convergence tolerance
        # so move the initial values away from zero if necessary
        try:
            xtol = kwargs['options']['xtol']
        except KeyError:
            pass
        else:
            for p in model_copy.param_names:
                pval = getattr(model_copy, p).value
                ### EDITED THIS LINE SO TAKE A LOOK IF 2D MATCHING GOES WRONG!!
                if abs(pval) < 20*xtol and not model_copy.fixed[p]:  # and 'offset' in p
                    getattr(model_copy, p).value = 20*xtol if pval == 0 \
                        else (np.sign(pval) * 20*xtol)

        tree = spatial.cKDTree(list(zip(*ref_coords)))
        # avoid _convert_input since tree can't be coerced to a float
        farg = (model_copy, in_coords, sigma, maxsig, k, tree)
        p0, _ = _model_to_fit_params(model_copy)

        result = self._opt_method(self.objective_function, p0, farg,
                                  **kwargs)
        fitted_params = result['x']
        _fitter_to_model_params(model_copy, fitted_params)
        self.statistic = result['fun']
        self.niter = result['nit']
        return model_copy


def fit_brute_then_simplex(model, xin, xout, sigma=5.0, tolerance=0.001,
                           unbound=False, unfix=False, verbose=True):
    """
    Finds the best-fitting mapping to convert from xin to xout, using a
    two-step approach by first doing a brute-force scan of parameter space,
    and then doing simplex fitting from this starting position.
    Handles a fixed parameter by setting the bounds equal to the value.

    Parameters
    ----------
    model: FittableModel
        initial model guess
    xin: array-like
        input coordinates
    xout: array-like
        coordinates to fit to
    sigma: float
        size of the mountains for the BruteLandscapeFitter
    tolerance: float
        accuracy of parameters in final answer
    unbound: boolean
        remove the parameter bounds for the simplex fit?
    unfix: boolean
        free fixed parameters for the simplex fit?
    verbose: boolean
        output model and time info?

    Returns
    -------
    Model: the best-fitting mapping from xin -> xout
    """
    log = logutils.get_logger(__name__)
    start = datetime.now()

    # Since optimize.brute can't handle "fixed" parameters, we have to unfix
    # them and control things by setting the bounds to a zero-width interval
    #for p in model.param_names:
    #    pval = getattr(model, p).value
    #    if getattr(model, p).fixed:
    #        getattr(model, p).bounds = (pval, pval)
    #        getattr(model, p).fixed = False

    # Brute-force grid search using an image landscape
    fit_it = BruteLandscapeFitter()
    m = fit_it(model, xin, xout, sigma=sigma)
    if verbose:
        log.stdinfo(_show_model(m, "Coarse model in {:.2f} seconds".
                                format((datetime.now() - start).total_seconds())))

    # Re-fix parameters in the intermediate model, if they were fixed
    # in the original model
    for p in m.param_names:
        if unfix:
            getattr(m, p).fixed = False
        if unbound:
            getattr(m, p).bounds = (None, None)
        try:
            if np.diff(getattr(model, p).bounds)[0] == 0:
                if not unfix:
                    getattr(m, p).fixed = True
                continue
        except TypeError:
            pass

    # More precise minimization using pairwise calculations
    fit_it = KDTreeFitter()
    # We don't care about how much the function value changes (ftol), only
    # that the position is robust (xtol)
    final_model = fit_it(m, xin, xout, method='Nelder-Mead',
                     options={'xtol': tolerance, 'ftol': 100.0})
    if verbose:
        log.stdinfo(_show_model(final_model, "Final model in {:.2f} seconds".
                                format((datetime.now() - start).total_seconds())))
    return final_model

def _show_model(model, intro=""):
    """Provide formatted output of a (possibly compound) transformation"""
    model_str = "{}\n".format(intro) if intro else ""
    try:
        iterator = iter(model)
    except TypeError:
        iterator = [model]
    # We don't want to show the centering model (or its inverse), and we want
    # to scale the model parameters to their internally-stored values
    for m in iterator:
        if m.name != 'Centering':
            for name, value in zip(m.param_names, m.parameters):
                if not getattr(m, name).fixed:
                    pscale = getattr(m, '_{}_scale'.format(name), 1.0)
                    model_str += "{}: {}\n".format(name, value/pscale)
    return model_str

##############################################################################

def align_catalogs(xin, yin, xref, yref, model_guess=None,
                   translation=None, translation_range=None,
                   rotation=None, rotation_range=None,
                   magnification=None, magnification_range=None,
                   tolerance=0.1, center_of_field=None):
    """
    Generic interface for a 2D catalog match. Either an initial model guess
    is provided, or a model will be created using a combination of
    translation, rotation, and magnification, as requested. Only those
    transformations for which a *range* is specified will be used. In order
    to keep the translation close to zero, the rotation and magnification
    are performed around the centre of the field, which can either be provided
    -- as (x,y) in 1-based pixels -- or will be determined from the mid-range
    of the x and y input coordinates.

    Parameters
    ----------
    xin, yin: float arrays
        input coordinates
    xref, yref: float arrays
        reference coordinates to map and match to
    model_guess: Model
        initial model guess (overrides the next parameters)
    translation: 2-tuple of floats
        initial translation guess
    translation_range: None, value, 2-tuple or 2x2-tuple
        None => fixed
        value => search range from initial guess (same for x and y)
        2-tuple => search limits (same for x and y)
        2x2-tuple => search limits for x and y
    rotation: float
        initial rotation guess (degrees)
    rotation_range: None, float, or 2-tuple
        extent of search space for rotation
    magnification: float
        initial magnification factor
    magnification_range: None, float, or 2-tuple
        extent of search space for magnification
    tolerance: float
        accuracy required for final result
    center_of_field: 2-tuple
        rotation and magnification have no effect at this location
         (if None, uses middle of xin,yin ranges)

    Returns
    -------
    Model: a model that maps (xin,yin) to (xref,yref)
    """
    def _get_value_and_range(value, range):
        """Converts inputs to a central value and a range tuple"""
        try:
            r1, r2 = range
        except TypeError:
            r1, r2 = range, None
        except ValueError:
            r1, r2 = None, None
        if value is not None:
            if r1 is not None and r2 is not None:
                if r1 <= value <= r2:
                    return value, (r1, r2)
                else:
                    extent = 0.5*abs(r2-r1)
                    return value, (value-extent, value+extent)
            elif r1 is not None:
                return value, (value-r1, value+r1)
            else:
                return value, None
        elif r1 is not None:
            if r2 is None:
                return 0.0, (-r1, r1)
            else:
                return 0.5*(r1+r2), (r1, r2)
        else:
            return None, None

    log = logutils.get_logger(__name__)
    if model_guess is None:
        # Some useful numbers for later
        x1, x2 = np.min(xin), np.max(xin)
        y1, y2 = np.min(yin), np.max(yin)
        pixel_range = 0.5*max(x2-x1, y2-y1)

        # Set up translation part of the model
        if hasattr(translation, '__len__'):
            xoff, yoff = translation
        else:
            xoff, yoff = translation, translation
        trange = np.array(translation_range)
        if len(trange.shape) == 2:
            xvalue, xrange = _get_value_and_range(xoff, trange[0])
            yvalue, yrange = _get_value_and_range(yoff, trange[1])
        else:
            xvalue, xrange = _get_value_and_range(xoff, translation_range)
            yvalue, yrange = _get_value_and_range(yoff, translation_range)
        if xvalue is None or yvalue is None:
            trans_model = None
        else:
            trans_model = Shift2D(xvalue, yvalue)
            if xrange is None:
                trans_model.x_offset.fixed = True
            else:
                trans_model.x_offset.bounds = xrange
            if yrange is None:
                trans_model.y_offset.fixed = True
            else:
                trans_model.y_offset.bounds = yrange

        # Set up rotation part of the model
        rvalue, rrange = _get_value_and_range(rotation, rotation_range)
        if rvalue is None:
            rot_model = None
        else:
            # Getting the rotation wrong by da (degrees) will cause a shift of
            # da/57.3*pixel_range at the edge of the data, so we want
            # da=tolerance*57.3/pixel_range
            rot_scaling = pixel_range / 57.3
            rot_model = Rotate2D(rvalue*rot_scaling, angle_scale=rot_scaling)
            if rrange is None:
                rot_model.angle.fixed = True
            else:
                rot_model.angle.bounds = tuple(x*rot_scaling for x in rrange)

        # Set up magnification part of the model
        mvalue, mrange = _get_value_and_range(magnification, magnification_range)
        if mvalue is None:
            mag_model = None
        else:
            # Getting the magnification wrong by dm will cause a shift of
            # dm*pixel_range at the edge of the data, so we want
            # dm=tolerance/pixel_range
            mag_scaling = pixel_range
            mag_model = Scale2D(mvalue*mag_scaling, factor_scale=mag_scaling)
            if mrange is None:
                mag_model.factor.fixed = True
            else:
                mag_model.factor.bounds = tuple(x*mag_scaling for x in mrange)

        # Make the compound model
        if rot_model is None and mag_model is None:
            if trans_model is None:
                return models.Identity(2)  # Nothing to do
            else:
                init_model = trans_model  # Don't need center of field
        else:
            if center_of_field is None:
                center_of_field = (0.5 * (x1 + x2), 0.5 * (y1 + y2))
                log.debug('No center of field given, using x={:.2f} '
                          'y={:.2f}'.format(*center_of_field))
            restore = Shift2D(*center_of_field).rename('Centering')
            restore.x_offset.fixed = True
            restore.y_offset.fixed = True

            init_model = restore.inverse
            if trans_model is not None:
                init_model |= trans_model
            if rot_model is not None:
                init_model |= rot_model
            if mag_model is not None:
                init_model |= mag_model
            init_model |= restore
    elif model_guess.fittable:
        init_model = model_guess
    else:
        log.warning('The transformation is not fittable!')
        return models.Identity(2)

    final_model = fit_brute_then_simplex(init_model, (xin, yin), (xref, yref),
                               sigma=10.0, tolerance=tolerance)
    return final_model

def match_sources(incoords, refcoords, radius=2.0, priority=[]):
    """
    Match two sets of sources that are on the same reference frame. In general
    the closest match will be used, but there can be a priority list that will
    take precedence.

    Parameters
    ----------
    incoords: 2xN array
        input source coords (transformed to reference frame)
    refcoords: 2xM array
        reference source coords
    radius:
        maximum separation for a match
    priority: list of ints
        items in incoords that should have priority, even if a closer
        match is found

    Returns
    -------
    int array of length N:
        index of matched sources in the reference list (-1 means no match)
    """
    try:
        iter(incoords[0])
    except TypeError:
        incoords = (incoords,)
        refcoords = (refcoords,)
    matched = np.full((len(incoords[0]),), -1, dtype=int)
    tree = spatial.cKDTree(list(zip(*refcoords)))
    dist, idx = tree.query(list(zip(*incoords)), distance_upper_bound=radius)
    for i in range(len(refcoords[0])):
        inidx = np.where(idx==i)[0][np.argsort(dist[np.where(idx==i)])]
        for ii in inidx:
            if ii in priority:
                matched[ii] = i
                break
        else:
            # No first_allowed so take the first one
            if len(inidx):
                matched[inidx[0]] = i
    return matched

def match_catalogs(xin, yin, xref, yref, use_in=None, use_ref=None,
                   model_guess=None, translation=None,
                   translation_range=None, rotation=None,
                   rotation_range=None, magnification=None,
                   magnification_range=None, tolerance=0.1,
                   center_of_field=None, match_radius=1.0):
    """
    Aligns catalogs with align_catalogs(), and then matches sources with
    match_sources()

    Parameters
    ----------
    xin, yin: float arrays
        input coordinates
    xref, yref: float arrays
        reference coordinates to map and match to
    use_in: list/None
        only use these input sources for matching (None => all)
    use_ref: list/None
        only use these reference sources for matching (None => all)
    model_guess: Model
        initial model guess (overrides the next parameters)
    translation: 2-tuple of floats
        initial translation guess
    translation_range: value, 2-tuple or 2x2-tuple
        value => search range from initial guess (same for x and y)
        2-tuple => search limits (same for x and y)
        2x2-tuple => search limits for x and y
    rotation: float
        initial rotation guess (degrees)
    rotation_range: float or 2-tuple
        extent of search space for rotation
    magnification: float
        initial magnification factor
    magnification_range: float or 2-tuple
        extent of search space for magnification
    tolerance: float
        accuracy required for final result
    center_of_field: 2-tuple
        rotation and magnification have no effect at this location
         (if None, uses middle of xin,yin ranges)

    Returns
    -------
    int array of length N:
        index of matched sources in the reference list (-1 means no match)
    Model:
        best-fitting alignment model
    """
    if use_in is None:
        use_in = list(range(len(xin)))
    if use_ref is None:
        use_ref = list(range(len(xref)))

    model = align_catalogs(xin[use_in], yin[use_in], xref[use_ref], yref[use_ref],
                           model_guess=model_guess, translation=translation,
                           translation_range=translation_range, rotation=rotation,
                           rotation_range=rotation_range, magnification=magnification,
                           magnification_range=magnification_range, tolerance=tolerance,
                           center_of_field=center_of_field)
    matched = match_sources(model(xin, yin), (xref, yref), radius=match_radius,
                               priority=use_in)
    return matched, model

def align_images_from_wcs(adinput, adref, first_pass=10, cull_sources=False,
                          initial_shift = (0,0), min_sources=1, rotate=False,
                          scale=False, full_wcs=False, refine=False,
                          tolerance=0.1, return_matches=False):
    """
    This function takes two images (an input image, and a reference image) and
    works out the modifications needed to the WCS of the input images so that
    the world coordinates of its OBJCAT sources match the world coordinates of
    the OBJCAT sources in the reference image. This is done by modifying the
    WCS of the input image and mapping the reference image sources to pixels
    in the input image via the reference image WCS (fixed) and the input image
    WCS. As such, in the nomenclature of the fitting routines, the pixel
    positions of the input image's OBJCAT become the "reference" sources,
    while the converted positions of the reference image's OBJCAT are the
    "input" sources.

    Parameters
    ----------
    adinput: AstroData
        input AD whose pixel shift is requested
    adref: AstroData
        reference AD image
    first_pass: float
        size of search box (in arcseconds)
    cull_sources: bool
        limit matched sources to "good" (i.e., stellar) objects
    min_sources: int
        minimum number of sources to use for cross-correlation, depending on the
        instrument used
    rotate: bool
        add a rotation to the alignment transform?
    scale: bool
        add a magnification to the alignment transform?
    full_wcs: bool
        use recomputed WCS at each iteration, rather than modify the positions
        in pixel space?
    refine: bool
        only do a simplex fit to refine an existing transformation?
        (requires full_wcs=True). Also ignores return_matches
    tolerance: float
        matching requirement (in pixels)
    return_matches: bool
        return a list of matched objects?

    Returns
    -------
    matches: 2 lists
        OBJCAT sources in input and reference that are matched
    WCS: new WCS for input image
    """
    log = logutils.get_logger(__name__)
    if len(adinput) * len(adref) != 1:
        log.warning('Can only match single-extension images')
        return None
    if not (hasattr(adinput[0], 'OBJCAT') and hasattr(adref[0], 'OBJCAT')):
        log.warning('Both input images must have object catalogs')
        return None

    if cull_sources:
        good_src1 = gt.clip_sources(adinput)[0]
        good_src2 = gt.clip_sources(adref)[0]
        if len(good_src1) < min_sources or len(good_src2) < min_sources:
            log.warning("Too few sources in culled list, using full set "
                        "of sources")
            x1, y1 = adinput[0].OBJCAT['X_IMAGE'], adinput[0].OBJCAT['Y_IMAGE']
            x2, y2 = adref[0].OBJCAT['X_IMAGE'], adref[0].OBJCAT['Y_IMAGE']
        else:
            x1, y1 = good_src1["x"], good_src1["y"]
            x2, y2 = good_src2["x"], good_src2["y"]
    else:
        x1, y1 = adinput[0].OBJCAT['X_IMAGE'], adinput[0].OBJCAT['Y_IMAGE']
        x2, y2 = adref[0].OBJCAT['X_IMAGE'], adref[0].OBJCAT['Y_IMAGE']

    # convert reference positions to sky coordinates
    ra2, dec2 = WCS(adref[0].hdr).all_pix2world(x2, y2, 1)

    func = match_catalogs if return_matches else align_catalogs

    if full_wcs:
        # Set up the (inverse) Pix2Sky transform with appropriate scalings
        pixel_range = max(adinput[0].data.shape)
        transform = Pix2Sky(WCS(adinput[0].hdr), factor=pixel_range,
                            factor_scale=pixel_range, angle=0.0,
                            angle_scale=pixel_range/57.3, direction=-1)
        x_offset, y_offset = initial_shift
        transform.x_offset = x_offset
        transform.y_offset = y_offset
        transform.angle.fixed = not rotate
        transform.factor.fixed = not scale

        if refine:
            fit_it = KDTreeFitter()
            final_model = fit_it(transform, (ra2, dec2), (x1, y1),
                                 method='Nelder-Mead',
                                 options={'xtol': tolerance, 'ftol': 100.0})
            log.stdinfo(_show_model(final_model, 'Refined transformation'))
            return final_model
        else:
            transform.x_offset.bounds = (x_offset-first_pass, x_offset+first_pass)
            transform.y_offset.bounds = (y_offset-first_pass, y_offset+first_pass)
            if rotate:
                # 5.73 degrees
                transform.angle.bounds = (-0.1*pixel_range, 0.1*pixel_range)
            if scale:
                # 5% scaling
                transform.factor.bounds = (0.95*pixel_range, 1.05*pixel_range)

            # map input positions (in reference frame) to reference positions
            func_ret = func(ra2, dec2, x1, y1, model_guess=transform,
                            tolerance=tolerance)
    else:
        x2a, y2a = WCS(adinput[0].hdr).all_world2pix(ra2, dec2, 1)
        func_ret = func(x2a, y2a, x1, y1, model_guess=None,
                        translation=initial_shift,
                        translation_range=first_pass,
                        rotation_range=5.0 if rotate else None,
                        magnification_range=0.05 if scale else None,
                        tolerance=tolerance)

    if return_matches:
        matched, transform = func_ret
        ind2 = np.where(matched >= 0)
        ind1 = matched[ind2]
        obj_list = [[], []] if len(ind1) < 1 else [list(zip(x1[ind1], y1[ind1])),
                                                   list(zip(x2[ind2], y2[ind2]))]
        return obj_list, transform
    else:
        return func_ret
