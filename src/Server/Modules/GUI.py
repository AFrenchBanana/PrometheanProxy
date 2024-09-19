#from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QSplitter


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("C2 Control Node")
        self.setGeometry(100, 100, 800, 600)

        # Create a vertical layout
        layout = QVBoxLayout()

        # Create buttons
        button1 = QPushButton("Button 1")
        button2 = QPushButton("Button 2")
        button3 = QPushButton("Button 3")

        # Add buttons to the layout
        layout.addWidget(button1)
        layout.addWidget(button2)
        layout.addWidget(button3)

        # Create a widget to hold the layout
        button_widget = QWidget()
        button_widget.setLayout(layout)

        # Create a text edit widget for the log
        self.log_text = QTextEdit()

        # Create a splitter to divide the window
        splitter = QSplitter()
        splitter.addWidget(button_widget)
        splitter.addWidget(self.log_text)

        # Set the initial size for the panes
        initial_size1 = int(self.height() * 0.75)
        initial_size2 = int(self.height() * 0.25)
        splitter.setSizes([initial_size1, initial_size2])

        # Set the central widget of the main window
        self.setCentralWidget(splitter)

        # Connect button click events to a slot
        button1.clicked.connect(lambda: self.log("Button 1 clicked"))
        button2.clicked.connect(lambda: self.log("Button 2 clicked"))
        button3.clicked.connect(lambda: self.log("Button 3 clicked"))

    def log(self, message):
        self.log_text.append(f"{message}")

