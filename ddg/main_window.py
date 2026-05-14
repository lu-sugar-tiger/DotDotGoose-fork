# -*- coding: utf-8 -*-
#
# DotDotGoose
# Author: Peter Ersts (ersts@amnh.org)
# Modified by: Anson, 2026-03 to 2026-05 — menu restructuring, removed Language menu
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
from ddg import CentralWidget
from PyQt6 import QtWidgets, QtCore, QtGui
from ddg import AboutDialog
from ddg import __version__


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.setWindowTitle('DotDotGoose [v {}]'.format(__version__))
        self.setWindowIcon(QtGui.QIcon("icons:ddg.png"))
        self.setCentralWidget(CentralWidget())
        self.about_dialog = AboutDialog(self)

        self.error_widget = QtWidgets.QTextBrowser()
        self.error_widget.setWindowTitle(self.tr('EXCEPTION DETECTED'))
        self.error_widget.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.error_widget.resize(900, 500)

        self.setMenuBar(QtWidgets.QMenuBar())
        self.menuBar().setNativeMenuBar(False)
        menu = self.menuBar().addMenu(self.tr('File'))
        menu.setObjectName('File')
        
        # New options
        menu.addAction(self.tr('Open Folder'), self.centralWidget().select_folder)
        menu.addAction(self.tr('Load Project'), self.centralWidget().point_widget.load)
        menu.addAction(self.tr('Import Configuration'), self.centralWidget().point_widget.import_metadata)
        menu.addSeparator()
        menu.addAction(self.tr('Save'), self.centralWidget().canvas.save)
        menu.addAction(self.tr('Save as...'), self.centralWidget().canvas.save_as)
        menu.addAction(self.tr('Save in Legacy'), self.centralWidget().canvas.save_as_legacy)
        menu.addSeparator()
        menu.addAction(self.tr('Export All Counts'), self.centralWidget().point_widget.export_counts)
        menu.addAction(self.tr('Export All Points'), self.centralWidget().point_widget.export_points)
        menu.addAction(self.tr('Export All Chips'), self.centralWidget().point_widget.export_chips)
        menu.addAction(self.tr('Export All Overlays'), self.centralWidget().point_widget.export_all_overlays)
        menu.addAction(self.tr('Export Single Overlay'), self.centralWidget().point_widget.export_single_overlay)
        menu.addSeparator()
        menu.addAction(self.tr('Reset Project'), self.centralWidget().point_widget.reset)
        menu.addSeparator()
        
        menu.addAction(self.tr('Quit'), self.quit)

        self.menuBar().addSeparator()

        self.menuBar().addAction(self.tr('About'), self.about_dialog.show)

    def closeEvent(self, event):
        if self.centralWidget().canvas.dirty_data_check():
            event.accept()
        else:
            event.ignore()

    def display_exception(self, error):
        self.error_widget.clear()
        for line in error:
            self.error_widget.append(line)
        self.error_widget.show()

    def quit(self):
        self.close()
