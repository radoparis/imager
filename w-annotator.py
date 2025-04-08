import sys
import os
from typing import List
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
    QWidget, QListWidget, QListWidgetItem, QSizePolicy, QComboBox
)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QIcon
from PyQt5.QtCore import Qt, QRect, QPoint, QSize
from PIL import Image, ImageDraw


class Annotator(QWidget):
    HANDLE_SIZE = 6

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Annotator")

        # Left: Image list + sort options
        self.image_list = QListWidget()
        self.image_list.setMinimumWidth(250)
        self.image_list.itemClicked.connect(self.load_selected_image)

        self.sort_selector = QComboBox()
        self.sort_selector.addItems(["Sort by name", "Sort by date"])
        self.sort_selector.currentIndexChanged.connect(self.refresh_file_list)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.sort_selector)
        left_layout.addWidget(self.image_list)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setMinimumWidth(350)

        # Right: Image view + buttons
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.image_label.setMouseTracking(True)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.open_folder_button = QPushButton("📂 Open Folder")
        self.open_folder_button.clicked.connect(self.select_folder)

        self.new_button = QPushButton("➕ New Rectangle")
        self.new_button.clicked.connect(self.add_new_rectangle)

        self.save_button = QPushButton("💾 Save Annotated Image")
        self.save_button.clicked.connect(self.save_annotated_image)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.image_label)
        right_layout.addWidget(self.open_folder_button)
        right_layout.addWidget(self.new_button)
        right_layout.addWidget(self.save_button)

        right_container = QWidget()
        right_container.setLayout(right_layout)

        # Combine left and right into main layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_container, 2)
        self.setLayout(main_layout)

        # State
        self.folder_path = None
        self.image_path = None
        self.original_pixmap = None
        self.rects: List[QRect] = []
        self.selected_index = -1
        self.dragging = False
        self.drag_offset = QPoint()
        self.resizing = False
        self.resize_corner = None

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder:
            self.folder_path = folder
            self.refresh_file_list()

    def refresh_file_list(self):
        if not self.folder_path:
            return

        self.image_list.clear()
        files = [
            f for f in os.listdir(self.folder_path)
            if f.lower().endswith(".jpg")
            and not f.startswith("taged_")
            and not f.startswith("xxx_")
        ]

        sort_by = self.sort_selector.currentText()
        if sort_by == "Sort by date":
            files.sort(key=lambda f: os.path.getmtime(os.path.join(self.folder_path, f)), reverse=True)
        else:
            files.sort()

        for file in files:
            full_path = os.path.join(self.folder_path, file)
            pixmap = QPixmap(full_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon = QIcon(pixmap)
            item = QListWidgetItem(icon, file)
            self.image_list.addItem(item)

        if files:
            self.image_list.setCurrentRow(0)
            self.load_selected_image(self.image_list.item(0))

    def load_selected_image(self, item: QListWidgetItem):
        filename = item.text()
        self.image_path = os.path.join(self.folder_path, filename)
        self.original_pixmap = QPixmap(self.image_path)
        self.image_label.setPixmap(self.original_pixmap)
        self.resize(self.original_pixmap.width(), self.original_pixmap.height() + 100)

        self.rects.clear()
        self.selected_index = -1
        self.dragging = False
        self.resizing = False
        self.update_display()

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

    def get_corner_handles(self, rect: QRect) -> dict:
        hs = self.HANDLE_SIZE
        return {
            'tl': QRect(rect.topLeft() - QPoint(hs, hs), QSize(hs * 2, hs * 2)),
            'tr': QRect(rect.topRight() - QPoint(hs, hs), QSize(hs * 2, hs * 2)),
            'bl': QRect(rect.bottomLeft() - QPoint(hs, hs), QSize(hs * 2, hs * 2)),
            'br': QRect(rect.bottomRight() - QPoint(hs, hs), QSize(hs * 2, hs * 2)),
        }

    def get_resize_corner(self, pos: QPoint, rect: QRect):
        for name, handle_rect in self.get_corner_handles(rect).items():
            if handle_rect.contains(pos):
                return name
        return None

    def mousePressEvent(self, event):
        if not self.original_pixmap:
            return

        pos = self.image_label.mapFromParent(event.pos())
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
        if not self.original_pixmap:
            return

        pos = self.image_label.mapFromParent(event.pos())

        if self.resizing and self.selected_index >= 0:
            rect = self.rects[self.selected_index]
            start = rect.topLeft()
            end = rect.bottomRight()

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
            new_pos = pos - self.drag_offset
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
                for handle_rect in self.get_corner_handles(r).values():
                    painter.fillRect(handle_rect, QColor(255, 0, 0))

        painter.end()
        self.image_label.setPixmap(pixmap)

    def save_annotated_image(self):
        if not self.image_path:
            return

        base_dir = os.path.dirname(self.image_path)
        base_name = os.path.basename(self.image_path)
        name_without_ext, ext = os.path.splitext(base_name)
        save_path = os.path.join(base_dir, f"taged_{name_without_ext}.jpg")

        img = Image.open(self.image_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        for r in self.rects:
            x, y, w, h = r.left(), r.top(), r.width(), r.height()
            for i in range(3):
                draw.rectangle([x - i, y - i, x + w + i, y + h + i], outline="red")

        img.save(save_path, "JPEG")
        print(f"✅ Saved: {save_path}")

        # Rename original
        new_path = os.path.join(base_dir, f"xxx_{name_without_ext}{ext}")
        try:
            os.rename(self.image_path, new_path)
            print(f"🔄 Renamed original to: {new_path}")
        except Exception as e:
            print(f"⚠️ Rename failed: {e}")

        # Clear state
        self.image_path = None
        self.original_pixmap = None
        self.rects.clear()
        self.selected_index = -1

        # Refresh UI
        self.refresh_file_list()

        # Select next image if available
        if self.image_list.count() > 0:
            self.image_list.setCurrentRow(0)
            self.load_selected_image(self.image_list.item(0))
        else:
            blank = QPixmap(400, 200)
            blank.fill(Qt.white)
            painter = QPainter(blank)
            painter.setPen(QColor(0, 150, 0))
            painter.setFont(self.font())
            painter.drawText(blank.rect(), Qt.AlignCenter, "🎉 All images done!")
            painter.end()
            self.image_label.setPixmap(blank)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    annotator = Annotator()
    annotator.show()
    sys.exit(app.exec_())
