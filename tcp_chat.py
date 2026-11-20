"""
tcp_chat.py - Chat qua TCP: nhận kết nối, nhận tin, mở/đóng chat, gửi tin.

Người phụ trách giải thích khi vấn đáp: HUY          Người review (teach-back): PHONG
Điểm rubric liên quan: TCP chat (20% - điểm cao nhất), Error handling (10%)
Đọc trước: đề mục 3.3, 5.1, 5.3; protocol.py. ĐỌC TIẾP: filetransfer.py (nơi nhận file khi kết nối là kiểu "file").

BỨC TRANH CHUNG (đề mục 5.1: mỗi kết nối TCP có thread nhận riêng, "TCP receiver one per connection")
  Thread acceptor : CHỜ accept(). Mỗi kết nối mới -> tạo MỘT thread riêng chạy handle_connection.
                    Vì sao? recv() chặn: dùng chung một thread thì người này đang chờ sẽ làm kẹt người kia.
  Thread nhận tin : CHỜ recv() của MỘT kết nối chat: hiện tin, đếm unread, dọn dẹp khi đóng.
  Main thread     : /chat, /leave, gửi tin (open_chat, send_text, leave_chat) - gọi từ lanchat.py.
  Chỉ MAIN thread gửi trên socket chat, nên hai thread không bao giờ cùng sendall một socket (byte hai frame
  không bị trộn). Gửi file dùng kết nối riêng (filetransfer.py).

MỖI KẾT NỐI BẮT ĐẦU BẰNG  HI|<name>|<kind>|  (accept() chỉ thấy (IP, cổng tạm), không biết tên người gọi
  và không biết họ muốn chat hay gửi file):  kind = "chat" -> lưu kết nối, nhận tin;  kind = "file" -> nhận file.

MỘT KẾT NỐI CHAT CHO MỖI CẶP NGƯỜI: A /chat B => A connect tới B; B accept và lưu kết nối đó. Khi B gõ /chat A thì
  DÙNG LẠI kết nối ấy (kết nối đi hai chiều; cả hai bên đều có thread nhận tin). Chuyển sang người khác KHÔNG
  đóng kết nối cũ: tin của người đó vẫn tới ngầm và được đếm "unread".

TIN CỦA NGƯỜI KHÔNG PHẢI PARTNER (đề mục 3.3): lưu lại + in "[*] New message from Huy (1 unread)";
  khi /chat người đó thì in lại các tin chưa đọc.

CÁC BẪY
  1. recv trả b"" / ConnectionError: peer thoát hoặc crash -> báo "disconnected", dọn kết nối, KHÔNG để thread chết im lặng.
  2. Windows: SO_REUSEADDR cho phép HAI chương trình cùng nghe một cổng TCP (kết nối đi lạc!). Dùng
     SO_EXCLUSIVEADDRUSE để cổng bận thì báo lỗi rõ ràng. Linux/macOS thì dùng SO_REUSEADDR để chạy lại ngay.
  3. /leave gỡ kết nối khỏi danh sách TRƯỚC khi đóng socket -> thread nhận tin thấy "không còn là kết nối đang
     được lưu" nên im lặng, không báo "mất kết nối" sai.
  4. In màn hình (ui.show_message) luôn NGOÀI lock: các hàm state.* đã nhả lock rồi mới trả về.
"""
import os
import socket
import threading

import config
import filetransfer
import protocol
import state
import ui


