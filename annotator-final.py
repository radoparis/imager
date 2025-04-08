import sys
import os
from typing import List
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
    QWidget, QListWidget, QListWidgetItem, QSizePolicy, QComboBox, QSplitter,
    QGroupBox, QSpinBox, QFormLayout, QShortcut
)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QIcon, QKeySequence
from PyQt5.QtCore import Qt, QRect, QPoint, QSize
from PIL import Image, ImageDraw


class ImageLabel(QLabel):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        self.parent.image_mouse_press(event)

    def mouseMoveEvent(self, event):
        self.parent.image_mouse_move(event)

    def mouseReleaseEvent(self, event):
        self.parent.image_mouse_release(event)


class Annotator(QWidget):
    HANDLE_SIZE = 6

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Annotator")
        self.default_rect_height = 150

        # Image label
        self.image_label = ImageLabel(self)
        self.image_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Image lists (left)
        self.image_list = QListWidget()
        self.image_list.setMinimumWidth(250)
        self.image_list.itemClicked.connect(self.load_selected_image)

        self.taged_list = QListWidget()
        self.xxx_list = QListWidget()
        self.taged_list.itemClicked.connect(self.load_processed_image)
        self.xxx_list.itemClicked.connect(self.load_processed_image)

        self.sort_selector = QComboBox()
        self.sort_selector.addItems(["Sort by name", "Sort by date"])
        self.sort_selector.currentIndexChanged.connect(self.refresh_file_lists)

        top_group = QGroupBox("🟡 To Annotate")
        top_layout = QVBoxLayout()
        top_layout.addWidget(self.sort_selector)
        top_layout.addWidget(self.image_list)
        top_group.setLayout(top_layout)

        bottom_group = QGroupBox("📁 Processed")
        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(QLabel("🟢 Tagged"))
        bottom_layout.addWidget(self.taged_list)
        bottom_layout.addWidget(QLabel("❌ Renamed Originals"))
        bottom_layout.addWidget(self.xxx_list)
        bottom_group.setLayout(bottom_layout)

        left_splitter = QSplitter(Qt.Vertical)
        left_splitter.addWidget(top_group)
        left_splitter.addWidget(bottom_group)
        left_splitter.setSizes([300, 200])

        # Buttons + input
        self.open_folder_button = QPushButton("📂 Open Folder")
        self.open_folder_button.clicked.connect(self.select_folder)

        self.new_button = QPushButton("➕ New Rectangle (Ctrl+N / Ctrl+A)")
        self.new_button.clicked.connect(self.add_new_rectangle)

        self.save_button = QPushButton("💾 Save (Ctrl+S)")
        self.save_button.clicked.connect(self.save_annotated_image)

        self.copy_button = QPushButton("📋 Copy to Clipboard (Ctrl+C)")
        self.copy_button.clicked.connect(self.copy_to_clipboard)

        self.height_input = QSpinBox()
        self.height_input.setRange(10, 1000)
        self.height_input.setValue(self.default_rect_height)
        self.height_input.setSuffix(" px")

        form = QFormLayout()
        form.addRow("📏 Rectangle Height:", self.height_input)

        controls_layout = QVBoxLayout()
        controls_layout.addWidget(self.open_folder_button)
        controls_layout.addWidget(self.new_button)
        controls_layout.addWidget(self.save_button)
        controls_layout.addWidget(self.copy_button)
        controls_layout.addLayout(form)
        controls_layout.addStretch()

        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)
        controls_widget.setFixedWidth(220)

        right_split = QHBoxLayout()
        right_split.addWidget(self.image_label, 3)
        right_split.addWidget(controls_widget)

        right_container = QWidget()
        right_container.setLayout(right_split)

        main_layout = QHBoxLayout()
        main_layout.addWidget(left_splitter, 1)
        main_layout.addWidget(right_container, 2)
        self.setLayout(main_layout)

        # Keyboard Shortcuts
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.add_new_rectangle)
        QShortcut(QKeySequence("Ctrl+A"), self).activated.connect(self.add_new_rectangle)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_annotated_image)
        QShortcut(QKeySequence("Ctrl+C"), self).activated.connect(self.copy_to_clipboard)

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
            self.refresh_file_lists()

    def refresh_file_lists(self):
        if not self.folder_path:
            return

        self.image_list.clear()
        self.taged_list.clear()
        self.xxx_list.clear()

        files = [f for f in os.listdir(self.folder_path) if f.lower().endswith(".jpg")]
        sort_by = self.sort_selector.currentText()
        key_func = (
            (lambda f: os.path.getmtime(os.path.join(self.folder_path, f)))
            if sort_by == "Sort by date"
            else (lambda f: f.lower())
        )

        to_annotate = sorted([f for f in files if not f.startswith("taged_") and not f.startswith("xxx_")], key=key_func, reverse=sort_by == "Sort by date")
        taged = sorted([f for f in files if f.startswith("taged_")], key=key_func, reverse=sort_by == "Sort by date")
        xxx = sorted([f for f in files if f.startswith("xxx_")], key=key_func, reverse=sort_by == "Sort by date")

        for f in to_annotate:
            path = os.path.join(self.folder_path, f)
            icon = QIcon(QPixmap(path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.image_list.addItem(QListWidgetItem(icon, f))

        for f in taged:
            self.taged_list.addItem(f)
        for f in xxx:
            self.xxx_list.addItem(f)

        if to_annotate:
            self.image_list.setCurrentRow(0)
            self.load_selected_image(self.image_list.item(0))

    def load_selected_image(self, item: QListWidgetItem):
        self.image_path = os.path.join(self.folder_path, item.text())
        self.original_pixmap = QPixmap(self.image_path)
        self.image_label.setPixmap(self.original_pixmap)
        self.image_label.setFixedSize(self.original_pixmap.size())
        self.rects.clear()
        self.selected_index = -1
        self.update_display()

    def load_processed_image(self, item: QListWidgetItem):
        self.image_path = os.path.join(self.folder_path, item.text())
        self.original_pixmap = QPixmap(self.image_path)
        self.image_label.setPixmap(self.original_pixmap)
        self.image_label.setFixedSize(self.original_pixmap.size())
        self.rects.clear()
        self.selected_index = -1
        self.update_display()

    def add_new_rectangle(self):
        if not self.original_pixmap:
            return
        img_w, img_h = self.original_pixmap.width(), self.original_pixmap.height()
        w = int(img_w * 0.9)
        h = min(self.height_input.value(), img_h - 20)
        x = (img_w - w) // 2
        y = (img_h - h) // 2
        self.rects.append(QRect(QPoint(x, y), QSize(w, h)))
        self.selected_index = len(self.rects) - 1
        self.update_display()

    def get_corner_handles(self, rect: QRect):
        hs = self.HANDLE_SIZE
        return {
            'tl': QRect(rect.topLeft() - QPoint(hs, hs), QSize(hs * 2, hs * 2)),
            'tr': QRect(rect.topRight() - QPoint(hs, hs), QSize(hs * 2, hs * 2)),
            'bl': QRect(rect.bottomLeft() - QPoint(hs, hs), QSize(hs * 2, hs * 2)),
            'br': QRect(rect.bottomRight() - QPoint(hs, hs), QSize(hs * 2, hs * 2)),
        }

    def get_resize_corner(self, pos, rect):
        for name, handle in self.get_corner_handles(rect).items():
            if handle.contains(pos):
                return name
        return None

    def image_mouse_press(self, event):
        pos = event.pos()
        self.selected_index = -1
        for i, r in enumerate(reversed(self.rects)):
            idx = len(self.rects) - 1 - i
            corner = self.get_resize_corner(pos, r)
            if corner:
                self.selected_index = idx
                self.resizing = True
                self.resize_corner = corner
                return
            elif r.contains(pos):
                self.selected_index = idx
                self.dragging = True
                self.drag_offset = pos - r.topLeft()
                return
        self.update_display()

    def image_mouse_move(self, event):
        pos = event.pos()
        if self.resizing and self.selected_index >= 0:
            r = self.rects[self.selected_index]
            start, end = r.topLeft(), r.bottomRight()
            if self.resize_corner == 'tl': start = pos
            elif self.resize_corner == 'tr': start.setY(pos.y()); end.setX(pos.x())
            elif self.resize_corner == 'bl': start.setX(pos.x()); end.setY(pos.y())
            elif self.resize_corner == 'br': end = pos
            self.rects[self.selected_index] = QRect(start, end).normalized()
        elif self.dragging and self.selected_index >= 0:
            new_pos = pos - self.drag_offset
            self.rects[self.selected_index].moveTopLeft(new_pos)
        self.update_display()

    def image_mouse_release(self, event):
        self.dragging = False
        self.resizing = False
        self.resize_corner = None

    def update_display(self):
        if not self.original_pixmap: return
        pixmap = QPixmap(self.original_pixmap)
        painter = QPainter(pixmap)
        pen = QPen(QColor(255, 0, 0), 3)
        painter.setPen(pen)
        for i, r in enumerate(self.rects):
            painter.drawRect(r)
            if i == self.selected_index:
                for h in self.get_corner_handles(r).values():
                    painter.fillRect(h, QColor(255, 0, 0))
        painter.end()
        self.image_label.setPixmap(pixmap)

    def save_annotated_image(self):
        if not self.image_path:
            return
        base_dir = os.path.dirname(self.image_path)
        base_name = os.path.basename(self.image_path)
        name, ext = os.path.splitext(base_name)
        save_path = os.path.join(base_dir, f"taged_{name}.jpg")

        img = Image.open(self.image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        for r in self.rects:
            x, y, w, h = r.left(), r.top(), r.width(), r.height()
            for i in range(3):
                draw.rectangle([x-i, y-i, x+w+i, y+h+i], outline="red")
        img.save(save_path, "JPEG")
        os.rename(self.image_path, os.path.join(base_dir, f"xxx_{name}{ext}"))
        self.copy_to_clipboard()
        self.image_path = None
        self.original_pixmap = None
        self.rects.clear()
        self.selected_index = -1
        self.refresh_file_lists()
        if self.image_list.count() > 0:
            self.image_list.setCurrentRow(0)
            self.load_selected_image(self.image_list.item(0))
        else:
            pixmap = QPixmap(400, 200)
            pixmap.fill(Qt.white)
            p = QPainter(pixmap)
            p.setPen(QColor(0, 150, 0))
            p.setFont(self.font())
            p.drawText(pixmap.rect(), Qt.AlignCenter, "🎉 All images done!")
            p.end()
            self.image_label.setPixmap(pixmap)

    def copy_to_clipboard(self):
        if not self.original_pixmap:
            return
        pixmap = QPixmap(self.original_pixmap)
        painter = QPainter(pixmap)
        pen = QPen(QColor(255, 0, 0), 3)
        painter.setPen(pen)
        for i, r in enumerate(self.rects):
            painter.drawRect(r)
            if i == self.selected_index:
                for h in self.get_corner_handles(r).values():
                    painter.fillRect(h, QColor(255, 0, 0))
        painter.end()
        QApplication.clipboard().setPixmap(pixmap)
        print("📋 Copied image to clipboard!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Annotator()
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec_())
