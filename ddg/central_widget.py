# -*- coding: utf-8 -*-
#
# DotDotGoose
# Author: Peter Ersts (ersts@amnh.org)
# Modified by: Anson, 2026-03 — keyboard shortcuts (undo/redo), menu layout,
#   folder/project switching, mode persistence
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
import sys
from PyQt6 import QtCore, QtWidgets, QtGui, uic

from ddg import Canvas
from ddg import PointWidget
from ddg.fields import BoxText, LineText

# from .ui_central_widget import Ui_central as CLASS_DIALOG
if getattr(sys, 'frozen', False):
    bundle_dir = os.path.join(sys._MEIPASS, 'ddg')
else:
    bundle_dir = os.path.dirname(__file__)
CLASS_DIALOG, _ = uic.loadUiType(os.path.join(bundle_dir, 'central_widget.ui'))


class CentralWidget(QtWidgets.QDialog, CLASS_DIALOG):

    load_custom_data = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self)
        self.setupUi(self)
        self.canvas = Canvas(self)

        self.point_widget = PointWidget(self.canvas, self)
        self.findChild(QtWidgets.QFrame, 'framePointWidget').layout().addWidget(self.point_widget)
        
        # Collapse right panel by default
        self.splitterMain.setSizes([425, 800, 0])
        self.labelWorkingDirectory.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.canvas.saving.connect(self.display_quick_save)
        self.canvas.directory_set.connect(lambda: self.point_widget.display_classes())

        # Keyboard shortcuts
        # Quick save using Ctrl+S
        self.save_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self.save_shortcut.setContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.save_shortcut.activated.connect(self.canvas.quick_save)

        # Undo Redo shortcuts
        self.undo_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.setContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.undo_shortcut.activated.connect(self.canvas.undo)

        self.redo_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+Z"), self)
        self.redo_shortcut.setContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.redo_shortcut.activated.connect(self.canvas.redo)

        # Arrow short cuts to move among images
        self.up_arrow = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Up), self)
        self.up_arrow.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.up_arrow.activated.connect(self.point_widget.previous)

        self.down_arrow = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Down), self)
        self.down_arrow.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.down_arrow.activated.connect(self.point_widget.next)

        # Same as arrow keys but conventient for right handed people
        self.w_key = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_W), self)
        self.w_key.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.w_key.activated.connect(self.point_widget.previous)

        self.s_key = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_S), self)
        self.s_key.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.s_key.activated.connect(self.point_widget.next)

        # Make signal slot connections
        self.graphicsView.setScene(self.canvas)
        self.graphicsView.drop_complete.connect(self.canvas.load)
        self.graphicsView.region_selected.connect(self.canvas.select_points)
        self.graphicsView.delete_selection.connect(self.canvas.delete_selected_points)
        self.graphicsView.relabel_selection.connect(self.canvas.relabel_selected_points)
        self.graphicsView.toggle_grid.connect(self.point_widget.checkBoxDisplayGrid.toggle)
        self.graphicsView.switch_class.connect(self.point_widget.set_active_class)
        self.graphicsView.add_point.connect(self.canvas.add_point)
        self.graphicsView.points_moved.connect(self.canvas.update_point_positions)
        self.canvas.image_loaded.connect(self.graphicsView.image_loaded)
        self.canvas.directory_set.connect(self.display_working_directory)
        self.canvas.active_class_changed.connect(self.graphicsView.update_add_cursor)

        # Image data fields
        self.canvas.image_loaded.connect(self.display_coordinates)
        self.canvas.image_loaded.connect(self.get_custom_field_data)
        self.canvas.fields_updated.connect(self.display_custom_fields)
        self.lineEditX.textEdited.connect(self.update_coordinates)
        self.lineEditY.textEdited.connect(self.update_coordinates)

        # Buttons
        self.pushButtonAddField.clicked.connect(self.add_field_dialog)
        self.pushButtonDeleteField.clicked.connect(self.delete_field_dialog)

        # Fix icons
        self.pushButtonDeleteField.setIcon(QtGui.QIcon('icons:delete.svg'))
        self.pushButtonAddField.setIcon(QtGui.QIcon('icons:add.svg'))
        
        # Connect status bar updates
        self.canvas.dirty_changed.connect(self.update_status_bar)
        self.canvas.directory_set.connect(self.update_status_bar)
        self.canvas.points_loaded.connect(self.update_status_bar)
        self.canvas.image_loaded.connect(self.on_file_opened)

        self.quick_save_frame = QtWidgets.QFrame(self.graphicsView)
        self.quick_save_frame.setStyleSheet("QFrame { background: #4caf50;color: #FFF;font-weight: bold}")
        self.quick_save_frame.setLayout(QtWidgets.QHBoxLayout())
        self.quick_save_frame.layout().addWidget(QtWidgets.QLabel(self.tr('Saving...')))
        self.quick_save_frame.setGeometry(3, 3, 100, 35)
        self.quick_save_frame.hide()

        # Initial Start Buttons Overlay
        self.start_overlay = QtWidgets.QWidget(self.graphicsView)
        layout = QtWidgets.QHBoxLayout(self.start_overlay)
        layout.setSpacing(10)
        
        self.btn_open_folder = QtWidgets.QPushButton(self.tr(" Open Folder"))
        self.btn_open_folder.setIcon(QtGui.QIcon('icons:folder.svg'))
        self.btn_open_folder.setIconSize(QtCore.QSize(24, 24))
        self.btn_open_folder.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.clicked.connect(self.select_folder)
        
        self.btn_load_project = QtWidgets.QPushButton(self.tr(" Load Project"))
        self.btn_load_project.setIcon(QtGui.QIcon('icons:load.svg'))
        self.btn_load_project.setIconSize(QtCore.QSize(24, 24))
        self.btn_load_project.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_load_project.clicked.connect(self.point_widget.load)
        
        layout.addStretch()
        layout.addWidget(self.btn_open_folder)
        layout.addWidget(self.btn_load_project)
        layout.addStretch()
        
        self.canvas.directory_set.connect(self.start_overlay.hide)
        self.canvas.points_loaded.connect(self.start_overlay.hide)

    def resizeEvent(self, theEvent):
        self.graphicsView.resize_image()
        self.update_status_bar()
        if hasattr(self, 'start_overlay'):
            self.start_overlay.adjustSize()
            w = self.start_overlay.width()
            h = self.start_overlay.height()
            self.start_overlay.setGeometry(int((self.graphicsView.width() - w) / 2), int((self.graphicsView.height() - h) / 2), w, h)

    # Image data field functions
    def add_field(self):
        field_def = (self.field_name.text(), self.field_type.currentText())
        field_names = [x[0] for x in self.canvas.custom_fields['fields']]
        if field_def[0] in field_names:
            QtWidgets.QMessageBox.warning(self, self.tr('Warning'), self.tr('Field name already exists'))
        else:
            self.canvas.add_custom_field(field_def)
            self.add_dialog.close()

    def add_field_dialog(self):
        self.field_name = QtWidgets.QLineEdit()
        self.field_type = QtWidgets.QComboBox()
        self.field_type.addItems(['line', 'box'])
        self.add_button = QtWidgets.QPushButton(self.tr('Save'))
        self.add_button.clicked.connect(self.add_field)
        self.add_dialog = QtWidgets.QDialog(self)
        self.add_dialog.setWindowTitle(self.tr('Add Custom Field'))
        self.add_dialog.setLayout(QtWidgets.QVBoxLayout())
        self.add_dialog.layout().addWidget(self.field_name)
        self.add_dialog.layout().addWidget(self.field_type)
        self.add_dialog.layout().addWidget(self.add_button)
        self.add_dialog.resize(250, self.add_dialog.height())
        self.add_dialog.show()

    def delete_field(self):
        self.canvas.delete_custom_field(self.field_list.currentText())
        self.delete_dialog.close()

    def delete_field_dialog(self):
        self.field_list = QtWidgets.QComboBox()
        self.field_list.addItems([x[0] for x in self.canvas.custom_fields['fields']])
        self.delete_button = QtWidgets.QPushButton(self.tr('Delete'))
        self.delete_button.clicked.connect(self.delete_field)
        self.delete_dialog = QtWidgets.QDialog(self)
        self.delete_dialog.setWindowTitle(self.tr('Delete Custom Field'))
        self.delete_dialog.setLayout(QtWidgets.QVBoxLayout())
        self.delete_dialog.layout().addWidget(self.field_list)
        self.delete_dialog.layout().addWidget(self.delete_button)
        self.delete_dialog.resize(250, self.delete_dialog.height())
        self.delete_dialog.show()

    def display_coordinates(self, directory, image):
        if image in self.canvas.coordinates:
            self.lineEditX.setText(self.canvas.coordinates[image]['x'])
            self.lineEditY.setText(self.canvas.coordinates[image]['y'])
        else:
            self.lineEditX.setText('')
            self.lineEditY.setText('')

    def display_custom_fields(self, fields):

        def build(item):
            container = QtWidgets.QGroupBox(item[0], self)
            container.setObjectName(item[0])
            container.setLayout(QtWidgets.QVBoxLayout())
            if item[1].lower() == 'line':
                edit = LineText(container)
            else:
                edit = BoxText(container)
            edit.update.connect(self.canvas.save_custom_field_data)
            self.load_custom_data.connect(edit.load_data)
            container.layout().addWidget(edit)
            return container

        custom_fields = self.findChild(QtWidgets.QFrame, 'frameCustomFields')
        if custom_fields.layout() is None:
            custom_fields.setLayout(QtWidgets.QVBoxLayout())
        else:
            layout = custom_fields.layout()
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        for item in fields:
            widget = build(item)
            custom_fields.layout().addWidget(widget)
        v = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        custom_fields.layout().addItem(v)
        self.get_custom_field_data()

    def display_working_directory(self, directory):
        self.update_status_bar()

    def update_status_bar(self, *args):
        text = ""
        if self.canvas.previous_file_name:
            # Show project name
            text = os.path.basename(self.canvas.previous_file_name)
        elif self.canvas.directory:
            # Show directory path
            text = self.canvas.directory
            
        if text and self.canvas.dirty:
            text += "*"
            
        # Elide text if too long
        metrics = QtGui.QFontMetrics(self.labelWorkingDirectory.font())
        # Use a more generous width for eliding
        available_width = max(600, self.labelWorkingDirectory.width())
        elided_text = metrics.elidedText(text, QtCore.Qt.TextElideMode.ElideMiddle, available_width)
        self.labelWorkingDirectory.setText(elided_text)
        self.labelWorkingDirectory.setToolTip(text) # Add tooltip for full path accessibility

    def on_file_opened(self, *args):
        self.update_status_bar()

    def display_quick_save(self):
        self.quick_save_frame.show()
        QtCore.QTimer.singleShot(500, self.quick_save_frame.hide)

    def get_custom_field_data(self):
        self.load_custom_data.emit(self.canvas.get_custom_field_data())

    def select_folder(self):
        if self.canvas.dirty_data_check():
            name = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr('Select image folder'), self.canvas.directory)
            if name != '':
                self.canvas.load([QtCore.QUrl('file:{}'.format(name))])
                # Set add mode only on initial folder load
                self.graphicsView.left_click_mode = 'add'
                self.graphicsView.update_add_cursor()

    def update_coordinates(self, text):
        x = self.lineEditX.text()
        y = self.lineEditY.text()
        self.canvas.save_coordinates(x, y)
