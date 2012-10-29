# -*- coding: utf-8 -*-

from __future__ import division, print_function, unicode_literals

### Logging ###
import logging
_logger = logging.getLogger("LayoutLoaderSVG")
###############

import os
import re
import sys
import shutil
from xml.dom import minidom

from Onboard             import Exceptions
from Onboard             import KeyCommon
from Onboard.KeyCommon   import StickyBehavior
from Onboard.KeyGtk      import RectKey
from Onboard.Layout      import LayoutRoot, LayoutBox, LayoutPanel, LayoutItem
from Onboard.utils       import hexstring_to_float, modifiers, Rect, \
                                toprettyxml, Version, open_utf8, \
                                permute_mask, LABEL_MODIFIERS

### Config Singleton ###
from Onboard.Config import Config
config = Config()
########################


class LayoutTemplates(LayoutItem):
    """
    Temporary container for template items. Only exists during layout loading.
    """
    visible = property(lambda x: False)

    def __init__(self):
        super(LayoutTemplates, self).__init__()
        self.templates = {}


class LayoutLoaderSVG:
    """
    Keyboard layout loaded from an SVG file.
    """
    # onboard <= 0.95
    LAYOUT_FORMAT_LEGACY      = Version(1, 0)

    # onboard 0.96, initial layout-tree
    LAYOUT_FORMAT_LAYOUT_TREE = Version(2, 0)

    # onboard 0.97, scanner overhaul, no more scan columns,
    # new attributes scannable, scan_priority
    LAYOUT_FORMAT_SCANNER     = Version(2, 1)

    # onboard 0.99, new attributes key.action, key.sticky_behavior.
    # allow (i.e. have by default) keycodes for modifiers.
    LAYOUT_FORMAT_2_2         = Version(2, 2)

    # current format
    LAYOUT_FORMAT             = LAYOUT_FORMAT_2_2

    # precalc mask permutations
    _label_modifier_masks = permute_mask(LABEL_MODIFIERS)

    def __init__(self):
        self._vk = None
        self._svg_cache = {}
        self._format = None   # format of the currently loading layout
        self._layout_filename = ""
        self._color_scheme = None

    def load(self, vk, layout_filename, color_scheme):
        """ Load layout root file. """
        layout = self._load(vk, layout_filename, color_scheme)
        if layout:
            # purge the now useless templates from the tree
            templates = [item for item in layout.iter_items() \
                         if isinstance(item, LayoutTemplates)]
            for template in templates:
                items = template.parent.items
                index = items.index(template)
                del items[index]
                template.parent = None

            # enable caching
            layout = LayoutRoot(layout)

        return layout

    def _load(self, vk, layout_filename, color_scheme):
        """ Load or include layout file at any depth level. """
        self._vk = vk
        self._layout_filename = layout_filename
        self._color_scheme = color_scheme
        return self._load_layout(layout_filename)

    def _load_layout(self, layout_filename):
        self.layout_dir = os.path.dirname(layout_filename)
        self._svg_cache = {}
        layout = None

        f = open_utf8(layout_filename)
        try:
            dom = minidom.parse(f).documentElement

            # check layout format, no format version means legacy layout
            format = self.LAYOUT_FORMAT_LEGACY
            if dom.hasAttribute("format"):
               format = Version.from_string(dom.attributes["format"].value)
            self._format = format

            root = LayoutPanel() # root, representing the 'keyboard' tag
            root.set_id("__root__")

            if format >= self.LAYOUT_FORMAT_LAYOUT_TREE:
                self._parse_dom_node(dom, root)
                if root.items:
                    layout = root
            else:
                _logger.warning(_format("Loading legacy layout, format '{}'. "
                            "Please consider upgrading to current format '{}'",
                            format, self.LAYOUT_FORMAT))
                items = self._parse_legacy_layout(dom)
                if items:
                    root.set_items(items)
                    layout = root
        finally:
            f.close()

        self._svg_cache = {} # Free the memory
        return layout

    def _parse_dom_node(self, dom_node, parent_item):
        """ Recursively parse the dom nodes of the layout tree. """
        for child in dom_node.childNodes:
            if child.nodeType == minidom.Node.ELEMENT_NODE:
                tag = child.tagName
                if tag == "include":
                    self._parse_include(child, parent_item)

                elif tag == "templates":
                    item = self._parse_templates(child, parent_item)
                    parent_item.append_item(item)

                elif tag == "keysym_rule":
                    self._parse_keysym_rule(child, parent_item)
                else:
                    if tag == "box":
                        item = self._parse_box(child)
                    elif tag == "panel":
                        item = self._parse_panel(child)
                    elif tag == "key":
                        item = self._parse_key(child, parent_item)
                    else:
                        item = None

                    if item:
                        parent_item.append_item(item)
                        self._parse_dom_node(child, item)

    def _parse_include(self, node, parent):
        items = None
        if node.hasAttribute("file"):
            filename = node.attributes["file"].value
            filepath = config.find_layout_filename(filename, "layout include")
            _logger.info("Including layout from " + filename)
            incl_root = LayoutLoaderSVG()._load(self._vk, filepath,
                                                self._color_scheme)
            if incl_root:
                parent.append_items(incl_root.items)
                parent.update_keysym_rules(incl_root.keysym_rules)
                incl_root.items = None # help garbage collector
                incl_root.keysym_rules = None

        return items

    def _parse_templates(self, node, parent):
        """
        Templates are partially defined layout items. Later non-template
        items inherit attributes of templates with matching id.
        """
        item = LayoutTemplates()
        for child in node.childNodes:
            if child.nodeType == minidom.Node.ELEMENT_NODE:
                tag = child.tagName
                if tag == "key":
                    self._parse_template(child, item, RectKey)
                else:
                    raise Exceptions.LayoutFileError(
                        "Unrecognized template '{} {}' in layout '{}'" \
                        .format(tag,
                                str(list(attributes.values())),
                                self._layout_filename))
        return item

    def _parse_template(self, node, item, classinfo):
        attributes = dict(list(node.attributes.items()))
        id = attributes.get("id")
        if not id:
            raise Exceptions.LayoutFileError(
                "'id' attribute required for template '{} {}' "
                "in layout '{}'" \
                .format(tag,
                        str(list(attributes.values())),
                        self._layout_filename))

        item.templates[(id, classinfo)] = attributes

    def _parse_keysym_rule(self, node, parent):
        """
        Keysym rules link attributes like labels, images
        to certain keysyms.
        """
        attributes = dict(list(node.attributes.items()))
        keysym = attributes.get("keysym")
        if keysym:
            del attributes["keysym"]
            if keysym.startswith("0x"):
                keysym = int(keysym, 16)
            else:
                # translate symbolic keysym name
                keysym = 0

            if keysym:
                parent.update_keysym_rules({keysym : attributes})

    def _parse_dom_node_item(self, node, item):
        """ Parses common properties of all LayoutItems """
        if node.hasAttribute("id"):
            item.id = node.attributes["id"].value
        if node.hasAttribute("group"):
            item.group = node.attributes["group"].value
        if node.hasAttribute("layer"):
            item.layer_id = node.attributes["layer"].value
        if node.hasAttribute("filename"):
            item.filename = node.attributes["filename"].value
        if node.hasAttribute("visible"):
            item.visible = node.attributes["visible"].value == "true"
        if node.hasAttribute("border"):
            item.border = float(node.attributes["border"].value)
        if node.hasAttribute("expand"):
            item.expand = node.attributes["expand"].value == "true"

    def _parse_box(self, node):
        item = LayoutBox()
        self._parse_dom_node_item(node, item)
        if node.hasAttribute("orientation"):
            item.horizontal = \
                node.attributes["orientation"].value.lower() == "horizontal"
        if node.hasAttribute("spacing"):
            item.spacing = float(node.attributes["spacing"].value)
        return item

    def _parse_panel(self, node):
        item = LayoutPanel()
        self._parse_dom_node_item(node, item)
        return item

    def _parse_key(self, node, parent):
        result = None

        key = RectKey()
        key.parent = parent # assign parent early to make get_filename() work

        # parse standard layout item attributes
        self._parse_dom_node_item(node, key)

        # find template attributes
        attributes = {}
        if node.hasAttribute("id"):
            ids = RectKey.split_id(node.attributes["id"].value)
            attributes = self.find_template(parent, RectKey, ids)

        # let current node override any preceding templates
        attributes.update(dict(list(node.attributes.items())))

        # keysym rules override both templates and the current node


        # set up the key
        self._init_key(key, attributes)

        # template item?
        if parent and parent.find_instance_in_path(LayoutTemplates):
            key.attributes = attributes
            result = key
        else:
            # get key geometry from the closest svg file
            filename = key.get_filename()
            if not filename:
                _logger.warning(_format("Ignoring key '{}'."
                                        " No svg filename defined.",
                                        key.theme_id))
            else:
                svg_keys = self._get_svg_keys(filename)
                svg_key = None
                if svg_keys:
                    svg_key = svg_keys.get(key.id)
                    if not svg_key:
                        _logger.warning(_format("Ignoring key '{}'."
                                                " Not found in '{}'.",
                                                key.theme_id, filename))
                    else:
                        key.set_border_rect(svg_key.get_border_rect().copy())
                        result = key

        return result  # ignore keys not found in an svg file

    def _init_key(self, key, attributes):
        # Re-parse the id to distinguish between the short key_id
        # and the optional longer theme_id.
        full_id = attributes["id"]
        key.set_id(full_id)

        value = attributes.get("modifier")
        if value:
            try:
                key.modifier = modifiers[value]
            except KeyError as ex:
                (strerror) = ex
                raise Exceptions.LayoutFileError("Unrecognized modifier %s in" \
                    "definition of %s" (strerror, full_id))

        value = attributes.get("action")
        if value:
            try:
                key.action = KeyCommon.actions[value]
            except KeyError as ex:
                (strerror) = ex
                raise Exceptions.LayoutFileError("Unrecognized key action {} in" \
                    "definition of {}".format(strerror, full_id))

        if "char" in attributes:
            key.code = attributes["char"]
            key.type = KeyCommon.CHAR_TYPE
        elif "keysym" in attributes:
            value = attributes["keysym"]
            key.type = KeyCommon.KEYSYM_TYPE
            if value[1] == "x":#Deals for when keysym is hex
                key.code = int(value,16)
            else:
                key.code = int(value,10)
        elif "keypress_name" in attributes:
            key.code = attributes["keypress_name"]
            key.type = KeyCommon.KEYPRESS_NAME_TYPE
        elif "macro" in attributes:
            key.code = attributes["macro"]
            key.type = KeyCommon.MACRO_TYPE
        elif "script" in attributes:
            key.code = attributes["script"]
            key.type = KeyCommon.SCRIPT_TYPE
        elif "keycode" in attributes:
            key.code = int(attributes["keycode"])
            key.type = KeyCommon.KEYCODE_TYPE
        elif "button" in attributes:
            key.code = key.id[:]
            key.type = KeyCommon.BUTTON_TYPE
        elif "draw_only" in attributes and \
             attributes["draw_only"].lower() == "true":
            key.code = None
            key.type = None
        elif key.modifier:
            key.code = None
            key.type = KeyCommon.LEGACY_MODIFIER_TYPE
        else:
            raise Exceptions.LayoutFileError(
                "key '{}' does not have a type defined in layout '{}'" \
                .format(full_id, self._layout_filename))

        # get the size group of the key
        if "group" in attributes:
            group_name = attributes["group"]
        else:
            group_name = "_default"

        # get the optional image filename
        if "image" in attributes:
            key.image_filename = attributes["image"]

        # get labels
        key.labels = self._parse_key_labels(attributes, key)

        key.group = group_name

        if "label_x_align" in attributes:
            key.label_x_align = float(attributes["label_x_align"])
        if "label_y_align" in attributes:
            key.label_y_align = float(attributes["label_y_align"])

        if "sticky" in attributes:
            sticky = attributes["sticky"].lower()
            if sticky == "true":
                key.sticky = True
            elif sticky == "false":
                key.sticky = False
            else:
                raise Exceptions.LayoutFileError(
                    "Invalid value '{}' for 'sticky' attribute of key '{}'" \
                    .format(sticky, key.id))
        else:
            key.sticky = False

        # legacy sticky key behavior was hard-coded for CAPS
        if self._format < LayoutLoaderSVG.LAYOUT_FORMAT_2_2:
            if key.id == "CAPS":
                key.sticky_behavior = StickyBehavior.LOCK_ONLY

        value = attributes.get("sticky_behavior")
        if value:
            try:
                key.sticky_behavior = StickyBehavior.from_string(value)
            except KeyError as ex:
                (strerror) = ex
                raise Exceptions.LayoutFileError("Unrecognized sticky behavior {} in" \
                    "definition of {}".format(strerror, full_id))

        if "scannable" in attributes:
            if attributes["scannable"].lower() == 'false':
                key.scannable = False

        if "scan_priority" in attributes:
            key.scan_priority = int(attributes["scan_priority"])

        if "tooltip" in attributes:
            key.tooltip = attributes["tooltip"]

        key.color_scheme = self._color_scheme

    def _parse_key_labels(self, attributes, key):
        labels = {}   # {modifier_mask : label, ...}

        # Get labels from keyboard mapping first.
        if key.type == KeyCommon.KEYCODE_TYPE and \
           not key.id in ["BKSP"]:
            if self._vk: # xkb keyboard found?
                try:
                    vkmodmasks = self._label_modifier_masks
                    vklabels = self._vk.labels_from_keycode(key.code,
                                                            vkmodmasks)
                except TypeError:
                    # virtkey until 0.61.0 didn't have the extra param.
                    vkmodmasks = (0, 1, 2, 128, 129) # used to be hard-coded
                    vklabels = self._vk.labels_from_keycode(key.code)

                if sys.version_info.major == 2:
                    vklabels = [x.decode("UTF-8") for x in vklabels]
                labels = {m : l for m, l in zip(vkmodmasks, vklabels)}
            else:
                if key.id.upper() == "SPCE":
                    labels = ["No X keyboard found, retrying..."]*5
                else:
                    labels = ["?"]*5

        # If key is a macro (snippet) generate label from its number.
        elif key.type == KeyCommon.MACRO_TYPE:
            label, text = config.snippets.get(int(key.code), \
                                                       (None, None))
            tooltip = _format("Snippet {}", key.code)
            if not label:
                labels[0] = "     --     "
                # i18n: full string is "Snippet n, unassigned"
                tooltip += _(", unassigned")
            else:
                labels[0] = label.replace("\\n", "\n")
            key.tooltip = tooltip

        # get labels from the key/template definition in the layout
        layout_labels = self._parse_layout_labels(attributes)
        if layout_labels:
            labels = layout_labels

        # override with per-keysym labels
        keysym_rules = self._get_keysym_rules(key)
        if key.type == KeyCommon.KEYCODE_TYPE:
            if self._vk: # xkb keyboard found?
                vkmodmasks = self._label_modifier_masks
                try:
                    vkkeysyms  = self._vk.keysyms_from_keycode(key.code,
                                                               vkmodmasks)
                except AttributeError:
                    # virtkey until 0.61.0 didn't have that method.
                    vkkeysyms = []

                # replace all labels whith keysyms matching a keysym rule
                for i, keysym in enumerate(vkkeysyms):
                    attributes = keysym_rules.get(keysym)
                    if attributes:
                        label = attributes.get("label")
                        if not label is None:
                            mask = vkmodmasks[i]
                            labels[mask] = label

        # Translate labels - Gettext behaves oddly when translating
        # empty strings
        labels = { mask : lab and _(lab) or None
                   for mask, lab in labels.items()}

        # Replace label and size group with overrides from
        # theme and/or system defaults.
        label_overrides = config.theme_settings.key_label_overrides
        override = label_overrides.get(key.id)
        if override:
            olabel, ogroup = override
            if olabel:
                labels = { 0 : olabel[:]}
                if ogroup:
                    group_name = ogroup[:]

        return labels

    def _parse_layout_labels(self, attributes):
        """ Deprecated label definitions up to v0.98.x """
        labels = {}
        # modifier masks were hard-coded in python-virtkey
        if "label" in attributes:
            labels[0] = attributes["label"]
            if "cap_label" in attributes:
                labels[1] = attributes["cap_label"]
            if "shift_label" in attributes:
                labels[2] = attributes["shift_label"]
            if "altgr_label" in attributes:
                labels[128] = attributes["altgr_label"]
            if "altgrNshift_label" in attributes:
                labels[129] = attributes["altgrNshift_label"]
            if "_label" in attributes:
                labels[129] = attributes["altgrNshift_label"]
        return labels

    def _get_svg_keys(self, filename):
        svg_keys = self._svg_cache.get(filename)
        if svg_keys is None:
            svg_keys = self._load_svg_keys(filename)
            self._svg_cache[filename] = svg_keys # Don't load it again next time

        return svg_keys

    def _load_svg_keys(self, filename):
        filename = os.path.join(self.layout_dir, filename)
        try:
            with open_utf8(filename) as svg_file:
                svg_dom = minidom.parse(svg_file).documentElement
                svg_keys = self._parse_svg(svg_dom)

        except Exception as xxx_todo_changeme1:
            (exception) = xxx_todo_changeme1
            raise Exceptions.LayoutFileError(_("Error loading ")
                + filename, chained_exception = exception)

        return svg_keys

    def _parse_svg(self, svg_dom):
        keys = {}
        for rect in svg_dom.getElementsByTagName("rect"):
            id = rect.attributes["id"].value

            rect = Rect(float(rect.attributes['x'].value),
                        float(rect.attributes['y'].value),
                        float(rect.attributes['width'].value),
                        float(rect.attributes['height'].value))

            # Use RectKey as cache for svg provided properties.
            # This key instance doesn't enter the layout and will
            # be discarded after the layout tree has been loaded.
            key = RectKey(id, rect)

            keys[id] = key

        return keys

    def find_template(self, item, classinfo, ids):
        """
        Look for a template definition upwards from item until the root.
        """
        for templates in self._iter_template_scopes(item):
            for id in ids:
                match = templates.get((id, classinfo))
                if match:
                    return match
        return {}

    def _iter_template_scopes(self, item):
        """
        Look for a template definition upwards from item until the root.
        """
        while item:
            for child in reversed(item.items):
                if isinstance(child, LayoutTemplates):
                    if child.templates:
                        yield child.templates
            item = item.parent

    def _get_keysym_rules(self, item):
        return self._merge_keysym_rules(item)

    def _merge_keysym_rules(self, scope_item):
        """
        Collect and merge keysym_rule from the root to item.
        Rules in nested items overwrite their parents'.
        """
        keysym_rules = {}
        for item in reversed(list(scope_item.iter_to_root())):
            if not item.keysym_rules is None:
                keysym_rules.update(item.keysym_rules)

        return keysym_rules


    # --------------------------------------------------------------------------
    # Legacy pane layout support
    # --------------------------------------------------------------------------
    def _parse_legacy_layout(self, dom_node):

        # parse panes
        panes = []
        is_scan = False
        for i, pane_node in enumerate(dom_node.getElementsByTagName("pane")):
            item = LayoutPanel()
            item.layer_id = "layer {}".format(i)

            item.id       = pane_node.attributes["id"].value
            item.filename = pane_node.attributes["filename"].value

            # parse keys
            keys = []
            for node in pane_node.getElementsByTagName("key"):
                key = self._parse_key(node, item)
                if key:
                    # some keys have changed since Onboard 0.95
                    if key.id == "middleClick":
                        key.set_id("middleclick")
                        key.type = KeyCommon.BUTTON_TYPE
                    if key.id == "secondaryClick":
                        key.set_id("secondaryclick")
                        key.type = KeyCommon.BUTTON_TYPE

                    keys.append(key)

            item.set_items(keys)

            # check for scan columns
            if pane_node.getElementsByTagName("column"):
                is_scan = True

            panes.append(item)

        layer_area = LayoutPanel()
        layer_area.id = "layer_area"
        layer_area.set_items(panes)

        # find the most frequent key width
        histogram = {}
        for key in layer_area.iter_keys():
            w = key.get_border_rect().w
            histogram[w] = histogram.get(w, 0) + 1
        most_frequent_width = max(list(zip(list(histogram.values()), list(histogram.keys()))))[1] \
                              if histogram else 18

        # Legacy onboard had automatic tab-keys for pane switching.
        # Simulate this by generating layer buttons from scratch.
        keys = []
        group = "__layer_buttons__"
        widen = 1.4 if not is_scan else 1.0
        rect = Rect(0, 0, most_frequent_width * widen, 20)

        key = RectKey()
        attributes = {}
        attributes["id"]     = "hide"
        attributes["group"]  = group
        attributes["image"]  = "close.svg"
        attributes["button"] = "true"
        attributes["scannable"] = "false"
        self._init_key(key, attributes)
        key.set_border_rect(rect.copy())
        keys.append(key)

        key = RectKey()
        attributes = {}
        attributes["id"]     = "move"
        attributes["group"]  = group
        attributes["image"]  = "move.svg"
        attributes["button"] = "true"
        attributes["scannable"] = "false"
        self._init_key(key, attributes)
        key.set_border_rect(rect.copy())
        keys.append(key)

        if len(panes) > 1:
            for i, pane in enumerate(panes):
                key = RectKey()
                attributes = {}
                attributes["id"]     = "layer{}".format(i)
                attributes["group"]  = group
                attributes["label"]  = pane.id
                attributes["button"] = "true"
                self._init_key(key, attributes)
                key.set_border_rect(rect.copy())
                keys.append(key)

        layer_switch_column = LayoutBox()
        layer_switch_column.horizontal = False
        layer_switch_column.set_items(keys)

        layout = LayoutBox()
        layout.border = 1
        layout.spacing = 2
        layout.set_items([layer_area, layer_switch_column])

        return [layout]

    @staticmethod
    def copy_layout(src_filename, dst_filename):
        src_dir = os.path.dirname(src_filename)
        dst_dir, name_ext = os.path.split(dst_filename)
        dst_basename, ext = os.path.splitext(name_ext)
        _logger.info(_format("copying layout '{}' to '{}'",
                             src_filename, dst_filename))

        domdoc = None
        svg_filenames = {}
        fallback_layers = {}

        with open_utf8(src_filename) as f:
            domdoc = minidom.parse(f)
            keyboard_node = domdoc.documentElement

            # check layout format
            format = LayoutLoaderSVG.LAYOUT_FORMAT_LEGACY
            if keyboard_node.hasAttribute("format"):
               format = Version.from_string(keyboard_node.attributes["format"].value)
            keyboard_node.attributes["id"] = dst_basename

            if format < LayoutLoaderSVG.LAYOUT_FORMAT_LAYOUT_TREE:
                raise Exceptions.LayoutFileError( \
                    _format("copy_layouts failed, unsupported layout format '{}'.",
                            format))
            else:
                # replace the basename of all svg filenames
                for node in LayoutLoaderSVG._iter_dom_nodes(keyboard_node):
                    if LayoutLoaderSVG.is_layout_node(node):
                        if node.hasAttribute("filename"):
                            filename = node.attributes["filename"].value

                            # Create a replacement layer name for the unlikely
                            # case  that the svg-filename doesn't contain a
                            # layer section (as in path/basename-layer.ext).
                            fallback_layer_name = fallback_layers.get(filename,
                                         "Layer" + str(len(fallback_layers)))
                            fallback_layers[filename] = fallback_layer_name

                            # replace the basename of this filename
                            new_filename = LayoutLoaderSVG._replace_basename( \
                                 filename, dst_basename, fallback_layer_name)

                            node.attributes["filename"].value = new_filename
                            svg_filenames[filename] = new_filename

        if domdoc:
            # write the new layout file
            with open_utf8(dst_filename, "w") as f:
                xml = toprettyxml(domdoc)
                if sys.version_info.major == 2:  # python 2?
                    xml = xml.encode("UTF-8")
                f.write(xml)

                # copy the svg files
                for src, dst in list(svg_filenames.items()):

                    dir, name = os.path.split(src)
                    if not dir:
                        src = os.path.join(src_dir, name)
                    dir, name = os.path.split(dst)
                    if not dir:
                        dst = os.path.join(dst_dir, name)

                    _logger.info(_format("copying svg file '{}' to '{}'", \
                                 src, dst))
                    shutil.copyfile(src, dst)

    @staticmethod
    def remove_layout(filename):
        for fn in LayoutLoaderSVG.get_layout_svg_filenames(filename):
            os.remove(fn)
        os.remove(filename)

    @staticmethod
    def get_layout_svg_filenames(filename):
        results = []
        domdoc = None
        with open_utf8(filename) as f:
            domdoc = minidom.parse(f).documentElement

        if domdoc:
            filenames = {}
            for node in LayoutLoaderSVG._iter_dom_nodes(domdoc):
                if LayoutLoaderSVG.is_layout_node(node):
                    if node.hasAttribute("filename"):
                        fn = node.attributes["filename"].value
                        filenames[fn] = fn

            layout_dir, name = os.path.split(filename)
            results = []
            for fn in list(filenames.keys()):
                dir, name = os.path.split(fn)
                results.append(os.path.join(layout_dir, name))

        return results

    @staticmethod
    def _replace_basename(filename, new_basename, fallback_layer_name):
        dir, name_ext = os.path.split(filename)
        name, ext = os.path.splitext(name_ext)
        components = name.split("-")
        if components:
            basename = components[0]
            if len(components) > 1:
                layer = components[1]
            else:
                layer = fallback_layer_name
            return "{}-{}{}".format(new_basename, layer, ext)
        return ""

    @staticmethod
    def is_layout_node(dom_node):
        return dom_node.tagName in ["box", "panel", "key"]

    @staticmethod
    def _iter_dom_nodes(dom_node):
        """ Recursive generator function to traverse aa dom tree """
        yield dom_node

        for child in dom_node.childNodes:
            if child.nodeType == minidom.Node.ELEMENT_NODE:
                for node in LayoutLoaderSVG._iter_dom_nodes(child):
                    yield node

