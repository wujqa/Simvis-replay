import json
import time

from PyQt5.QtCore import QObject, QTimer

from state_manager import global_state_manager, global_state_mutex


class ReplayPlayer(QObject):
    """Plays back previously recorded gamestates from a JSON file.

    The JSON file is expected to contain either a list of frame objects or an
    object with a top level ``frames`` key that holds that list.  Each frame
    must match the format consumed by ``GameState.read_from_json``.  On every
    timer tick the next frame is fed into the global ``GameState`` instance
    used by the renderer.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.frames = []
        self.frame_idx = 0
        self.fps = 60

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------
    # Loading / control helpers
    # ------------------------------------------------------------------
    def load_file(self, path: str):
        """Load replay data from ``path``.

        The file should contain a JSON array where each element is a frame in
        the expected gamestate format, or a dictionary with a ``frames`` key
        containing such an array.
        """

        with open(path, "r") as f:
            data = json.load(f)

        # Support both [frame, frame, ...] and {"frames": [...]} layouts
        if isinstance(data, dict) and "frames" in data:
            self.frames = data["frames"]
        else:
            self.frames = data

        self.frame_idx = 0

    def play(self, fps: int = 60):
        """Begin playback at ``fps`` frames per second."""

        self.fps = fps
        interval_ms = max(int(1000 / max(fps, 1)), 1)
        self.timer.start(interval_ms)

    def stop(self):
        self.timer.stop()

    # ------------------------------------------------------------------
    # Timer callback
    # ------------------------------------------------------------------
    def _tick(self):
        if self.frame_idx >= len(self.frames):
            # End of replay
            self.stop()
            return

        frame = self.frames[self.frame_idx]

        # Update global state for the renderer.  We guard the access with the
        # global mutex just like the socket listener would.
        with global_state_mutex:
            global_state_manager.state.read_from_json(frame)
            global_state_manager.state.recv_time = time.time()
            global_state_manager.state.recv_interval = 1.0 / max(self.fps, 1)

        self.frame_idx += 1

