import re
from abc import ABC, abstractmethod
from copy import copy
from functools import cmp_to_key

from bokeh.core.property.instance import Instance
from bokeh.layouts import column, row
from bokeh.models import (BoxAnnotation, Button, CustomJS, Dropdown,
                          NumeralTickFormatter, RangeSlider, Slider, TextInput, Div, NumericInput)
from bokeh import models as bm

from geminidr.interactive import server
from geminidr.interactive.fit.help import DEFAULT_HELP
from geminidr.interactive.server import register_callback
from gempy.library.astrotools import cartesian_regions_to_slices, parse_user_regions
from gempy.library.config import FieldValidationError


# Singleton instance, there is only ever one of these
_visualizer = None


class PrimitiveVisualizer(ABC):
    def __init__(self, config=None, title='', primitive_name='',
                 filename_info='', template=None, help_text=None):
        """
        Initialize a visualizer.

        This base class creates a submit button suitable for any subclass
        to use and it also listens for the UI window to close, executing a
        submit if that happens.  The submit button will cause the `bokeh`
        event loop to exit and the code will resume executing in whatever
        top level call you are visualizing from.

        Parameters
        ----------
        config : `~gempy.library.config.Config`
            DRAGONS primitive configuration data to work from
        title : str
            Title fo the primitive for display, currently not used
        primitive_name : str
            Name of the primitive function related to this UI, used in the title bar
        filename_info : str
            Information about the file being operated on
        template : str
            Optional path to an html template to render against, if customization is desired
        """
        global _visualizer
        _visualizer = self

        # set help to default, subclasses should override this with something specific to them
        self.help_text = help_text if help_text else DEFAULT_HELP

        self.exited = False
        self.title = title
        self.filename_info = filename_info if filename_info else ''
        self.primitive_name = primitive_name if primitive_name else ''
        self.template = template
        self.extras = dict()
        if config is None:
            self.config = None
        else:
            self.config = copy(config)

        self.user_satisfied = False

        self.bokeh_legend = Div(text='Plot Tools<br/><img src="dragons/static/bokehlegend.png" />')
        self.submit_button = Button(align='center',
                                    button_type='success',
                                    css_classes=["submit_btn"],
                                    id="_submit_btn",
                                    label="Accept",
                                    name="submit_btn",
                                    width_policy='min',
                                    )

        # This now happens indirectly via the /shutdown ajax js callback
        # Remove this line if we stick with that
        # self.submit_button.on_click(self.submit_button_handler)
        callback = CustomJS(code="""
            $.ajax('/shutdown').done(function()
                {
                    window.close();
                });
        """)
        self.submit_button.js_on_click(callback)
        self.doc = None

    def make_ok_cancel_dialog(self, btn, message, callback):
        # This is a bit hacky, but bokeh makes it very difficult to bridge the python-js gap.
        def _internal_handler(args):
            if callback:
                if args['result'] == [b'confirmed']:
                    result = True
                else:
                    result = False
                self.do_later(lambda: callback(result))

        callback_name = register_callback(_internal_handler)

        js_confirm_callback = CustomJS(code="""
            cb_obj.name = '';
            var confirmed = confirm('%s');
            var cbid = '%s';
            if (confirmed) {
                $.ajax('/handle_callback?callback=' + cbid + '&result=confirmed');
            } else {
                $.ajax('/handle_callback?callback=' + cbid + '&result=rejected');
            }
            """ % (message, callback_name))
        btn.js_on_click(js_confirm_callback)

    def submit_button_handler(self, stuff):
        """
        Handle the submit button by stopping the bokeh server, which
        will resume python execution in the DRAGONS primitive.

        Parameters
        ----------
        stuff
            passed by bokeh, but we do not use it

        Returns
        -------
        none
        """
        if not self.exited:
            self.exited = True
            self.user_satisfied = True
            server.stop_server()

    def get_filename_div(self):
        """
        Returns a Div element that displays the current filename.
        """
        div = Div(text=f"<b>Current&nbsp;filename:&nbsp;</b>&nbsp;{self.filename_info}",
                  style={
                         "color": "dimgray",
                         "font-size": "16px",
                         "float": "right",
                  },
                  align="end",
                  )
        return div

    def visualize(self, doc):
        """
        Perform the visualization.

        This is called via bkapp by the bokeh server and happens
        when the bokeh server is spun up to interact with the user.

        Subclasses should implement this method with their particular
        UI needs, but also should call super().visualize(doc) to
        listen for session terminations.

        Parameters
        ----------
        doc : :class:`~bokeh.document.document.Document`
            Bokeh document, this is saved for later in :attr:`~geminidr.interactive.interactive.PrimitiveVisualizer.doc`
        """
        self.doc = doc
        doc.on_session_destroyed(self.submit_button_handler)

        # doc.add_root(self._ok_cancel_dlg.layout)
        # Add an OK/Cancel dialog we can tap into later

    def do_later(self, fn):
        """
        Perform an operation later, on the bokeh event loop.

        This call lets you stage a function to execute within the bokeh event loop.
        This is necessary if you want to interact with the bokeh and you are not
        coming from code that is already executing in that context.  Basically,
        this happens when the code is executing because a key press in the browser
        came in through the tornado server via the `handle_key` URL.

        Parameters
        ----------
        fn : function
            Function to execute in the bokeh loop (should not take required arguments)
        """
        if self.doc is None:
            if hasattr(self, 'log') and self.log is not None:
                self.log.warn("Call to do_later, but no document is set.  Does this PrimitiveVisualizer call "
                              "super().visualize(doc)?")
            # no doc, probably ok to just execute
            fn()
        else:
            self.doc.add_next_tick_callback(lambda: fn())

    def make_modal(self, widget, message):
        """
        Make a modal dialog that activates whenever the widget is disabled.

        A bit of a hack, but this attaches a modal message that freezes
        the whole UI when a widget is disabled.  This is intended for long-running
        operations.  So, what you do is you set `widget.disabled=True` in your
        code and then use `do_later` to queue a long running bit of work.  When
        that work is finished, it should also do a `widget.disabled=False`.

        The reason the work has to be posted to the bokeh loop via `do_later`
        is to allow this modal dialog to execute first.

        Parameters
        ----------
        widget : :class:`~bokeh.models.widgets.widget.Widget`
            bokeh widget to watch for disable/enable
        message : str
            message to display in the popup modal
        """
        callback = CustomJS(args=dict(source=widget), code="""
            if (source.disabled) {
                openModal('%s');
            } else {
                closeModal();
            }
        """ % message)
        widget.js_on_change('disabled', callback)

    def make_widgets_from_config(self, params, extras, reinit_live,
                                 slider_width=256):
        """
        Makes appropriate widgets for all the parameters in params,
        using the config to determine the type. Also adds these widgets
        to a dict so they can be accessed from the calling primitive.

        Parameters
        ----------
        params : list of str
            which DRAGONS configuration fields to make a UI for
        extras : dict
            Dictionary of additional field definitions for anything not included in the primitive configuration
        reinit_live : bool
            True if recalcuating points is cheap, in which case we don't need a button and do it on any change.
            Currently only viable for text-slider style inputs
        slider_width : int (default: 256)
            Default width for sliders created here.

        Returns
        -------
        list : Returns a list of widgets to display in the UI.
        """
        extras = {} if extras is None else extras
        params = [] if params is None else params
        widgets = []
        if self.config is None:
            self.log.warn("No config, unable to make widgets")
            return widgets
        for pname, value in self.config.items():
            if pname not in params:
                continue
            field = self.config._fields[pname]
            # Do some inspection of the config to determine what sort of widget we want
            doc = field.doc.split('\n')[0]
            if hasattr(field, 'min'):
                # RangeField => Slider
                start, end = field.min, field.max
                # TODO: Be smarter here!
                if start is None:
                    start = -20
                if end is None:
                    end = 50
                step = start
                allow_none = field.optional
                is_float = field.dtype is not int

                widget = build_text_slider(
                    doc, value, step, start, end, obj=self.config, attr=pname,
                    slider_width=slider_width, allow_none=allow_none,
                    is_float=is_float)

                self.widgets[pname] = widget.children[0]
            elif hasattr(field, 'allowed'):
                # ChoiceField => drop-down menu
                widget = Dropdown(label=doc, menu=list(self.config.allowed.keys()))
            else:
                # Anything else
                print("FIELD", pname)
                widget = TextInput(title=doc)

            widgets.append(widget)
            # Complex multi-widgets will already have been added
            if pname not in self.widgets:
                self.widgets[pname] = widget

        for pname, field in extras.items():
            # Do some inspection of the config to determine what sort of widget we want
            doc = field.doc.split('\n')[0]
            if hasattr(field, 'min'):
                # RangeField => Slider
                start, end = field.min, field.max
                # TODO: Be smarter here!
                if start is None:
                    start = -20
                if end is None:
                    end = 50
                step = start
                allow_none = field.optional
                is_float = field.dtype is not int

                widget = build_text_slider(
                    doc, field.default, step, start, end, obj=self.extras,
                    attr=pname, handler=self.slider_handler_factory(
                        pname, reinit_live=reinit_live),
                    throttled=True, slider_width=slider_width,
                    allow_none=allow_none, is_float=is_float)

                self.widgets[pname] = widget.children[0]
                self.extras[pname] = field.default
            else:
                # Anything else
                widget = TextInput(title=doc)
                self.extras[pname] = ''

            widgets.append(widget)
            # Complex multi-widgets will already have been added
            if pname not in self.widgets:
                self.widgets[pname] = widget

        return widgets

    def slider_handler_factory(self, key, reinit_live=False):
        """
        Returns a function that updates the `extras` attribute.

        Parameters
        ----------
        key : str
            The parameter name to be updated.
        reinit_live : bool, optional
            Update the reconstructed points on "real time".

        Returns
        -------
        function : callback called when we change the slider value.
        """

        def handler(val):
            self.extras[key] = val
            if reinit_live:
                self.reconstruct_points()

        return handler


