# -*- coding: utf-8 -*-
#
# DotDotGoose
# DotDotGoose
# Author: Peter Ersts (ersts@amnh.org)
# Modified by: Anson on 2026-03-08 for new mouse interactions
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
from PyQt6 import QtWidgets, QtCore


class CentralGraphicsView(QtWidgets.QGraphicsView):
    add_point = QtCore.pyqtSignal(QtCore.QPointF)
    drop_complete = QtCore.pyqtSignal(list)
    region_selected = QtCore.pyqtSignal(QtCore.QRectF)
    delete_selection = QtCore.pyqtSignal()
    relabel_selection = QtCore.pyqtSignal()
    toggle_points = QtCore.pyqtSignal()
    toggle_grid = QtCore.pyqtSignal()
    switch_class = QtCore.pyqtSignal(int)

    points_moved = QtCore.pyqtSignal(list, float, float)

    def __init__(self, parent=None):
        QtWidgets.QGraphicsView.__init__(self, parent)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.shift = False
        self.ctrl = False
        self.alt = False
        self.delay = 0
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        
        self.left_click_mode = 'add'
        self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        self._pan_start = None
        self._drag_start = None
        self._items_to_move = []
        self._original_item_positions = {}

    def enterEvent(self, event):
        self.setFocus()

    def dragEnterEvent(self, event):
        event.setAccepted(True)

    def dragMoveEvent(self, event):
        pass

    def dropEvent(self, event):
        if len(event.mimeData().urls()) > 0:
            self.drop_complete.emit(event.mimeData().urls())

    def image_loaded(self, directory, file_name):
        self.resetTransform()
        self.fitInView(self.scene().itemsBoundingRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self.setSceneRect(self.scene().itemsBoundingRect())

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Alt:
            self.alt = True
        elif event.key() == QtCore.Qt.Key.Key_Control:
            self.ctrl = True
        elif event.key() == QtCore.Qt.Key.Key_Shift:
            self.shift = True
        elif event.key() == QtCore.Qt.Key.Key_Delete or event.key() == QtCore.Qt.Key.Key_Backspace:
            self.delete_selection.emit()
        elif event.key() == QtCore.Qt.Key.Key_R:
            self.relabel_selection.emit()
        elif event.key() == QtCore.Qt.Key.Key_D:
            self.toggle_points.emit()
        elif event.key() == QtCore.Qt.Key.Key_G:
            self.toggle_grid.emit()
        elif event.key() == QtCore.Qt.Key.Key_1:
            self.switch_class.emit(0)
        elif event.key() == QtCore.Qt.Key.Key_2:
            self.switch_class.emit(1)
        elif event.key() == QtCore.Qt.Key.Key_3:
            self.switch_class.emit(2)
        elif event.key() == QtCore.Qt.Key.Key_4:
            self.switch_class.emit(3)
        elif event.key() == QtCore.Qt.Key.Key_5:
            self.switch_class.emit(4)
        elif event.key() == QtCore.Qt.Key.Key_6:
            self.switch_class.emit(5)
        elif event.key() == QtCore.Qt.Key.Key_7:
            self.switch_class.emit(6)
        elif event.key() == QtCore.Qt.Key.Key_8:
            self.switch_class.emit(7)
        elif event.key() == QtCore.Qt.Key.Key_9:
            self.switch_class.emit(8)
        elif event.key() == QtCore.Qt.Key.Key_0:
            self.switch_class.emit(9)

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Alt:
            self.alt = False
        elif event.key() == QtCore.Qt.Key.Key_Control:
            self.ctrl = False
        elif event.key() == QtCore.Qt.Key.Key_Shift:
            self.shift = False

    def mouseMoveEvent(self, event):
        if self._pan_start is not None:
            delta = self._pan_start - event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta.y())
            self._pan_start = event.pos()
            event.accept()
            return
            
        if self._drag_start is not None:
            scene_pos = self.mapToScene(event.pos())
            delta = scene_pos - self._drag_start
            
            # visually move items for live dragging feedback
            for (c, p), item in self._original_item_positions.items():
                item.setTransform(QtGui.QTransform().translate(delta.x(), delta.y()))
            
            event.accept()
            return
            
        QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self._pan_start = event.pos()
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() == QtCore.Qt.MouseButton.RightButton:
            if self.left_click_mode == 'add':
                self.left_click_mode = 'select_move'
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            else:
                self.left_click_mode = 'add'
                self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
            event.accept()
            return
            
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.left_click_mode == 'add':
                self.add_point.emit(self.mapToScene(event.pos()))
            elif self.left_click_mode == 'select_move':
                scene_pos = self.mapToScene(event.pos())
                
                padding = self.scene().ui['point']['radius'] if hasattr(self.scene(), 'ui') else 10
                rect = QtCore.QRectF(scene_pos.x() - padding, scene_pos.y() - padding, padding * 2, padding * 2)
                items = self.scene().items(rect, QtCore.Qt.ItemSelectionMode.IntersectsItemShape, QtCore.Qt.SortOrder.DescendingOrder, self.transform())
                
                item = None
                for i in items:
                    if isinstance(i, QtWidgets.QGraphicsEllipseItem) and hasattr(i, '_class_name'):
                        item = i
                        break
                
                if isinstance(item, QtWidgets.QGraphicsEllipseItem) and hasattr(item, '_class_name'):
                    class_name = item._class_name
                    point = item._point
                    
                    is_selected = False
                    if hasattr(self.scene(), 'selection'):
                        for sel_class, sel_point in self.scene().selection:
                            if sel_class == class_name and sel_point.x() == point.x() and sel_point.y() == point.y():
                                is_selected = True
                                break
                    
                    self._drag_start = scene_pos
                    if is_selected:
                        self._items_to_move = self.scene().selection.copy()
                    else:
                        self._items_to_move = [(class_name, point)]
                    
                    self._original_item_positions = {}
                    for c, p in self._items_to_move:
                        for scene_item in self.scene().items():
                            if isinstance(scene_item, QtWidgets.QGraphicsEllipseItem):
                                if hasattr(scene_item, '_class_name') and scene_item._class_name == c and scene_item._point.x() == p.x() and scene_item._point.y() == p.y():
                                    self._original_item_positions[(c, p)] = scene_item
                                    break
                else:
                    self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
                    QtWidgets.QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self._pan_start = None
            if self.left_click_mode == 'add':
                self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
            else:
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            event.accept()
            return
            
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self._drag_start is not None:
                scene_pos = self.mapToScene(event.pos())
                delta = scene_pos - self._drag_start
                if delta.x() != 0 or delta.y() != 0:
                    self.points_moved.emit(self._items_to_move, delta.x(), delta.y())
                
                for (c, p), item in self._original_item_positions.items():
                    item.setTransform(QtGui.QTransform())
                
                self._drag_start = None
                self._items_to_move = []
                self._original_item_positions = {}
                event.accept()
                return

            if self.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag:
                rect = self.rubberBandRect()
                self.region_selected.emit(self.mapToScene(rect).boundingRect())
                QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)
        
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)

    def resizeEvent(self, event):
        self.resize_image()

    def resize_image(self):
        vsb = self.verticalScrollBar().isVisible()
        hsb = self.horizontalScrollBar().isVisible()
        if not (vsb or hsb):
            self.fitInView(self.scene().itemsBoundingRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            self.setSceneRect(self.scene().itemsBoundingRect())

    def wheelEvent(self, event):
        if len(self.scene().items()) > 0:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()

    def zoom_in(self):
        self.scale(1.1, 1.1)
        # Fix for MacOS and PyQt5 > v5.10
        self.repaint()

    def zoom_out(self):
        self.scale(0.9, 0.9)
        # Fix for MacOS and PyQt5 > v5.10
        self.repaint()
