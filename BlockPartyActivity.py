from BlockParty import BlockParty
from gi.repository import Gtk
from gi.repository import Gdk
from sugar3.activity import activity
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.graphics.toolbutton import ToolButton
from sugar3.activity.widgets import StopButton

class BlockPartyActivity(activity.Activity):
    def __init__(self, handle):
        activity.Activity.__init__(self, handle)
        self.connect('destroy', self._cleanup_cb)
        
        self.gamename = 'blockparty'
        self.set_title("BlockParty")
        
        self.connect('focus_in_event', self._focus_in)
        self.connect('focus_out_event', self._focus_out)
        # Create a canvas
        canvas = Gtk.DrawingArea()
        self.set_canvas(canvas)
        canvas.grab_focus()
        canvas.show()
        self.show_all()

        self.block_party = BlockParty(canvas)
        self.build_toolbar()

    def build_toolbar(self):

        toolbar_box = ToolbarBox()
        self.set_toolbar_box(toolbar_box)
        toolbar_box.show()

        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, -1)
        activity_button.show()

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.show_all()

    def _cleanup_cb(self, data=None):
        return

    def _focus_in(self, event, data=None):
        return

    def _focus_out(self, event, data=None):
        return