def build_text_slider(title, value, step, min_value, max_value, obj=None,
                      attr=None, handler=None, throttled=False,
                      slider_width=256, config=None, allow_none=False,
                      is_float=None):
    """
    Make a slider widget to use in the bokeh interface.

    Parameters
    ----------
    title : str
        Title for the slider
    value : int
        Value to initially set
    step : float
        Step size
    min_value : int
        Minimum slider value, or None defaults to min(value,0)
    max_value : int
        Maximum slider value, or None defaults to value*2
    obj : object
        Instance to modify the attribute of when slider changes
    attr : str
        Name of attribute in obj to be set with the new value
    handler : method
        Function to call after setting the attribute
    throttled : bool
        Set to `True` to limit handler calls to when the slider is released (default False)
    allow_none : bool
        Set to `True` to allow an empty text entry to specify a `None` value
    is_float : bool
        nature of parameter (None => try to figure it out)

    Returns
    -------
        :class:`~bokeh.models.layouts.Row` bokeh Row component with the interface inside

    """
    if min_value is None and config is not None:
        field = config._fields.get(attr, None)
        if field is not None:
            if hasattr(field, 'min'):
                min_value = field.min
    if max_value is None and config is not None:
        field = config._fields.get(attr, None)
        if field is not None:
            if hasattr(field, 'max'):
                max_value = field.max

    if value is None:
        start = min_value if min_value is not None else 0
        end = max_value if max_value is not None else 10
        slider_value = start
    else:
        start = min(value, min_value) if min_value is not None else min(value, 0)
        end = max(value, max_value) if max_value is not None else max(10, value*2)
        slider_value = value

    # trying to convince int-based sliders to behave
    if is_float is None:
        is_float = ((value is not None and not isinstance(value, int)) or
                    (min_value is not None and not isinstance(min_value, int)) or
                    (max_value is not None and not isinstance(max_value, int)))
    if step is None:
        if is_float:
            step = 0.1
        else:
            step = 1
    fmt = None
    if not is_float:
        fmt = NumeralTickFormatter(format='0,0')
        slider = Slider(start=start, end=end, value=slider_value, step=step,
                        title=title, format=fmt)
    else:
        slider = Slider(start=start, end=end, value=slider_value, step=step,
                        title=title)

    slider.width = slider_width

    # NOTE: although NumericInput can handle a high/low limit, it
    # offers no feedback to the user when it does.  Since some of our
    # inputs are capped and others open-ended, we use the js callbacks
    # below to enforce the range limits, if any.
    text_input = NumericInput(width=64, value=value,
                              format=fmt,
                              mode='float' if is_float else 'int')

    # Custom range enforcement with alert messages
    if max_value is not None:
        text_input.js_on_change('value', CustomJS(
            args=dict(inp=text_input),
            code="""
                if (%s inp.value > %s) {
                    alert('Maximum is %s');
                    inp.value = %s;
                }
            """ % ("inp.value != null && " if allow_none else "", max_value, max_value, max_value)))
    if min_value is not None:
        text_input.js_on_change('value', CustomJS(
            args=dict(inp=text_input),
            code="""
                if (%s inp.value < %s) {
                    alert('Minimum is %s');
                    inp.value = %s;
                }
            """ % ("inp.value != null && " if allow_none else "", min_value, min_value, min_value)))

    component = row(slider, text_input, css_classes=["text_slider_%s" % attr, ])

    def _input_check(val):
        # Check if the value is viable as an int or float, according to our type
        if ((not is_float) and isinstance(val, int)) or (is_float and isinstance(val, float)):
            return True
        if val is None and not allow_none:
            return False
        if val is None and allow_none:
            return True
        try:
            if is_float:
                float(val)
            else:
                int(val)
            return True
        except ValueError:
            return False

    def update_slider(attrib, old, new):
        # Update the slider with the new value from the text input
        if not _input_check(new):
            if _input_check(old):
                text_input.value = old
            return
        if new is not None and old != new:
            if is_float:
                ival = float(new)
            else:
                ival = int(new)
            if ival > slider.end and not max_value:
                slider.end = ival
            if ival < slider.end and end < slider.end:
                slider.end = max(end, ival)
            if 0 <= ival < slider.start and min_value is None:
                slider.start = ival
            if ival > slider.start and start > slider.start:
                slider.start = min(ival, start)
            if slider.start <= ival <= slider.end:
                slider.value = ival
            slider.show_value = True
        elif new is None:
            slider.show_value = False

    def update_text_input(attrib, old, new):
        # Update the text input
        if new != old:
            text_input.value = new

    def handle_value(attrib, old, new):
        # Handle a new value and set the registered object/attribute accordingly
        # Also updates the slider and calls the registered handler function, if any
        if obj and attr:
            try:
                if not hasattr(obj, attr) and isinstance(obj, dict):
                    obj[attr] = new
                else:
                    obj.__setattr__(attr, new)
            except FieldValidationError:
                # reset textbox
                text_input.remove_on_change("value", handle_value)
                text_input.value = old
                text_input.on_change("value", handle_value)
            else:
                update_slider(attrib, old, new)
        if handler:
            if new is not None:
                handler(new)
            else:
                handler(new)

    if throttled:
        # Since here the text_input calls handle_value, we don't
        # have to call it from the slider as it will happen as
        # a side-effect of update_text_input
        slider.on_change("value_throttled", update_text_input)
        text_input.on_change("value", handle_value)
    else:
        slider.on_change("value", update_text_input)
        # since slider is listening to value, this next line will cause the slider
        # to call the handle_value method and we don't need to do so explicitly
        text_input.on_change("value", handle_value)
    return component


