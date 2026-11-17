"""
lanchat.py - Chương trình chính: đọc tham số, khởi động các thread, xử lý lệnh gõ vào.

Chạy:  python lanchat.py --name Quan --port 5000
Người phụ trách: HUY (lead tích hợp)       Người review: cả nhóm
Điểm rubric liên quan: Demo & code quality (5%), và là chỗ ghép mọi phần lại
Đọc trước: đề mục 4 (lệnh, ví dụ phiên chạy), 5.1 (bảng thread)

----------------------------------------------------------------------------------------
FILE NÀY CHỈ "ĐIỀU PHỐI", KHÔNG CHỨA LOGIC MẠNG.
  - Gõ chữ thường  -> tcp_chat.send_text
  - Gõ /lệnh       -> hàm cmd_* tương ứng
  Giữ file ngắn gọn: khi vấn đáp bạn có thể đi từ đây xuống từng module và giải thích toàn bộ luồng.

BẢNG LỆNH (đề mục 4.1):
  /list                  Hiện người online (số, tên, IP, status)      -> discovery
  /chat <tên|số>         Mở chat (kết nối TCP)                         -> tcp_chat
  <văn bản>              Gửi tin cho partner hiện tại                  -> tcp_chat
  /send <file>           Gửi file cho partner hiện tại                 -> filetransfer
  /leave                 Đóng chat hiện tại                            -> tcp_chat
  /status <online|away>  Đổi trạng thái                                -> discovery
  /help                  Liệt kê lệnh
  /quit                  Thoát

THỨ TỰ KHỞI ĐỘNG (main) - tự viết theo các bước:
  1. argparse: --name (bắt buộc), --port (mặc định config.DEFAULT_TCP_PORT), --bcast (mặc định config.DEFAULT_BCAST)
  2. Kiểm tra tên hợp lệ: không rỗng, KHÔNG chứa ký tự '|' (vì '|' là dấu phân cách trong giao thức!), độ dài hợp lý
  3. Gán state.my_name / state.my_tcp_port / state.my_status
  4. ui.init_terminal()
  5. server_sock = tcp_chat.start_acceptor(port)  -> in "[*] Listening on TCP port 5000"
  6. discovery.start_discovery(name, port, bcast) -> in "[*] Broadcasting presence on UDP port 9999"
  7. ui.input_loop(handle_line)   <- main thread nằm ở đây cho tới khi /quit
  8. Dọn dẹp: state.stop_event.set(); tcp_chat.close_all(); đóng server_sock; ui.restore_terminal(); in "[*] Bye!"
  Bọc 7-8 bằng try/finally để lỗi bất ngờ vẫn dọn dẹp.
----------------------------------------------------------------------------------------
"""
import argparse

import config
import discovery
import filetransfer
import state
import tcp_chat
import ui

HELP_TEXT = """\
TODO: viết nội dung /help - liệt kê đủ 8 lệnh ở bảng trên, mỗi lệnh một dòng ngắn."""


def parse_args():
    """Dùng argparse. Trả về đối tượng args có .name, .port, .bcast.
    Gợi ý: argparse.ArgumentParser(); add_argument("--name", required=True); add_argument("--port", type=int, default=...)."""
    raise NotImplementedError("TODO: parse_args")


def handle_line(line):
    """Được ui.input_loop gọi mỗi khi người dùng bấm Enter. Trả về False để thoát chương trình, ngược lại True.

    Việc cần làm:
      - line.strip() rỗng -> bỏ qua.
      - Bắt đầu bằng "/" : tách lệnh và tham số (str.split(maxsplit=1)), chuyển tới cmd_* tương ứng.
        Lệnh lạ -> in "[!] Unknown command" + gợi ý /help (đề mục 5.3: lệnh sai thì hiện help ngắn).
      - Ngược lại : tcp_chat.send_text(line)
    Mẹo thiết kế: dùng dict {"/list": cmd_list, ...} thay vì một chuỗi if/elif dài - dễ thêm lệnh, dễ giải thích.
    """
    raise NotImplementedError("TODO: handle_line")


def cmd_list(arg):
    """In discovery.format_peer_list() - từng dòng một qua ui.show_message."""
    raise NotImplementedError("TODO: cmd_list")


def cmd_chat(arg):
    """/chat <tên|số>: thiếu tham số -> báo cách dùng; discovery.find_peer(arg) -> tcp_chat.open_chat(name).
    Không tìm thấy -> báo lỗi (gợi ý gõ /list)."""
    raise NotImplementedError("TODO: cmd_chat")


def cmd_send(arg):
    """/send <file>: thiếu tham số -> báo cách dùng; gọi filetransfer.send_file_async(partner, path).
    Đường dẫn có dấu cách thì sao? (arg lấy trọn phần còn lại của dòng)."""
    raise NotImplementedError("TODO: cmd_send")


def cmd_leave(arg):
    """/leave: tcp_chat.leave_chat(). Chưa chat với ai -> báo nhẹ nhàng."""
    raise NotImplementedError("TODO: cmd_leave")


def cmd_status(arg):
    """/status <online|away>: discovery.set_status(arg). Thiếu/sai tham số -> báo cách dùng."""
    raise NotImplementedError("TODO: cmd_status")


def cmd_help(arg):
    """In HELP_TEXT."""
    raise NotImplementedError("TODO: cmd_help")


def cmd_quit(arg):
    """/quit: trả về False để handle_line báo input_loop dừng. (Việc dọn dẹp làm ở main, bước 8.)"""
    raise NotImplementedError("TODO: cmd_quit")


def main():
    """Xem 'THỨ TỰ KHỞI ĐỘNG' ở đầu file."""
    raise NotImplementedError("TODO: main")


if __name__ == "__main__":
    main()
