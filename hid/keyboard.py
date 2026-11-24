import sys

import cpu.bytes as byte
import gpu.gpu as graphics
import gpu.screen as screen
import gpu.strings as string


class ConsoleKeys:

    QUEUE = 1
    """
    how many unanswered keys to remember. one: a backwriting of the same key
    would keep steering long after it was let go and for a direction the
    newest press is the only one that means anything
    """

    def __init__(self, console=None):
        if console is None:
            import msvcrt

            console = msvcrt
        self.console = console
        self.pending: list[str] = []

    def _drain(self) -> None:
        while self.console.kbhit():
            char = self.console.getwch()
            if not char or not char.isprintable():
                continue
            self.pending.append(char.lower())
            del self.pending[:-self.QUEUE]

    def is_pressed(self, key: str) -> bool:
        self._drain()
        if key in self.pending:
            self.pending.remove(key)
            return True
        return False


def _backend():
    try:
        import keyboard as kb

        return kb
    except Exception:
        pass
    try:
        if sys.stdin is not None and sys.stdin.isatty():
            return ConsoleKeys()
    except Exception:
        pass
    return None


class Keyboard:
    """
    reads the real keyboard.  A key is named the same way a character is
    anywhere else in this machine: by its word in the string map, so
    `mov &15, "a"` then `syscall key` asks about the  key.
    """

    def __init__(self, byte_handler: byte.Byte, string_handler: string.String,
                 backend=None):
        self.keyboard = _backend() if backend is None else backend
        self.byte = byte_handler
        self.string = string_handler

    @property # REMINDER that could be why it breaks !!!!!!!!!!!!!!!!!!!!!!!!!!!!
    def available(self) -> bool:
        """False when there is nothing behind it, so nothing is pressed"""
        return (screen.current() is not None or graphics.WINDOW
                or self.keyboard is not None)

    @property
    def kind(self) -> str:
        """which one is answering, for whoever wants to print it"""
        if screen.current() is not None:
            return "window"
        if graphics.WINDOW:
            return "window (not opened yet)"
        if self.keyboard is None:
            return "none"
        if isinstance(self.keyboard, ConsoleKeys):
            return "console"
        return getattr(self.keyboard, "__name__", "keyboard")

    def keystate(self, bitstring_keychar: str):
        """is the key for this character word held down right now?"""
        character = self.string.get(bitstring_keychar)
        if not character:
            return False
        window = screen.pressed(character) # None while there is no window
        if window is not None:
            return window
        if self.keyboard is None:
            return False
        try:
            return bool(self.keyboard.is_pressed(character))
        except Exception:
            return False # unknown key name, no permission, no consol


Keyboard_ = Keyboard


class Keyboard8B(Keyboard):
    def __init__(self, backend=None):
        super().__init__(byte.Byte8(), string.String8B(), backend)


class Keyboard16B(Keyboard):
    def __init__(self, backend=None):
        super().__init__(byte.Byte16(), string.String16B(), backend)


class Keyboard32B(Keyboard):
    def __init__(self, backend=None):
        super().__init__(byte.Byte32(), string.String32B(), backend)