def build_range_slider(title, location, start, end, step, min_value, max_value, obj=None, location_attr=None,
                       start_attr=None, end_attr=None, handler=None, throttled=False):
    """
    Make a range slider widget to use in the bokeh interface.

    Parameters
    ----------
    title : str
        Title for the slider
    location : int or float
        Value for the location
    start : int or float
        Value to initially set for start
    end : int or float
        Value to initially set for end
    step : int or float
        Step size
    min_value : int or float
        Minimum slider value, or None defaults to min(start,0)
    max_value : int or float
        Maximum slider value, or None defaults to end*2
    obj : object
        Instance to modify the attribute of when slider changes
    start_attr : str
        Name of attribute in obj to be set with the new start value
    end_attr : str
        Name of the attribute on obj to be set with the new end value
    handler : method
        Function to call after setting the attribute
    throttled : bool
        Set to `True` to limit handler calls to when the slider is released (default False)

    Returns
    -------
        :class:`~bokeh.models.layouts.Row` bokeh Row component with the interface inside
    """
    # We track of this entry is working on int values or float.  This affects the
    # behavior and type conversion throughout the rest of the slider logic
    is_float = True
    if isinstance(start, int) and isinstance(end, int):
        is_float = False

    slider_start = min(start, min_value) if min_value else min(start, 0)
    slider_end = max(end, max_value) if max_value else max(10, end*2)
    slider = RangeSlider(start=slider_start, end=slider_end, value=(start, end), step=step, title=title)
    slider.width = 192

    start_text_input = TextInput()
    start_text_input.width = 64
    start_text_input.value = str(start)
    location_text_input = TextInput()
    location_text_input.width = 64
    location_text_input.value = str(location)
    end_text_input = TextInput()
    end_text_input.width = 64
    end_text_input.value = str(end)
    component = row(slider, start_text_input, location_text_input, end_text_input)

    def _input_check(val):
        """
        Check the validity of the input value, or reject

        Parameters
        ----------
        val : float or int

        Returns
        -------
            bool : True of the input is valid, False if not.  This may also be the case if a float is passed
            where int is expected
        """
        if ((not is_float) and isinstance(val[0], int) and isinstance(val[1], int)) \
                or (is_float and isinstance(val[0], float) and isinstance(val[1], float)):
            return True
        try:
            if is_float:
                if float(val[0]) > float(val[1]):
                    return False
            else:
                if int(val[0]) > int(val[1]):
                    return False
            if (slider.start > float(val[0]) > slider.end) or (slider.start > float(val[1]) > slider.end):
                # out of view
                return False
            return True
        except ValueError:
            return False

    def update_slider(attrib, old, new):
        """
        This performs an :meth:`~geminidr.interactive.interactive.build_range_slider._input_check`
        on the new value.  If it passes, it is converted and accepted into the slider.  If it
        is a bad value, the change is rolled back and we use the `old` value.

        Parameters
        ----------
        attrib : ignored
        old : tuple of int or float
            old value pair from the range slider
        new : tuple of int or float or str
            new value pair from the range slider/text fields.  This may be passes as a tuple of str from the text inputs
        """
        # Update the slider with a new (start, end) value
        if not _input_check(new):
            if _input_check(old):
                start_text_input.value = str(old[0])
                end_text_input.value = str(old[1])
            return
        if old != new:
            if is_float:
                start_val = float(new[0])
                end_val = float(new[1])
            else:
                start_val = int(new[0])
                end_val = int(new[1])
            if start_val > end_val:
                start_val, end_val = end_val, start_val
            if end_val > slider.end and not max_value:
                slider.end = end_val
            if 0 <= start_val < slider.start and min_value is None:
                slider.start = start_val
            if slider.start <= start_val <= end_val <= slider.end:
                slider.value = (start_val, end_val)

    def update_text_input(attrib, old, new):
        # Update the text inputs with the new (start, end) value for the slider
        if new != old:
            start_text_input.value = str(new[0])
            end_text_input.value = str(new[1])

    def handle_start_value(attrib, old, new):
        if new == old:
            return
        # called by the start text input.  We pull the end value and delegate to handle_value
        try:
            if slider.start <= float(new) <= slider.end:
                if float(new) > float(location_text_input.value):
                    location_text_input.value = new
                handle_value(attrib, (old, location_text_input.value, end_text_input.value),
                             [new, location_text_input.value, end_text_input.value])
                return
        except ValueError as ve:
            pass
        start_text_input.value = old

    def handle_location_value(attrib, old, new):
        if new == old:
            return
        # called by the location text input.  We pull the end value and delegate to handle_value
        try:
            if slider.start <= float(new) <= slider.end:
                handle_value(attrib, (slider.value[0], old, slider.value[1]),
                             [slider.value[0], new, str(slider.value[1])])
                return
        except ValueError:
            pass
        location_text_input.value = old

    def handle_end_value(attrib, old, new):
        if new == old:
            return
        # called by the end text input.  We pull the start value and delegate to handle_value
        try:
            if slider.start <= float(new) <= slider.end:
                if float(new) < float(location_text_input.value):
                    location_text_input.value = new
                handle_value(attrib, (start_text_input.value, location_text_input.value, old),
                             [start_text_input.value, location_text_input.value, new])
                return
        except ValueError:
            pass
        end_text_input.value = old

    def handle_value(attrib, old, new):
        if new == old:
            return
        # Handle a change in value.  Since this has a value that is
        # (start, end) we always end up working on both values.  This
        # is even though typically the user will only be changing one
        # or the other.
        if obj and start_attr and end_attr:
            if is_float:
                start_numeric_value = float(new[0])
                location_numeric_value = float(new[1])
                end_numeric_value = float(new[2])
            else:
                start_numeric_value = int(new[0])
                location_numeric_value = int(new[1])
                end_numeric_value = int(new[2])
            try:
                if start_numeric_value > end_numeric_value:
                    start_numeric_value, end_numeric_value = end_numeric_value, start_numeric_value
                    new[2], new[0] = new[0], new[2]
                if location_numeric_value > end_numeric_value:
                    location_numeric_value = end_numeric_value
                    location_text_input.remove_on_change("value", handle_location_value)
                    location_text_input.value = str(location_numeric_value)
                    location_text_input.on_change("value", handle_location_value)
                if location_numeric_value < start_numeric_value:
                    location_numeric_value = start_numeric_value
                    location_text_input.remove_on_change("value", handle_location_value)
                    location_text_input.value = str(location_numeric_value)
                    location_text_input.on_change("value", handle_location_value)
                obj.__setattr__(start_attr, start_numeric_value)
                obj.__setattr__(location_attr, location_numeric_value)
                obj.__setattr__(end_attr, end_numeric_value)
            except FieldValidationError:
                # reset textbox
                start_text_input.remove_on_change("value", handle_start_value)
                start_text_input.value = str(old[0])
                start_text_input.on_change("value", handle_start_value)
                end_text_input.remove_on_change("value", handle_end_value)
                end_text_input.value = str(old[2])
                end_text_input.on_change("value", handle_end_value)
                location_text_input.remove_on_change("value", handle_location_value)
                location_text_input.value = str(old[1])
                location_text_input.on_change("value", handle_location_value)
            else:
                update_slider(attrib, (old[0], old[2]), (new[0], new[2]))
        if handler:
            handler()

    if throttled:
        # Since here the text_input calls handle_value, we don't
        # have to call it from the slider as it will happen as
        # a side-effect of update_text_input
        slider.on_change("value_throttled", update_text_input)
    else:
        slider.on_change("value", update_text_input)
        # since slider is listening to value, this next line will cause the slider
        # to call the handle_value method and we don't need to do so explicitly
    start_text_input.on_change("value", handle_start_value)
    location_text_input.on_change("value", handle_location_value)
    end_text_input.on_change("value", handle_end_value)

    return component


