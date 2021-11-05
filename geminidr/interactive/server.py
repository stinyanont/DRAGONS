import uuid

from astrodata import version

import pathlib

import tornado
from bokeh.application import Application
from bokeh.application.handlers import Handler
from bokeh.server.server import Server
from jinja2 import Environment, FileSystemLoader

from geminidr.interactive import controls

__all__ = ["test_mode", "interactive_fitter", "stop_server"]

# Set to True to tell the interactive code to automatically submit in
# order to test the interactive paths automatically
test_mode = False

from bokeh.themes import built_in_themes

from geminidr.interactive.interactive_config import interactive_conf

_bokeh_server = None
_visualizer = None

__version__ = version()

TEMPLATE_PATH = '%s/templates' % pathlib.Path(__file__).parent.absolute()


class VersionHandler(tornado.web.RequestHandler):
    """
    Handler for geting the DRAGONS version.
    """
    def get(self):
        self.write(__version__)


def _handle_key(doc):
    """
    Web endpoint for telling the bokeh python a key was pressed.

    Parameters
    ----------
    doc : :class:`~bokeh.document.Document`
        Document reference for the user's browser tab to hold the user interface.

    Returns
    -------
    none
    """
    key = doc.session_context.request.arguments['key'][0].decode('utf-8')
    if controls.controller:
        controls.controller.handle_key(key)


# to store the mapping from ID to callable for the registered web callbacks
_callbacks = dict()


def register_callback(fn):
    """
    Register a function with the `callback` web endpoint.

    This will register a function to respond to calls to the `callback`
    web endpoint.  It will assign the function a unique UUID and return it
    to the caller as a string.  This ID should be passed in the web calls
    as the query argument `callback`.

    Parameters
    ----------
    fn : callable
        Function to call when callback is accessed via the URL.  It will be passed the web call arguments.

    Returns
    -------
    str : Unique ID for the callback, to be passed in the URL
    """
    name = str(uuid.uuid1())
    _callbacks[name] = fn
    return name


def _handle_callback(doc):
    """
    Web handler for 'callback' urls.

    This handler is for functions registered as callbacks for the javascript.
    This allows us to write javascript logic that calls back down into the python
    via this endpoint.

    Parameters
    ----------
    doc : :class:`~bokeh.document.Document`
        Document reference for the user's browser tab to hold the user interface.

    Returns
    -------
    none
    """
    cb = doc.session_context.request.arguments['callback'][0].decode('utf-8')
    args = doc.session_context.request.arguments
    callback = _callbacks.get(cb)
    if callback is not None:
        callback(args)


def _bkapp(doc):
    """
    Callback for bokeh on server start.

    When the bokeh service starts, it is given this method as the root level
    handler.  When the user's browser opens, the `doc` for that page will be
    passed down through here.

    Parameters
    ----------
    doc : :class:`~bokeh.document.Document`
        Document reference for the user's browser tab to hold the user interface.

    Returns
    -------
    none
    """
    ic = interactive_conf()
    bokeh_theme = ic.bokeh_theme
    bokeh_template_css = ic.bokeh_template_css

    template = "index.html"
    if bokeh_theme in built_in_themes:
        doc.theme = built_in_themes[bokeh_theme]
    if _visualizer.template:
        template = _visualizer.template
    with open('%s/%s' % (TEMPLATE_PATH, template)) as f:
        title = _visualizer.title
        if not title:
            title = 'Interactive'
        primitive_name = _visualizer.primitive_name
        template = f.read()
        t = Environment(loader=FileSystemLoader(TEMPLATE_PATH)).from_string(template)
        doc.template = t
        doc.template_variables['css_template'] = bokeh_template_css
        doc.template_variables['primitive_title'] = title.replace(' ', '&nbsp;')
        doc.template_variables['primitive_name'] = primitive_name.replace(' ', '&nbsp;')

        if hasattr(_visualizer, "filename_info"):
            doc.template_variables['filename_info'] = _visualizer.filename_info

    _visualizer.show(doc)
    doc.title = title


import yaml
from bokeh.themes import Theme


_jupyter_doc = None


def setup_jupyter(doc, fn=None):
    global _jupyter_doc
    _jupyter_doc = doc
    doc.theme = Theme(json=yaml.load("""
        attrs:
            Figure:
                background_fill_color: "#DDDDDD"
                outline_line_color: white
                toolbar_location: above
                height: 500
                width: 800
            Grid:
                grid_line_dash: [6, 4]
                grid_line_color: white
    """, Loader=yaml.FullLoader))
    if fn is not None:
        # trying threaded version
        def threaded_redux():
            import threading
            t = threading.Thread(name='jupyter_dragons_interactive_thread', target=fn)
            t.start()

        doc.add_next_tick_callback(threaded_redux)


def jupyter_reduce(files=[], recipename=None, uparms=None, upload=[], mode=None):
    from recipe_system.reduction.coreReduce import Reduce
    from bokeh.io import show, output_notebook

    output_notebook()

    def stub_redux():
        redux = Reduce()
        redux.files = files
        redux.recipename= recipename
        if uparms:
            redux.uparms = uparms
        redux.upload = upload
        if mode:
            redux.mode = mode
        redux.runr()

    show(lambda x: setup_jupyter(x, stub_redux))


_doc = None


def _helpapp(doc):
    """
    Tornado request handler for showing help for the active visuializer.

    Parameters
    ----------
    doc : :class:`~bokeh.document.Document`
        The web page showing the bokeh interface
    """
    with open(f'{TEMPLATE_PATH}/help.html') as f:
        template = f.read()

    title = _visualizer.title or 'Interactive'
    primitive_name = _visualizer.primitive_name
    t = Environment(loader=FileSystemLoader(TEMPLATE_PATH)).from_string(template)
    doc.template = t
    doc.template_variables.update({
        'help_text': _visualizer.help_text,
        'primitive_title': title.replace(' ', '&nbsp;'),
        'primitive_name': primitive_name.replace(' ', '&nbsp;'),
    })
    doc.title = title


