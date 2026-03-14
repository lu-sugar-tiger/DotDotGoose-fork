# -*- coding: utf-8 -*-
#
# DotDotGoose
# Author: Peter Ersts (ersts@amnh.org)
# Modified by: Anson, 2026-03 — class editor sorting, name-based interactions,
#   double-click relabel, blockSignals fix, batch overlay export
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
import sys
from PyQt6 import QtCore, QtGui, QtWidgets, uic

from .chip_dialog import ChipDialog

# from .ui_point_widget import Ui_Pointwidget as WIDGET
if getattr(sys, 'frozen', False):
    bundle_dir = os.path.join(sys._MEIPASS, 'ddg')
else:
    bundle_dir = os.path.dirname(__file__)
WIDGET, _ = uic.loadUiType(os.path.join(bundle_dir, 'point_widget.ui'))


class PointWidget(QtWidgets.QWidget, WIDGET):

    def __init__(self, canvas, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.setupUi(self)
        self.canvas = canvas

        self.pushButtonAddClass.clicked.connect(self.add_class)
        self.pushButtonRemoveClass.clicked.connect(self.remove_class)

        self.pushButtonRemoveClass.setIcon(QtGui.QIcon('icons:delete.svg'))
        self.pushButtonAddClass.setIcon(QtGui.QIcon('icons:add.svg'))

        self.tableWidgetClasses.verticalHeader().setVisible(False)
        self.tableWidgetClasses.setColumnCount(4)
        item_color = QtWidgets.QTableWidgetItem("")
        item_visibility = QtWidgets.QTableWidgetItem("")
        item_visibility.setIcon(QtGui.QIcon('icons:eye.svg'))
        item_class = QtWidgets.QTableWidgetItem(self.tr("Class"))
        item_class.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        item_count = QtWidgets.QTableWidgetItem(self.tr("Count"))
        self.tableWidgetClasses.setHorizontalHeaderItem(0, item_visibility)
        self.tableWidgetClasses.setHorizontalHeaderItem(1, item_color)
        self.tableWidgetClasses.setHorizontalHeaderItem(2, item_class)
        self.tableWidgetClasses.setHorizontalHeaderItem(3, item_count)
        self.tableWidgetClasses.horizontalHeader().setMinimumSectionSize(1)
        self.tableWidgetClasses.horizontalHeader().setStretchLastSection(False)
        self.tableWidgetClasses.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.tableWidgetClasses.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.tableWidgetClasses.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.tableWidgetClasses.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.tableWidgetClasses.setColumnWidth(0, 30)
        self.tableWidgetClasses.setColumnWidth(1, 30)
        self.tableWidgetClasses.setColumnWidth(3, 50)
        self.tableWidgetClasses.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidgetClasses.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableWidgetClasses.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.tableWidgetClasses.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableWidgetClasses.setSortingEnabled(True)
        self.tableWidgetClasses.sortByColumn(2, QtCore.Qt.SortOrder.AscendingOrder)
        self.tableWidgetClasses.cellClicked.connect(self.cell_clicked)
        self.tableWidgetClasses.cellDoubleClicked.connect(self.cell_double_clicked)
        self.tableWidgetClasses.cellChanged.connect(self.cell_changed)
        self.tableWidgetClasses.selectionModel().selectionChanged.connect(self.selection_changed)
        self.tableWidgetClasses.horizontalHeader().setSectionsClickable(True)
        self.tableWidgetClasses.horizontalHeader().sectionClicked.connect(self.header_clicked)
        self.tableWidgetClasses.horizontalHeader().setSortIndicatorShown(False)

        self.checkBoxDisplayGrid.toggled.connect(self.display_grid)
        self.canvas.image_loading.connect(self.set_sliders)
        self.canvas.image_loaded.connect(self.image_loaded)
        self.canvas.update_point_count.connect(self.update_point_count)
        self.canvas.points_loaded.connect(self.points_loaded)
        self.canvas.metadata_imported.connect(self.display_count_tree)

        self.model = QtGui.QStandardItemModel()
        self.current_model_index = QtCore.QModelIndex()
        self.treeView.setModel(self.model)
        self.reset_model()
        self.treeView.doubleClicked.connect(self.select_model_item)

        self.spinBoxPointRadius.valueChanged.connect(self.canvas.set_point_radius)
        self.spinBoxGrid.valueChanged.connect(self.canvas.set_grid_size)

        icon = QtGui.QPixmap(20, 20)
        icon.fill(QtCore.Qt.GlobalColor.white)
        self.labelGridColor.setPixmap(icon)
        self.labelGridColor.mousePressEvent = self.change_grid_color

        self.horizontalSliderBrightness.valueChanged.connect(self.set_brightness)
        self.horizontalSliderContrast.valueChanged.connect(self.set_contrast)

    def add_class(self):
        max_num = 0
        for class_name in self.canvas.classes:
            if class_name.startswith('Class '):
                try:
                    num = int(class_name[6:])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
        new_class = 'Class {}'.format(max_num + 1)
        self.canvas.add_class(new_class)
        self.display_classes()
        self.display_count_tree()
        self.set_active_class(new_class)

    def display_grid(self, display):
        self.canvas.toggle_grid(display=display)

    def cell_changed(self, row, column):
        if column == 2:
            item = self.tableWidgetClasses.item(row, column)
            if not item:
                return
            old_class = item.data(QtCore.Qt.ItemDataRole.UserRole)
            new_class = item.text().strip()
            if new_class and old_class != new_class:
                self.tableWidgetClasses.selectionModel().clear()
                self.canvas.rename_class(old_class, new_class)
                self.display_classes()
                self.display_count_tree()
                # Restore selection to the renamed class
                self.set_active_class(new_class)
            else:
                self.tableWidgetClasses.blockSignals(True)
                item.setText(old_class)
                self.tableWidgetClasses.blockSignals(False)

    def cell_double_clicked(self, row, column):
        item_name = self.tableWidgetClasses.item(row, 2)
        if not item_name:
            return
        class_name = item_name.text()

        if column == 2:
            # Double-click on name: rename if over the text, relabel if beyond text
            text_width = self.tableWidgetClasses.fontMetrics().boundingRect(item_name.text()).width()
            pos = self.tableWidgetClasses.viewport().mapFromGlobal(QtGui.QCursor.pos())
            rect = self.tableWidgetClasses.visualRect(self.tableWidgetClasses.model().index(row, column))
            if pos.x() - rect.x() <= text_width + 10:
                # Over the text: open rename editor
                item_name.setFlags(item_name.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
                self.tableWidgetClasses.editItem(item_name)
            else:
                # Beyond text: relabel selected points to this class
                if hasattr(self.canvas, 'selection') and self.canvas.selection:
                    self.canvas.current_class_name = class_name
                    self.canvas.relabel_selected_points()
                    self.display_classes()
                    self.display_count_tree()
        elif column == 3:
            # Double-click on count column: relabel selected points to this class
            if hasattr(self.canvas, 'selection') and self.canvas.selection:
                self.canvas.current_class_name = class_name
                self.canvas.relabel_selected_points()
                self.display_classes()
                self.display_count_tree()
        # cols 0 (visibility) and 1 (color): single-click already handles these, do nothing extra here

    def cell_clicked(self, row, column):
        item = self.tableWidgetClasses.item(row, 2)
        if not item:
            return
        class_name = item.text()
        
        if column == 1:
            for i, p_color in enumerate(self.canvas.palette):
                QtWidgets.QColorDialog.setCustomColor(i, p_color)
            color = QtWidgets.QColorDialog.getColor()
            if color.isValid():
                self.canvas.colors[class_name] = color
                self.canvas.dirty = True
                
                # Update the icon in the table
                new_icon_item = QtWidgets.QTableWidgetItem()
                icon = QtGui.QPixmap(20, 20)
                icon.fill(color)
                new_icon_item.setData(QtCore.Qt.ItemDataRole.DecorationRole, icon)
                new_icon_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
                self.tableWidgetClasses.setItem(row, 1, new_icon_item)
                
                if self.canvas.current_class_name == class_name:
                    self.canvas.active_class_changed.emit(class_name)
                    
        elif column == 0:
            self.canvas.toggle_class_visibility(class_name)
            self.display_classes()

    def header_clicked(self, column):
        if column == 0:
            # Check if any are hidden
            all_visible = all(self.canvas.visibility.values())
            self.canvas.toggle_all_visibility(not all_visible)
            self.display_classes()
            
            item_visibility = QtWidgets.QTableWidgetItem("")
            if not all_visible:
                item_visibility.setIcon(QtGui.QIcon('icons:eye.svg'))
            else:
                item_visibility.setIcon(QtGui.QIcon('icons:eye_slash.svg'))
            self.tableWidgetClasses.setHorizontalHeaderItem(0, item_visibility)

    def change_grid_color(self, event):
        for i, p_color in enumerate(self.canvas.palette):
            QtWidgets.QColorDialog.setCustomColor(i, p_color)
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.set_grid_color(color)

    def display_classes(self):
        self.tableWidgetClasses.blockSignals(True)
        try:
            self.tableWidgetClasses.setSortingEnabled(False)
            self.tableWidgetClasses.setRowCount(len(self.canvas.classes))
            row = 0
            for class_name in self.canvas.classes:
                item = QtWidgets.QTableWidgetItem()
                icon = QtGui.QPixmap(20, 20)
                icon.fill(self.canvas.colors[class_name])
                item.setData(QtCore.Qt.ItemDataRole.DecorationRole, icon)
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
                self.tableWidgetClasses.setItem(row, 1, item)
                
                # Visibility icon
                item_vis = QtWidgets.QTableWidgetItem()
                if self.canvas.visibility.get(class_name, True):
                    item_vis.setIcon(QtGui.QIcon('icons:eye.svg'))
                else:
                    item_vis.setIcon(QtGui.QIcon('icons:eye_slash.svg'))
                item_vis.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
                self.tableWidgetClasses.setItem(row, 0, item_vis)

                item = QtWidgets.QTableWidgetItem(class_name)
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, class_name)
                self.tableWidgetClasses.setItem(row, 2, item)
                
                count = 0
                for image in self.canvas.points:
                    if class_name in self.canvas.points[image]:
                        count += len(self.canvas.points[image][class_name])
                
                item = QtWidgets.QTableWidgetItem(str(count) + "  ")
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
                self.tableWidgetClasses.setItem(row, 3, item)
                row += 1
                
            self.tableWidgetClasses.setSortingEnabled(True)
            self.tableWidgetClasses.sortByColumn(2, QtCore.Qt.SortOrder.AscendingOrder)
            self.tableWidgetClasses.horizontalHeader().setSortIndicatorShown(False)
            
            # Restore selection
            if self.canvas.current_class_name:
                items = self.tableWidgetClasses.findItems(self.canvas.current_class_name, QtCore.Qt.MatchFlag.MatchExactly)
                if items:
                    self.tableWidgetClasses.selectRow(items[0].row())
            elif len(self.canvas.classes) > 0:
                self.tableWidgetClasses.selectRow(0)
        finally:
            self.tableWidgetClasses.blockSignals(False)

    def display_count_tree(self):
        self.reset_model()
        for image in sorted(self.canvas.points):
            image_item = QtGui.QStandardItem(image)
            image_item.setEditable(False)
            class_item = QtGui.QStandardItem('')
            class_item.setEditable(False)
            self.model.appendRow([image_item, class_item])
            file_name = os.path.join(self.canvas.directory, image)
            if not os.path.exists(file_name):
                font = image_item.font()
                font.setStrikeOut(True)
                image_item.setFont(font)
                image_item.setForeground(QtGui.QBrush(QtCore.Qt.GlobalColor.red))
            if image == self.canvas.current_image_name:
                font = image_item.font()
                font.setBold(True)
                image_item.setFont(font)
                self.treeView.setExpanded(image_item.index(), True)
                self.current_model_index = image_item.index()

            for class_name in sorted(self.canvas.classes):
                class_item = QtGui.QStandardItem(class_name)
                class_item.setEditable(False)
                class_item.setSelectable(False)
                class_count = QtGui.QStandardItem('0  ')
                if class_name in self.canvas.points[image]:
                    class_count = QtGui.QStandardItem(str(len(self.canvas.points[image][class_name])) + '  ')
                class_count.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                class_count.setEditable(False)
                class_count.setSelectable(False)
                image_item.appendRow([class_item, class_count])
        self.treeView.scrollTo(self.current_model_index)

    def export_counts(self):
        file_name = QtWidgets.QFileDialog.getSaveFileName(self, self.tr('Export Count Summary'), os.path.join(self.canvas.directory, 'counts.csv'), 'Text CSV (*.csv)')
        if file_name[0] != '':
            self.canvas.export_counts(file_name[0])

    def export_points(self):
        file_name = QtWidgets.QFileDialog.getSaveFileName(self, self.tr('Export Points'), os.path.join(self.canvas.directory, 'points.csv'), 'Text CSV (*.csv)')
        if file_name[0] != '':
            self.canvas.export_points(file_name[0])

    def export_all_overlays(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr('Select Output Directory'), self.canvas.directory)
        if directory != '':
            self.canvas.export_all_overlays(directory)

    def export_single_overlay(self):
        file_name = QtWidgets.QFileDialog.getSaveFileName(self, self.tr('Export Overlay'), os.path.join(self.canvas.directory, 'overlay_' + str(self.canvas.current_image_name)), 'Image File (*.png)')
        if file_name[0] != '':
            self.canvas.export_overlay(file_name[0])

    def export_chips(self):
        from ddg.chip_dialog import ChipDialog
        self.chip_dialog = ChipDialog(self.canvas.classes, self.canvas.points, self.canvas.directory, self.canvas.survey_id)
        self.chip_dialog.show()

    def image_loaded(self, directory, file_name):
        # self.tableWidgetClasses.selectionModel().clear()
        self.display_count_tree()

    def import_metadata(self):
        if self.canvas.dirty_data_check():
            file_name = QtWidgets.QFileDialog.getOpenFileName(self, self.tr('Select Points File'), self.canvas.directory, 'Point Files (*.pnt)')
            if file_name[0] != '':
                self.canvas.import_metadata(file_name[0])

    def load(self):
        if self.canvas.dirty_data_check():
            file_name = QtWidgets.QFileDialog.getOpenFileName(self, self.tr('Select Points File'), self.canvas.directory, 'Point Files (*.pnt)')
            if file_name[0] != '':
                self.canvas.load_points(file_name[0])

    def next(self):
        max_index = self.model.rowCount()
        next_index = self.current_model_index.row() + 1
        if next_index < max_index:
            item = self.model.item(next_index)
            self.select_model_item(item.index())

    def points_loaded(self):
        self.display_classes()
        self.update_ui_settings()

    def previous(self):
        next_index = self.current_model_index.row() - 1
        if next_index >= 0:
            item = self.model.item(next_index)
            self.select_model_item(item.index())

    def reset(self):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setWindowTitle(self.tr('Warning'))
        msgBox.setText(self.tr('You are about to clear all data'))
        msgBox.setInformativeText(self.tr('Do you want to continue?'))
        msgBox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Cancel | QtWidgets.QMessageBox.StandardButton.Ok)
        msgBox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        response = msgBox.exec()
        if response == QtWidgets.QMessageBox.StandardButton.Ok:
            self.canvas.reset()
            self.display_classes()
            self.display_count_tree()

    def reset_model(self):
        self.current_model_index = QtCore.QModelIndex()
        self.model.clear()
        self.model.setColumnCount(2)
        self.model.setHeaderData(0, QtCore.Qt.Orientation.Horizontal, self.tr('Image'))
        self.model.setHeaderData(1, QtCore.Qt.Orientation.Horizontal, self.tr('Count'))
        self.model.setHeaderData(1, QtCore.Qt.Orientation.Horizontal, QtCore.Qt.AlignmentFlag.AlignCenter, role=QtCore.Qt.ItemDataRole.TextAlignmentRole)
        self.treeView.setExpandsOnDoubleClick(False)
        self.treeView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.treeView.header().setStretchLastSection(False)
        self.treeView.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.treeView.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.treeView.setColumnWidth(1, 50)
        self.treeView.setTextElideMode(QtCore.Qt.TextElideMode.ElideMiddle)

    def remove_class(self):
        indexes = self.tableWidgetClasses.selectedIndexes()
        if len(indexes) > 0:
            class_name = self.tableWidgetClasses.item(indexes[0].row(), 2).text()
            msgBox = QtWidgets.QMessageBox()
            msgBox.setWindowTitle(self.tr('Warning'))
            msgBox.setText(self.tr('{} [{}] '.format(self.tr('You are about to remove class'), class_name)))
            msgBox.setInformativeText(self.tr('Do you want to continue?'))
            msgBox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Cancel | QtWidgets.QMessageBox.StandardButton.Ok)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Cancel)
            response = msgBox.exec()
            if response == QtWidgets.QMessageBox.StandardButton.Ok:
                self.canvas.remove_class(class_name)
                self.display_classes()
                self.display_count_tree()

    def select_model_item(self, model_index):
        item = self.model.itemFromIndex(model_index)
        if item.isSelectable():
            if item.column() != 0:
                index = self.model.index(item.row(), 0)
                item = self.model.itemFromIndex(index)
            path = os.path.join(self.canvas.directory, item.text())
            self.canvas.load_image(path)

    def selection_changed(self, selected, deselected):
        if len(selected.indexes()) > 0:
            class_name = self.tableWidgetClasses.item(selected.indexes()[0].row(), 2).text()
            self.canvas.set_current_class_by_name(class_name)
        elif len(self.canvas.classes) > 0:
            self.tableWidgetClasses.blockSignals(True)
            if self.canvas.current_class_name:
                items = self.tableWidgetClasses.findItems(self.canvas.current_class_name, QtCore.Qt.MatchFlag.MatchExactly)
                if items:
                    self.tableWidgetClasses.selectRow(items[0].row())
                else:
                    self.tableWidgetClasses.selectRow(0)
                    item = self.tableWidgetClasses.item(0, 2)
                    if item:
                        self.canvas.set_current_class_by_name(item.text())
            else:
                self.tableWidgetClasses.selectRow(0)
                item = self.tableWidgetClasses.item(0, 2)
                if item:
                    self.canvas.set_current_class_by_name(item.text())
            self.tableWidgetClasses.blockSignals(False)
        else:
            self.canvas.set_current_class_by_name(None)



    def set_active_class(self, class_name):
        # Allow passing either a row index or a class name (robustness)
        if isinstance(class_name, int):
            if class_name < len(self.canvas.classes):
                class_name = self.canvas.classes[class_name]
            else:
                return

        if class_name:
            items = self.tableWidgetClasses.findItems(class_name, QtCore.Qt.MatchFlag.MatchExactly)
            if items:
                self.tableWidgetClasses.blockSignals(True)
                self.tableWidgetClasses.selectRow(items[0].row())
                self.tableWidgetClasses.blockSignals(False)
                self.canvas.set_current_class_by_name(class_name)

    def set_brightness(self, value):
        self.canvas.generate_lookup_table(value, self.horizontalSliderContrast.value())
        self.canvas.redraw_image()

    def set_contrast(self, value):
        self.canvas.generate_lookup_table(self.horizontalSliderBrightness.value(), value)
        self.canvas.redraw_image()

    def set_grid_color(self, color):
        icon = QtGui.QPixmap(20, 20)
        icon.fill(color)
        self.labelGridColor.setPixmap(icon)
        self.canvas.set_grid_color(color)

    def set_sliders(self, large_image, redraw):
        self.horizontalSliderBrightness.setTracking(not large_image)
        self.horizontalSliderContrast.setTracking(not large_image)
        if not redraw:
            self.horizontalSliderBrightness.blockSignals(True)
            self.horizontalSliderContrast.blockSignals(True)
            self.horizontalSliderBrightness.setValue(0)
            self.horizontalSliderContrast.setValue(0)
            self.horizontalSliderBrightness.blockSignals(False)
            self.horizontalSliderContrast.blockSignals(False)

    def update_point_count(self, image_name, class_name, class_count):
        items = self.model.findItems(image_name)
        if len(items) == 0:
            self.display_count_tree()
        else:
            # Tree children are sorted alphabetically
            sorted_classes = sorted(self.canvas.classes)
            if class_name in sorted_classes:
                child_row = sorted_classes.index(class_name)
                items[0].child(child_row, 1).setText(str(class_count) + "  ")

        # Update the main class table count automatically
        if class_name in self.canvas.classes:
            items = self.tableWidgetClasses.findItems(class_name, QtCore.Qt.MatchFlag.MatchExactly)
            if items:
                row = items[0].row()
                total_count = sum(len(self.canvas.points[img].get(class_name, [])) for img in self.canvas.points)
                item = self.tableWidgetClasses.item(row, 3)
                if item:
                    item.setText(str(total_count) + "  ")

    def update_ui_settings(self):
        ui = self.canvas.ui
        color = QtGui.QColor(ui['grid']['color'][0], ui['grid']['color'][1], ui['grid']['color'][2])
        self.set_grid_color(color)
        self.spinBoxGrid.setValue(ui['grid']['size'])
        self.spinBoxPointRadius.setValue(ui['point']['radius'])