def connect_figure_extras(fig, region_model):
    """
    Connect a figure to an aperture and region model for rendering.

    This call will add extra visualizations to the bokeh figure to
    show the regions and apertures in the given models.  Either may
    be passed as None if not relevant.

    This call also does a fix to bokeh to work around a rendering bug.

    Parameters
    ----------
    fig : :class:`~bokeh.plotting.Figure`
        bokeh Figure to add visualizations too
    aperture_model : :class:`~geminidr.interactive.interactive.GIApertureModel`
        Aperture model to add view for
    region_model : :class:`~geminidr.interactive.interactive.GIRegionModel`
        Band model to add view for
    """
    # If we have regions or apertures to show, show them
    if region_model:
        regions = GIRegionView(fig, region_model)

    # This is a workaround for a bokeh bug.  Without this, things like the background shading used for
    # apertures and regions will not update properly after the figure is visible.
    fig.js_on_change('center', CustomJS(args=dict(plot=fig),
                                        code="plot.properties.renderers.change.emit()"))


class GIRegionListener(ABC):
    """
    interface for classes that want to listen for updates to a set of regions.
    """

    @abstractmethod
    def adjust_region(self, region_id, start, stop):
        """
        Called when the model adjusted a region's range.

        Parameters
        ----------
        region_id : int
            ID of the region that was adjusted
        start : float
            New start of the range
        stop : float
            New end of the range
        """
        pass

    @abstractmethod
    def delete_region(self, region_id):
        """
        Called when the model deletes a region.

        Parameters
        ----------
        region_id : int
            ID of the region that was deleted
        """
        pass

    @abstractmethod
    def finish_regions(self):
        """
        Called by the model when a region update completes and any resulting
        region merges have already been done.
        """
        pass