def _shutdown(doc):
    """
    Tornado request handler for shutdown requests from the HTML client.

    Parameters
    ----------
    doc : :class:`~bokeh.document.Document`
        Document for the webpage the request is coming from (there's only one)
    """
    user_satisfied = True
    if 'user_satisfied' in doc.session_context.request.arguments:
        user_satisfied = doc.session_context.request.arguments['user_satisfied'][0].decode('utf-8')
        if user_satisfied is not None and user_satisfied.lower() in ('0', 'n', 'f', 'no', 'false'):
            user_satisfied = False
    _visualizer.session_ended(None, user_satisfied)


def set_visualizer(visualizer):
    """
    Set the visualizer for the UI.

    This sets the visualizer that will control the user interface when we start
    the bokeh server.  This is generally defined under `fit` in the same file with the
    fit model and helper method.  For instance, see the `~geminidr.interactive.fit.fit1d.Fit1DVisualizer`.

    Parameters
    ----------
    visualizer : :class:`~geminidr.interactive.interactive.PrimitiveVisualizer`
    """
    global _visualizer
    global _jupyter_doc

    _visualizer = visualizer
    if visualizer is not None and _jupyter_doc is not None:
        _visualizer.show(_jupyter_doc)


class DRAGONSStaticHandler(Handler):
    """
    Simple Tornado handler to serve static content from the embedded webserver
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._static = '%s/static' % pathlib.Path(__file__).parent.absolute()


# Check if we are running in a Jupyter notebook and set using_jupyter accordingly
try:
    __IPYTHON__
    using_jupyter = True
except NameError:
    using_jupyter = False
_jup_running = False


def start_server_jupyter():
    """
    Tell the interactive code we are starting interactivity in Jupyter

    This is analagous to :meth:`start_server` but it just blocks while
    polling for the interactive session to end.  This way, it can be
    used as a drop-in replacement for that call when running in a
    notebook.  This works best from a separate thread as seein in
    :meth:`jupyter_reduce`
    """
    global _jup_running
    _jup_running = True

    while _jup_running:
        import time
        time.sleep(2)


def start_server():
    """
    Start the bokeh server.

    This will begin an IO loop to handle user interaction via
    bokeh.  Until the server is explicitly stopped, the method
    will block and this call will not return.
    """
    if using_jupyter:
        start_server_jupyter()
        return

    global _bokeh_server

    if not _bokeh_server:
        static_app = Application(DRAGONSStaticHandler())
        port = 5006
        while port < 5701 and _bokeh_server is None:
            try:
                # NOTE:
                # Tornado generates a WebSocketClosedError when the user
                # is on Safari.  This seems to be a regression as Safari
                # has had this problem before with bokeh and web scokets.
                # Chrome and FireFox work fine.
                #
                # To get Safari to behave, I have added the
                # keep_alive_milliseconds=0 argument below.  This
                # disables the keep alive heartbeat that causes the
                # above error.  If you remove that argument, bokeh
                # will re-enable the heartbeat but Safari won't work
                # in interactive mode any more.  See below for a way
                # to make interactive use "chrome" (or "firefox")
                # regardless of the selected browser if desired.
                def dummy_logger(*args, **kwargs):
                    """
                    Empty logger method to convince Tornado to not log.  This is so the reduce.log
                    isn't filled with HTTP response codes and URLs
                    """
                    pass

                _bokeh_server = Server(
                    {
                        '/': _bkapp,
                        '/dragons': static_app,
                        '/handle_key': _handle_key,
                        '/handle_callback': _handle_callback,
                        '/help': _helpapp,
                        '/shutdown': _shutdown,
                    },
                    keep_alive_milliseconds=0,
                    num_procs=1,
                    extra_patterns=[('/version', VersionHandler)],
                    log_function=dummy_logger,
                    port=port)
            except OSError:
                port = port+1
                if port >= 5701:
                    raise
        _bokeh_server.start()

    if test_mode:
        # kwargs = {"browser": ["chrome", "--headless", "--disable-gpu", "--dump-dom"]}
        kwargs = {"browser": "chrome"}
    else:
        ic = interactive_conf()
        kwargs = {"browser": ic.browser}
    _bokeh_server.io_loop.add_callback(_bokeh_server.show, "/", **kwargs)
    _bokeh_server.io_loop.start()

    # The server normally stops when the user hits the Submit button in the
    # visualizer, or when they close the tab.


def stop_server():
    """
    Stop the bokeh server.

    This will end the IO loop and unblock the :meth:`~geminidr.interactive.server.start_server()` call.
    This normally gets called when the user hits the submit button
    or closes the UI browser tab.
    """
    global _jup_running
    if using_jupyter:
        # what to do?
        _jup_running = False
        return

    global _bokeh_server
    _bokeh_server.io_loop.stop()


def interactive_fitter(visualizer):
    """
    Start the interactive fitter with the given visualizer.

    This will spin up the bokeh server using the provided
    visualizer to build a UI.  It returns when the user
    submits the result.

    Parameters
    ----------
    visualizer : :class:`~geminidr.interactive.interactive.PrimitiveVisualizer`
        The visualizer UI to display
    """
    set_visualizer(visualizer)
    start_server()

    set_visualizer(None)
    if not visualizer.user_satisfied and not using_jupyter:
        raise KeyboardInterrupt()
