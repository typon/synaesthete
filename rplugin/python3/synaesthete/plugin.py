from functools import partial, wraps

try:
    import pynvim as neovim
except ImportError:
    import neovim

from pyrsistent import pmap
from copy import copy

from .handler import BufferHandler
from .node import hl_groups

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
error, debug, info, warn = (
    logger.error,
    logger.debug,
    logger.info,
    logger.warning,
)


# _subcommands = {}


# def subcommand(func=None, needs_handler=False, silent_fail=True):
#     """Decorator to register `func` as a ":Synaesthete [...]" subcommand.

#     If `needs_handler`, the subcommand will fail if no buffer handler is
#     currently active. If `silent_fail`, it will fail silently, otherwise an
#     error message is printed.
#     """
#     if func is None:
#         return partial(subcommand, needs_handler=needs_handler, silent_fail=silent_fail)

#     @wraps(func)
#     def wrapper(self, *args, **kwargs):
#         # pylint: disable=protected-access
#         if self._options is None:
#             self._init_with_vim()
#         if needs_handler and self._cur_handler is None:
#             if not silent_fail:
#                 self.echo_error("Synaesthete is not enabled in this buffer!")
#             return
#         func(self, *args, **kwargs)

#     _subcommands[func.__name__] = wrapper
#    return wrapper


def handle_registration():
    """
    Pre/post event handler decorator
    This allows us to disable any event handler when the
    plugin is disabled
    """
    def wrapper(f):
        @wraps(f)
        def wrapped(self, *f_args, **f_kwargs):
            if self.plugin_enabled:
                f(self, *f_args, **f_kwargs)

        return wrapped

    return wrapper


EVENTS = {
    "BufEnter",
    "BufLeave",
    "VimResized",
    "TextChanged",
    "TextChangedI",
    "VimLeave",
    "CursorMoved",
    "CursorMovedI",
}

initial_request_handlers = None