class GIRegionModel:
    """
    Model for tracking a set of regions.
    """
    def __init__(self, domain=None):
        # Right now, the region model is effectively stateless, other
        # than maintaining the set of registered listeners.  That is
        # because the regions are not used for anything, so there is
        # no need to remember where they all are.  This is likely to
        # change in future and that information should likely be
        # kept in here.
        self.region_id = 1
        self.listeners = list()
        self.regions = dict()
        if domain:
            self.min_x = domain[0]
            self.max_x = domain[1]
        else:
            self.min_x = None
            self.max_x = None

    def add_listener(self, listener):
        """
        Add a listener to this region model.

        The listener can either be a :class:`GIRegionListener` or
        it can be a function,  The function should expect as
        arguments, the `region_id`, and `start`, and `stop` x
        range values.

        Parameters
        ----------
        listener : :class:`~geminidr.interactive.interactive.GIRegionListener`
        """
        if not isinstance(listener, GIRegionListener):
            raise ValueError("must be a BandListener")
        self.listeners.append(listener)

    def clear_regions(self):
        """
        Deletes all regions.
        """
        for region_id in self.regions.keys():
            for listener in self.listeners:
                listener.delete_region(region_id)
        self.regions = dict()

    def load_from_tuples(self, tuples):
        self.clear_regions()
        self.region_id = 1

        def constrain_min(val, min):
            if val is None:
                return min
            if min is None:
                return val
            return max(val, min)
        def constrain_max(val, max):
            if val is None:
                return max
            if max is None:
                return val
            return min(val, max)
        for tup in tuples:
            start = tup.start
            stop = tup.stop
            start = constrain_min(start, self.min_x)
            stop = constrain_min(stop, self.min_x)
            start = constrain_max(start, self.max_x)
            stop = constrain_max(stop, self.max_x)
            self.adjust_region(self.region_id, start, stop)
            self.region_id = self.region_id + 1
        self.finish_regions()

    def load_from_string(self, region_string):
        self.load_from_tuples(cartesian_regions_to_slices(region_string))

    def adjust_region(self, region_id, start, stop):
        """
        Adjusts the given region ID to the specified X range.

        The region ID may refer to a brand new region ID as well.
        This method will call into all registered listeners
        with the updated information.

        Parameters
        ----------
        region_id : int
            ID fo the region to modify
        start : float
            Starting coordinate of the x range
        stop : float
            Ending coordinate of the x range

        """
        if start is not None and stop is not None and start > stop:
            start, stop = stop, start
        if start is not None:
            start = int(start)
        if stop is not None:
            stop = int(stop)
        self.regions[region_id] = [start, stop]
        for listener in self.listeners:
            listener.adjust_region(region_id, start, stop)

    def delete_region(self, region_id):
        """
        Delete a region by id

        Parameters
        ----------
        region_id : int
            ID of the region to delete

        """
        if self.regions[region_id]:
            del self.regions[region_id]
            for listener in self.listeners:
                listener.delete_region(region_id)

    def finish_regions(self):
        """
        Finish operating on the regions.

        This call is for when a region update is completed.  During normal
        mouse movement, we update the view to be interactive.  We do not
        do more expensive stuff like merging intersecting regions together
        or updating the mask and redoing the fit.  That is done here
        instead once the region is set.
        """
        # first we do a little consolidation, in case we have overlaps
        region_dump = list()
        for key, value in self.regions.items():
            region_dump.append([key, value])
        for i in range(len(region_dump)-1):
            for j in range(i+1, len(region_dump)):
                # check for overlap and delete/merge regions
                akey, aregion = region_dump[i]
                bkey, bregion = region_dump[j]
                if (aregion[0] is None or bregion[1] is None or aregion[0] < bregion[1]) \
                        and (aregion[1] is None or bregion[0] is None or aregion[1] > bregion[0]):
                    # full overlap?
                    if (aregion[0] is None or (bregion[0] is not None and aregion[0] <= bregion[0])) \
                            and (aregion[1] is None or (bregion is not None and aregion[1] >= bregion[1])):
                        # remove bregion
                        self.delete_region(bkey)
                    elif (bregion[0] is None or (aregion[0] is not None and aregion[0] >= bregion[0])) \
                            and (bregion[1] is None or (aregion[1] is not None and aregion[1] <= bregion[1])):
                        # remove aregion
                        self.delete_region(akey)
                    else:
                        aregion[0] = None if None in (aregion[0], bregion[0]) else min(aregion[0], bregion[0])
                        aregion[1] = None if None in (aregion[1], bregion[1]) else max(aregion[1], bregion[1])
                        self.adjust_region(akey, aregion[0], aregion[1])
                        self.delete_region(bkey)
        for listener in self.listeners:
            listener.finish_regions()

    def find_region(self, x):
        """
        Find the first region that contains x in it's range, or return a tuple of None

        Parameters
        ----------
        x : float
            Find the first region that contains x, if any

        Returns
        -------
            tuple : (region id, start, stop) or (None, None, None) if there are no matches
        """
        for region_id, region in self.regions.items():
            if (region[0] is None or region[0] <= x) and (region[1] is None or x <= region[1]):
                return region_id, region[0], region[1]
        return None, None, None

    def closest_region(self, x):
        """
        Fid the region with an edge closest to x.

        Parameters
        ----------
        x : float
            x position to find closest edge to

        Returns
        -------
        int, float : int region id and float position of other edge or None, None if no regions exist
        """
        ret_region_id = None
        ret_region = None
        closest = None
        for region_id, region in self.regions.items():
            distance = None if region[1] is None else abs(region[1]-x)
            if closest is None or (distance is not None and distance < closest):
                ret_region_id = region_id
                ret_region = region[0]
                closest = distance
            distance = None if region[0] is None else abs(region[0] - x)
            if closest is None or (distance is not None and distance < closest):
                ret_region_id = region_id
                ret_region = region[1]
                closest = distance
        return ret_region_id, ret_region

    def contains(self, x):
        """
        Check if any of the regions contains point x

        Parameters
        ----------
        x : float
            point to check for region inclusion

        Returns
        -------
        bool : True if there are no regions defined, or if any region contains x in it's range
        """
        if len(self.regions.values()) == 0:
            return True
        for b in self.regions.values():
            if (b[0] is None or b[0] <= x) and (b[1] is None or x <= b[1]):
                return True
        return False

    def build_regions(self):

        def none_cmp(x, y):
            if x is None and y is None:
                return 0
            if x is None:
                return -1
            if y is None:
                return 1
            return x - y

        def region_sorter(a, b):
            retval = none_cmp(a[0], b[0])
            if retval == 0:
                retval = none_cmp(a[1], b[1])
            return retval

        def deNone(val, offset=0):
            return '' if val is None else val + offset

        if self.regions is None or len(self.regions.values()) == 0:
            return ''

        sorted_regions = list()
        sorted_regions.extend(self.regions.values())
        sorted_regions.sort(key=cmp_to_key(region_sorter))
        return ', '.join(['{}:{}'.format(deNone(b[0], offset=1), deNone(b[1]))
                          for b in sorted_regions])


