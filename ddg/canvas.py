# -*- coding: utf-8 -*-
#
# DotDotGoose
# Author: Peter Ersts (ersts@amnh.org)
# Modified by: Anson, 2026-03 — undo/redo, selection UX, visibility toggles,
#   half-transparent selection, relabel flow, batch overlay export
#
# --------------------------------------------------------------------------
#
# This file is part of the DotDotGoose application.
# DotDotGoose was forked from the Neural Network Image Classifier (Nenetic).
#
# DotDotGoose is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DotDotGoose is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with with this software.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
import os
import json
import datetime
import glob
import numpy as np

from PIL import Image
from PyQt6 import QtCore, QtGui, QtWidgets


class Canvas(QtWidgets.QGraphicsScene):
    image_loading = QtCore.pyqtSignal(bool, bool)  # Params (Large image, redraw)
    image_loaded = QtCore.pyqtSignal(str, str, bool)  # Params (directory, image_name, is_redraw)
    points_loaded = QtCore.pyqtSignal(str)  # Params(survey_id)
    directory_set = QtCore.pyqtSignal(str)  # Params (directory)
    fields_updated = QtCore.pyqtSignal(list)
    update_point_count = QtCore.pyqtSignal(str, str, int)  # Params (image_name, class, count)
    metadata_imported = QtCore.pyqtSignal()
    saving = QtCore.pyqtSignal()
    active_class_changed = QtCore.pyqtSignal(str)
    dirty_changed = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        QtWidgets.QGraphicsScene.__init__(self, parent)
        self._dirty = False
        self.points = {}
        self.colors = {}
        self.visibility = {}
        self.coordinates = {}
        self.custom_fields = {'fields': [], 'data': {}}
        self.classes = []
        self.selection = []
        self.redo_queue = []
        self.undo_queue = []
        self.ui = {'grid': {'size': 5, 'color': [255, 255, 255]}, 'point': {'radius': 5, 'color': [255, 255, 0]}, 'guideline': {'color': [0, 255, 255]}}

        self.survey_id = ''

        self.directory = ''
        self.previous_file_name = None  # used for quick save
        self.current_image_name = None
        self.current_class_name = None
        self.pixmap = None
        self.current_w = 0
        self.current_h = 0

        self.image_cache = {'file_name': '', 'channels': 0, 'data': None}
        self.LUT = np.array([x for x in range(0, 256)], dtype=np.uint8)
        self.show_grid = True
        self.show_guidelines = True
        self.show_points = True
        self.visibility = {}
        self.image_data = {}  # per-image: transforms + guidelines
        self.guideline_items = []  # scene items for current guides
        self.grid_items = []       # scene items for current grid

        self.palette = [
            QtGui.QColor(255, 0, 0),       # Red
            QtGui.QColor(0, 255, 0),       # Green
            QtGui.QColor(0, 0, 255),       # Blue
            QtGui.QColor(255, 255, 0),     # Yellow
            QtGui.QColor(255, 0, 255),     # Magenta
            QtGui.QColor(0, 255, 255),     # Cyan
            QtGui.QColor(255, 128, 0),     # Orange
            QtGui.QColor(128, 0, 128),     # Purple
            QtGui.QColor(0, 128, 128),     # Teal
            QtGui.QColor(128, 128, 0),     # Olive
        ]
        self.color_index = 0


    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, value):
        if self._dirty != value:
            self._dirty = value
            self.dirty_changed.emit(value)

    # -- Per-image data helpers -----------------------------------------------

    def _default_image_data(self):
        return {'transform': {'rotation': 0, 'flip_h': False, 'flip_v': False},
                'guidelines': {'horizontal': [], 'vertical': []}}

    def _get_image_data(self, image_name=None):
        name = image_name or self.current_image_name
        if name not in self.image_data:
            self.image_data[name] = self._default_image_data()
        return self.image_data[name]

    def _get_current_transform(self):
        if self.current_image_name:
            return self._get_image_data()['transform']
        return {'rotation': 0, 'flip_h': False, 'flip_v': False}

    # -- Coordinate transform helpers -----------------------------------------

    def _transform_point(self, x_ratio, y_ratio):
        """Original stored ratio → display ratio (for rendering)."""
        t = self._get_current_transform()
        x, y = x_ratio, y_ratio
        # Apply rotation (CW)
        for _ in range(t['rotation'] // 90):
            x, y = 1.0 - y, x
        # Apply flips (after rotation)
        if t['flip_h']:
            x = 1.0 - x
        if t['flip_v']:
            y = 1.0 - y
        return x, y

    def _inverse_transform_point(self, x_ratio, y_ratio):
        """Display ratio → original stored ratio (for storing new points)."""
        t = self._get_current_transform()
        x, y = x_ratio, y_ratio
        # Undo flips first (reverse of apply order)
        if t['flip_v']:
            y = 1.0 - y
        if t['flip_h']:
            x = 1.0 - x
        # Undo rotation (CCW = 4 - n times CW)
        ccw = (4 - (t['rotation'] // 90)) % 4
        for _ in range(ccw):
            x, y = 1.0 - y, x
        return x, y

    def _apply_array_transform(self, array):
        """Apply current image transform to numpy array for display."""
        t = self._get_current_transform()
        result = array
        if t['rotation']:
            k = t['rotation'] // 90
            result = np.rot90(result, k=4 - k)  # np.rot90 is CCW, we want CW
        if t['flip_h']:
            result = np.fliplr(result)
        if t['flip_v']:
            result = np.flipud(result)
        return np.ascontiguousarray(result)

    # -- Transform actions (called from UI buttons) ---------------------------

    def rotate_current_image(self):
        if not self.current_image_name:
            return
        t = self._get_image_data()['transform']
        t['rotation'] = (t['rotation'] + 90) % 360
        self.dirty = True
        self.image_cache['file_name'] = ''  # force reload
        self.redraw_image()

    def flip_h_current_image(self):
        if not self.current_image_name:
            return
        t = self._get_image_data()['transform']
        t['flip_h'] = not t['flip_h']
        self.dirty = True
        self.image_cache['file_name'] = ''
        self.redraw_image()

    def flip_v_current_image(self):
        if not self.current_image_name:
            return
        t = self._get_image_data()['transform']
        t['flip_v'] = not t['flip_v']
        self.dirty = True
        self.image_cache['file_name'] = ''
        self.redraw_image()

    def reset_transform_current_image(self):
        if not self.current_image_name:
            return
        data = self._get_image_data()
        data['transform'] = {'rotation': 0, 'flip_h': False, 'flip_v': False}
        self.dirty = True
        self.image_cache['file_name'] = ''
        self.redraw_image()

    # -- Guideline actions ----------------------------------------------------

    def get_guidelines(self):
        if not self.current_image_name:
            return {'horizontal': [], 'vertical': []}
        return self._get_image_data()['guidelines']

    def add_guideline(self, orientation, ratio):
        """Add a guide line. orientation: 'horizontal' or 'vertical'. ratio: can be outside 0.0-1.0. Returns new index or -1."""
        if not self.current_image_name:
            return -1
        guides = self.get_guidelines()
        if len(guides[orientation]) >= 10:
            return -1
        guides[orientation].append(ratio)
        self.dirty = True
        self.display_guidelines()
        return len(guides[orientation]) - 1

    def move_guideline(self, orientation, index, new_ratio):
        guides = self.get_guidelines()
        if 0 <= index < len(guides[orientation]):
            guides[orientation][index] = new_ratio
            self.dirty = True
            self.display_guidelines()

    def remove_guideline(self, orientation, index):
        guides = self.get_guidelines()
        if 0 <= index < len(guides[orientation]):
            guides[orientation].pop(index)
            self.dirty = True
            self.display_guidelines()

    def set_guideline_color(self, color):
        self.ui['guideline']['color'] = [color.red(), color.green(), color.blue()]
        self.display_guidelines()

    def toggle_guidelines(self, display):
        self.show_guidelines = display
        self.display_guidelines()

    def toggle_points(self, display):
        self.show_points = display
        self.display_points()

    def clear_all_items(self):
        """Safely clear the entire scene and all internal item trackers."""
        self.clear()
        self.guideline_items = []
        self.grid_items = []

    def clear_guidelines(self):
        for item in self.guideline_items:
            try:
                if item.scene() == self:
                    self.removeItem(item)
            except RuntimeError:
                pass
        self.guideline_items = []

    def clear_grid(self):
        for item in self.grid_items:
            try:
                if item.scene() == self:
                    self.removeItem(item)
            except RuntimeError:
                pass
        self.grid_items = []

    def display_guidelines(self):
        self.clear_guidelines()
        if not self.current_image_name or not self.show_guidelines or self.current_w <= 0:
            return
        guides = self.get_guidelines()
        gc = self.ui['guideline']['color']
        guide_color = QtGui.QColor(gc[0], gc[1], gc[2])
        line_width = max(1, (1.0 / 1000.0) * self.current_w if self.current_w > 0 else 1) # Fallback if diag not handy, but better use diag
        diag = np.sqrt(self.current_w**2 + self.current_h**2)
        line_width = max(1, (1.0 / 2000.0) * diag)
        pen = QtGui.QPen(guide_color, 1.0, QtCore.Qt.PenStyle.SolidLine)
        pen.setWidthF(line_width)
        pen.setCosmetic(False)
        w = self.current_w
        h = self.current_h
        
        # Horizontal stored guides
        for i, y_ratio in enumerate(guides['horizontal']):
            tx0, ty0 = self._transform_point(0.0, y_ratio)
            tx1, ty1 = self._transform_point(1.0, y_ratio)
            
            if abs(ty0 - ty1) < 1e-4: # Horizontal display
                y = ty0 * h
                line = self.addLine(QtCore.QLineF(-1000000, y, 1000000, y), pen)
            else: # Vertical display
                x = tx0 * w
                line = self.addLine(QtCore.QLineF(x, -1000000, x, 1000000), pen)
            line.setZValue(50)
            line._orientation = 'horizontal'
            line._index = i
            line._orig_ratio = y_ratio
            self.guideline_items.append(line)
            
        # Vertical stored guides
        for i, x_ratio in enumerate(guides['vertical']):
            tx0, ty0 = self._transform_point(x_ratio, 0.0)
            tx1, ty1 = self._transform_point(x_ratio, 1.0)
            
            if abs(tx0 - tx1) < 1e-4: # Vertical display
                x = tx0 * w
                line = self.addLine(QtCore.QLineF(x, -1000000, x, 1000000), pen)
            else: # Horizontal display
                y = ty0 * h
                line = self.addLine(QtCore.QLineF(-1000000, y, 1000000, y), pen)
            line.setZValue(50)
            line._orientation = 'vertical'
            line._index = i
            line._orig_ratio = x_ratio
            self.guideline_items.append(line)

    def add_class(self, class_name, dirty=True):
        if class_name not in self.classes:
            self.classes.append(class_name)
            
            self.colors[class_name] = self.palette[self.color_index % len(self.palette)]
            self.color_index += 1
            
            self.visibility[class_name] = True
            if dirty:
                self.dirty = True

    def add_custom_field(self, field_def):
        self.custom_fields['fields'].append(field_def)
        self.custom_fields['data'][field_def[0]] = {}
        self.fields_updated.emit(self.custom_fields['fields'])
        self.dirty = True

    def add_point(self, point):
        if not self.show_points or not self.visibility.get(self.current_class_name, True):
            return
            
        if self.current_image_name is not None and self.current_class_name is not None and self.current_w > 0:
            if self.current_class_name not in self.points[self.current_image_name]:
                self.points[self.current_image_name][self.current_class_name] = []
                
            w = self.current_w
            h = self.current_h
            diag = np.sqrt(w**2 + h**2)
            
            # Inverse-transform display position to original ratio for storage
            display_ratio_x = point.x() / w
            display_ratio_y = point.y() / h
            orig_x, orig_y = self._inverse_transform_point(display_ratio_x, display_ratio_y)
            ratio_point = QtCore.QPointF(orig_x, orig_y)
            self.points[self.current_image_name][self.current_class_name].append(ratio_point)
            
            if self.visibility.get(self.current_class_name, True):
                display_radius = (self.ui['point']['radius'] / 500.0) * diag
                display_radius = max(1, display_radius)
                brush = QtGui.QBrush(self.colors[self.current_class_name], QtCore.Qt.BrushStyle.SolidPattern)
                pen = QtGui.QPen(brush, 2)
                item = self.addEllipse(QtCore.QRectF(point.x() - ((display_radius - 1) / 2), point.y() - ((display_radius - 1) / 2), display_radius, display_radius), pen, brush)
                item.setZValue(100)
                item._class_name = self.current_class_name
                item._point = ratio_point
            self.update_point_count.emit(self.current_image_name, self.current_class_name, len(self.points[self.current_image_name][self.current_class_name]))
            self.undo_queue.append(('add', self.current_class_name, ratio_point))
            self.redo_queue = []  # New action clears redo history
            self.dirty = True
            if hasattr(self, 'selection') and self.selection:
                self.selection = []
                self.display_points()

    def clear_grid(self):
        for item in self.grid_items:
            try:
                if item.scene() == self:
                    self.removeItem(item)
            except RuntimeError:
                pass
        self.grid_items = []

    def clear_points(self):
        for graphic in self.items():
            if isinstance(graphic, QtWidgets.QGraphicsEllipseItem):
                try:
                    if graphic.scene() == self:
                        self.removeItem(graphic)
                except RuntimeError:
                    pass

    def clear_queues(self):
        self.redo_queue = []
        self.undo_queue = []

    def delete_selected_points(self):
        if self.current_image_name is not None:
            points = self.points[self.current_image_name]
            self.undo_queue.append(('delete', None, self.selection))
            for class_name, point in self.selection:
                points[class_name].remove(point)
                self.update_point_count.emit(self.current_image_name, class_name, len(self.points[self.current_image_name][class_name]))
            self.selection = []
            self.display_points()
            self.dirty = True

    def delete_custom_field(self, field):
        if field in self.custom_fields['data']:
            self.custom_fields['data'].pop(field)
            index = -1
            for i, (field_name, _) in enumerate(self.custom_fields['fields']):
                if field_name == field:
                    index = i
            if index >= 0:
                self.custom_fields['fields'].pop(index)
            self.fields_updated.emit(self.custom_fields['fields'])
            self.dirty = True

    def dirty_data_check(self):
        proceed = True
        if self.dirty:
            msg_box = QtWidgets.QMessageBox(self.parent())
            msg_box.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
            msg_box.setWindowTitle(self.tr('Unsaved Changes'))
            msg_box.setText(self.tr('Point or field data have been modified.'))
            msg_box.setInformativeText(self.tr('Do you want to save your changes?'))
            msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Save | QtWidgets.QMessageBox.StandardButton.Cancel | QtWidgets.QMessageBox.StandardButton.Ignore)
            msg_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Save)
            response = msg_box.exec()
            if response == QtWidgets.QMessageBox.StandardButton.Save:
                proceed = self.save()
            elif response == QtWidgets.QMessageBox.StandardButton.Cancel:
                proceed = False
        return proceed

    def display_external_annotations(self, file_name):
        file_name = '{}.json'.format(os.path.splitext(file_name)[0])
        try:
            file = open(file_name, 'r')
            annotations = json.load(file)
            file.close()
            # Hard code for now, really needs to come from UI settings
            brush = QtGui.QBrush(QtCore.Qt.GlobalColor.magenta, QtCore.Qt.BrushStyle.SolidPattern)
            pen = QtGui.QPen(brush, 4)
            if 'shapes' in annotations and 'imageData' in annotations:
                # Labelme format
                for shape in annotations['shapes']:
                    if shape['shape_type'] == 'polygon':
                        points = []
                        for point in shape['points']:
                            points.append(QtCore.QPointF(point[0], point[1]))
                        # Consider saving in object for redisplay improvement
                        self.addPolygon(QtGui.QPolygonF(points), pen)
            else:
                # Future formats can be added
                pass
        except Exception:
            pass

    def display_grid(self):
        self.clear_grid()
        if self.current_image_name and self.show_grid and self.current_w > 0:
            w = self.current_w
            h = self.current_h
            
            grid_color = QtGui.QColor(self.ui['grid']['color'][0], self.ui['grid']['color'][1], self.ui['grid']['color'][2])
            grid_cols = max(1, int(self.ui['grid']['size']))
            
            draw_w = w
            draw_h = h
            x_step = draw_w / grid_cols
            y_step = draw_h / grid_cols
            
            diag = np.sqrt(w**2 + h**2)
            line_width = max(1, (1.0 / 2000.0) * diag)
            
            brush = QtGui.QBrush(grid_color, QtCore.Qt.BrushStyle.SolidPattern)
            pen = QtGui.QPen(brush, 1.0)
            pen.setWidthF(line_width)
            pen.setCosmetic(False)
            for i in range(1, grid_cols):
                x = i * x_step
                line = QtCore.QLineF(x, 0.0, x, draw_h)
                l_item = self.addLine(line, pen)
                l_item.setZValue(10)
                self.grid_items.append(l_item)
            for i in range(1, grid_cols):
                y = i * y_step
                line_obj = QtCore.QLineF(0.0, y, draw_w, y)
                line = self.addLine(line_obj, pen)
                line.setZValue(10)
                self.grid_items.append(line)

    def display_points(self):
        self.clear_points()
        if not self.show_points:
            return
            
        if self.current_image_name in self.points and self.current_w > 0:
            w = self.current_w
            h = self.current_h
            diag = np.sqrt(w**2 + h**2)
            display_radius = (self.ui['point']['radius'] / 500.0) * diag
            display_radius = max(1, display_radius)

            # Build set of selected points for fast lookup
            has_selection = bool(hasattr(self, 'selection') and self.selection)
            selected_set = set()
            if has_selection:
                for sel_class, sel_point in self.selection:
                    selected_set.add((sel_class, sel_point.x(), sel_point.y()))

            for class_name in self.points[self.current_image_name]:
                if not self.visibility.get(class_name, True):
                    continue
                base_color = self.colors[class_name]
                points = self.points[self.current_image_name][class_name]
                for point in points:
                    is_selected = has_selection and (class_name, point.x(), point.y()) in selected_set
                    
                    brush = QtGui.QBrush(base_color, QtCore.Qt.BrushStyle.SolidPattern)
                    pen = QtGui.QPen(brush, 2)
                        
                    # Transform stored ratio to display position
                    tx, ty = self._transform_point(point.x(), point.y())
                    draw_x = tx * w
                    draw_y = ty * h
                    item = self.addEllipse(QtCore.QRectF(draw_x - ((display_radius - 1) / 2), draw_y - ((display_radius - 1) / 2), display_radius, display_radius), pen, brush)
                    item.setZValue(100)
                    item._class_name = class_name
                    item._point = point
                    
                    if is_selected:
                        halo_radius = display_radius + 4
                        halo_pen = QtGui.QPen(QtCore.Qt.GlobalColor.gray, 1, QtCore.Qt.PenStyle.DashLine)
                        halo_brush = QtGui.QBrush(QtCore.Qt.BrushStyle.NoBrush)
                        halo = self.addEllipse(QtCore.QRectF(draw_x - ((halo_radius - 1) / 2), draw_y - ((halo_radius - 1) / 2), halo_radius, halo_radius), halo_pen, halo_brush)
                        halo.setZValue(99) # Render just behind the point
                        halo.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)

    def update_point_positions(self, items_to_move, dx, dy):
        if self.current_image_name is None:
            return
            
        for class_name, old_point in items_to_move:
            if class_name in self.points[self.current_image_name]:
                points_list = self.points[self.current_image_name][class_name]
                for i, p in enumerate(points_list):
                    if p.x() == old_point.x() and p.y() == old_point.y():
                        # The incoming dx and dy are ratio deltas calculated
                        # in the graphics view based on inverse-transformed mouse movement.
                        new_p = QtCore.QPointF(p.x() + dx, p.y() + dy)
                        points_list[i] = new_p
                        
                        # Update selection if this point was selected
                        for j, (sel_class, sel_point) in enumerate(self.selection):
                            if sel_class == class_name and sel_point.x() == old_point.x() and sel_point.y() == old_point.y():
                                self.selection[j] = (class_name, new_p)
                                break
                        break
                        
        self.dirty = True
        self.display_points()

    def export_counts(self, file_name):
        if self.current_image_name is not None:
            file = open(file_name, 'w')
            output = self.tr('survey id,image')
            for class_name in self.classes:
                output += ',' + class_name
            output += ",x,y"
            for field_name, _ in self.custom_fields['fields']:
                output += ',{}'.format(field_name)
            output += '\n'
            file.write(output)
            for image in self.points:
                output = self.survey_id + ',' + image
                for class_name in self.classes:
                    if class_name in self.points[image]:
                        output += ',' + str(len(self.points[image][class_name]))
                    else:
                        output += ',0'
                if image in self.coordinates:
                    output += ',' + self.coordinates[image]['x']
                    output += ',' + self.coordinates[image]['y']
                else:
                    output += ',,'
                for field_name, _ in self.custom_fields['fields']:
                    if image in self.custom_fields['data'][field_name]:
                        output += ',{}'.format(self.custom_fields['data'][field_name][image])
                    else:
                        output += ','
                output += "\n"
                file.write(output)
            file.close()

    def export_points(self, file_name):
        if self.current_image_name is not None:
            file = open(file_name, 'w')
            output = self.tr('survey id,image,class,x,y')
            file.write(output)
            for image in self.points:
                for class_name in self.classes:
                    if class_name in self.points[image]:
                        for point in self.points[image][class_name]:
                            output = '\n{},{},{},{},{}'.format(self.survey_id, image, class_name, point.x(), point.y())
                            file.write(output)
            file.close()

    def export_overlay(self, file_name):
        if self.current_image_name is not None:
            image = QtGui.QImage(int(self.sceneRect().width()), int(self.sceneRect().height()), QtGui.QImage.Format.Format_RGB32)
            painter = QtGui.QPainter(image)
            self.render(painter)
            image.save(file_name)
            painter.end()

    def export_all_overlays(self, output_directory):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
        display_radius = self.ui['point']['radius']
        
        for image_name in self.points:
            try:
                image_path = os.path.join(self.directory, image_name)
                image = QtGui.QImage(image_path)
                if image.isNull():
                    continue

                if image.format() not in [QtGui.QImage.Format.Format_RGB32, QtGui.QImage.Format.Format_ARGB32]:
                    image = image.convertToFormat(QtGui.QImage.Format.Format_RGB32)

                painter = QtGui.QPainter(image)
                
                if image_name in self.points:
                     for class_name in self.points[image_name]:
                        if class_name in self.colors:
                             color = self.colors[class_name]
                             brush = QtGui.QBrush(color, QtCore.Qt.BrushStyle.SolidPattern)
                             pen = QtGui.QPen(brush, 2)
                             painter.setPen(pen)
                             painter.setBrush(brush)
                             
                             points = self.points[image_name][class_name]
                             for point in points:
                                 painter.drawEllipse(QtCore.QRectF(point.x() - ((display_radius - 1) / 2), point.y() - ((display_radius - 1) / 2), display_radius, display_radius))
                
                painter.end()
                
                output_path = os.path.join(output_directory, 'overlay_' + image_name)
                image.save(output_path)
            except Exception:
                pass
        
        QtWidgets.QApplication.restoreOverrideCursor()

    def generate_lookup_table(self, brightness, contrast):
        LUT = [i for i in range(0, 256)]
        # Brighten image
        base_min = brightness
        base_max = 255
        for i in range(0, 256):
            LUT[i] = min(255, LUT[i] + brightness)

        # Apply contrast
        new_min = base_min - contrast
        new_max = 255 + contrast
        for i in range(0, 256):
            value = ((LUT[i] - base_min) / (base_max - base_min)) * (new_max - new_min) + new_min
            LUT[i] = min(255, max(0, value))
        self.LUT = np.array(LUT, dtype=np.uint8)

    def get_custom_field_data(self):
        data = {}
        if self.current_image_name is not None:
            for field_def in self.custom_fields['fields']:
                if self.current_image_name in self.custom_fields['data'][field_def[0]]:
                    data[field_def[0]] = self.custom_fields['data'][field_def[0]][self.current_image_name]
                else:
                    data[field_def[0]] = ''
        return data

    def import_metadata(self, file_name):
        file = open(file_name, 'r')
        data = json.load(file)
        file.close()

        # Backward compat
        if 'custom_fields' in data:
            self.custom_fields = data['custom_fields']
        else:
            self.custom_fields = {'fields': [], 'data': {}}
        if 'ui' in data:
            self.ui = data['ui']
        else:
            self.ui = {'grid': {'size': 3, 'color': [255, 255, 255]}, 'point': {'radius': 3, 'color': [255, 255, 0]}}
        # Ensure guideline key exists (added in fork.2)
        if 'guideline' not in self.ui:
            self.ui['guideline'] = {'color': [0, 255, 255]}
        # Load per-image data (transforms + guidelines)
        if 'image_data' in data:
            # Merge or overwrite image_data
            for k, v in data['image_data'].items():
                self.image_data[k] = v
        
        # Ensure the UI reflects the loaded state immediately
        self.display_grid()
        self.display_guidelines()
        self.display_points()

        # End Backward compat

        self.colors = data['colors']
        for class_name in data['colors']:
            self.colors[class_name] = QtGui.QColor(self.colors[class_name][0], self.colors[class_name][1], self.colors[class_name][2])
        self.classes = data['classes']
        self.fields_updated.emit(self.custom_fields['fields'])
        self.points_loaded.emit('')
        self.metadata_imported.emit()

    def load(self, drop_list):
        peek = drop_list[0].toLocalFile()
        if os.path.isdir(peek):
            # strip off trailing sep from path
            osx_hack = os.path.join(peek, 'OSX')
            directory = os.path.split(osx_hack)[0]
            # end
            if self.directory != '' and self.directory != directory:
                self.reset()
            
            self.directory = directory
            self.directory_set.emit(self.directory)
            files = glob.glob(os.path.join(self.directory, '*'))
            image_format = [".jpg", ".jpeg", ".png", ".tif"]
            f = (lambda x: os.path.splitext(x)[1].lower() in image_format)
            image_list = list(filter(f, files))
            image_list = sorted(image_list)
            self.load_images(image_list)
        else:
            base_path = os.path.split(peek)[0]
            for entry in drop_list:
                file_name = entry.toLocalFile()
                path = os.path.split(file_name)[0]
                error = False
                message = ''
                if os.path.isdir(file_name):
                    error = True
                    message = self.tr('Mix of files and directories detected. Load canceled.')
                if base_path != path:
                    error = True
                    message = self.tr('Files from multiple directories detected. Load canceled.')
                if self.directory != '' and self.directory != path:
                    error = True
                    message = self.tr('Image originated outside current working directory. Load canceled.')
                if error:
                    QtWidgets.QMessageBox.warning(self.parent(), self.tr('Warning'), message, QtWidgets.QMessageBox.StandardButton.Ok)
                    return None
            self.directory = base_path
            self.directory_set.emit(self.directory)
            self.load_images(drop_list)

    def load_image(self, in_file_name, redraw=False):
        Image.MAX_IMAGE_PIXELS = 1000000000
        file_name = in_file_name
        if isinstance(file_name, QtCore.QUrl):
            file_name = in_file_name.toLocalFile()

        if self.directory == '':
            self.directory = os.path.split(file_name)[0]
            self.directory_set.emit(self.directory)

        if self.directory == os.path.split(file_name)[0]:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
            self.selection = []
            self.clear_all_items()
            self.pixmap = None
            self.current_w = 0
            self.current_h = 0
            self.current_image_name = os.path.split(file_name)[1]
            if self.current_image_name not in self.points:
                self.points[self.current_image_name] = {}
            try:
                if self.image_cache['file_name'] != file_name:
                    self.image_cache['file_name'] = file_name
                    img = Image.open(file_name)
                    self.image_cache['channels'] = len(img.getbands())
                    self.image_cache['data'] = np.array(img)
                    img.close()
                channels = self.image_cache['channels']
                array = self.image_cache['data']
                # Apply per-image transform for display
                array = self._apply_array_transform(array)
                self.current_h, self.current_w = array.shape[:2]
                if not redraw:
                    self.generate_lookup_table(0, 0)
                if array.shape[0] > 10000 or array.shape[1] > 10000:
                    self.image_loading.emit(True, redraw)
                    # Make smaller tiles to save memory
                    stride = 100
                    max_stride = (array.shape[1] // stride) * stride
                    tail = array.shape[1] - max_stride
                    tile_channels = array.shape[2] if array.ndim == 3 else 1
                    tile = np.zeros((array.shape[0], stride, tile_channels), dtype=np.uint8)
                    for s in range(0, max_stride, stride):
                        tile[:, :] = self.LUT[array[:, s:s + stride]]
                        if tile_channels == 1:
                            qt_image = QtGui.QImage(tile.data, tile.shape[1], tile.shape[0], QtGui.QImage.Format.Format_Grayscale8)
                        else:
                            qt_image = QtGui.QImage(tile.data, tile.shape[1], tile.shape[0], QtGui.QImage.Format.Format_RGB888)
                        pixmap = QtGui.QPixmap.fromImage(qt_image)
                        item = self.addPixmap(pixmap)
                        item.moveBy(s, 0)
                    # Fix for windows, thin slivers at the end cause the app to hang. QImage bug?
                    if tail > 0:
                        tile = np.ones((array.shape[0], stride, tile_channels), dtype=np.uint8) * 255
                        tile[:, 0:tail] = array[:, max_stride:array.shape[1]]
                        if tile_channels == 1:
                            qt_image = QtGui.QImage(tile.data, tile.shape[1], tile.shape[0], QtGui.QImage.Format.Format_Grayscale8)
                        else:
                            qt_image = QtGui.QImage(tile.data, tile.shape[1], tile.shape[0], QtGui.QImage.Format.Format_RGB888)
                        pixmap = QtGui.QPixmap.fromImage(qt_image)
                        item = self.addPixmap(pixmap)
                        item.moveBy(max_stride, 0)
                else:
                    self.image_loading.emit(False, redraw)
                    if channels == 1:
                        qt_image = QtGui.QImage(array.data, array.shape[1], array.shape[0], QtGui.QImage.Format.Format_Grayscale8)
                    else:
                        array = self.LUT[array]
                        bpl = int(array.nbytes / array.shape[0])
                        if array.shape[2] == 4:
                            qt_image = QtGui.QImage(array.data, array.shape[1], array.shape[0], QtGui.QImage.Format.Format_RGBA8888)
                        else:
                            qt_image = QtGui.QImage(array.data, array.shape[1], array.shape[0], bpl, QtGui.QImage.Format.Format_RGB888)
                    self.pixmap = QtGui.QPixmap.fromImage(qt_image)
                    self.current_w = self.pixmap.width()
                    self.current_h = self.pixmap.height()
                    self.addPixmap(self.pixmap)
                self.display_external_annotations(file_name)
                self.display_grid()
                self.display_guidelines()
                self.display_points()
            except FileNotFoundError:
                QtWidgets.QMessageBox.critical(None, self.tr('File Not Found'), '{} {}'.format(self.current_image_name, self.tr('is not in the same folder as the point file.')))
                if not redraw:
                    self.image_loaded.emit(self.directory, self.current_image_name, False)
            else:
                self.image_loaded.emit(self.directory, self.current_image_name, redraw)
                if not redraw:
                    self.clear_queues()
            QtWidgets.QApplication.restoreOverrideCursor()

    def load_images(self, images):
        for file in images:
            file_name = file
            if isinstance(file, QtCore.QUrl):
                file_name = file.toLocalFile()

            image_name = os.path.split(file_name)[1]
            if image_name not in self.points:
                self.points[image_name] = {}
        if not self.classes:
            self.add_class('Default', dirty=False)
            self.points_loaded.emit('')
        self.dirty = False # Fresh folder load shouldn't be dirty
        if len(images) > 0:
            self.load_image(images[0])

    def load_points(self, file_name):
        self.clear_all_items()
        self.directory = os.path.dirname(file_name)
        file = open(file_name, 'r')
        self.previous_file_name = file_name
        data = json.load(file)
        file.close()
        self.survey_id = data['metadata']['survey_id']

        is_legacy = 'version' not in data or data['version'] != '1.7.0-fork.2'

        # Backward compat
        if 'custom_fields' in data:
            self.custom_fields = data['custom_fields']
        else:
            self.custom_fields = {'fields': [], 'data': {}}
        if 'ui' in data:
            self.ui = data['ui']
        else:
            self.ui = {'grid': {'size': 3, 'color': [255, 255, 255]}, 'point': {'radius': 3, 'color': [255, 255, 0]}}
        # Ensure guideline key exists (added in fork.2)
        if 'guideline' not in self.ui:
            self.ui['guideline'] = {'color': [0, 255, 255]}
        # Load per-image data (transforms + guidelines)
        if 'image_data' in data:
            # Merge or overwrite image_data
            for k, v in data['image_data'].items():
                self.image_data[k] = v
        
        # Ensure the UI reflects the loaded state immediately
        self.display_grid()
        self.display_guidelines()
        self.display_points()

        # End Backward compat

        self.colors = data['colors']
        self.classes = data['classes']
        self.coordinates = data['metadata']['coordinates']
        self.points = {}
        if 'points' in data:
            self.points = data['points']

        first_image_dims = None

        for image in self.points:
            if is_legacy:
                img_path = os.path.join(self.directory, image)
                reader = QtGui.QImageReader(img_path)
                size = reader.size()
                w, h = size.width(), size.height()
                if w > 0 and h > 0:
                    if first_image_dims is None:
                        first_image_dims = (w, h)
                else:
                    w, h = 1000, 1000  # Fallback
                    
                for class_name in self.points[image]:
                    for p in range(len(self.points[image][class_name])):
                        point = self.points[image][class_name][p]
                        self.points[image][class_name][p] = QtCore.QPointF(point['x'] / w, point['y'] / h)
            else:
                for class_name in self.points[image]:
                    for p in range(len(self.points[image][class_name])):
                        point = self.points[image][class_name][p]
                        self.points[image][class_name][p] = QtCore.QPointF(point['x'], point['y'])
                        
        if is_legacy and first_image_dims:
            fw, fh = first_image_dims
            diag = np.sqrt(fw**2 + fh**2)
            self.ui['grid']['size'] = max(1, int(fw / max(1, self.ui['grid']['size'])))
            self.ui['point']['radius'] = max(1, int((self.ui['point']['radius'] / diag) * 100.0))

        for class_name in data['colors']:
            self.colors[class_name] = QtGui.QColor(self.colors[class_name][0], self.colors[class_name][1], self.colors[class_name][2])
        self.points_loaded.emit(self.survey_id)
        self.fields_updated.emit(self.custom_fields['fields'])
        # Force rescan of working folder for new images
        self.load([QtCore.QUrl('file:{}'.format(self.directory))])

    def package_points(self, legacy=False):
        count = 0
        package = {'classes': [], 'points': {}, 'colors': {}, 'metadata': {'survey_id': self.survey_id, 'coordinates': self.coordinates}, 'custom_fields': self.custom_fields, 'ui': self.ui}
        
        if not legacy:
            package['version'] = '1.7.0-fork.2'
            
        package['classes'] = self.classes
        for class_name in self.colors:
            r = self.colors[class_name].red()
            g = self.colors[class_name].green()
            b = self.colors[class_name].blue()
            package['colors'][class_name] = [r, g, b]
            
        first_img_dims = None
            
        for image in self.points:
            package['points'][image] = {}
            w, h = 1000, 1000
            if legacy:
                img_path = os.path.join(self.directory, image)
                reader = QtGui.QImageReader(img_path)
                size = reader.size()
                tw, th = size.width(), size.height()
                if tw > 0 and th > 0:
                    w, h = tw, th
                    if first_img_dims is None:
                        first_img_dims = (w, h)
                        
            for class_name in self.points[image]:
                package['points'][image][class_name] = []
                src = self.points[image][class_name]
                dst = package['points'][image][class_name]
                for point in src:
                    if legacy:
                        p = {'x': point.x() * w, 'y': point.y() * h}
                    else:
                        p = {'x': point.x(), 'y': point.y()}
                    dst.append(p)
                    count += 1
                    
        package['ui'] = {'grid': {'size': self.ui['grid']['size'], 'color': self.ui['grid']['color']}, 'point': {'radius': self.ui['point']['radius'], 'color': self.ui['point']['color']}, 'guideline': {'color': self.ui['guideline']['color']}}
        if not legacy:
            # Serialize per-image data (transforms + guidelines)
            package['image_data'] = {}
            for img_name, img_data in self.image_data.items():
                # Only store entries with non-default values
                t = img_data.get('transform', {})
                g = img_data.get('guidelines', {})
                has_transform = t.get('rotation', 0) != 0 or t.get('flip_h', False) or t.get('flip_v', False)
                has_guides = len(g.get('horizontal', [])) > 0 or len(g.get('vertical', [])) > 0
                if has_transform or has_guides:
                    package['image_data'][img_name] = img_data
        if legacy and first_img_dims:
            fw, fh = first_img_dims
            diag = np.sqrt(fw**2 + fh**2)
            package['ui']['grid']['size'] = max(1, int(fw / max(1, self.ui['grid']['size'])))
            package['ui']['point']['radius'] = int((self.ui['point']['radius'] / 100.0) * diag)
            # Remove guideline from legacy output
            if 'guideline' in package['ui']:
                del package['ui']['guideline']
            
        return (package, count)

    def quick_save(self):
        if self.previous_file_name is None:
            self.save()
        else:
            self.saving.emit()
            self.save_points(self.previous_file_name)


    def redraw_image(self):
        if self.directory != '':
            self.load_image(self.directory + "/" + self.current_image_name, redraw=True)

    def relabel_selected_points(self):
        if self.current_class_name is not None:
            self.undo_queue.append(('relabel', self.current_class_name, self.selection))
            for class_name, point in self.selection:
                # Remove original point
                self.points[self.current_image_name][class_name].remove(point)
                self.update_point_count.emit(self.current_image_name, class_name, len(self.points[self.current_image_name][class_name]))
                if self.current_class_name not in self.points[self.current_image_name]:
                    self.points[self.current_image_name][self.current_class_name] = []
                self.points[self.current_image_name][self.current_class_name].append(point)
                self.update_point_count.emit(self.current_image_name, self.current_class_name, len(self.points[self.current_image_name][self.current_class_name]))
            self.selection = []
            self.display_points()
            self.dirty = True

    def rename_class(self, old_class, new_class):
        index = self.classes.index(old_class)
        del self.classes[index]
        if new_class not in self.classes:
            self.colors[new_class] = self.colors.pop(old_class)
            self.classes.append(new_class)
            self.classes.sort()
        else:
            del self.colors[old_class]

        for image in self.points:
            if old_class in self.points[image] and new_class in self.points[image]:
                self.points[image][new_class] += self.points[image].pop(old_class)
            elif old_class in self.points[image]:
                self.points[image][new_class] = self.points[image].pop(old_class)
        self.display_points()
        self.dirty = True

    def reset(self):
        self.dirty = False
        self.points = {}
        self.colors = {}
        self.visibility = {}
        self.image_data = {}
        self.classes = []
        self.selection = []
        self.redo_queue = []
        self.undo_queue = []
        self.coordinates = {}
        self.custom_fields = {'fields': [], 'data': {}}
        self.color_index = 0

        self.clear()
        self.directory = ''
        self.previous_file_name = None
        self.current_image_name = ''
        self.current_class_name = None
        self.fields_updated.emit([])
        self.points_loaded.emit('')
        self.image_loaded.emit('', '')
        self.directory_set.emit('')
        
        self.show_guidelines = True
        self.add_class('Default', dirty=False)
        self._dirty = False # Explicitly set internal state to avoid signal loop
        self.dirty_changed.emit(False)

    def remove_class(self, class_name):
        index = self.classes.index(class_name)
        del self.colors[class_name]
        del self.classes[index]
        for image in self.points:
            if class_name in self.points[image]:
                del self.points[image][class_name]
        self.display_points()
        self.dirty = True

    def save_as(self, override=False, legacy=False):
        folder_name = os.path.basename(self.directory) if self.directory else 'untitled'
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        default_file = f"{folder_name}_{date_str}.pnt"
        
        file_name = QtWidgets.QFileDialog.getSaveFileName(self.parent(), self.tr('Save Points'), os.path.join(self.directory, default_file), 'Point Files (*.pnt)')
        if file_name[0] != '':
            if override is False and self.directory != os.path.split(file_name[0])[0]:
                QtWidgets.QMessageBox.warning(self.parent(), self.tr('ERROR'), self.tr('You are attempting to save the pnt file outside of the working directory. Operation canceled. POINT DATA NOT SAVED.'), QtWidgets.QMessageBox.StandardButton.Ok)
            else:
                if self.save_points(file_name[0], legacy=legacy) is False:
                    msg_box = QtWidgets.QMessageBox()
                    msg_box.setWindowTitle(self.tr('ERROR'))
                    msg_box.setText(self.tr('Save Failed!'))
                    msg_box.setInformativeText(self.tr('It appears you cannot save your pnt file in the working directory, possibly due to permissions.\n\nEither change the permissions on the folder or click the SAVE button and select another location outside of the working directory. Remember to copy of the pnt file back into the current working directory.'))
                    msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Save | QtWidgets.QMessageBox.StandardButton.Cancel)
                    msg_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Save)
                    response = msg_box.exec()
                    if response == QtWidgets.QMessageBox.StandardButton.Save:
                        self.save_as(override=True, legacy=legacy)
                    else:
                        return False
                self.previous_file_name = file_name[0]
                self.clear_queues()
                return True
        return False
        
    def save_as_legacy(self):
        self.save_as(override=True, legacy=True)

    def save(self, override=False):
        if self.previous_file_name and os.path.exists(os.path.split(self.previous_file_name)[0]):
            self.save_points(self.previous_file_name)
            self.clear_queues()
            return True
        else:
            return self.save_as(override)
    def save_coordinates(self, x, y):
        if self.current_image_name is not None:
            if self.current_image_name not in self.coordinates:
                self.coordinates[self.current_image_name] = {'x': '', 'y': ''}
            self.coordinates[self.current_image_name]['x'] = x
            self.coordinates[self.current_image_name]['y'] = y

    def save_custom_field_data(self, field, data):
        if self.current_image_name is not None:
            if self.current_image_name not in self.custom_fields['data'][field]:
                self.custom_fields['data'][field][self.current_image_name] = ''
            self.custom_fields['data'][field][self.current_image_name] = data

    def save_points(self, file_name, legacy=False):
        try:
            output, _ = self.package_points(legacy=legacy)
            file = open(file_name, 'w')
            json.dump(output, file, indent=2)
            file.close()
            self.dirty = False
        except OSError:
            return False
        return True

    def select_points(self, rect):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        is_ctrl = bool(modifiers & QtCore.Qt.KeyboardModifier.ControlModifier)
        
        if not is_ctrl:
            self.selection = []
            
        if self.current_w <= 0:
            return
            
        w = self.current_w
        h = self.current_h
            
        current = self.points[self.current_image_name]
        for class_name in current:
            for point in current[class_name]:
                # Transform stored ratio to display coords for hit-testing
                tx, ty = self._transform_point(point.x(), point.y())
                px = tx * w
                py = ty * h
                if rect.contains(QtCore.QPointF(px, py)):
                    found = False
                    for i, (sel_class, sel_point) in enumerate(self.selection):
                        if sel_class == class_name and abs(sel_point.x() - point.x()) < 1e-6 and abs(sel_point.y() - point.y()) < 1e-6:
                            found = True
                            if is_ctrl:
                                self.selection.pop(i)
                            break
                    if not found:
                        self.selection.append((class_name, point))
                        
        self.display_points()

    def set_current_class(self, class_index):
        if class_index is None or class_index >= len(self.classes):
            self.set_current_class_by_name(None)
        else:
            self.set_current_class_by_name(self.classes[class_index])

    def set_current_class_by_name(self, class_name):
        self.current_class_name = class_name
        self.display_points()
        self.active_class_changed.emit(self.current_class_name if self.current_class_name else '')

    def set_grid_color(self, color):
        self.ui['grid']['color'] = [color.red(), color.green(), color.blue()]
        self.display_grid()

    def set_grid_size(self, size):
        self.ui['grid']['size'] = size
        self.display_grid()

    def set_point_color(self, color):
        self.ui['point']['color'] = [color.red(), color.green(), color.blue()]
        self.display_points()

    def set_point_radius(self, radius):
        self.ui['point']['radius'] = radius
        self.display_points()

    def toggle_grid(self, display):
        self.show_grid = display
        if self.show_grid:
            self.display_grid()
        else:
            self.clear_grid()


    def undo(self):
        if len(self.undo_queue) > 0:
            event = self.undo_queue.pop()
            if event[0] == 'add':
                if event[1] in self.points[self.current_image_name]:
                    if event[2] in self.points[self.current_image_name][event[1]]:
                        self.points[self.current_image_name][event[1]].remove(event[2])
                    self.update_point_count.emit(self.current_image_name, event[1], len(self.points[self.current_image_name][event[1]]))
                self.display_points()
                self.redo_queue.append(event)
            elif event[0] == 'delete':
                for class_name, point in event[2]:
                    if class_name not in self.points[self.current_image_name]:
                        self.points[self.current_image_name][class_name] = []
                    self.points[self.current_image_name][class_name].append(point)
                    self.update_point_count.emit(self.current_image_name, class_name, len(self.points[self.current_image_name][class_name]))
                self.display_points()
                self.redo_queue.append(event)
            elif event[0] == 'relabel':
                # event[1] is new class, event[2] is list of (old_class, point)
                for old_class, point in event[2]:
                    if event[1] in self.points[self.current_image_name] and point in self.points[self.current_image_name][event[1]]:
                        self.points[self.current_image_name][event[1]].remove(point)
                    self.update_point_count.emit(self.current_image_name, event[1], len(self.points[self.current_image_name][event[1]]))
                    if old_class not in self.points[self.current_image_name]:
                        self.points[self.current_image_name][old_class] = []
                    self.points[self.current_image_name][old_class].append(point)
                    self.update_point_count.emit(self.current_image_name, old_class, len(self.points[self.current_image_name][old_class]))
                self.display_points()
                self.redo_queue.append(event)
            self.dirty = True

    def redo(self):
        if len(self.redo_queue) > 0:
            event = self.redo_queue.pop()
            if event[0] == 'add':
                # Re-add point: event[1]=class, event[2]=point
                if event[1] not in self.points[self.current_image_name]:
                    self.points[self.current_image_name][event[1]] = []
                self.points[self.current_image_name][event[1]].append(event[2])
                self.update_point_count.emit(self.current_image_name, event[1], len(self.points[self.current_image_name][event[1]]))
                self.display_points()
                self.undo_queue.append(event)
            elif event[0] == 'delete':
                # Re-delete: event[2]=list of (class, point)
                for class_name, point in event[2]:
                    if class_name in self.points[self.current_image_name] and point in self.points[self.current_image_name][class_name]:
                        self.points[self.current_image_name][class_name].remove(point)
                    self.update_point_count.emit(self.current_image_name, class_name, len(self.points[self.current_image_name][class_name]))
                self.display_points()
                self.undo_queue.append(event)
            elif event[0] == 'relabel':
                # Re-relabel: event[1]=new class, event[2]=list of (old_class, point)
                for old_class, point in event[2]:
                    if old_class in self.points[self.current_image_name] and point in self.points[self.current_image_name][old_class]:
                        self.points[self.current_image_name][old_class].remove(point)
                    self.update_point_count.emit(self.current_image_name, old_class, len(self.points[self.current_image_name][old_class]))
                    if event[1] not in self.points[self.current_image_name]:
                        self.points[self.current_image_name][event[1]] = []
                    self.points[self.current_image_name][event[1]].append(point)
                    self.update_point_count.emit(self.current_image_name, event[1], len(self.points[self.current_image_name][event[1]]))
                self.display_points()
                self.undo_queue.append(event)
            self.dirty = True

    def toggle_class_visibility(self, class_name):
        self.visibility[class_name] = not self.visibility.get(class_name, True)
        # Deselect any selected points of the hidden class
        if not self.visibility[class_name] and hasattr(self, 'selection'):
            self.selection = [(c, p) for c, p in self.selection if c != class_name]
        self.display_points()

    def toggle_all_visibility(self, visible):
        for cn in self.visibility:
            self.visibility[cn] = visible
        # Deselect any selected points of hidden classes
        if not visible and hasattr(self, 'selection'):
            self.selection = []
        self.display_points()

    def update_survey_id(self, text):
        self.survey_id = text
