#!/usr/bin/env python3

#------------------------------------------------------------------------------
# Displays a PyGtk TreeView widget populated with information about all
# keybindings found in the gsettings configuration.
#------------------------------------------------------------------------------

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gtk
import re

# CSS to control styling of the Gtk objects.
GTK_CSS_STRING =b"""
#HelpLabel {
    background: #ddddcc;
    padding:    10px 10px 10px 10px;
}
#MainView {
    background-color: #fefef0;
    -GtkTreeView-horizontal-separator: 40;
}
#MainView:selected {
    background-color: #6060e3;
}
#MainView header button {
    color:          #103000;
    background:     #e0e0fa;
    font-weight:    bold; 
    padding-top:    16px;
    padding-bottom: 16px;
}
#QuitButton {
    background:  #fdfdfd;
}
"""

class KeybindingSpec(object):
    """Represents a single key binding associated with a gsettings schema and
    action."""

    def __init__(self, schema, action, modifiers, key):
        self.schema    = schema
        self.action    = action
        self.modifiers = modifiers
        self.key       = key

    def ToList(self):
        return [self.schema, self.action, self.modifiers, self.key]

class KeybindingCollector(object):
    """Interacts with gsettings API to collect KeybindingSpec instances for all
    current key bindings."""

    def __init__(self):
        # GVariant type for keybinding values (string array).
        self._keybinding_type = GLib.VariantType.new('as')
        # Compiled regular expression for parsing binding strings.
        self._modifier_re = re.compile('<[^>]+>')

    def GetAllSpecs(self):
        src = Gio.SettingsSchemaSource.get_default()
        (non_relocatable_schemas, relocatable_schemas) = src.list_schemas(True)
        specs = []
        for schema in non_relocatable_schemas + relocatable_schemas:
            if 'keybindings' in schema and src.lookup(schema, False).get_path():
                specs += self._GetSpecsForSchema(schema)
        return specs

    def _GetSpecsForSchema(self, schema):
        """Returns a list of KeybindingSpec instances for each keybinding found
        in the given schema."""
        specs = []
        settings = Gio.Settings.new(schema)
        for action in settings.keys():
            if settings.get_value(action).is_of_type(self._keybinding_type):
                keybindings = settings.get_strv(action)
                if keybindings:
                    specs += [self._BuildSpec(schema, action, binding)
                              for binding in keybindings if binding]
        return specs

    def _BuildSpec(self, schema, action, binding):
        modifiers = []

        # Parse the modifiers from the binding and remove them.
        key = binding
        for modifier in self._modifier_re.findall(key):
            if modifier == '<Shift>':
                modifiers.append('Shift')
            elif modifier == '<Primary>' or modifier == '<Control>':
                modifiers.append('Control')
            elif modifier == '<Alt>':
                modifiers.append('Alt')
            elif modifier == '<Super>':
                modifiers.append('Super')
            key = key.replace(modifier, '')
        return KeybindingSpec(schema, action, ' '.join(modifiers), key)

class TreeViewWindow(Gtk.Window):
    """Gtk Window showing a TreeView of all of the keybindings. Contents can be
    sorted by any column."""

    def __init__(self, specs):
        # Set up a context for style properties.
        css_provider = Gtk.CssProvider()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Load the CSS
        css_provider.load_from_data(GTK_CSS_STRING)

        Gtk.Window.__init__(self, title="Keybinding Display")

        self.set_border_width(10)

        self._column_titles = ['Schema', 'Action', 'Modifiers', 'Key']

        # The Gtk List model.
        list_model = Gtk.ListStore(str, str, str, str)
        for spec in specs:
            list_model.append(spec.ToList())

        # The Gtk TreeView.
        view = Gtk.TreeView(model=list_model)
        view.set_name('MainView')
        view.set_enable_search(True)
        view.set_search_equal_func(self._Search)
        for i, title in enumerate(self._column_titles):
            renderer = Gtk.CellRendererText()
            # Center the text in all cells.
            renderer.set_alignment(0.5, 0.5)
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            column.set_sort_column_id(i)
            column.set_alignment(0.5)
            view.append_column(column)

        # A button to dismiss the window and quit the app.
        quit_button = Gtk.Button.new_with_mnemonic('_Quit')
        quit_button.set_name('QuitButton')
        quit_button.set_hexpand(True)
        quit_button.connect('clicked', self._Quit)
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.pack_start(quit_button, False, False, 0)

        # Set up a Box with a help label, a ScrolledWindow holding the
        # TreeView, and the quit button.
        help_label = Gtk.Label('Click a column header to sort.' +
                               ' Use Ctrl-F/Ctrl-G to search')
        help_label.set_name('HelpLabel')
        quit_button.set_name('QuitButton')
        scroll_win = Gtk.ScrolledWindow()
        scroll_win.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll_win.set_hexpand(True)
        scroll_win.set_vexpand(True)
        scroll_win.add(view)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.pack_start(help_label, False, False, 0)
        vbox.pack_start(scroll_win, True,  True,  0)
        vbox.pack_start(button_box, False, False, 0)
        self.add(vbox)
        self.resize(200, 1800)

    def _Search(self, model, column, key, rowiter):
        """Search function that searches all columns."""
        row = model[rowiter]
        # False means a match was found.
        for i, title in enumerate(self._column_titles):
            if key.lower() in row[i].lower():
                return False
        return True

    def _Quit(self, button):
        Gtk.main_quit()

def main():
    specs = KeybindingCollector().GetAllSpecs()
    win = TreeViewWindow(specs)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == '__main__':
    main()
