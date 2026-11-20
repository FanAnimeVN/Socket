"""
discovery.py - Phát hiện peer qua UDP: broadcast "mình đang online" + lắng nghe người khác + trạng thái online/away.

Người phụ trách giải thích khi vấn đáp: NGỌC          Người review (teach-back): HUY
Điểm rubric liên quan: UDP discovery, online list, status (15%) ; Error handling (10%)
Đọc trước: đề mục 3.1, 3.2, 5.2; docs/PROTOCOL.md (mục 1). Test: tests/test_discovery.py.
ĐỌC TIẾP: tcp_chat.py (chat với người vừa tìm thấy).

HAI THREAD CỦA FILE NÀY (thread nào đang chờ cái gì? - câu hỏi vấn đáp kinh điển)
  * Broadcaster : CHỜ ĐỒNG HỒ. Mỗi 3 giây gửi   HELLO|<name>|<tcp_port>|<status>   tới địa chỉ broadcast, cổng 9999.
  * Listener    : CHỜ GÓI UDP. Mỗi vòng lặp: (1) recvfrom tối đa 1 giây, (2) gói hợp lệ thì cập nhật danh sách
                  online trong state.py và báo "[*] Minh is online", (3) dọn người im quá 10 giây, báo "went offline".
                  Vì sao recvfrom chỉ chờ 1 giây (settimeout)? Nếu chờ vô hạn thì lúc không ai gửi gì,
                  bước (3) dọn người hết hạn sẽ không bao giờ chạy.

CÁC BẪY
  1. Nhiều instance chạy trên MỘT máy phải bind chung cổng 9999 -> SO_REUSEADDR, đặt TRƯỚC bind().
  2. Phải bật SO_BROADCAST thì mới gửi tới địa chỉ broadcast được.
  3. Mình cũng nhận lại chính gói broadcast của mình -> bỏ qua bằng cách so tên. Vì vậy tên phải duy nhất:
     lúc khởi động, find_name_owner() nghe 3.5 giây xem đã có ai dùng tên mình chưa.
  4. Thông báo online/offline in NGOÀI lock (state.update_peer đã nhả lock rồi mới trả về).
  5. Windows nhiều card mạng (VPN, WSL, Hyper-V...) thì 255.255.255.255 có thể đi sai card -> tham số --bcast.
  6. Gói UDP lạ/rác không được làm chết thread: parse_hello trả None thì bỏ qua gói đó.
"""
import socket
import threading
import time

import config
import state
import ui

_send_now = threading.Event()     # "công tắc đánh thức": bật lên thì broadcaster gửi ngay, không chờ nốt 3 giây


# ======================================================================== gói HELLO
def build_hello(name, tcp_port, status):
    """Ghép gói HELLO (kiểu bytes, sẵn sàng gửi bằng sendto). Ví dụ: HELLO|Quan|5000|online"""
    return f"HELLO|{name}|{tcp_port}|{status}".encode(config.ENCODING)


def parse_hello(data):
    """bytes -> (name, tcp_port:int, status), hoặc None nếu gói không hợp lệ."""
    parts = data.decode(config.ENCODING, errors="replace").split("|")
    if len(parts) != 4 or parts[0] != "HELLO":
        return None
    _, name, port_text, status = parts
    if name == "" or not port_text.isdigit():
        return None
    port = int(port_text)
    if not 1 <= port <= 65535 or status not in config.VALID_STATUS:
        return None
    return name, port, status


# ======================================================================== socket UDP
def _make_receiver_socket():
    """Socket UDP để NGHE gói HELLO trên cổng config.UDP_PORT (9999)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)       # SOCK_DGRAM = UDP (SOCK_STREAM mới là TCP)
    # Cho phép nhiều chương trình (nhiều instance trên một máy) cùng bind một cổng. PHẢI đặt TRƯỚC bind().
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):                           # macOS/Linux cần thêm dòng này
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", config.UDP_PORT))                              # "" = nghe trên MỌI card mạng
    return sock


def _make_sender_socket():
    """Socket UDP để GỬI broadcast. Không cần bind (hệ điều hành tự chọn cổng nguồn)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)    # bắt buộc bật thì mới gửi tới địa chỉ broadcast được
    return sock


# ======================================================================== khởi động
def find_name_owner(name, seconds=config.NAME_CHECK_SECONDS):
    """Gọi MỘT lần lúc khởi động. Nghe `seconds` giây (3.5 s, lâu hơn chu kỳ 3 s của mọi peer) xem có HELLO nào
    mang tên `name` không. Lúc này mình chưa phát gì nên gói trùng tên chắc chắn là của người khác.
    Trả về IP của người đang dùng tên đó, hoặc None nếu tên còn trống."""
    sock = _make_receiver_socket()
    sock.settimeout(0.5)
    deadline = time.time() + seconds
    try:
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(config.UDP_BUFFER_SIZE)
            except socket.timeout:
                continue
            except OSError:
                time.sleep(0.1)
                continue
            parsed = parse_hello(data)
            if parsed is not None and parsed[0].lower() == name.lower():
                return addr[0]
        return None
    finally:
        sock.close()


