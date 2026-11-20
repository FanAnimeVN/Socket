"""
lanchat.py - Chương trình chính: đọc tham số, khởi động các thread, xử lý lệnh gõ vào.

CHẠY:  python lanchat.py --name Quan --port 5000
  --name   tên hiển thị (bắt buộc, duy nhất trong mạng, không dấu cách, không có ký tự '|')
  --port   cổng TCP của mình (mặc định 5000). Chạy nhiều instance trên MỘT máy thì mỗi instance một cổng khác.
  --bcast  địa chỉ broadcast (mặc định 255.255.255.255). Cần đổi khi mạng có nhiều card (VPN/WSL...) hoặc khi test
           offline trên một máy:  --bcast 127.255.255.255   hoặc địa chỉ mạng con, ví dụ 192.168.1.255

Người phụ trách giải thích khi vấn đáp: HUY (lead tích hợp)       Người review: cả nhóm
Điểm rubric liên quan: Demo & code quality (5%), và là chỗ ghép mọi phần lại
Đọc trước: đề mục 4 (lệnh, ví dụ phiên chạy), 5.1 (bảng thread). Cách đọc cả dự án: docs/HUONG_DAN_DOC_CODE.md

FILE NÀY CHỈ "ĐIỀU PHỐI", KHÔNG CHỨA LOGIC MẠNG:
  - Gõ chữ thường -> tcp_chat.send_text          - Gõ /lệnh -> hàm cmd_* tương ứng (bảng COMMANDS)

BẢNG LỆNH (đề mục 4.1):
  /list                  Hiện người online (số, tên, IP, status)      -> discovery
  /chat <tên|số>         Mở chat (kết nối TCP)                         -> tcp_chat
  <văn bản>              Gửi tin cho partner hiện tại                  -> tcp_chat
  /send <file>           Gửi file cho partner hiện tại                 -> filetransfer
  /leave                 Đóng chat hiện tại                            -> tcp_chat
  /status <online|away>  Đổi trạng thái                                -> discovery
  /help                  Liệt kê lệnh
  /quit                  Thoát

THỨ TỰ KHỞI ĐỘNG (main), từng bước:
  1. đọc và kiểm tra tham số                         5. kiểm tra tên chưa ai dùng       (discovery.find_name_owner)
  2. ui.init_terminal()                              6. bắt đầu nghe + phát UDP         (discovery.start_discovery)
  3. lưu tên/cổng của mình vào state                 7. vòng lặp gõ phím (main thread)  (ui.input_loop)
  4. mở cổng TCP chờ kết nối (tcp_chat.start_acceptor)   8. thoát: bật cờ dừng, gửi BYE, đóng socket
CÁC THREAD (đề mục 5.1): main (bàn phím) · udp-broadcaster · udp-listener · tcp-acceptor
  · tcp-receiver / chat-receiver (mỗi kết nối một thread) · file-sender (mỗi lần gửi file).
"""
import argparse
import sys

import config
import discovery
import filetransfer
import protocol
import state
import tcp_chat
import ui

HELP_LINES = [
    "Commands (text without / is sent as a chat message):",
    "  /list                  show online users",
    "  /chat <name|number>    open a chat with a user",
    "  /send <file>           send a file to the current chat partner",
    "  /leave                 close the current chat",
    "  /status <online|away>  change your status",
    "  /help                  show this help",
    "  /quit                  exit the program",
]


# ======================================================================== tham số
def parse_args():
    """Đọc tham số dòng lệnh (--name, --port, --bcast)."""
    parser = argparse.ArgumentParser(description="LAN chat and file sharing over TCP + UDP")
    parser.add_argument("--name", required=True, help="your display name (unique on the network)")
    parser.add_argument("--port", type=int, default=config.DEFAULT_TCP_PORT, help="your TCP port (default 5000)")
    parser.add_argument("--bcast", default=config.DEFAULT_BCAST, help="UDP broadcast address (default 255.255.255.255)")
    return parser.parse_args()


def check_args(args):
    """Trả về câu báo lỗi nếu tham số sai, hoặc None nếu ổn. Tên không được có '|' vì '|' là dấu ngăn cách của giao thức."""
    name = args.name
    if name == "" or any(ch.isspace() or ch == "|" or not ch.isprintable() for ch in name):
        return "The name must not be empty, and must not contain spaces or the '|' character."
    if len(name) > config.MAX_NAME_LEN:
        return f"The name is too long (max {config.MAX_NAME_LEN} characters)."
    if not 1 <= args.port <= 65535:
        return "The port must be between 1 and 65535."
    return None


