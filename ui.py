"""
ui.py - Giao diện console: dòng nhập luôn ở cuối, tin đến chèn lên TRÊN, chữ đang gõ dở không bị mất.

Người phụ trách giải thích khi vấn đáp: PHONG        Người review (teach-back): NGỌC
Điểm rubric liên quan: Console UI (15%), nền cho mọi thông báo của chương trình
Test: tests/test_ui.py (giả lập phím + màn hình). ĐỌC TIẾP: lanchat.py (nơi gọi input_loop).

Ý TƯỞNG (đề mục 4.3; 3 bước khi có tin đến - câu hỏi vấn đáp chắc chắn có)
  Console không có "khung" riêng, nên ta giả lập: dòng cuối màn hình luôn là dòng nhập "> ...",
  mọi thứ phía trên là lịch sử chat. Khi có tin đến lúc người dùng đang gõ dở, show_message() làm:
    1. Xóa dòng nhập hiện tại     :  "\\r" + "\\033[K"   (về đầu dòng + xóa tới cuối dòng)
    2. In tin nhắn + xuống dòng
    3. Vẽ lại "> " + chữ đang gõ dở (lưu trong biến _buffer)
  _screen_lock bảo đảm hai thread KHÔNG bao giờ in cùng lúc.

BA FILE TRONG MỘT (đọc từ trên xuống):
  A. Đọc phím   : get_key()              Windows dùng msvcrt, Linux/macOS dùng termios (chưa chạy thử nhánh này)
  B. Vẽ màn hình: show_message(), _type_char(), _backspace(), _take_line()
  C. Vòng lặp   : input_loop(on_line)    chạy ở MAIN thread

BỐN BẪY
  1. threading.Lock không "reentrant": khi bấm Enter, _take_line() chỉ lấy dòng ra TRONG lock; việc CHẠY lệnh
     (on_line) làm NGOÀI lock. Nếu chạy lệnh trong lock, lệnh gọi show_message (cũng xin lock) -> treo vĩnh viễn.
  2. Mọi thread (UDP listener, TCP receiver, file sender) chỉ in qua show_message(), KHÔNG print() trực tiếp.
  3. Windows: phím đặc biệt (mũi tên, F1...) trả về 2 mã: "\\x00" hoặc "\\xe0" rồi mã thứ hai -> đọc bỏ mã thứ hai.
     os.system("") bật mã ANSI cho console Windows.
  4. Hạn chế đã biết của cách vẽ lại thủ công: dòng gõ dài hơn bề rộng cửa sổ, ký tự rộng/emoji, mũi tên/Home/End.
CHẾ ĐỘ THƯỜNG: nếu đầu vào không phải console thật (chạy qua pipe, ví dụ test tự động) thì bỏ mã ANSI và dấu nhắc,
  đọc từng DÒNG bằng sys.stdin.
"""
import os
import sys
import threading

PROMPT = "> "
CLEAR_LINE = "\r\033[K"          # về đầu dòng + xóa tới cuối dòng

_screen_lock = threading.Lock()  # chỉ MỘT thread được ghi ra màn hình tại một thời điểm
_buffer = ""                     # chữ người dùng đang gõ dở
_interactive = False             # True khi chạy trong console thật (có dòng nhập + mã ANSI)


# ======================================================================== A. đọc phím
if os.name == "nt":
    import msvcrt

    def _setup_keys():
        pass

    def _restore_keys():
        pass

    def get_key():
        """Đọc MỘT phím (chặn tới khi có). Trả về ký tự, hoặc None nếu là phím đặc biệt cần bỏ qua."""
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):       # phím đặc biệt gửi 2 mã: đọc và bỏ mã thứ hai
            msvcrt.getwch()
            return None
        return ch

else:
    import termios
    import tty

    _old_settings = None

    def _setup_keys():
        global _old_settings
        if sys.stdin.isatty():
            _old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())   # phím tới từng cái một, không tự hiện lên

    def _restore_keys():
        if _old_settings is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, _old_settings)

    def get_key():
        ch = sys.stdin.read(1)
        if ch == "":                     # hết dữ liệu nhập: coi như Ctrl+C
            return "\x03"
        if ch == "\x1b":                 # phím mũi tên: ESC [ A  -> bỏ qua
            sys.stdin.read(2)
            return None
        return ch


