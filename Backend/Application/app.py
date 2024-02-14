import sys
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QFileDialog, QVideoWidget
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

class VideoPlayerApp(QMainWindow):
    def __init__(self):
        super(VideoPlayerApp, self).__init__()

        self.setWindowTitle("OpenCV Video Stream with PyQt Media Player")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.video_widget = QVideoWidget(self)
        self.video_widget.setMinimumSize(640, 480)  # Set your desired size

        self.media_player = QMediaPlayer(self)
        self.media_player.setVideoOutput(self.video_widget)

        self.play_button = QPushButton("Play", self)
        self.play_button.clicked.connect(self.play_video)

        self.open_button = QPushButton("Open Video", self)
        self.open_button.clicked.connect(self.open_video)

        self.layout = QVBoxLayout(self.central_widget)
        self.layout.addWidget(self.video_widget)
        self.layout.addWidget(self.play_button)
        self.layout.addWidget(self.open_button)

        self.video_capture = None

    def play_video(self):
        if not self.media_player.isAvailable():
            return

        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_button.setText("Play")
        else:
            self.media_player.play()
            self.play_button.setText("Pause")

    def open_video(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mkv *.mov)", options=options)

        if file_name:
            media_content = QMediaContent(QUrl.fromLocalFile(file_name))
            self.media_player.setMedia(media_content)
            self.media_player.play()
            self.play_button.setText("Pause")

    def closeEvent(self, event):
        self.media_player.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoPlayerApp()
    window.show()
    sys.exit(app.exec_())
