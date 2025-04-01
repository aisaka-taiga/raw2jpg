import sys
import os
import rawpy
import imageio
import threading
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QStyleFactory, QProgressBar
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt, QThread, Signal
import qt_material

SUPPORTED_FORMATS = (".crw", ".cr2", ".cr3", ".arw", ".raf", ".dng", ".rw2", ".nef", ".nrw")

class ConvertThread(QThread):
    progress = Signal(int, int)  # 현재 진행 상황 업데이트 (완료된 개수, 총 개수)
    completed = Signal()
    
    def __init__(self, files, output_folder):
        super().__init__()
        self.files = files
        self.output_folder = output_folder
    
    def run(self):
        total_files = len(self.files)
        for i, file_path in enumerate(self.files, 1):
            extract_thumbnail(file_path, self.output_folder)
            self.progress.emit(i, total_files)
        self.completed.emit()

def convert_raw_to_jpg(file_path, output_folder):
    output_path = os.path.join(output_folder, os.path.basename(file_path).replace(os.path.splitext(file_path)[1], ".jpg"))
    
    if os.path.exists(output_path):
        print(f"Skipped {file_path} (already converted)")
        return
    
    with rawpy.imread(file_path) as raw:
        rgb = raw.postprocess()
        imageio.imwrite(output_path, rgb)
        print(f"Converted {file_path} -> {output_path}")

def extract_thumbnail(file_path, output_folder):
    try:
        with rawpy.imread(file_path) as raw:
            thumb = raw.extract_thumb()
            thumb_path = os.path.join(output_folder, os.path.basename(file_path).replace(os.path.splitext(file_path)[1], "_thumb.jpg"))
            
            if thumb.format == rawpy.ThumbFormat.JPEG:
                with open(thumb_path, 'wb') as f:
                    f.write(thumb.data)
            elif thumb.format == rawpy.ThumbFormat.BITMAP:
                imageio.imwrite(thumb_path, thumb.data)
            print(f"Extracted thumbnail: {thumb_path}")
    except (rawpy.LibRawNoThumbnailError, rawpy.LibRawUnsupportedThumbnailError):
        print(f"No valid thumbnail found for {file_path}, converting full image instead.")
        convert_raw_to_jpg(file_path, output_folder)

class RAWConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        self.label = QLabel("폴더를 선택하거나 RAW 파일을 끌어다 놓으세요.")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        
        self.progress_label = QLabel("")  # 진행 상태 표시용
        self.progress_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_bar)
        
        self.button = QPushButton("폴더 선택")
        self.button.clicked.connect(self.choose_folder)
        layout.addWidget(self.button)
        
        self.setAcceptDrops(True)
        self.setLayout(layout)
        self.setWindowTitle("RAW to JPG 변환기")
        self.setGeometry(100, 100, 400, 200)
        qt_material.apply_stylesheet(self, theme='dark_teal.xml')
    
    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder:
            self.label.setText(f"선택한 폴더: {folder}")
            self.convert_folder(folder)
    
    def convert_folder(self, folder):
        output_folder = os.path.join(folder, "converted")
        os.makedirs(output_folder, exist_ok=True)
        
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(SUPPORTED_FORMATS)]
        
        if files:
            self.progress_bar.setMaximum(len(files))
            self.thread = ConvertThread(files, output_folder)
            self.thread.progress.connect(self.update_progress)
            self.thread.completed.connect(self.complete_progress)
            self.thread.start()
    
    def update_progress(self, current, total):
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"변환 진행 중: {current}/{total}")
    
    def complete_progress(self):
        self.progress_label.setText("변환 완료")
        self.progress_bar.setValue(self.progress_bar.maximum())
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        output_folder = os.path.join(os.getcwd(), "converted")
        os.makedirs(output_folder, exist_ok=True)
        
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self.convert_folder(path)
                return
            elif path.lower().endswith(SUPPORTED_FORMATS):
                files.append(path)
        
        if files:
            self.progress_bar.setMaximum(len(files))
            self.thread = ConvertThread(files, output_folder)
            self.thread.progress.connect(self.update_progress)
            self.thread.completed.connect(self.complete_progress)
            self.thread.start()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setStyle(QStyleFactory.create("Fusion"))
    window = RAWConverterApp()
    window.show()
    sys.exit(app.exec())