# ======================================================================== xử lý dòng gõ vào
def handle_line(line):
    """Được ui.input_loop gọi mỗi khi bấm Enter. Trả về False để thoát chương trình, ngược lại True.
    Chữ thường -> gửi tin; "/lệnh tham số" -> tra bảng COMMANDS; lệnh lạ -> báo lỗi + hiện danh sách lệnh ngắn.
    Lỗi bất ngờ trong một lệnh được bắt lại: không được làm chết cả chương trình."""
    text = line.strip()
    if text == "":
        return True
    try:
        if not text.startswith("/"):
            tcp_chat.send_text(text)
            return True
        parts = text.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        handler = COMMANDS.get(command)
        if handler is None:
            ui.show_message(f"[!] Unknown command: {command}")
            cmd_help("")
            return True
        return handler(arg) is not False
    except Exception as error:
        ui.show_message(f"[!] Error: {error}")
        return True


def cmd_list(arg):
    """/list: in danh sách người online."""
    ui.show_lines(discovery.format_peer_list())


def cmd_chat(arg):
    """/chat <tên|số>: chọn người (theo tên hoặc số trong /list) rồi mở chat."""
    if arg == "":
        ui.show_message("[*] Usage: /chat <name|number>   (see /list)")
    elif arg.lower() == state.get_name().lower():
        ui.show_message("[!] You cannot chat with yourself.")
    else:
        name = discovery.find_peer(arg)
        if name is None:
            ui.show_message(f"[!] No online user '{arg}'. Type /list to see who is online.")
        else:
            tcp_chat.open_chat(name)


def cmd_send(arg):
    """/send <file>: gửi file cho partner. Đường dẫn là phần còn lại của dòng (có dấu cách vẫn được);
    bỏ dấu nháy nếu có (ví dụ khi kéo-thả file vào cửa sổ)."""
    path = arg.strip().strip('"').strip("'")
    if path == "":
        ui.show_message("[*] Usage: /send <file>")
    else:
        filetransfer.send_file_async(state.get_partner(), path)


def cmd_leave(arg):
    """/leave: đóng chat hiện tại."""
    tcp_chat.leave_chat()


def cmd_status(arg):
    """/status <online|away>: đổi trạng thái (đi tới người khác qua UDP)."""
    discovery.set_status(arg)


def cmd_help(arg):
    """/help: liệt kê lệnh."""
    ui.show_lines(HELP_LINES)


def cmd_quit(arg):
    """/quit: trả về False để handle_line báo input_loop dừng. (Việc dọn dẹp làm ở main, bước 8.)"""
    return False


COMMANDS = {
    "/list": cmd_list,
    "/chat": cmd_chat,
    "/send": cmd_send,
    "/leave": cmd_leave,
    "/status": cmd_status,
    "/help": cmd_help,
    "/quit": cmd_quit,
}


# ======================================================================== main
def start_network(args):
    """Bước 4-6: mở cổng TCP, kiểm tra tên, bật thread UDP. Trả về (server_socket, None) hoặc (None, lỗi)."""
    try:
        server = tcp_chat.start_acceptor(args.port)
    except OSError as error:
        return None, f"Cannot use TCP port {args.port} ({error}). Try another one with --port."
    ui.show_message(f"[*] Checking that the name '{args.name}' is free ({config.NAME_CHECK_SECONDS:g} s) ...")
    owner_ip = discovery.find_name_owner(args.name)
    if owner_ip is not None:
        protocol.close_quietly(server)
        return None, f"The name '{args.name}' is already used by {owner_ip}. Choose another --name."
    discovery.start_discovery(args.name, args.port, args.bcast)
    ui.show_message(f"[*] Listening on TCP port {args.port}")
    ui.show_message(f"[*] Broadcasting presence on UDP port {config.UDP_PORT} (to {args.bcast})")
    ui.show_message("[*] Type /help for the list of commands")
    return server, None


def main():
    args = parse_args()
    error = check_args(args)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    ui.init_terminal()
    state.set_identity(args.name, args.port)
    try:
        server, error = start_network(args)
        if error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        try:
            ui.input_loop(handle_line)                  # main thread nằm ở đây cho tới khi /quit
        except KeyboardInterrupt:
            pass
        finally:
            state.request_stop()                        # báo các thread nền dừng
            tcp_chat.close_all()                        # gửi BYE + đóng mọi kết nối chat
            protocol.close_quietly(server)
    finally:
        ui.restore_terminal()
    print("[*] Bye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
