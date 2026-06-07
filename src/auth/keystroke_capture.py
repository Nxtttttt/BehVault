import time
import tkinter as tk

from src.auth.feature_extractor import KeystrokeEvent


class KeystrokeCapture:
    """Captures key press/release events from a Tkinter widget."""

    def __init__(self, widget: tk.Widget):
        self.widget = widget
        self._events: list[KeystrokeEvent] = []
        self._pending_press: dict[str, float] = {}
        self._active = False

    def bind_events(self):
        self.widget.bind("<KeyPress>", self._on_key_press, add=True)
        self.widget.bind("<KeyRelease>", self._on_key_release, add=True)

    def unbind_events(self):
        self.widget.unbind("<KeyPress>")
        self.widget.unbind("<KeyRelease>")

    def start_capture(self):
        self._events.clear()
        self._pending_press.clear()
        self._active = True

    def stop_capture(self) -> list[KeystrokeEvent]:
        self._active = False
        return list(self._events)

    def get_current_events(self) -> list[KeystrokeEvent]:
        return list(self._events)

    def _on_key_press(self, event: tk.Event):
        if not self._active:
            return
        if event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R",
                            "Alt_L", "Alt_R", "Caps_Lock", "Tab", "Escape"):
            return
        self._pending_press[event.keysym] = time.time()

    def _on_key_release(self, event: tk.Event):
        if not self._active:
            return
        if event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R",
                            "Alt_L", "Alt_R", "Caps_Lock", "Tab", "Escape"):
            return
        press_time = self._pending_press.pop(event.keysym, None)
        if press_time is None:
            return
        is_bs = event.keysym == "BackSpace"
        self._events.append(KeystrokeEvent(
            key=event.keysym,
            press_time=press_time,
            release_time=time.time(),
            is_backspace=is_bs,
        ))

    def clear_buffer(self):
        self._events.clear()
        self._pending_press.clear()
