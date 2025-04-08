import sys
import os

from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QFileDialog, QVBoxLayout, QWidget
)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, QPoint
from PIL import Image, ImageDraw


class Annotator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Annotator")
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.image_label.setMouseTracking(True)

        self.save_button = QPushButton("Save Annotated Image")
        self.save_button.clicked.connect(self.save_annotated_image)

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

        self.image_path = None
        self.rect = QRect(100, 100, 200, 100)
        self.dragging = False
        self.offset = QPoint()

        self.load_image()

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_path = file_path
            self.original_pixmap = QPixmap(file_path)
            self.image_label.setPixmap(self.draw_rectangle())
            self.resize(self.original_pixmap.width(), self.original_pixmap.height() + 50)

    def draw_rectangle(self):
        pixmap = QPixmap(self.original_pixmap)
        painter = QPainter(pixmap)
        pen = QPen(QColor(255, 0, 0), 3)
        painter.setPen(pen)
        painter.drawRect(self.rect)
        painter.end()
        return pixmap

    def mousePressEvent(self, event):
        if self.rect.contains(event.pos()):
            self.dragging = True
            self.offset = event.pos() - self.rect.topLeft()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.rect.moveTopLeft(event.pos() - self.offset)
            self.image_label.setPixmap(self.draw_rectangle())

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def save_annotated_image(self):
        if not self.image_path:
            return

        # Draw rectangle on image using PIL
        img = Image.open(self.image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        x, y, w, h = self.rect.left(), self.rect.top(), self.rect.width(), self.rect.height()
        for i in range(3):  # 3 px thick
            draw.rectangle([x-i, y-i, x+w+i, y+h+i], outline="red")

        save_path = os.path.join(
            os.path.dirname(self.image_path),
            "circle_" + os.path.basename(self.image_path)
        )
        img.save(save_path)
        print(f"Saved annotated image to {save_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    annotator = Annotator()
    annotator.show()
    sys.exit(app.exec_())
