# -*- coding: utf-8 -*-
#
# DotDotGoose
# Author: Peter Ersts (ersts@amnh.org)
# Modified by: Anson, 2026-03 — mouse modes, selection/deselect, drag-move,
#   custom cursors, relabel flow
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
from PyQt6 import QtWidgets, QtCore, QtGui


class CentralGraphicsView(QtWidgets.QGraphicsView):
    add_point = QtCore.pyqtSignal(QtCore.QPointF)
    drop_complete = QtCore.pyqtSignal(list)
    region_selected = QtCore.pyqtSignal(QtCore.QRectF)
    delete_selection = QtCore.pyqtSignal()
    relabel_selection = QtCore.pyqtSignal()
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
        
        self.left_click_mode = 'select_move'
        self.add_cursor = None
        self.update_add_cursor()
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        self._pan_start = None
        self._drag_start = None
        self._items_to_move = []

    def enterEvent(self, event):
        self.setFocus()

    def dragEnterEvent(self, event):
        event.setAccepted(True)

    def dragMoveEvent(self, event):
        pass

    def dropEvent(self, event):
        if len(event.mimeData().urls()) > 0:
            self.drop_complete.emit(event.mimeData().urls())

    def update_add_cursor(self, class_name=None):
        pixmap = QtGui.QPixmap('icons:pen.svg').scaled(32, 32, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        scene = self.scene()
        active_class = class_name if class_name is not None else (scene.current_class_name if hasattr(scene, 'current_class_name') else None)
        if scene and active_class and hasattr(scene, 'colors') and active_class in scene.colors:
            color = scene.colors[active_class]
            painter = QtGui.QPainter(pixmap)
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.black, 1))
            painter.drawEllipse(18, 18, 12, 12)
            painter.end()
        self.add_cursor = QtGui.QCursor(pixmap, 0, 32)
        if hasattr(self, 'left_click_mode') and self.left_click_mode == 'add':
            self.setCursor(self.add_cursor)

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
            
            if delta.x() != 0 or delta.y() != 0:
                self.points_moved.emit(self._items_to_move, delta.x(), delta.y())
                
                # Update our local tracker to precisely match the new data locations
                if hasattr(self.scene(), 'pixmap') and self.scene().pixmap is not None:
                    w = self.scene().pixmap.width()
                    h = self.scene().pixmap.height()
                    r_dx = delta.x() / w
                    r_dy = delta.y() / h
                    for i in range(len(self._items_to_move)):
                        c, p = self._items_to_move[i]
                        self._items_to_move[i] = (c, QtCore.QPointF(p.x() + r_dx, p.y() + r_dy))
                
                self._drag_start = scene_pos
            
            event.accept()
            return
            
        if self.left_click_mode == 'add' and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            if self._add_start is not None and (event.pos() - self._add_start).manhattanLength() > 10:
                self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
                QtWidgets.QGraphicsView.mouseMoveEvent(self, event)
            return

        if self.left_click_mode == 'select_move':
            scene_pos = self.mapToScene(event.pos())
            hit_point = False
            
            point_radius = self.scene().ui['point']['radius'] if hasattr(self.scene(), 'ui') else 10
            padding = max(20, point_radius * 1.5)
            
            if hasattr(self.scene(), 'points') and self.scene().current_image_name in self.scene().points:
                for c_name, p_list in self.scene().points[self.scene().current_image_name].items():
                    for p in p_list:
                        dist = (p.x() - scene_pos.x())**2 + (p.y() - scene_pos.y())**2
                        if dist <= padding**2:
                            is_selected = False
                            if hasattr(self.scene(), 'selection'):
                                for sel_class, sel_point in self.scene().selection:
                                    if sel_class == c_name and abs(sel_point.x() - p.x()) < 1e-4 and abs(sel_point.y() - p.y()) < 1e-4:
                                        is_selected = True
                                        break
                            if is_selected:
                                hit_point = True
                            break
                    if hit_point:
                        break
                        
            if hit_point:
                self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
                
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
                self.setCursor(self.add_cursor)
            event.accept()
            return
            
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.left_click_mode == 'add':
                self._add_start = event.pos()
                # We will set DragMode later in mouseMoveEvent if we moved enough
                # to distinguish from a single click
                QtWidgets.QGraphicsView.mousePressEvent(self, event)
            elif self.left_click_mode == 'select_move':
                scene_pos = self.mapToScene(event.pos())
                
                hit_point = None
                hit_class = None
                min_dist = float('inf')
                
                # Sensitivity: Use a minimum of 20 pixels or 1.5x the radius
                point_radius = self.scene().ui['point']['radius'] if hasattr(self.scene(), 'ui') else 10
                padding = max(20, point_radius * 1.5)
                
                if hasattr(self.scene(), 'points') and self.scene().current_image_name in self.scene().points:
                    w = self.scene().pixmap.width() if hasattr(self.scene(), 'pixmap') and self.scene().pixmap else 1
                    h = self.scene().pixmap.height() if hasattr(self.scene(), 'pixmap') and self.scene().pixmap else 1
                    
                    for c_name, p_list in self.scene().points[self.scene().current_image_name].items():
                        for p in p_list:
                            px = p.x() * w
                            py = p.y() * h
                            dist = (px - scene_pos.x())**2 + (py - scene_pos.y())**2
                            if dist < min_dist and dist <= padding**2:
                                min_dist = dist
                                hit_point = p
                                hit_class = c_name
                
                if hit_point is not None:
                    class_name = hit_class
                    point = hit_point
                    
                    is_selected = False
                    if hasattr(self.scene(), 'selection'):
                        for sel_class, sel_point in self.scene().selection:
                            if sel_class == class_name and abs(sel_point.x() - point.x()) < 1e-4 and abs(sel_point.y() - point.y()) < 1e-4:
                                is_selected = True
                                break
                    
                    self._drag_start = scene_pos
                    
                    if self.ctrl:
                        if is_selected:
                            new_sel = []
                            for sel_class, sel_point in self.scene().selection:
                                if not (sel_class == class_name and abs(sel_point.x() - point.x()) < 1e-4 and abs(sel_point.y() - point.y()) < 1e-4):
                                    new_sel.append((sel_class, sel_point))
                            self.scene().selection = new_sel
                            self.scene().display_points()
                            
                            self._items_to_move = []
                            self._drag_start = None
                            event.accept()
                            return
                        else:
                            if not hasattr(self.scene(), 'selection'):
                                self.scene().selection = []
                            self.scene().selection.append((class_name, point))
                            self.scene().display_points()
                            self._items_to_move = self.scene().selection.copy()
                    else:
                        if is_selected:
                            self._items_to_move = self.scene().selection.copy()
                        else:
                            self._items_to_move = [(class_name, point)]
                            
                            if hasattr(self.scene(), 'selection'):
                                self.scene().selection = [(class_name, point)]
                                self.scene().display_points()
                    
                    self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
                    event.accept()
                    return
                else:
                    self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
                    QtWidgets.QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self._pan_start = None
            if self.left_click_mode == 'add':
                self.setCursor(self.add_cursor)
            else:
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            event.accept()
            return
            
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self._drag_start is not None:
                self._drag_start = None
                self._items_to_move = []
                
                if self.left_click_mode == 'add':
                    self.setCursor(self.add_cursor)
                else:
                    self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
                    
                event.accept()
                return

            is_click = True
            if self.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag:
                rect = self.rubberBandRect()
                is_click = rect.width() < 5 and rect.height() < 5
                if not is_click:
                    self.region_selected.emit(self.mapToScene(rect).boundingRect())
                elif self.left_click_mode == 'select_move':
                    # Tiny rubberband = empty-area click: deselect all
                    scene = self.scene()
                    if hasattr(scene, 'selection') and scene.selection:
                        scene.selection = []
                        scene.display_points()
            
            if self.left_click_mode == 'add' and is_click:
                if hasattr(self, '_add_start') and self._add_start is not None:
                    self.add_point.emit(self.mapToScene(self._add_start))
                    
                if hasattr(self, '_add_start'):
                    self._add_start = None
                QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)
        
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
        if self.left_click_mode == 'add':
            self.setCursor(self.add_cursor)
        else:
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

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
        if self.transform().m11() > 0.5:
            self.scale(0.9, 0.9)
            # Fix for MacOS and PyQt5 > v5.10
            self.repaint()