class RegionHolder:
    """
    Used by `~geminidr.interactive.interactive.GIRegionView` to track start/stop
    independently of the bokeh Annotation since we want to support `None`.

    We need to know if the start/stop values are a specific value or `None`
    which is open ended left/right.
    """
    def __init__(self, annotation, start, stop):
        self.annotation = annotation
        self.start = start
        self.stop = stop


class GIRegionView(GIRegionListener):
    """
    View for the set of regions to show then in a figure.
    """
    def __init__(self, fig, model):
        """
        Create the view for the set of regions managed in the given model
        to display them in a figure.

        Parameters
        ----------
        fig : :class:`~bokeh.plotting.Figure`
            the figure to display the regions in
        model : :class:`~geminidr.interactive.interactive.GIRegionModel`
            the model for the region information (may be shared by multiple
            :class:`~geminidr.interactive.interactive.GIRegionView` instances)
        """
        self.fig = fig
        self.model = model
        model.add_listener(self)
        self.regions = dict()
        fig.y_range.on_change('start', lambda attr, old, new: self.update_viewport())
        fig.y_range.on_change('end', lambda attr, old, new: self.update_viewport())

    def adjust_region(self, region_id, start, stop):
        """
        Adjust a region by it's ID.

        This may also be a new region, if it is an ID we haven't
        seen before.  This call will create or adjust the glyphs
        in the figure to reflect the new data.

        Parameters
        ----------
        region_id : int
            id of region to create or adjust
        start : float
            start of the x range of the region
        stop : float
            end of the x range of the region
        """
        def fn():
            draw_start = start
            draw_stop = stop
            if draw_start is None:
                draw_start = self.fig.x_range.start - ((self.fig.x_range.end - self.fig.x_range.start) / 10.0)
            if draw_stop is None:
                draw_stop = self.fig.x_range.end + ((self.fig.x_range.end - self.fig.x_range.start) / 10.0)
            if region_id in self.regions:
                region = self.regions[region_id]
                region.start = start
                region.stop = stop
                region.annotation.left = draw_start
                region.annotation.right = draw_stop
            else:
                region = BoxAnnotation(left=draw_start, right=draw_stop, fill_alpha=0.1, fill_color='navy')
                self.fig.add_layout(region)
                self.regions[region_id] = RegionHolder(region, start, stop)
        if self.fig.document is not None:
            self.fig.document.add_next_tick_callback(lambda: fn())
        else:
            # do it now
            fn()

    def update_viewport(self):
        """
        Update the view in the figure.

        This call is made whenever we detect a change in the display
        area of the view.  By redrawing, we ensure the lines and
        axis label are in view, at 80% of the way up the visible
        Y axis.

        """
        if self.fig.y_range.start is not None and self.fig.y_range.end is not None:
            for region in self.regions.values():
                if region.start is None or region.stop is None:
                    draw_start = region.start
                    draw_stop = region.stop
                    if draw_start is None:
                        draw_start = self.fig.x_range.start - ((self.fig.x_range.end - self.fig.x_range.start) / 10.0)
                    if draw_stop is None:
                        draw_stop = self.fig.x_range.end + ((self.fig.x_range.end - self.fig.x_range.start) / 10.0)
                    region.annotation.left = draw_start
                    region.annotation.right = draw_stop

    def delete_region(self, region_id):
        """
        Delete a region by ID.

        If the view does not recognize the id, this is a no-op.
        Otherwise, all related glyphs are cleaned up from the figure.

        Parameters
        ----------
        region_id : int
            ID of region to remove

        """
        def fn():
            if region_id in self.regions:
                region = self.regions[region_id]
                region.annotation.left = 0
                region.annotation.right = 0
                region.start = 0
                region.stop = 0
                # TODO remove it (impossible?)
        # We have to defer this as the delete may come via the keypress URL
        # But we aren't in the PrimitiveVisualizaer so we reference the
        # document and queue it directly
        self.fig.document.add_next_tick_callback(lambda: fn())

    def finish_regions(self):
        pass


