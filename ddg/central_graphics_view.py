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
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        self.left_click_mode = 'select_move'
        self.add_cursor = None
        self.update_add_cursor()
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        self._pan_start = None
        self._drag_start = None
        self._items_to_move = []
        self._guide_dragging = False
        self._guide_creating = False
        self._guide_index = -1
        self._guide_orientation = None
        self.EDGE_MARGIN = 20

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
        orig_pixmap = QtGui.QIcon('icons:ink_marker.svg').pixmap(QtCore.QSize(32, 32))
        scene = self.scene()
        active_class = class_name if class_name is not None else (scene.current_class_name if hasattr(scene, 'current_class_name') else None)
        
        can_add = True
        if scene:
            can_add = scene.show_points and scene.visibility.get(active_class, True)
            
        pixmap = QtGui.QPixmap(orig_pixmap.size())
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        
        if scene and active_class and hasattr(scene, 'colors') and active_class in scene.colors:
            color = scene.colors[active_class]
            painter = QtGui.QPainter(pixmap)
            painter.drawPixmap(0, 0, orig_pixmap)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), color)
            painter.end()
        else:
            pixmap = orig_pixmap
            
        self.add_cursor = QtGui.QCursor(pixmap, 3, 29)
        
        if hasattr(self, 'left_click_mode') and self.left_click_mode == 'add':
            if not can_add:
                self.left_click_mode = 'select_move'
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            else:
                self.setCursor(self.add_cursor)

    def image_loaded(self, directory, file_name, is_redraw=False):
        scene = self.scene()
        if not is_redraw:
            self.resetTransform()
        
        if scene and hasattr(scene, 'current_w') and scene.current_w > 0:
            rect = QtCore.QRectF(0, 0, scene.current_w, scene.current_h)
            self.setSceneRect(rect)
            if is_redraw:
                self.centerOn(rect.center())
            else:
                self.fitInView(rect, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        else:
            if not is_redraw:
                self.fitInView(scene.itemsBoundingRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
                self.setSceneRect(scene.itemsBoundingRect())
            else:
                self.setSceneRect(scene.itemsBoundingRect())
                self.centerOn(scene.itemsBoundingRect().center())

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
        """Handle cursor clues and dragging."""
        pos = event.position().toPoint()
        
        # 1. Handle guide dragging if active
        if self._guide_dragging:
            scene = self.scene()
            if scene and hasattr(scene, 'current_w') and scene.current_w > 0:
                scene_pos = self.mapToScene(pos)
                w = scene.current_w
                h = scene.current_h
                disp_x, disp_y = scene_pos.x() / w, scene_pos.y() / h
                orig_x, orig_y = scene._inverse_transform_point(disp_x, disp_y)
                
                if self._guide_orientation == 'horizontal':
                    ratio = orig_y
                else:
                    ratio = orig_x
                
                # NO CLIPPING: Let user drag anywhere on canvas
                
                if self._guide_index >= 0:
                    scene.move_guideline(self._guide_orientation, self._guide_index, ratio)
            event.accept()
            # Do NOT call base mouseMoveEvent while dragging guide
            return

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
                scene = self.scene()
                if scene and hasattr(scene, 'current_w') and scene.current_w > 0:
                    try:
                        w = scene.current_w
                        h = scene.current_h
                        
                        disp_start_x, disp_start_y = self._drag_start.x() / w, self._drag_start.y() / h
                        disp_end_x, disp_end_y = scene_pos.x() / w, scene_pos.y() / h
                        
                        orig_start_x, orig_start_y = scene._inverse_transform_point(disp_start_x, disp_start_y)
                        orig_end_x, orig_end_y = scene._inverse_transform_point(disp_end_x, disp_end_y)
                        
                        r_dx = orig_end_x - orig_start_x
                        r_dy = orig_end_y - orig_start_y
                        
                        self.points_moved.emit(self._items_to_move, r_dx, r_dy)
                        
                        for i in range(len(self._items_to_move)):
                            c, p = self._items_to_move[i]
                            self._items_to_move[i] = (c, QtCore.QPointF(p.x() + r_dx, p.y() + r_dy))
                    except (RuntimeError, AttributeError):
                        self._drag_start = None
                        return
                self._drag_start = scene_pos
            event.accept()
            return

        # 2. Update cursor for potential guide interaction
        guide_info = self._find_guide_at(pos)
        ruler_info = self._get_ruler_at(pos)
        
        if guide_info:
            if guide_info[0] == 'horizontal':
                self.setCursor(QtCore.Qt.CursorShape.SplitVCursor)
            else:
                self.setCursor(QtCore.Qt.CursorShape.SplitHCursor)
        elif ruler_info:
            if ruler_info == 'horizontal':
                self.setCursor(QtCore.Qt.CursorShape.SplitVCursor)
            else:
                self.setCursor(QtCore.Qt.CursorShape.SplitHCursor)
        elif self.left_click_mode == 'add':
            self.setCursor(self.add_cursor)
        else:
            # Default cursor logic, potentially overridden by point hover
            scene_pos = self.mapToScene(event.pos())
            hit_point = False
            scene = self.scene()
            
            point_radius = scene.ui['point']['radius'] if hasattr(scene, 'ui') else 10
            padding = max(20, point_radius * 1.5)
            w = scene.current_w if hasattr(scene, 'current_w') and scene.current_w > 0 else 1
            h = scene.current_h if hasattr(scene, 'current_h') and scene.current_h > 0 else 1
            
            if hasattr(scene, 'points') and scene.current_image_name in scene.points:
                for c_name, p_list in scene.points[scene.current_image_name].items():
                    for p in p_list:
                        # Transform stored ratio to display coords
                        tx, ty = scene._transform_point(p.x(), p.y())
                        px = tx * w
                        py = ty * h
                        dist = (px - scene_pos.x())**2 + (py - scene_pos.y())**2
                        if dist <= padding**2:
                            is_selected = False
                            if hasattr(scene, 'selection'):
                                for sel_class, sel_point in scene.selection:
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
                # Check if hovering a guide line
                guide_hit = self._find_guide_at(event.pos())
                if guide_hit:
                    orient, _ = guide_hit
                    self.setCursor(QtCore.Qt.CursorShape.SplitVCursor if orient == 'horizontal' else QtCore.Qt.CursorShape.SplitHCursor)
                else:
                    # Check if in ruler strip
                    ruler = self._get_ruler_at(event.pos())
                    if ruler:
                        self.setCursor(QtCore.Qt.CursorShape.SplitVCursor if ruler == 'horizontal' else QtCore.Qt.CursorShape.SplitHCursor)
                    else:
                        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
                
        QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

    def mousePressEvent(self, event):
        """Handle clicks for guides, points, or zooming."""
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self._pan_start = event.pos()
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() == QtCore.Qt.MouseButton.RightButton:
            scene = self.scene()
            can_add = True
            if scene:
                can_add = scene.show_points and scene.visibility.get(scene.current_class_name, True)
            
            if self.left_click_mode == 'add':
                self.left_click_mode = 'select_move'
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            elif can_add:
                self.left_click_mode = 'add'
                self.setCursor(self.add_cursor)
            else:
                # Force select_move if add is not allowed
                self.left_click_mode = 'select_move'
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            event.accept()
            return
            
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            
            # 1. Check for guide manipulation FIRST (always active)
            # Existing guide grab?
            guide_info = self._find_guide_at(pos)
            if guide_info:
                self._guide_dragging = True
                self._guide_orientation, self._guide_index = guide_info
                event.accept()
                return
            
            # Ruler click for new guide?
            ruler_info = self._get_ruler_at(pos)
            if ruler_info:
                self._guide_dragging = True
                self._guide_creating = True
                self._guide_orientation = ruler_info
                scene = self.scene()
                scene_pos = self.mapToScene(pos)
                if not (scene and hasattr(scene, 'current_w') and scene.current_w > 0):
                    # Cannot create guide without image dimensions
                    event.ignore()
                    return
                
                scene_pos = self.mapToScene(pos)
                w = scene.current_w
                h = scene.current_h
                disp_x, disp_y = scene_pos.x() / w, scene_pos.y() / h
                orig_x, orig_y = scene._inverse_transform_point(disp_x, disp_y)
                
                # We need to determine if clicking at (disp_x, disp_y) vs (disp_x + 0.01, disp_y)
                # changes the original X or the original Y.
                ox1, oy1 = scene._inverse_transform_point(disp_x + 0.01, disp_y)
                dx_maps_to_ox = abs(ox1 - orig_x) > abs(oy1 - orig_y)
                
                if ruler_info == 'vertical': # Clicking Left Edge -> Constant Display X -> Vertical Display Line (Fixed Disp X)
                    # We want to know which original coordinate is FIXED when Display X is fixed.
                    orientation = 'vertical' if dx_maps_to_ox else 'horizontal'
                    ratio = orig_x if dx_maps_to_ox else orig_y
                else: # horizontal ruler (top edge) -> Constant Display Y -> Horizontal Display Line (Fixed Disp Y)
                    # For a horizontal line, clicking top vs top+delta would change Disp Y.
                    # BUT wait, the logic for 'dx_maps_to_ox' above probes Disp X. 
                    # Let's probe Disp Y for better clarity if we are top edge.
                    ox_y, oy_y = scene._inverse_transform_point(disp_x, disp_y + 0.01)
                    dy_maps_to_ox = abs(ox_y - orig_x) > abs(oy_y - orig_y)
                    
                    orientation = 'vertical' if dy_maps_to_ox else 'horizontal'
                    ratio = orig_x if dy_maps_to_ox else orig_y
                
                self._guide_orientation = orientation
                try:
                    self._guide_index = scene.add_guideline(orientation, ratio)
                except RuntimeError as e:
                    print(f"Error adding guideline: {e}")
                    self._guide_index = -1 # Indicate failure
                    event.ignore()
                    return

                self._guide_creating = True
                self._guide_dragging = True
                event.accept()
                return

            # 2. Handle point-related actions if no guide was hit
            if self.left_click_mode == 'add':
                self._add_start = pos
                # We will set DragMode later in mouseMoveEvent if we moved enough
                # to distinguish from a single click
                QtWidgets.QGraphicsView.mousePressEvent(self, event)
                event.accept()
                return
            
            if self.left_click_mode == 'select_move':
                scene_pos = self.mapToScene(event.pos())
                
                hit_point = None
                hit_class = None
                min_dist = float('inf')
                
                # Sensitivity: Use a minimum of 20 pixels or 1.5x the radius
                point_radius = self.scene().ui['point']['radius'] if hasattr(self.scene(), 'ui') else 10
                padding = max(20, point_radius * 1.5)
                
                if hasattr(self.scene(), 'points') and self.scene().current_image_name in self.scene().points:
                    w = self.scene().current_w if hasattr(self.scene(), 'current_w') and self.scene().current_w > 0 else 1
                    h = self.scene().current_h if hasattr(self.scene(), 'current_h') and self.scene().current_h > 0 else 1
                    
                    for c_name, p_list in self.scene().points[self.scene().current_image_name].items():
                        for p in p_list:
                            # Transform stored ratio to display coords
                            tx, ty = self.scene()._transform_point(p.x(), p.y())
                            px = tx * w
                            py = ty * h
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
        # Guide drag release
        if event.button() == QtCore.Qt.MouseButton.LeftButton and (self._guide_dragging or self._guide_creating):
            scene = self.scene()
            if self._guide_dragging and scene and self._guide_index >= 0:
                # Delete guide if released outside the visible viewport
                viewport_rect = self.viewport().rect()
                if not viewport_rect.contains(event.pos()):
                    scene.remove_guideline(self._guide_orientation, self._guide_index)
                else:
                    # Final safety clip when released (optional, but requested drag 'anywhere')
                    # Actually, user said only delete when dragged to outside total canvas/viewport.
                    # So we just keep it where it is.
                    pass
            self._guide_dragging = False
            self._guide_creating = False
            self._guide_orientation = None
            self._guide_index = -1
            if self.left_click_mode == 'add':
                self.setCursor(self.add_cursor)
            else:
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            event.accept()
            return

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
        QtWidgets.QGraphicsView.resizeEvent(self, event)

    def resize_image(self):
        vsb = self.verticalScrollBar().isVisible()
        hsb = self.horizontalScrollBar().isVisible()
        scene = self.scene()
        if scene and not (vsb or hsb):
            items_rect = scene.itemsBoundingRect()
            if items_rect.width() > 0:
                self.fitInView(items_rect, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
                self.setSceneRect(items_rect)

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
        # Limit zoom out to 50% scale
        if self.transform().m11() > 0.5:
            self.scale(0.9, 0.9)
            self.repaint()

    # -- Guide interaction helpers -----------------------------------------------

    def _get_ruler_at(self, viewport_pos):
        """Return 'horizontal' or 'vertical' if pos is near the viewport edges, else None."""
        scene = self.scene()
        if not scene or not hasattr(scene, 'current_w') or scene.current_w <= 0:
            return None
        
        # Check top edge
        if 0 <= viewport_pos.y() <= self.EDGE_MARGIN:
             return 'horizontal'
        
        # Check left edge
        if 0 <= viewport_pos.x() <= self.EDGE_MARGIN:
             return 'vertical'
        
        return None

    def _find_guide_at(self, viewport_pos, tolerance=8):
        """Return (orientation, index) if pos is near a guide line, else None."""
        scene = self.scene()
        if not scene or not hasattr(scene, 'guideline_items'):
            return None
        scene_pos = self.mapToScene(viewport_pos)
        
        # Compute tolerance in scene coords
        tol_scene = tolerance / self.transform().m11() if self.transform().m11() > 0 else tolerance
        
        for item in scene.guideline_items:
            try:
                if not hasattr(item, '_orientation'):
                    continue
                line = item.line()
                # Infinite lines: check dist from point to line
                if abs(line.x1() - line.x2()) < 1e-4: # Vertical
                    if abs(scene_pos.x() - line.x1()) <= tol_scene:
                        return (item._orientation, item._index)
                else: # Horizontal
                    if abs(scene_pos.y() - line.y1()) <= tol_scene:
                        return (item._orientation, item._index)
            except RuntimeError:
                continue
        return None


