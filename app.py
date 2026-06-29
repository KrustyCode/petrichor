"""
Petrichor — PyQt6 UI for the ambient soundscape engine.
  > pip install PyQt6
"""

import sys
from config import PRESETS
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSlider, QScrollArea, QFrame,
)



# Param (layer) list, derived from the presets so they stay in sync.
PARAMS = list(next(iter(PRESETS.values())).keys())

# Palette

BG       = "#0b1d26"
PANEL    = "#11283"
MIST     = "#9fc4c0"
AMBER    = "#e8a33d"
INK      = "#eef3f1"
INK_DIM  = "#b9cdc9"


# stylesheet for widgets and objects
STYLESHEET = f"""
QWidget {{
    background: {BG};
    color: {INK};
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size: 13px;
}}
#Title {{
    font-size: 30px;
    color: {INK};
    font-style: italic;
}}
#Subtitle {{
    color: {INK_DIM};
    font-size: 11px;
    letter-spacing: 2px;
}}
QPushButton#Preset {{
    background: rgba(159,196,192,0.06);
    border: 1px solid rgba(159,196,192,0.20);
    color: {INK_DIM};
    border-radius: 14px;
    padding: 7px 10px;
}}
QPushButton#Preset:hover {{ border-color: {AMBER}; color: {INK}; }}
QPushButton#Preset[active="true"] {{
    background: rgba(232,163,61,0.14);
    border: 1px solid {AMBER};
    color: {AMBER};
}}
QPushButton#Play {{
    background: rgba(159,196,192,0.08);
    border: 1.5px solid {MIST};
    border-radius: 26px;
    color: {INK};
    font-size: 18px;
}}
QPushButton#Play:hover {{ background: rgba(159,196,192,0.18); }}
QLabel#ParamName {{ color: {INK}; }}
QLabel#ParamVal  {{ color: {AMBER}; }}
QSlider::groove:horizontal {{
    height: 3px; background: rgba(159,196,192,0.25); border-radius: 2px;
}}
QSlider::sub-page:horizontal {{ background: {MIST}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 14px; height: 14px; margin: -6px 0;
    background: {MIST}; border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{ background: {AMBER}; }}
#Card {{ background: rgba(17,40,52,0.5); border-radius: 16px; }}
"""


# ---------------------------------------------------------------------------
# One slider row (name | slider | value)
# ---------------------------------------------------------------------------
class SliderRow(QWidget):
    # emits (param_name, value in 0..1)
    valueChanged = pyqtSignal(str, float)

    def __init__(self, name):
        super().__init__()
        self.name = name
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(name.title())
        self.label.setObjectName("ParamName")
        self.label.setFixedWidth(120)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.valueChanged.connect(self._on_change)

        self.val = QLabel("0")
        self.val.setObjectName("ParamVal")
        self.val.setFixedWidth(32)
        self.val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(self.label)
        row.addWidget(self.slider, 1)
        row.addWidget(self.val)

    def _on_change(self, v):
        self.val.setText(str(v))
        self.valueChanged.emit(self.name, v / 100.0)

    def set_value(self, value, block=False):
        """Set slider from a 0..1 value. block=True suppresses the signal."""
        if block:
            self.slider.blockSignals(True)
        self.slider.setValue(int(round(value * 100)))
        self.val.setText(str(int(round(value * 100))))
        if block:
            self.slider.blockSignals(False)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class SoundscapeWindow(QMainWindow):
    def __init__(self, engine=None):
        super().__init__()
        self.engine = engine
        self.playing = False
        self.rows = {}           # param name -> SliderRow
        self.preset_btns = {}    # preset name -> QPushButton

        self.setWindowTitle("Petrichor")
        self.setMinimumSize(560, 720)
        self.setStyleSheet(STYLESHEET)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(18)

        # --- header ---
        title = QLabel("Petrichor")
        title.setObjectName("Title")
        sub = QLabel("AMBIENCE SOUNDS SYNTHESIZER")
        sub.setObjectName("Subtitle")
        outer.addWidget(title)
        outer.addWidget(sub)

        # --- preset grid ---
        preset_card = QFrame()
        preset_card.setObjectName("Card")
        pc = QVBoxLayout(preset_card)
        pc.setContentsMargins(14, 14, 14, 14)
        grid = QGridLayout()
        grid.setSpacing(8)
        COLS = 3
        for i, name in enumerate(PRESETS.keys()):
            btn = QPushButton(name.replace("_", " ").title())
            btn.setObjectName("Preset")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, n=name: self.apply_preset(n))
            self.preset_btns[name] = btn
            grid.addWidget(btn, i // COLS, i % COLS)
        pc.addLayout(grid)
        outer.addWidget(preset_card)

        # --- transport ---
        transport = QHBoxLayout()
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("Play")
        self.play_btn.setFixedSize(52, 52)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.clicked.connect(self.on_play_clicked)
        transport.addWidget(self.play_btn)
        transport.addStretch(1)
        outer.addLayout(transport)

        # --- sliders (scrollable) ---
        sliders_card = QFrame()
        sliders_card.setObjectName("Card")
        sc = QVBoxLayout(sliders_card)
        sc.setContentsMargins(16, 12, 16, 12)
        sc.setSpacing(10)
        for name in PARAMS:
            row = SliderRow(name)
            row.valueChanged.connect(self.on_level_changed)
            self.rows[name] = row
            sc.addWidget(row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(sliders_card)
        outer.addWidget(scroll, 1)

    # (play / pause transport)
    def on_play_clicked(self):
        self.playing = not self.playing
        self.play_btn.setText("⏸" if self.playing else "▶")

        if self.engine:
            if self.playing:
                # First press: start the engine (renderers + priming + stream).
                # Subsequent presses: resume the paused stream.
                if getattr(self.engine, "stream", None) is None:
                    self.engine.start()
                else:
                    self.engine.resume()
            else:
                self.engine.pause()


    def on_level_changed(self, name, value):
        if self.engine:
            self.engine.set_level(name, value)

    def apply_preset(self, name):
        preset = PRESETS[name]

        # highlight the active button
        for n, btn in self.preset_btns.items():
            btn.setProperty("active", "true" if n == name else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # move every slider to the preset value.
        # block=False lets each move emit valueChanged -> on_level_changed,
        # which forwards to the engine. So setting the sliders IS the engine update
        for param in PARAMS:
            self.rows[param].set_value(preset.get(param, 0.0), block=False)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from engine import Engine
    import sounds as s
    app = QApplication(sys.argv)

    engine = Engine()

    engine.add_sound(s.Rain())
    engine.add_sound(s.Wind())
    engine.add_sound(s.Bird())
    engine.add_sound(s.Cricket())
    engine.add_sound(s.Woodpecker())
    engine.add_sound(s.Frog())
    engine.add_sound(s.SavannahGrass())
    engine.add_sound(s.Beetle())
    engine.add_sound(s.Cicada())
    engine.add_sound(s.DistantCall())
    engine.add_sound(s.ThunderStrike())
    engine.add_sound(s.River())

    win = SoundscapeWindow(engine=engine)
    win.apply_preset("savannah")
    win.show()
    sys.exit(app.exec())