# ======================================================================== phía NHẬN
def start_acceptor(port):
    """Mở cổng TCP `port`, bắt đầu chờ kết nối ở một thread daemon. Trả về server socket (để /quit đóng lại).
    Cổng đang bận -> ném OSError (lanchat.py báo "hãy dùng --port khác")."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if os.name == "nt":
        server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)   # xem BẪY #2
    else:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(("", port))              # "" = nhận kết nối từ mọi card mạng
        server.listen()
    except OSError:
        server.close()
        raise
    server.settimeout(1.0)                   # để vòng accept thỉnh thoảng nhìn cờ dừng
    threading.Thread(target=_accept_loop, args=(server,), daemon=True, name="tcp-acceptor").start()
    return server


def _accept_loop(server):
    """Thread acceptor: lặp accept(); mỗi kết nối mới chạy handle_connection ở một thread riêng."""
    while not state.is_stopped():
        try:
            conn, addr = server.accept()
        except socket.timeout:
            continue
        except OSError:
            return                           # server socket đã bị đóng (/quit)
        threading.Thread(target=handle_connection, args=(conn, addr), daemon=True, name="tcp-receiver").start()


def handle_connection(conn, addr):
    """Thread của MỘT kết nối đến. Đọc frame HI để biết đây là kết nối chat hay file:
         kind "chat" -> lưu vào state, chạy vòng nhận tin tới khi kết nối đóng
         kind "file" -> đọc frame FILE rồi nhận file (kết nối file chỉ chở MỘT file)
    Chống treo: kết nối mới phải gửi xong HI trong 5 giây, không thì bị đóng (đề phòng kết nối rác)."""
    try:
        conn.settimeout(config.HANDSHAKE_TIMEOUT)
        frame = protocol.read_frame(conn)
        if frame[0] != "HI":
            raise ValueError("the first frame must be HI")
        _, name, kind = frame

        if kind == protocol.KIND_FILE:
            frame = protocol.read_frame(conn)
            if frame[0] != "FILE":
                raise ValueError("a file connection must send a FILE frame after HI")
            conn.settimeout(config.FILE_STALL_TIMEOUT)   # nhận file: 30 s không có byte nào thì coi là đứt
            filetransfer.receive_file(conn, name, frame[1], frame[2])
            protocol.close_quietly(conn)
        else:
            conn.settimeout(None)                        # chat: chờ tin vô thời hạn
            old_conn = state.add_connection(name, conn)
            if old_conn is not None:                     # kết nối chat cũ với người này (có thể đã chết) -> đóng
                protocol.close_quietly(old_conn)
            _receive_loop(conn, name)
    except (OSError, ValueError):
        protocol.close_quietly(conn)                     # kết nối rác hoặc đứt giữa chừng: bỏ, không crash


def _receive_loop(sock, name):
    """Nhận tin từ `name` trên `sock` cho tới khi kết nối đóng. Cả bên connect lẫn bên accept đều chạy hàm này."""
    reason = "left the chat"
    try:
        while True:
            frame = protocol.read_frame(sock)
            if frame[0] == "MSG":
                _show_incoming(name, frame[1])
            elif frame[0] == "BYE":
                break                                    # đối phương chủ động rời chat
            else:
                raise ValueError(f"unexpected {frame[0]} frame on a chat connection")
    except ConnectionError:
        reason = "disconnected (connection lost)"        # đối phương tắt đột ngột / mất mạng
    except (OSError, ValueError) as error:
        reason = f"disconnected ({error})"               # lỗi khác hoặc dữ liệu hỏng
    finally:
        _cleanup(sock, name, reason)


def _show_incoming(name, text):
    """Một tin vừa đến từ `name`: lưu vào lịch sử rồi hiện ngay (nếu là partner) hoặc đếm chưa đọc."""
    line = f"[{name}] {text}"
    is_partner, unread = state.record_incoming(name, line)   # sửa dữ liệu TRONG lock (bên trong state)
    if is_partner:
        ui.show_message(line)                                # in màn hình NGOÀI lock
    else:
        ui.show_message(f"[*] New message from {name} ({unread} unread)")


def _cleanup(sock, name, reason):
    """Dọn dẹp khi kết nối kết thúc. Chỉ báo người dùng nếu kết nối này vẫn là kết nối đang được lưu
    (đã bị /leave hoặc bị kết nối mới thay thế thì im lặng, tránh báo lặp)."""
    was_registered, was_partner = state.remove_connection(name, sock)
    protocol.close_quietly(sock)
    if was_registered:
        ui.show_message(f"[*] {name} {reason}." + (" Chat closed." if was_partner else ""))


# ======================================================================== phía GỌI ĐI + GỬI
def connect_to(name):
    """Mở kết nối chat tới `name`: connect -> gửi HI -> lưu -> bật thread nhận tin.
    Trả về socket, hoặc None nếu thất bại (đã báo lỗi; ví dụ người đó vừa offline: timeout 3 s, không crash)."""
    peer = state.get_peer(name)
    if peer is None:
        ui.show_message(f"[!] Cannot connect to {name}: not online")
        return None
    try:
        sock = protocol.connect_and_introduce(peer["ip"], peer["tcp_port"], state.get_name(), protocol.KIND_CHAT)
    except OSError as error:
        ui.show_message(f"[!] Cannot connect to {name}: {error}")
        return None
    old_sock = state.add_connection(name, sock)
    if old_sock is not None:
        protocol.close_quietly(old_sock)
    threading.Thread(target=_receive_loop, args=(sock, name), daemon=True, name="chat-receiver").start()
    return sock


def open_chat(name):
    """/chat: dùng lại kết nối có sẵn hoặc mở mới, đặt `name` làm partner, in lại tin chưa đọc."""
    if state.get_connection(name) is None:
        if connect_to(name) is None:
            return False                                     # connect_to đã báo lỗi
        peer = state.get_peer(name)
        address = f" ({peer['ip']}:{peer['tcp_port']})" if peer else ""
        header = f"[*] Connected to {name}{address}"
    else:
        header = f"[*] Switched to {name}"
    state.set_partner(name)
    ui.show_lines([header] + _lines_to_replay(name))
    return True


def _lines_to_replay(name):
    """Các dòng in lại khi mở chat: tin chưa đọc, hoặc vài tin gần nhất nếu không có tin chưa đọc."""
    unread = state.take_unread(name)                         # lấy số chưa đọc và đặt lại về 0
    if unread > 0:
        return [f"[*] {unread} unread:"] + state.history_tail(name, unread)
    recent = state.history_tail(name, config.HISTORY_REPLAY_LINES)
    return ["[*] Recent messages:"] + recent if recent else []


def send_text(text):
    """Gửi `text` cho partner hiện tại và hiện dòng "[Tên_mình] text". Chưa /chat ai thì nhắc."""
    name = state.get_partner()
    if name is None:
        ui.show_message("[*] No chat open. Use /chat <name|number> first (see /list).")
        return
    if len(text.encode(config.ENCODING)) > config.MAX_MSG_BYTES:
        ui.show_message("[!] Message too long.")
        return
    sock = state.get_connection(name)
    if sock is None:                                         # kết nối đã mất mà partner chưa kịp reset
        state.set_partner(None)
        ui.show_message(f"[!] Connection with {name} is closed. Use /chat {name} to reconnect.")
        return
    try:
        protocol.send_msg(sock, text)                        # gửi qua mạng NGOÀI lock (có thể chậm)
    except OSError as error:
        state.remove_connection(name, sock)
        protocol.close_quietly(sock)
        ui.show_message(f"[!] Could not send to {name}: {error}. Chat closed.")
        return
    line = f"[{state.get_name()}] {text}"
    state.record_outgoing(name, line)
    ui.show_message(line)


def leave_chat():
    """/leave: gửi BYE, đóng kết nối với partner hiện tại, không còn partner. Người kia thấy "left the chat"."""
    name = state.get_partner()
    if name is None:
        ui.show_message("[*] You are not in a chat.")
        return
    sock = state.get_connection(name)
    if sock is not None:
        state.remove_connection(name, sock)   # gỡ khỏi danh sách TRƯỚC (xem BẪY #3)
        _say_goodbye(sock)
    state.set_partner(None)
    ui.show_message(f"[*] Left the chat with {name}.")


def close_all():
    """/quit: gửi BYE và đóng mọi kết nối chat. Một kết nối hỏng không được làm các kết nối sau bị bỏ sót."""
    for _name, sock in state.pop_all_connections():
        _say_goodbye(sock)


def _say_goodbye(sock):
    try:
        protocol.send_bye(sock)
    except OSError:
        pass                                  # đối phương đã mất rồi: không sao
    protocol.close_quietly(sock)
