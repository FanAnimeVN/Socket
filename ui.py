"""
ui.py - Giao diện console: dòng nhập luôn ở cuối, tin đến chèn lên TRÊN, chữ đang gõ dở không bị mất.

Người phụ trách: PHONG        Người review (teach-back): NGỌC
Điểm rubric liên quan: Console UI (15%), nền cho mọi thông báo của chương trình
Đọc trước: đề mục 4.3; option_b_manual_redraw.py (file demo của đề). GÕ LẠI từng dòng + chú thích bằng lời
           của mình, đừng dán. Phương án dự phòng nếu quá nhiều lỗi: option_a_prompt_toolkit.py.

----------------------------------------------------------------------------------------
Ý TƯỞNG (3 bước khi có tin đến - câu hỏi vấn đáp chắc chắn có)
  1. Xóa dòng nhập hiện tại      :  "\\r" + "\\033[K"   (về đầu dòng + xóa tới cuối dòng)
  2. In tin nhắn + xuống dòng
  3. Vẽ lại "> " + nội dung đang gõ dở (lưu trong biến `buffer`)
  `screen_lock` đảm bảo hai thread KHÔNG in cùng lúc.

BỐN BẪY
  1. threading.Lock không "reentrant". Demo option_b xử lý phím BÊN TRONG `with screen_lock`. Khi lệnh
     (vd /list) cũng gọi show_message (cũng xin screen_lock) -> treo vĩnh viễn.
     => Khi bấm Enter: trong lock chỉ lấy dòng ra + xóa buffer; NHẢ lock; rồi mới chạy on_line(line).
  2. Mọi thread (UDP listener, TCP receiver, file sender) chỉ được in qua show_message(), KHÔNG print() trực tiếp.
  3. Windows: msvcrt.getwch() đọc 1 phím không cần Enter. Phím đặc biệt (mũi tên, F1...) trả về 2 mã:
     "\\x00" hoặc "\\xe0" rồi mã thứ hai -> đọc bỏ mã thứ hai. os.system("") bật mã ANSI cho console cũ.
  4. Giới hạn đã biết của cách vẽ lại thủ công: dòng gõ dài hơn bề rộng cửa sổ, ký tự rộng/emoji, phím
     mũi tên/Home/End. Chấp nhận và ghi vào report (mục "hạn chế"). Thử gõ tiếng Việt (Unikey/Telex) SỚM.
----------------------------------------------------------------------------------------
"""
import os
import sys
import threading

PROMPT = "> "
CLEAR_LINE = "\r\033[K"          # về đầu dòng + xóa tới cuối dòng

buffer = ""                      # chữ người dùng đang gõ dở
screen_lock = threading.Lock()   # chỉ MỘT thread được ghi ra màn hình tại một thời điểm


def init_terminal():
    """Chuẩn bị console (gọi một lần lúc khởi động).

    Windows: os.system("") để bật ANSI. (Tùy chọn) Linux/macOS: chuyển terminal sang chế độ đọc từng phím
    (tty.setcbreak) - lưu cài đặt cũ để restore. Nhóm dùng Windows thì có thể bỏ qua nhánh Linux, nhưng
    hãy hiểu demo option_b viết nhánh đó để làm gì.
    """
    raise NotImplementedError("TODO: init_terminal")


def restore_terminal():
    """Trả terminal về như cũ khi thoát (Linux/macOS cần; Windows có thể để trống)."""
    raise NotImplementedError("TODO: restore_terminal")


def get_key():
    """Đọc MỘT phím (chặn tới khi có phím). Trả về ký tự, hoặc None nếu là phím đặc biệt cần bỏ qua.

    Windows: msvcrt.getwch(); gặp "\\x00"/"\\xe0" -> đọc thêm một mã nữa rồi return None.
    """
    raise NotImplementedError("TODO: get_key")


def show_message(line):
    """In `line` phía TRÊN dòng nhập, rồi vẽ lại prompt + buffer. Mọi thread gọi hàm này để in.

    Việc cần làm (giữ screen_lock suốt 3 bước):
      1. ghi CLEAR_LINE   2. ghi line + "\\n"   3. ghi PROMPT + buffer   4. flush
    Vì sao cần flush? (stdout có bộ đệm -> chưa chắc hiện ngay.)
    """
    raise NotImplementedError("TODO: show_message")


def input_loop(on_line):
    """Vòng lặp của MAIN thread: đọc từng phím, cập nhật buffer, khi Enter thì gọi on_line(line).

    on_line(line) -> trả về False để yêu cầu thoát vòng lặp (khi /quit), ngược lại True/None.

    Xử lý từng loại phím (trong screen_lock, TRỪ lúc gọi on_line!):
      - Ký tự in được (ch.isprintable()) : buffer += ch ; echo ký tự ra màn hình
      - Backspace ("\\b" hoặc "\\x7f")      : nếu buffer rỗng thì bỏ qua, ngược lại cắt 1 ký tự + xóa trên màn hình
      - Enter ("\\r" hoặc "\\n")            : line = buffer; buffer = ""; xóa dòng nhập; (nhả lock) -> on_line(line)
      - Ctrl+C ("\\x03")                   : coi như /quit
      - Phím đặc biệt (get_key trả None)   : bỏ qua
    Sau khi on_line chạy xong, nếu nó không in gì thì phải vẽ lại PROMPT để người dùng thấy dấu "> ".
    Hiển thị tin mình vừa gửi: do tcp_chat.send_text in "[Tên] nội dung" (không phải ui).
    """
    raise NotImplementedError("TODO: input_loop")
