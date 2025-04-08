import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QFileDialog, QVBoxLayout, QWidget
)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, QPoint, QSize
from PIL import Image, ImageDraw
from typing import List

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

        # ⬇️ NEW
        self.rects: List[QRect] = []  # multiple rectangles
        self.selected_index = -1  # none selected
        self.dragging = False
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
        pos = event.pos()
        self.selected_index = -1

        # Check if clicked inside an existing rect
        for i, r in enumerate(reversed(self.rects)):
            actual_index = len(self.rects) - 1 - i
            if r.contains(pos):
                self.selected_index = actual_index
                self.dragging = True
                self.drag_offset = pos - r.topLeft()
                break

        # If none selected, create a new one
        if self.selected_index == -1:
            new_rect = QRect(pos, QSize(120, 80))
            self.rects.append(new_rect)
            self.selected_index = len(self.rects) - 1
            self.dragging = True
            self.drag_offset = QPoint(10, 10)

        self.update_display()

    def mouseMoveEvent(self, event):
        if self.resizing:
            # Enforce minimum size
            new_width = max(20, event.x() - self.rect.x())
            new_height = max(20, event.y() - self.rect.y())
            self.rect.setSize(QSize(new_width, new_height))
            self.image_label.setPixmap(self.draw_rectangle())
        elif self.dragging and self.selected_index >= 0:
            new_pos = event.pos() - self.drag_offset
            self.rects[self.selected_index].moveTopLeft(new_pos)
            self.update_display()

    def mouseReleaseEvent(self, event):
        self.dragging = False

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

    def update_display(self):
        pixmap = QPixmap(self.original_pixmap)
        painter = QPainter(pixmap)

        pen = QPen(QColor(255, 0, 0), 3)
        painter.setPen(pen)

        for i, r in enumerate(self.rects):
            painter.drawRect(r)
            if i == self.selected_index:
                painter.fillRect(QRect(r.bottomRight() - QPoint(self.HANDLE_SIZE, self.HANDLE_SIZE),
                                       QSize(self.HANDLE_SIZE * 2, self.HANDLE_SIZE * 2)), QColor(255, 0, 0))

        painter.end()
        self.image_label.setPixmap(pixmap)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    annotator = Annotator()
    annotator.show()
    sys.exit(app.exec_())
