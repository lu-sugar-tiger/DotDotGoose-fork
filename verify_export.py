
import sys
import os
import shutil
from PyQt6 import QtWidgets, QtCore, QtGui
from ddg.canvas import Canvas

def test_export():
    app = QtWidgets.QApplication(sys.argv)
    
    # Setup test directory
    test_dir = os.path.abspath("test_export_overlay")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # Create a dummy image
    image_name = "test_image.png"
    image_path = os.path.join(test_dir, image_name)
    image = QtGui.QImage(100, 100, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtCore.Qt.GlobalColor.white)
    image.save(image_path)
    
    # Initialize Canvas
    canvas = Canvas()
    canvas.directory = test_dir
    canvas.classes = ["bird"]
    canvas.colors = {"bird": QtGui.QColor(255, 0, 0)} # Red
    
    # Add a point
    canvas.points = {
        image_name: {
            "bird": [QtCore.QPointF(50.0, 50.0)]
        }
    }
    
    # Export
    output_dir = os.path.join(test_dir, "output")
    os.makedirs(output_dir)
    
    print(f"Exporting to {output_dir}")
    canvas.export_all_overlays(output_dir)
    
    # Verify
    expected_output = os.path.join(output_dir, "overlay_" + image_name)
    if os.path.exists(expected_output):
        print(f"SUCCESS: Exported file found at {expected_output}")
        # Optionally load checking content?
    else:
        print(f"FAILURE: Exported file NOT found at {expected_output}")

    # Clean up (optional, keep for inspection if needed)
    # shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_export()
