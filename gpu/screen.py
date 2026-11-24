try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QFont, QFontMetrics, QPainter
    from PyQt5.QtWidgets import QApplication, QWidget
    AVAILABLE = True
except ImportError:
    AVAILABLE = False
    QWidget = object


BASIC = [
    (0, 0, 0), (170, 0, 0), (0, 170, 0), (170, 85, 0),
    (0, 0, 170), (170, 0, 170), (0, 170, 170), (170, 170, 170),
    (85, 85, 85), (255, 85, 85), (85, 255, 85), (255, 255, 85),
    (85, 85, 255), (255, 85, 255), (85, 255, 255), (255, 255, 255),
]
CUBE = [0, 95, 135, 175, 215, 255]


def rgb(col: int):
    # AI generated. do not touch
    """an ansi 256 colour number as r, g, b. same numbers as on the console"""
    col = int(col) % 256
    if col < 16:
        return BASIC[col]
    if col > 231:
        grey = 8 + (col - 232) * 10
        return (grey, grey, grey)
    col -= 16
    return (CUBE[col // 36], CUBE[col % 36 // 6], CUBE[col % 6])


class Screen(QWidget):
    def __init__(self, x: int, y: int, point_size: int = 14, title: str = "CASM"):
        super().__init__()
        self.cols = x
        self.rows = y
        self.rendered: list[list[list[str, int]]] = []
        self.held: set[str] = set() # every key that is down right now
        self.closed = False

        self.font = QFont("Consolas") # mayybe somthing else
        self.font.setStyleHint(QFont.Monospace)
        self.font.setPointSize(point_size)
        metrics = QFontMetrics(self.font)
        self.cell_x = metrics.horizontalAdvance("W")
        self.cell_y = metrics.height()
        self.baseline = metrics.ascent()

        self.setWindowTitle(title)
        self.setFixedSize(self.cols * self.cell_x, self.rows * self.cell_y)
        self.setFocusPolicy(Qt.StrongFocus)
        self.show()
        self.activateWindow()
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        painter.setFont(self.font)
        for y, row in enumerate(self.rendered):
            for x, cell in enumerate(row):
                glyph, col = cell
                if not glyph or glyph == " ":
                    continue
                painter.setPen(QColor(*rgb(col if col else 7)))
                painter.drawText(x * self.cell_x, y * self.cell_y + self.baseline, glyph)
        painter.end()

    def keyPressEvent(self, event):
        key = event.text().lower()
        if key and key.isprintable():
            self.held.add(key)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.text().lower()
        if key:
            self.held.discard(key)

    def focusOutEvent(self, event):
        self.held.clear()

    def closeEvent(self, event):
        self.closed = True
        event.accept()

    def pressed(self, character: str):
        return character in self.held

    def draw(self, rendered: list):
        self.rendered = rendered
        self.update()
        self.pump()
        return True

    def clear(self):
        self.rendered = []
        self.update()
        self.pump()
        return True

    def pump(self):
        QApplication.processEvents()
        return True


APP = None
SCREEN = None


def start(x: int, y: int, title: str = "CASM"):
    """one window. a second create() only resizes it"""
    global APP, SCREEN
    if not AVAILABLE:
        return None
    if APP is None:
        APP = QApplication.instance() or QApplication([])
    if SCREEN is None or SCREEN.closed:
        SCREEN = Screen(x, y, title=title)
        return SCREEN
    SCREEN.cols = x
    SCREEN.rows = y
    SCREEN.setFixedSize(x * SCREEN.cell_x, y * SCREEN.cell_y)
    return SCREEN


def current():
    if SCREEN is None or SCREEN.closed:
        return None
    return SCREEN


def pressed(character: str):
    """True, False, or None when there is no window to ask"""
    window = current()
    if window is None:
        return None
    window.pump()
    return window.pressed(character)


def pump():
    window = current()
    if window is None:
        return False
    return window.pump()


def hold():
    """keep the window open after the cpu stopped, until it is closed"""
    window = current()
    if window is None:
        return False
    window.setWindowTitle(window.windowTitle() + " - halted")
    APP.exec_()
    return True