@neovim.plugin
class Plugin:
    """Synaesthete Neovim plugin.

    The plugin handles vim events and commands, and delegates them to a buffer
    handler. (Each buffer is handled by a synaesthete.BufferHandler instance.)
    """

    def __init__(self, vim):
        self._vim = vim
        # A mapping (buffer number -> buffer handler)
        self._handlers = {}
        # The currently active buffer handler
        self._cur_handler = None
        self._options = Options(vim)
        # self.initial_request_handlers = None
        self.host_handlers_are_noops = False
        self.plugin_enabled = False

    def _init_with_vim(self):
        """Initialize with vim available.

        Initialization code which interacts with vim can't be safely put in
        __init__ because vim itself may not be fully started up.
        """
        self._options = Options(self._vim)

    def echo(self, *msgs):
        msg = " ".join([str(m) for m in msgs])
        self._vim.out_write(msg + "\n")

    def echo_error(self, *msgs):
        msg = " ".join([str(m) for m in msgs])
        self._vim.err_write(msg + "\n")

    # @neovim.autocmd("FileType", eval="expand('<amatch>')", sync=True)
    # def event_filetype_changed(self, filetype):
    #     # filetype = self._vim.command_output("echo &filetype")
    #     if filetype not in self._options.filetypes:
    #         self.disable()
    #     else:
    #         self.enable()

    @neovim.autocmd("BufEnter", pattern="*.py", eval="[expand('<abuf>'), line('w0'), line('w$')]", sync=True)
    @handle_registration()
    def event_buf_enter(self, args):

        buf_num, view_start, view_stop = args
        self._select_handler(int(buf_num))
        self._update_viewport(view_start, view_stop)
        self._cur_handler.update()
        self._mark_selected()

    @neovim.autocmd("BufLeave", pattern="*.py", sync=True)
    @handle_registration()
    def event_buf_leave(self):
        self._cur_handler = None

    @neovim.function("SynaestheteBufWipeout", sync=True)
    def event_buf_wipeout(self, args):
        self._remove_handler(args[0])

    @neovim.autocmd("VimResized", pattern="*.py", eval="[line('w0'), line('w$')]", sync=True)
    @handle_registration()
    def event_vim_resized(self, args):
        self.echo(str(args))
        view_start, view_end = args
        self._update_viewport(view_start, view_end)
        self._mark_selected()

    @neovim.autocmd("CursorMoved", pattern="*.py", eval="[line('w0'), line('w$')]", sync=True)
    @handle_registration()
    def event_cursor_moved_command_mode(self, args):
        self.event_cursor_moved(args)

    @neovim.autocmd("CursorMovedI", pattern="*.py", eval="[line('w0'), line('w$')]", sync=True)
    @handle_registration()
    def event_cursor_moved_insert_mode(self, args):
        self.event_cursor_moved(args)

    def event_cursor_moved(self, args):
        if self._cur_handler is None:
            # CursorMoved may trigger before BufEnter, so select the buffer if
            # we didn't enter it yet.
            self.event_buf_enter((self._vim.current.buffer.number, *args))
            return
        self._update_viewport(*args)
        self._mark_selected()

    @neovim.autocmd("TextChanged", pattern="*.py", sync=True)
    @handle_registration()
    def event_text_changed_command_mode(self):
        self.event_text_changed()
        # Note: TextChanged event doesn't trigger if text was changed in
        # unfocused buffer via e.g. nvim_buf_set_lines().

    @neovim.autocmd("TextChangedI", pattern="*.py", sync=True)
    @handle_registration()
    def event_text_changed_insert_mode(self):
        self.event_text_changed()

    def event_text_changed(self):
        self._cur_handler.update()

    @neovim.autocmd("VimLeave", sync=True)
    @handle_registration()
    def event_vim_leave(self):
        for handler in self._handlers.values():
            handler.shutdown()

    # @neovim.command("Synaesthete", nargs="*", complete="customlist,SynaestheteComplete", sync=True)
    # def cmd_synaesthete(self, args):
    #     if not args:
    #         self.echo("This is synaesthete.")
    #         return
    #     try:
    #         func = _subcommands[args[0]]
    #     except KeyError:
    #         self.echo_error("Subcommand not found: %s" % args[0])
    #         return
    #     func(self, *args[1:])

    # @staticmethod
    # @neovim.function("SynaestheteComplete", sync=True)
    # def func_complete(arg):
    #     lead, *_ = arg
    #     return [c for c in _subcommands if c.startswith(lead)]

    @neovim.function("SynaestheteInternalEval", sync=True)
    def _internal_eval(self, args):
        """Eval Python code in plugin context.

        Only used for testing."""
        plugin = self  # noqa pylint: disable=unused-variable
        return eval(args[0])  # pylint: disable=eval-used

    def capture_host_instance(self):
        self.host = self._vim._err_cb.__self__

    def reset_host_handlers(self):
        global initial_request_handlers
        if self.host_handlers_are_noops:
            debug("-------------------------ARE NOOPS")
            self.host._request_handlers = initial_request_handlers
            self.host_handlers_are_noops = False

        if initial_request_handlers is None:
            initial_request_handlers = copy(self.host._request_handlers)

    @neovim.command("SynaestheteEnable", sync=True)
    def enable(self):
        self.plugin_enabled = True
        # filetype = self._vim.command_output("echo &filetype")
        # if filetype not in self._options.filetypes:
        #     return

        # debug("-------------------------LEW")
        # self.capture_host_instance()
        # self.reset_host_handlers()
        self._attach_listeners()
        self._select_handler(self._vim.current.buffer)
        self._update_viewport(*self._vim.eval('[line("w0"), line("w$")]'))
        self.highlight()

    @neovim.command("SynaestheteDisable", sync=True)
    def disable(self):
        # self._err_cb(
        self.plugin_enabled = False
        self.clear()
        self.detach_request_handlers()
        self._cur_handler = None
        self._remove_handler(self._vim.current.buffer)

    # @subcommand(needs_handler=True)
    # def disable(self):
    #     self.clear()
    #     self._detach_listeners()
    #     self._cur_handler = None
    #     self._remove_handler(self._vim.current.buffer)

    # @subcommand
    # def toggle(self):
    #     if self._listeners_attached():
    #         self.disable()
    #     else:
    #         self.enable()

    # @subcommand(needs_handler=True)
    # def pause(self):
    #     self._detach_listeners()

    # @subcommand(needs_handler=True, silent_fail=False)
    def highlight(self):
        self._cur_handler.update(force=True, sync=True)

    # @subcommand(needs_handler=True)
    def clear(self):
        self._cur_handler.clear_highlights()

    # @subcommand(needs_handler=True, silent_fail=False)
    # def rename(self, new_name=None):
    #     self._cur_handler.rename(self._vim.current.window.cursor, new_name)

    # @subcommand(needs_handler=True, silent_fail=False)
    # def goto(self, *args, **kwargs):
    #     self._cur_handler.goto(*args, **kwargs)

    # @subcommand(needs_handler=True, silent_fail=False)
    # def error(self):
    #     self._cur_handler.show_error()

    # @subcommand
    # def status(self):
    #     self.echo("current handler: {handler}\n" "handlers: {handlers}".format(handler=self._cur_handler, handlers=self._handlers))

    def _select_handler(self, buf_or_buf_num):
        """Select handler for `buf_or_buf_num`."""
        if isinstance(buf_or_buf_num, int):
            buf = None
            buf_num = buf_or_buf_num
        else:
            buf = buf_or_buf_num
            buf_num = buf.number
        try:
            handler = self._handlers[buf_num]
        except KeyError:
            if buf is None:
                buf = self._vim.buffers[buf_num]
            handler = BufferHandler(buf, self._vim, self._options)
            self._handlers[buf_num] = handler
        self._cur_handler = handler

    def _remove_handler(self, buf_or_buf_num):
        """Remove handler for buffer with the number `buf_num`."""
        if isinstance(buf_or_buf_num, int):
            buf_num = buf_or_buf_num
        else:
            buf_num = buf_or_buf_num.number
        try:
            handler = self._handlers.pop(buf_num)
        except KeyError:
            return
        else:
            handler.shutdown()

    def _update_viewport(self, start, stop):
        self._cur_handler.viewport(start, stop)

    def _mark_selected(self):
        if not self._options.mark_selected_nodes:
            return
        self._cur_handler.mark_selected(self._vim.current.window.cursor)

    def _attach_listeners(self):
        # self._vim.call("synaesthete#buffer_attach")
        pass

    def detach_request_handlers(self):
        # for name, handler in self.host._request_handlers.items():
        #     for event in EVENTS:
        #         if event in name:
        #             self.host._request_handlers[name] = noop
        # self.host_handlers_are_noops = True
        pass

    def _listeners_attached(self):
        """Return whether event listeners are attached to the current buffer.
        """
        return self._vim.eval('get(b:, "synaesthete_attached", v:false)')


def noop(*args, **kwargs):
    pass


class Options:
    """Plugin options.

    The options will only be read and set once on init.
    """

    _defaults = {
        "filetypes": ["python"],
        "excluded_hl_groups": ["local"],
        "mark_selected_nodes": 1,
        "no_default_builtin_highlight": True,
        "simplify_markup": True,
        "error_sign": True,
        "error_sign_delay": 1.5,
        "always_update_all_highlights": False,
        "tolerate_syntax_errors": True,
        "update_delay_factor": 0.0,
        "self_to_attribute": True,
    }

    def __init__(self, vim):
        for key, val_default in Options._defaults.items():
            val = vim.vars.get("synaesthete#" + key, val_default)
            # vim.vars doesn't support setdefault(), so set value manually
            vim.vars["synaesthete#" + key] = val
            try:
                converter = getattr(Options, "_convert_" + key)
            except AttributeError:
                pass
            else:
                val = converter(val)
            setattr(self, key, val)

    @staticmethod
    def _convert_excluded_hl_groups(items):
        try:
            return [hl_groups[g] for g in items]
        except KeyError as e:
            # TODO Use err_write instead?
            raise Exception('"%s" is an unknown highlight group.' % e.args[0])
