"""GUI application for the Image → Python Code Converter.

This provides a modern desktop interface (using PyQt5) around the logic in
`image_to_python_sketch.py`, letting users:

- Select an image file
- Choose mode: sketch (black-and-white edges) or color pixels
- Adjust max size / detail
- Generate Python code that draws the image with matplotlib
- Preview the generated code
- Save the result to a `.py` file

It also includes a simple image ↔ PNG icon converter using Pillow.

Requirements (install via pip):

    pip install PyQt5 pillow numpy matplotlib

Run with:

    python gui_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

# Reuse the existing image processing + code-generation logic
import image_to_python_sketch as converter


class CodeHighlighter(QtGui.QSyntaxHighlighter):
    """Simple Python syntax highlighter for the code display box.

    This is intentionally lightweight – just highlights comments, strings,
    keywords, and numbers for a more professional feel.
    """

    KEYWORDS = {
        "import",
        "from",
        "def",
        "return",
        "if",
        "elif",
        "else",
        "for",
        "while",
        "in",
        "as",
        "with",
        "True",
        "False",
        "None",
    }

    def __init__(self, document: QtGui.QTextDocument) -> None:
        super().__init__(document)

        self._comment_format = QtGui.QTextCharFormat()
        self._comment_format.setForeground(QtGui.QColor("#6b7280"))
        self._comment_format.setFontItalic(True)

        self._keyword_format = QtGui.QTextCharFormat()
        self._keyword_format.setForeground(QtGui.QColor("#22d3ee"))
        self._keyword_format.setFontWeight(QtGui.QFont.DemiBold)

        self._string_format = QtGui.QTextCharFormat()
        self._string_format.setForeground(QtGui.QColor("#a5b4fc"))

        self._number_format = QtGui.QTextCharFormat()
        self._number_format.setForeground(QtGui.QColor("#facc15"))

    def highlightBlock(self, text: str) -> None:  # type: ignore[override]
        # Comments
        if "#" in text:
            idx = text.find("#")
            self.setFormat(idx, len(text) - idx, self._comment_format)

        # Strings (very naive – single and double quotes)
        in_single = False
        in_double = False
        start_idx = 0
        for i, ch in enumerate(text):
            if ch == "'" and not in_double:
                if in_single:
                    self.setFormat(start_idx, i - start_idx + 1, self._string_format)
                    in_single = False
                else:
                    in_single = True
                    start_idx = i
            elif ch == '"' and not in_single:
                if in_double:
                    self.setFormat(start_idx, i - start_idx + 1, self._string_format)
                    in_double = False
                else:
                    in_double = True
                    start_idx = i

        # Keywords and numbers – split by whitespace and punctuation
        import re

        for match in re.finditer(r"\b[\w_]+\b", text):
            word = match.group(0)
            if word in self.KEYWORDS:
                self.setFormat(match.start(), len(word), self._keyword_format)
            elif word.isdigit():
                self.setFormat(match.start(), len(word), self._number_format)


class IconConverter:
    """Image ↔ PNG icon conversions using Pillow.

    This mirrors the basic behaviour from the web UI: convert any image or .ico
    into a square PNG that can be used as an icon / favicon.
    """

    def __init__(self, size: int = 256) -> None:
        self.size = size

    def image_to_png_icon(self, src: Path, dst: Path) -> None:
        from PIL import Image

        img = Image.open(src).convert("RGBA")
        img.thumbnail((self.size, self.size))
        # Center onto square canvas
        canvas = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
        x = (self.size - img.width) // 2
        y = (self.size - img.height) // 2
        canvas.paste(img, (x, y), img)
        canvas.save(dst, format="PNG")

    def icon_to_png(self, src: Path, dst: Path) -> None:
        from PIL import Image

        img = Image.open(src).convert("RGBA")
        img.save(dst, format="PNG")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image → Python Code Converter – Desktop Edition")
        self.setMinimumSize(1100, 650)
        self._current_image: Optional[Path] = None
        self._current_code: str = ""

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        root_layout = QtWidgets.QHBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        # Left column: controls
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setSpacing(12)

        header = self._build_header()
        left_layout.addWidget(header)

        image_panel = self._build_image_panel()
        left_layout.addWidget(image_panel)

        icon_panel = self._build_icon_panel()
        left_layout.addWidget(icon_panel)

        left_layout.addStretch(1)

        # Right column: code display
        code_panel = self._build_code_panel()

        root_layout.addWidget(left, stretch=1)
        root_layout.addWidget(code_panel, stretch=1)

        self._apply_dark_palette()

    def _build_header(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        logo_label = QtWidgets.QLabel()
        logo_label.setFixedSize(40, 40)
        logo_path = Path("logo.png")
        if logo_path.is_file():
            pix = QtGui.QPixmap(str(logo_path))
            logo_label.setPixmap(pix.scaled(40, 40, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        logo_label.setStyleSheet(
            "border-radius:20px; border:1px solid #1f2937;"
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #22c55e, stop:1 #22d3ee);"
        )

        title_box = QtWidgets.QWidget()
        t_layout = QtWidgets.QVBoxLayout(title_box)
        t_layout.setContentsMargins(0, 0, 0, 0)

        title = QtWidgets.QLabel("Image → Python Code Converter")
        title_font = QtGui.QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)

        subtitle = QtWidgets.QLabel(
            "Turn any image into a ready‑to‑run matplotlib sketch or color mosaic script."
        )
        subtitle.setStyleSheet("color:#9ca3af; font-size:11px;")

        t_layout.addWidget(title)
        t_layout.addWidget(subtitle)

        layout.addWidget(logo_label)
        layout.addWidget(title_box, 1)

        return w

    def _build_image_panel(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Image → Python generator")
        box.setStyleSheet("QGroupBox{font-weight:bold; border:1px solid #1f2937; border-radius:8px; margin-top:8px;}"
                          "QGroupBox::title{subcontrol-origin:margin; left:10px; padding:0 4px;}" )
        layout = QtWidgets.QVBoxLayout(box)
        layout.setSpacing(8)

        # Image file selection
        file_row = QtWidgets.QHBoxLayout()
        self.image_path_edit = QtWidgets.QLineEdit()
        self.image_path_edit.setPlaceholderText("Choose an image (PNG, JPG, WEBP…) or leave empty to use latest in folder")
        browse_btn = QtWidgets.QPushButton("Browse…")
        browse_btn.clicked.connect(self.browse_image)
        file_row.addWidget(self.image_path_edit, 1)
        file_row.addWidget(browse_btn)

        layout.addWidget(QtWidgets.QLabel("Source image"))
        layout.addLayout(file_row)

        # Mode selection
        mode_label = QtWidgets.QLabel("Output mode")
        mode_label.setStyleSheet("color:#9ca3af; font-size:11px;")

        self.mode_sketch = QtWidgets.QRadioButton("Python sketch (black & white edges)")
        self.mode_color = QtWidgets.QRadioButton("Python color pixels (mosaic)")
        self.mode_sketch.setChecked(True)

        mode_col = QtWidgets.QVBoxLayout()
        mode_col.addWidget(self.mode_sketch)
        mode_col.addWidget(self.mode_color)

        mode_row = QtWidgets.QHBoxLayout()
        mode_row.addLayout(mode_col)

        layout.addWidget(mode_label)
        layout.addLayout(mode_row)

        # Max size
        size_row = QtWidgets.QHBoxLayout()
        size_label = QtWidgets.QLabel("Max size (longest side, pixels)")
        self.max_size_spin = QtWidgets.QSpinBox()
        self.max_size_spin.setRange(32, 512)
        self.max_size_spin.setValue(160)
        self.max_size_spin.setToolTip("Higher = more detail and more Python code")
        size_row.addWidget(size_label)
        size_row.addStretch(1)
        size_row.addWidget(self.max_size_spin)

        layout.addLayout(size_row)

        hint = QtWidgets.QLabel("Higher size gives a more detailed image but generates a larger .py file.")
        hint.setStyleSheet("color:#6b7280; font-size:10px;")
        layout.addWidget(hint)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        self.generate_btn = QtWidgets.QPushButton("Generate Python code")
        self.generate_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.generate_btn.clicked.connect(self.generate_code)

        self.save_btn = QtWidgets.QPushButton("Save .py…")
        self.save_btn.setEnabled(False)
        self.save_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton))
        self.save_btn.clicked.connect(self.save_code)

        self.preview_btn = QtWidgets.QPushButton("Run preview")
        self.preview_btn.setEnabled(False)
        self.preview_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        self.preview_btn.clicked.connect(self.preview_code)

        btn_row.addWidget(self.generate_btn)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.preview_btn)
        btn_row.addStretch(1)

        layout.addLayout(btn_row)

        # Status label
        self.status_label = QtWidgets.QLabel()
        self.status_label.setStyleSheet("color:#9ca3af; font-size:10px;")
        layout.addWidget(self.status_label)

        return box

    def _build_icon_panel(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Icon & favicon helper")
        box.setStyleSheet("QGroupBox{font-weight:bold; border:1px solid #1f2937; border-radius:8px; margin-top:8px;}"
                          "QGroupBox::title{subcontrol-origin:margin; left:10px; padding:0 4px;}" )
        layout = QtWidgets.QVBoxLayout(box)
        layout.setSpacing(8)

        mode_row = QtWidgets.QHBoxLayout()
        self.icon_mode_combo = QtWidgets.QComboBox()
        self.icon_mode_combo.addItem("Image → PNG icon", "img_to_icon")
        self.icon_mode_combo.addItem("ICO → PNG image", "icon_to_img")
        mode_row.addWidget(QtWidgets.QLabel("Conversion mode"))
        mode_row.addStretch(1)
        mode_row.addWidget(self.icon_mode_combo)

        layout.addLayout(mode_row)

        file_row = QtWidgets.QHBoxLayout()
        self.icon_path_edit = QtWidgets.QLineEdit()
        self.icon_path_edit.setPlaceholderText("Select an image or .ico file")
        browse_btn = QtWidgets.QPushButton("Browse…")
        browse_btn.clicked.connect(self.browse_icon)
        file_row.addWidget(self.icon_path_edit, 1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        size_row = QtWidgets.QHBoxLayout()
        self.icon_size_spin = QtWidgets.QSpinBox()
        self.icon_size_spin.setRange(16, 512)
        self.icon_size_spin.setValue(256)
        size_row.addWidget(QtWidgets.QLabel("Icon size (for image → icon)"))
        size_row.addStretch(1)
        size_row.addWidget(self.icon_size_spin)
        layout.addLayout(size_row)

        btn_row = QtWidgets.QHBoxLayout()
        self.icon_convert_btn = QtWidgets.QPushButton("Convert")
        self.icon_convert_btn.clicked.connect(self.convert_icon)
        btn_row.addWidget(self.icon_convert_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.icon_status_label = QtWidgets.QLabel()
        self.icon_status_label.setStyleSheet("color:#9ca3af; font-size:10px;")
        layout.addWidget(self.icon_status_label)

        return box

    def _build_code_panel(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Generated Python code")
        box.setStyleSheet("QGroupBox{font-weight:bold; border:1px solid #1f2937; border-radius:8px; margin-top:8px;}"
                          "QGroupBox::title{subcontrol-origin:margin; left:10px; padding:0 4px;}" )
        layout = QtWidgets.QVBoxLayout(box)

        self.code_edit = QtWidgets.QPlainTextEdit()
        self.code_edit.setReadOnly(True)
        self.code_edit.setPlaceholderText("Your generated Python code will appear here…")
        font = QtGui.QFont("Consolas")
        font.setStyleHint(QtGui.QFont.Monospace)
        font.setPointSize(10)
        self.code_edit.setFont(font)
        self.code_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)

        CodeHighlighter(self.code_edit.document())

        layout.addWidget(self.code_edit)

        # Small footer hint
        hint = QtWidgets.QLabel(
            "Tip: Save the script as .py and run it with `python your_file.py` after installing matplotlib."
        )
        hint.setStyleSheet("color:#6b7280; font-size:10px;")
        layout.addWidget(hint)

        return box

    def _apply_dark_palette(self) -> None:
        """Apply a Tailwind-ish dark theme palette for a professional look."""
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor("#020617"))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor("#020617"))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#0f172a"))
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor("#e5e7eb"))
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#e5e7eb"))
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor("#111827"))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor("#e5e7eb"))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor("#22d3ee"))
        palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#022c22"))
        self.setPalette(palette)

        # Buttons – gradient primary look
        self.setStyleSheet(
            "QWidget{background-color:#020617; color:#e5e7eb;}"
            "QPushButton{background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            " stop:0 #22c55e, stop:1 #22d3ee);"
            " color:#022c22; border-radius:999px; padding:6px 14px; font-weight:600;}"
            "QPushButton:disabled{background:#1f2937; color:#6b7280;}"
            "QLineEdit, QSpinBox, QComboBox{background:#020617; border:1px solid #374151;"
            " border-radius:6px; padding:4px 6px;}"
        )

    # ------------------------------------------------------------------
    # Slots / actions
    # ------------------------------------------------------------------
    def browse_image(self) -> None:
        here = str(Path(".").resolve())
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select image",
            here,
            "Image files (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff);;All files (*.*)",
        )
        if file_path:
            self.image_path_edit.setText(file_path)
            self._current_image = Path(file_path)

    def generate_code(self) -> None:
        # Determine image path
        text = self.image_path_edit.text().strip()
        if text:
            img_path = Path(text)
        else:
            # Use the same strategy as the CLI: latest image in current folder
            img_path = converter.find_latest_image(Path("."))

        if not img_path.is_file():
            QtWidgets.QMessageBox.warning(self, "Image not found", f"Cannot find image: {img_path}")
            return

        self._current_image = img_path

        max_size = int(self.max_size_spin.value())
        mode = "sketch" if self.mode_sketch.isChecked() else "color"

        self.status_label.setText("Processing image…")
        self.status_label.repaint()
        QtWidgets.QApplication.processEvents()

        try:
            if mode == "sketch":
                (w, h), points = converter.image_to_points_sketch(str(img_path), max_size=max_size)
                code = converter.generate_python_code_sketch(w, h, points)
                self.status_label.setText(f"Generated sketch code with {len(points)} edge points.")
            else:
                # color: use same logic as CLI – default smaller size if user keeps 160
                size = max_size if max_size != 160 else 80
                (w, h), points = converter.image_to_points_color(str(img_path), max_size=size)
                code = converter.generate_python_code_color(w, h, points)
                self.status_label.setText(f"Generated color code with {len(points)} pixels.")

            self._current_code = code
            self.code_edit.setPlainText(code)
            self.save_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)

        except Exception as exc:  # pragma: no cover - UI error path
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to generate code:\n{exc}")
            self.status_label.setText("Generation failed.")

    def save_code(self) -> None:
        if not self._current_code:
            return

        default_name = "image_code.py"
        if self._current_image is not None:
            base = self._current_image.stem or "image_code"
            default_name = f"{base}.py"

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Python file",
            default_name,
            "Python files (*.py);;All files (*.*)",
        )
        if not file_path:
            return

        try:
            Path(file_path).write_text(self._current_code, encoding="utf-8")
            self.status_label.setText(f"Saved: {file_path}")
        except Exception as exc:  # pragma: no cover - UI error path
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save file:\n{exc}")

    def preview_code(self) -> None:
        """Run the generated code in-memory using runpy, similar to the CLI.

        This will open a matplotlib window if the environment allows.
        """
        import tempfile
        import runpy

        if not self._current_code:
            return

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir) / "preview.py"
                tmp_path.write_text(self._current_code, encoding="utf-8")
                runpy.run_path(str(tmp_path))
        except Exception as exc:  # pragma: no cover - UI error path
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to run preview:\n{exc}")

    def browse_icon(self) -> None:
        here = str(Path(".").resolve())
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select image or icon",
            here,
            "Image or icon (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.ico *.tif *.tiff);;All files (*.*)",
        )
        if file_path:
            self.icon_path_edit.setText(file_path)

    def convert_icon(self) -> None:
        src_text = self.icon_path_edit.text().strip()
        if not src_text:
            QtWidgets.QMessageBox.warning(self, "No file", "Please select an image or .ico file first.")
            return

        src = Path(src_text)
        if not src.is_file():
            QtWidgets.QMessageBox.warning(self, "File not found", f"Cannot find file: {src}")
            return

        mode = self.icon_mode_combo.currentData()
        size = int(self.icon_size_spin.value())

        if mode == "img_to_icon":
            default_name = f"{src.stem}-icon.png"
        else:
            default_name = f"{src.stem}-from-icon.png"

        dst_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save PNG",
            default_name,
            "PNG image (*.png);;All files (*.*)",
        )
        if not dst_path:
            return

        converter_obj = IconConverter(size=size)

        try:
            if mode == "img_to_icon":
                converter_obj.image_to_png_icon(src, Path(dst_path))
                self.icon_status_label.setText("Saved PNG icon.")
            else:
                converter_obj.icon_to_png(src, Path(dst_path))
                self.icon_status_label.setText("Saved PNG image from icon.")
        except Exception as exc:  # pragma: no cover - UI error path
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to convert icon/image:\n{exc}")
            self.icon_status_label.setText("Conversion failed.")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Image → Python Code Converter")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