class RegionEditor(GIRegionListener):
    """
    Widget used to create/edit fitting Regions.

    Parameters
    ----------
    region_model : GIRegionModel
        Class that connects this element to the regions on plots.
    """
    def __init__(self, region_model):
        self.text_input = TextInput(
            title="Regions (i.e. 101:500,511:900,951: Press 'Enter' to apply):",
            max_width=600,
            sizing_mode="stretch_width",
            width_policy="max",
        )
        self.text_input.value = region_model.build_regions()
        self.region_model = region_model
        self.region_model.add_listener(self)
        self.text_input.on_change("value", self.handle_text_value)

        self.error_message = Div(text="<b> <span style='color:red'> "
                                      "  Please use comma separated : delimited "
                                      "  values (i.e. 101:500,511:900,951:). "
                                      " Negative values are not allowed."
                                      "</span></b>")

        self.error_message.visible = False
        self.widget = column(self.text_input, self.error_message)
        self.handling = False

    def adjust_region(self, region_id, start, stop):
        pass

    def delete_region(self, region_id):
        self.text_input.value = self.region_model.build_regions()

    def finish_regions(self):
        self.text_input.value = self.region_model.build_regions()

    @staticmethod
    def standardize_region_text(region_text):
        """
        Remove spaces near commas separating values, and removes
        leading/trailing commas in string.

        Parameters
        ----------
        region_text : str
            Region text to clean up.

        Returns
        -------
        str : Clean region text.
        """
        # Handles when deleting last region
        region_text = '' if region_text is None else region_text

        # Replace " ," or ", " with ","
        region_text = re.sub(r'[ ,]+', ',', region_text)

        # Remove comma if region_text starts with ","
        region_text = re.sub(r'^,', '', region_text)

        # Remove comma if region_text ends with ","
        region_text = re.sub(r',$', '', region_text)

        return region_text

    def handle_text_value(self, attr, old, new):
        """
        Handles the new text value inside the Text Input field. The
        (attr, old, new) callback signature is a requirement from Bokeh.

        Parameters
        ----------
        attr :
            Attribute that would be changed. Not used here.
        old : str
            Old attribute value. Not used here.
        new : str
            New attribute value. Used to update regions.
        """
        if not self.handling:
            self.handling = True
            region_text = self.standardize_region_text(new)
            current = self.region_model.build_regions()

            # Clean up regions if text input is empty
            if not region_text or region_text.isspace():
                self.region_model.clear_regions()
                self.text_input.value = ""
                current = None
                region_text = None
                self.region_model.finish_regions()

            if current != region_text:
                unparseable = False
                try:
                    parse_user_regions(region_text)
                except ValueError:
                    unparseable = True
                if not unparseable and re.match(r'^((\d+:|\d+:\d+|:\d+)(,\d+:|,\d+:\d+|,:\d+)*)$|^ *$', region_text):
                    self.region_model.load_from_string(region_text)
                    self.text_input.value = self.region_model.build_regions()
                    self.error_message.visible = False
                else:
                    self.text_input.value = current
                    if 'region_input_error' not in self.text_input.css_classes:
                        self.error_message.visible = True
            else:
                self.error_message.visible = False

            self.handling = False

    def get_widget(self):
        return self.widget