def init_terminal():
    """Chuẩn bị console (gọi MỘT lần lúc khởi động)."""
    global _interactive
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")   # in được tiếng Việt, không crash vì ký tự lạ
        except (AttributeError, ValueError):
            pass
    _interactive = sys.stdout.isatty() and sys.stdin.isatty()
    if _interactive:
        if os.name == "nt":
            os.system("")                # bật mã ANSI (\033[K) cho console Windows
        _setup_keys()


def restore_terminal():
    """Trả terminal về như cũ khi thoát (Linux/macOS cần; Windows không làm gì)."""
    if _interactive:
        _restore_keys()


# ======================================================================== B. vẽ màn hình
def _write(text):
    sys.stdout.write(text)
    sys.stdout.flush()           # stdout có bộ đệm -> phải flush thì chữ mới hiện ngay


def show_message(line):
    """In `line` phía TRÊN dòng nhập, rồi vẽ lại dấu nhắc + chữ đang gõ dở. MỌI thread gọi hàm này để in."""
    with _screen_lock:
        if _interactive:
            _write(CLEAR_LINE + line + "\n" + PROMPT + _buffer)
        else:
            _write(line + "\n")


def show_lines(lines):
    """In nhiều dòng liền nhau trong MỘT lần giữ lock, để thread khác không chen vào giữa."""
    show_message("\n".join(lines))


def _redraw_prompt():
    """Vẽ lại dòng nhập (dùng sau khi chạy xong một lệnh)."""
    if _interactive:
        with _screen_lock:
            _write(CLEAR_LINE + PROMPT + _buffer)


def _type_char(ch):
    """Người dùng gõ thêm một ký tự: thêm vào buffer và hiện lên màn hình."""
    global _buffer
    with _screen_lock:
        _buffer += ch
        _write(ch)


def _backspace():
    """Bấm Backspace: bỏ ký tự cuối của buffer rồi vẽ lại cả dòng nhập (đúng cả với ký tự rộng)."""
    global _buffer
    with _screen_lock:
        if _buffer:
            _buffer = _buffer[:-1]
            _write(CLEAR_LINE + PROMPT + _buffer)


def _take_line():
    """Bấm Enter: lấy chữ đã gõ ra, làm rỗng buffer, xóa dòng nhập. Trả về chữ đã gõ."""
    global _buffer
    with _screen_lock:
        line = _buffer
        _buffer = ""
        if _interactive:
            _write(CLEAR_LINE)
        return line


# ======================================================================== C. vòng lặp gõ phím
def input_loop(on_line, key_reader=None):
    """Vòng lặp của MAIN thread: đọc từng phím, cập nhật buffer; Enter thì gọi on_line(line).
    on_line trả về False -> thoát vòng lặp (lệnh /quit). Cũng thoát khi Ctrl+C hoặc hết dữ liệu nhập.
    `key_reader` thay được bằng hàm giả khi test."""
    if not _interactive:
        for raw_line in sys.stdin:       # chế độ thường: mỗi dòng đọc được là một lần Enter
            if on_line(raw_line.rstrip("\r\n")) is False:
                return
        return

    read_key = key_reader or get_key
    _redraw_prompt()                     # hiện dấu nhắc "> " lần đầu
    while True:
        ch = read_key()
        if ch is None:                   # phím đặc biệt: bỏ qua
            continue
        if ch in ("\r", "\n"):           # Enter
            line = _take_line()          # lấy dòng ra (trong lock) ...
            if on_line(line) is False:   # ... rồi chạy lệnh NGOÀI lock
                return
            _redraw_prompt()             # lệnh có thể không in gì -> vẽ lại "> "
        elif ch in ("\b", "\x7f"):       # Backspace
            _backspace()
        elif ch == "\x03":               # Ctrl+C
            return
        elif ch.isprintable():           # ký tự thường (kể cả tiếng Việt)
            _type_char(ch)
