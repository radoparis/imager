import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QFileDialog, QVBoxLayout, QWidget
)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, QPoint, QSize
from PIL import Image, ImageDraw


class Annotator(QWidget):
    HANDLE_SIZE = 10

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
        self.resizing = False
        self.drag_offset = QPoint()

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

        # Red outline
        pen = QPen(QColor(255, 0, 0), 3)
        painter.setPen(pen)
        painter.drawRect(self.rect)

        # Resize handle (bottom right)
        handle = QRect(
            self.rect.right() - self.HANDLE_SIZE,
            self.rect.bottom() - self.HANDLE_SIZE,
            self.HANDLE_SIZE * 2,
            self.HANDLE_SIZE * 2
        )
        painter.fillRect(handle, QColor(255, 0, 0))
        painter.end()

        return pixmap

    def mousePressEvent(self, event):
        if self.in_resize_handle(event.pos()):
            self.resizing = True
        elif self.rect.contains(event.pos()):
            self.dragging = True
            self.drag_offset = event.pos() - self.rect.topLeft()

    def mouseMoveEvent(self, event):
        if self.resizing:
            # Enforce minimum size
            new_width = max(20, event.x() - self.rect.x())
            new_height = max(20, event.y() - self.rect.y())
            self.rect.setSize(QSize(new_width, new_height))
            self.image_label.setPixmap(self.draw_rectangle())
        elif self.dragging:
            new_pos = event.pos() - self.drag_offset
            self.rect.moveTopLeft(new_pos)
            self.image_label.setPixmap(self.draw_rectangle())

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing = False

    def in_resize_handle(self, pos: QPoint):
        handle = QRect(
            self.rect.right() - self.HANDLE_SIZE,
            self.rect.bottom() - self.HANDLE_SIZE,
            self.HANDLE_SIZE * 2,
            self.HANDLE_SIZE * 2
        )
        return handle.contains(pos)

    def save_annotated_image(self):
        if not self.image_path:
            return

        img = Image.open(self.image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        x, y, w, h = self.rect.left(), self.rect.top(), self.rect.width(), self.rect.height()

        for i in range(3):  # 3 px border
            draw.rectangle([x - i, y - i, x + w + i, y + h + i], outline="red")

        out_path = os.path.join(
            os.path.dirname(self.image_path),
            "circle_" + os.path.basename(self.image_path)
        )
        img.save(out_path)
        print(f"✅ Saved to {out_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    annotator = Annotator()
    annotator.show()
    sys.exit(app.exec_())