class TabsTurboInjector:
    """
    This helper class wraps a bokeh Tabs widget
    and improves performance by dynamically
    adding and removing children from the DOM
    as their tabs are un/selected.

    There is a moment when the new tab is visually
    blank before the contents pop in, but I think
    the tradeoff is worth it if you're finding your
    tabs unresponsive at scale.
    """
    def __init__(self, tabs: bm.layouts.Tabs):
        """
        Create a tabs turbo helper for the given bokeh Tabs.

        :param tabs: :class:`~bokeh.model.layout.Tabs`
            bokeh Tabs to manage
        """
        if tabs.tabs:
            raise ValueError("TabsTurboInjector expects an empty Tabs object")

        self.tabs = tabs
        self.tab_children = list()
        self.tab_dummy_children = list()

        for i, tab in enumerate(tabs.tabs):
            self.tabs.append(tab)
            self.tab_children.append(tab.child)
            self.tab_dummy_children.append(row())

            if i != tabs.active:
                tab.child = self.tab_dummy_children[i]

        tabs.on_change('active', self.tabs_callback)

    def add_tab(self, child: Instance(bm.layouts.LayoutDOM), title: str):
        """
        Add the given bokeh widget as a tab with the given title.

        This child widget will be tracked by the Turbo helper.  When the tab
        becomes active, the child will be placed into the tab.  When the
        tab is inactive, it will be cleared to improve performance.

        :param child: :class:~bokeh.core.properties.Instance(bokeh.models.layouts.LayoutDOM)
            Widget to add as a panel's contents
        :param title: str
            Title for the new tab
        """
        tab_dummy = row(Div(),)
        tab_child = child

        self.tab_children.append(child)
        self.tab_dummy_children.append(tab_dummy)

        if self.tabs.tabs:
            self.tabs.tabs.append(bm.Panel(child=row(tab_dummy,), title=title))
        else:
            self.tabs.tabs.append(bm.Panel(child=row(tab_child,), title=title))

    def tabs_callback(self, attr, old, new):
        """
        This callback will be used when the tab selection changes.  It will clear the DOM
        of the contents of the inactive tab and add back the new tab to the DOM.

        :param attr: str
            unused, will be ``active``
        :param old: int
            The old selection
        :param new: int
            The new selection
        """
        if old != new:
            self.tabs.tabs[old].child.children[0] = self.tab_dummy_children[old]
            self.tabs.tabs[new].child.children[0] = self.tab_children[new]


def do_later(fn):
    """
    Helper method to queue work to be done on the bokeh UI thread.

    When actiona happen as a result of a key press, for instance, this comes in
    on a different thread than bokeh UI is operating on.  Performing any UI
    impacting changes on this other thread can cause issues.  Instead, wrap
    the desired changes in a function and pass it in here to be run on the UI
    thread.

    This works by referencing the active singleton Visualizer, so that
    code doesn't have to all track the visualizer.

    :param fn:
    :return:
    """
    _visualizer.do_later(fn)
