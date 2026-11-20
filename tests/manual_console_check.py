"""
tests/manual_console_check.py - KIỂM TRA CHẠY TAY (chỉ Windows): bơm phím THẬT vào một console THẬT.

Các test khác giả lập phím và màn hình. File này kiểm tra đường thật: msvcrt.getwch + mã ANSI trên console Windows.
Cách làm: chạy lanchat.py trong một console ẩn (tên "Con"), dùng WriteConsoleInputW để "bấm phím" vào đó, và đọc lại
nội dung màn hình console bằng ReadConsoleOutputCharacterW. Một instance thứ hai ("Peer") gửi tin cho Con đúng lúc Con
đang gõ dở "you can che" -> kết quả phải là: tin chen lên trên, dòng nhập "> you can che" được vẽ lại nguyên vẹn.

Chạy:   python tests/manual_console_check.py
Kết quả lưu ở docs/evidence/console_typing_while_receiving.txt (minh chứng cho báo cáo).
Không có tên test_*.py nên "unittest discover" không chạy file này.
"""
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tests.test_end_to_end import Instance, free_port  # noqa: E402

OUTPUT = os.path.join(ROOT, "docs", "evidence", "console_typing_while_receiving.txt")
BCAST = "127.255.255.255"          # chỉ trong máy này
CREATE_NO_WINDOW = 0x08000000      # console thật nhưng ẩn, không hiện cửa sổ


class COORD(ctypes.Structure):
    _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]


class SMALL_RECT(ctypes.Structure):
    _fields_ = [("L", ctypes.c_short), ("T", ctypes.c_short), ("R", ctypes.c_short), ("B", ctypes.c_short)]


class SCREEN_INFO(ctypes.Structure):
    _fields_ = [("size", COORD), ("cursor", COORD), ("attr", wintypes.WORD), ("window", SMALL_RECT), ("maxsize", COORD)]


class KEY_EVENT(ctypes.Structure):
    _fields_ = [("down", wintypes.BOOL), ("repeat", wintypes.WORD), ("vk", wintypes.WORD),
                ("scan", wintypes.WORD), ("char", wintypes.WCHAR), ("ctrl", wintypes.DWORD)]


class EVENT_UNION(ctypes.Union):
    _fields_ = [("key", KEY_EVENT)]


class INPUT_RECORD(ctypes.Structure):
    _fields_ = [("type", wintypes.WORD), ("ev", EVENT_UNION)]


def load_kernel32():
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    k32.WriteConsoleInputW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    k32.ReadConsoleOutputCharacterW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, COORD,
                                                ctypes.POINTER(wintypes.DWORD)]
    k32.GetConsoleScreenBufferInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(SCREEN_INFO)]
    return k32


K32 = load_kernel32() if os.name == "nt" else None


def open_console_handle(name):
    handle = K32.CreateFileW(name, 0xC0000000, 3, None, 3, 0, None)    # đọc+ghi, chia sẻ, mở có sẵn
    if handle in (None, ctypes.c_void_p(-1).value):
        raise OSError(f"cannot open {name}: error {ctypes.get_last_error()}")
    return handle


def press(h_in, char, vk=0, scan=0):
    """Bấm và nhả một phím (một ký tự, hoặc Enter/Backspace nếu có mã vk)."""
    records = (INPUT_RECORD * 2)()
    for index, down in enumerate((1, 0)):
        records[index].type = 1                                   # KEY_EVENT
        records[index].ev.key.down = down
        records[index].ev.key.repeat = 1
        records[index].ev.key.vk = vk
        records[index].ev.key.scan = scan
        records[index].ev.key.char = char
    written = wintypes.DWORD()
    if not K32.WriteConsoleInputW(h_in, records, 2, ctypes.byref(written)):
        raise OSError(f"WriteConsoleInputW failed: {ctypes.get_last_error()}")


def type_text(h_in, text):
    for ch in text:
        press(h_in, ch)
        time.sleep(0.03)


def press_enter(h_in):
    press(h_in, "\r", vk=0x0D, scan=0x1C)


def press_backspace(h_in):
    press(h_in, "\b", vk=0x08, scan=0x0E)


def read_screen(h_out):
    """Đọc các dòng của màn hình console từ trên xuống dòng chứa con trỏ."""
    info = SCREEN_INFO()
    K32.GetConsoleScreenBufferInfo(h_out, ctypes.byref(info))
    rows = []
    for y in range(0, info.cursor.Y + 1):
        buffer = ctypes.create_unicode_buffer(info.size.X)
        got = wintypes.DWORD()
        K32.ReadConsoleOutputCharacterW(h_out, buffer, info.size.X, COORD(0, y), ctypes.byref(got))
        rows.append(buffer.value.rstrip())
    return rows


def main():
    if os.name != "nt":
        print("This check only works on Windows.")
        return 1
    report = ["MINH CHUNG: go phim THAT trong console Windows THAT (tests/manual_console_check.py)", ""]
    peer = Instance("Peer", BCAST)
    con = subprocess.Popen([sys.executable, "lanchat.py", "--name", "Con", "--port", str(free_port()), "--bcast", BCAST],
                           cwd=ROOT, creationflags=CREATE_NO_WINDOW)
    try:
        time.sleep(7)                                             # chờ cả hai qua bước kiểm tra tên và thấy nhau
        peer.say("/chat Con")
        time.sleep(1)
        K32.FreeConsole()
        if not K32.AttachConsole(con.pid):
            raise OSError(f"AttachConsole failed: {ctypes.get_last_error()}")
        h_in, h_out = open_console_handle("CONIN$"), open_console_handle("CONOUT$")

        report += ["[1] Man hinh luc khoi dong:"] + read_screen(h_out)
        type_text(h_in, "/chat Peer")
        press_enter(h_in)
        time.sleep(1)
        type_text(h_in, "you can che")                            # gõ dở ...
        time.sleep(0.5)
        peer.say("ok, which part?")                               # ... đúng lúc này có tin đến
        time.sleep(1.2)
        report += ["", "[2] Tin den luc dang go do 'you can che' (dong cuoi phai la '> you can che'):"] + read_screen(h_out)
        press_backspace(h_in)
        press_backspace(h_in)
        type_text(h_in, "ck tiếng Việt ế")                       # gõ tiếp, có tiếng Việt
        press_enter(h_in)
        time.sleep(1)
        report += ["", "[3] Sau 2 lan Backspace, go tiep va bam Enter:"] + read_screen(h_out)
        type_text(h_in, "/quit")
        press_enter(h_in)
        time.sleep(1.5)
    finally:
        K32.FreeConsole()
        if con.poll() is None:
            con.kill()
        peer_lines = [line for line in peer.lines if "Con" in line]
        peer.stop()
    report += ["", "[4] Peer (instance thu hai) nhan duoc:"] + peer_lines
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
