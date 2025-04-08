import sys
import os
from typing import List
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

        self.new_button = QPushButton("➕ New Rectangle")
        self.new_button.clicked.connect(self.add_new_rectangle)

        self.save_button = QPushButton("💾 Save Annotated Image")
        self.save_button.clicked.connect(self.save_annotated_image)

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.new_button)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

        self.image_path = None
        self.original_pixmap = None

        self.rects: List[QRect] = []
        self.selected_index = -1
        self.dragging = False
        self.drag_offset = QPoint()

        self.load_image()

        self.resizing = False
        self.resize_corner = None  # One of 'tl', 'tr', 'bl', 'br'

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_path = file_path
            self.original_pixmap = QPixmap(file_path)
            self.image_label.setPixmap(self.original_pixmap)
            self.resize(self.original_pixmap.width(), self.original_pixmap.height() + 100)

    def get_resize_corner(self, pos: QPoint, rect: QRect):
        hs = self.HANDLE_SIZE
        corners = {
            'tl': rect.topLeft(),
            'tr': rect.topRight(),
            'bl': rect.bottomLeft(),
            'br': rect.bottomRight(),
        }

        for name, corner_point in corners.items():
            # Center the handle area on the corner point
            area = QRect(
                corner_point - QPoint(hs, hs),
                QSize(hs * 2, hs * 2)
            )
            if area.contains(pos):
                return name
        return None

    def add_new_rectangle(self):
        if not self.original_pixmap:
            return

        w, h = 200, 150
        img_w, img_h = self.original_pixmap.width(), self.original_pixmap.height()
        x = (img_w - w) // 2
        y = (img_h - h) // 2

        new_rect = QRect(QPoint(x, y), QSize(w, h))
        self.rects.append(new_rect)
        self.selected_index = len(self.rects) - 1
        self.update_display()

    def mousePressEvent(self, event):
        pos = event.pos()
        self.selected_index = -1

        for i, r in enumerate(reversed(self.rects)):
            actual_index = len(self.rects) - 1 - i
            corner = self.get_resize_corner(pos, r)
            if corner:
                self.selected_index = actual_index
                self.resizing = True
                self.resize_corner = corner
                break
            elif r.contains(pos):
                self.selected_index = actual_index
                self.dragging = True
                self.drag_offset = pos - r.topLeft()
                break

        self.update_display()

    def mouseMoveEvent(self, event):
        if self.resizing and self.selected_index >= 0:
            rect = self.rects[self.selected_index]
            start = rect.topLeft()
            end = rect.bottomRight()
            pos = event.pos()

            if self.resize_corner == 'tl':
                start = pos
            elif self.resize_corner == 'tr':
                start.setY(pos.y())
                end.setX(pos.x())
            elif self.resize_corner == 'bl':
                start.setX(pos.x())
                end.setY(pos.y())
            elif self.resize_corner == 'br':
                end = pos

            new_rect = QRect(start, end).normalized()
            self.rects[self.selected_index] = new_rect
            self.update_display()

        elif self.dragging and self.selected_index >= 0:
            new_pos = event.pos() - self.drag_offset
            self.rects[self.selected_index].moveTopLeft(new_pos)
            self.update_display()

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing = False
        self.resize_corner = None

    def update_display(self):
        if not self.original_pixmap:
            return

        pixmap = QPixmap(self.original_pixmap)
        painter = QPainter(pixmap)
        pen = QPen(QColor(255, 0, 0), 3)
        painter.setPen(pen)

        for i, r in enumerate(self.rects):
            painter.drawRect(r)

            if i == self.selected_index:
                # Draw resize handles on corners (centered)
                hs = self.HANDLE_SIZE
                corners = [r.topLeft(), r.topRight(), r.bottomLeft(), r.bottomRight()]
                for point in corners:
                    handle = QRect(point - QPoint(hs, hs), QSize(hs * 2, hs * 2))
                    painter.fillRect(handle, QColor(255, 0, 0))

        painter.end()
        self.image_label.setPixmap(pixmap)

    def save_annotated_image(self):
        if not self.image_path:
            return

        img = Image.open(self.image_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        for r in self.rects:
            x, y, w, h = r.left(), r.top(), r.width(), r.height()
            for i in range(3):
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