def start_discovery(name, tcp_port, bcast=config.DEFAULT_BCAST):
    """Khởi động 2 thread (broadcaster + listener) rồi trả về ngay (không chặn).
    daemon=True: thoát chương trình thì thread tự chết theo, không giữ chương trình lại."""
    listen_sock = _make_receiver_socket()
    listen_sock.settimeout(1.0)
    send_sock = _make_sender_socket()
    threading.Thread(target=_broadcaster_loop, args=(send_sock, name, tcp_port, bcast), daemon=True, name="udp-broadcaster").start()
    threading.Thread(target=_listener_loop, args=(listen_sock, name), daemon=True, name="udp-listener").start()


# ======================================================================== thread 1: broadcaster
def _broadcaster_loop(sock, name, tcp_port, bcast):
    warned = False                                  # chỉ báo lỗi mạng MỘT lần, khỏi spam mỗi 3 giây
    while not state.is_stopped():
        try:
            sock.sendto(build_hello(name, tcp_port, state.get_status()), (bcast, config.UDP_PORT))
            warned = False
        except OSError as error:                    # mạng chập chờn: báo rồi thử lại, không để thread chết
            if not warned:
                ui.show_message(f"[!] Cannot broadcast to {bcast}: {error}")
                warned = True
        _send_now.wait(config.BROADCAST_INTERVAL)   # chờ 3 giây, hoặc tới khi có người đánh thức (đổi /status)
        _send_now.clear()


# ======================================================================== thread 2: listener
def _listener_loop(sock, my_name):
    while not state.is_stopped():
        try:
            data, addr = sock.recvfrom(config.UDP_BUFFER_SIZE)
            _handle_packet(data, addr[0], my_name)
        except socket.timeout:
            pass                                    # 1 giây không có gói nào: bình thường, xuống bước dọn dẹp
        except OSError:
            time.sleep(0.2)                         # lỗi lạ (Windows đôi khi báo "connection reset" cho UDP): bỏ qua
        for name in state.remove_expired_peers(config.PEER_TIMEOUT):
            ui.show_message(f"[*] {name} went offline")


def _handle_packet(data, ip, my_name):
    """Xử lý một gói UDP nhận được từ địa chỉ `ip`."""
    parsed = parse_hello(data)
    if parsed is None:
        return                                      # gói rác: bỏ qua
    name, tcp_port, status = parsed
    if name.lower() == my_name.lower():
        return                                      # gói do chính mình phát
    result = state.update_peer(name, ip, tcp_port, status)
    if result == "new":
        suffix = "" if status == config.STATUS_ONLINE else f" ({status})"
        ui.show_message(f"[*] {name} is online{suffix}")
    elif result == "status":
        ui.show_message(f"[*] {name} is now {status}")


# ======================================================================== phục vụ các lệnh /list /chat /status
def find_peer(arg):
    """`arg` là tên hoặc số thứ tự (bắt đầu từ 1, theo /list). Trả về tên đúng, hoặc None nếu không có/ngoài phạm vi."""
    arg = arg.strip()
    items = state.get_peers_sorted()
    if arg.isdigit():
        index = int(arg)
        return items[index - 1][0] if 1 <= index <= len(items) else None
    for name, _ in items:                           # ưu tiên khớp chính xác, rồi tới không phân biệt hoa/thường
        if name == arg:
            return name
    for name, _ in items:
        if name.lower() == arg.lower():
            return name
    return None


def format_peer_list():
    """Các dòng cho /list, đúng mẫu của đề:   "  1. Minh   (192.168.1.12)  online"
    Thêm "[N unread]" nếu có tin chưa đọc, "<- chatting" cho người đang chat cùng."""
    items = state.get_peers_sorted()
    if not items:
        return ["[*] Nobody else is online yet."]
    partner = state.get_partner()
    width = max(len(name) for name, _ in items)
    lines = []
    for number, (name, info) in enumerate(items, start=1):
        line = f"  {number}. {name.ljust(width)}  ({info['ip']})  {info['status']}"
        unread = state.unread_count(name)
        if unread > 0:
            line += f"  [{unread} unread]"
        if name == partner:
            line += "  <- chatting"
        lines.append(line)
    return lines


def set_status(status):
    """/status: đổi trạng thái của mình và gửi HELLO ngay (khỏi để người khác chờ tối đa 3 giây).
    Trạng thái đi tới người khác QUA UDP, nằm sẵn trong gói HELLO. Trả về True nếu hợp lệ."""
    status = status.strip().lower()
    if not state.set_status(status):
        ui.show_message(f"[*] Usage: /status <{'|'.join(config.VALID_STATUS)}>")
        return False
    _send_now.set()
    ui.show_message(f"[*] Your status is now {status}")
    return True
