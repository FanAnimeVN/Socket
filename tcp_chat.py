"""
tcp_chat.py - Chat qua TCP: nhận kết nối, nhận tin, mở/đóng chat, gửi tin.

Người phụ trách: HUY          Người review (teach-back): PHONG
Điểm rubric liên quan: TCP chat (20% - điểm cao nhất), Error handling (10%)
Đọc trước: đề mục 3.3, 5.1, 5.3; protocol.py (viết xong trước file này)

----------------------------------------------------------------------------------------
BỨC TRANH CHUNG
  * TCP acceptor thread : accept() chờ kết nối mới; mỗi kết nối -> tạo 1 RECEIVER thread riêng
                          (đây chính là "TCP receiver (one per connection)" trong cập nhật 09/11 của đề).
  * Receiver thread     : vòng lặp read_frame() cho 1 kết nối: MSG -> hiện/lưu; BYE hoặc lỗi -> dọn dẹp.
  * Main thread         : /chat, /leave, gửi tin (send_text) - gọi từ lanchat.py.

MỖI KẾT NỐI TCP BẮT ĐẦU BẰNG frame HI|<name>|
  Vì accept() chỉ cho biết (IP, cổng tạm), KHÔNG cho biết tên người gọi, và trên 1 máy mọi peer cùng IP.

MỘT KẾT NỐI CHAT CHO MỖI CẶP NGƯỜI
  A /chat B => A connect tới B. B thấy kết nối đến (accept) và lưu vào state.connections["A"].
  Khi B gõ /chat A thì DÙNG LẠI kết nối đó (đừng mở thêm). Kết nối hai chiều: cả hai bên đều gửi/nhận
  trên cùng socket, nên CẢ bên connect lẫn bên accept đều phải có receiver thread.

TIN CỦA NGƯỜI KHÔNG PHẢI PARTNER HIỆN TẠI (đề mục 3.3)
  Lưu vào state.history + tăng state.unread, in "[*] New message from Huy (1 unread)".
  Khi /chat người đó -> in lại các tin đã lưu rồi reset unread về 0.

CÁC BẪY
  1. Không bao giờ gọi ui.show_message khi đang giữ state.data_lock (xem state.py).
  2. recv trả b"" / ConnectionError / ConnectionResetError -> peer thoát hoặc crash: báo
     "[*] Minh disconnected", xóa khỏi state.connections, đóng socket, KHÔNG để thread chết im lặng.
  3. Hai thread cùng sendall trên một socket sẽ trộn byte -> file KHÔNG gửi trên kết nối chat
     (filetransfer.py mở kết nối riêng).
  4. Server socket: setsockopt SO_REUSEADDR để chạy lại ngay cùng cổng không bị "Address already in use".
  5. connect tới người vừa offline: dùng timeout (config.CONNECT_TIMEOUT), bắt OSError, báo lỗi, không crash.
----------------------------------------------------------------------------------------
"""
import socket
import threading

import config
import discovery
import filetransfer
import protocol
import state
import ui


def start_acceptor(port):
    """Tạo server socket, bắt đầu nghe, chạy _accept_loop trong một thread daemon.

    Việc cần làm: socket TCP -> SO_REUSEADDR -> bind(("", port)) -> listen() -> Thread(daemon=True).start().
    Nếu bind lỗi (cổng bận) -> báo rõ "cổng X đang được dùng, hãy chạy với --port khác" rồi thoát gọn.
    Trả về server socket (để lúc /quit đóng nó lại).
    """
    raise NotImplementedError("TODO: start_acceptor")


def _accept_loop(server_sock):
    """Thread acceptor: lặp accept() -> với mỗi (conn, addr) tạo thread chạy handle_connection.

    Dừng khi server_sock bị đóng (accept sẽ ném OSError) hoặc state.stop_event set.
    Vì sao mỗi kết nối cần một thread riêng? (recv chặn: nếu dùng chung một thread thì người này
    đang chờ sẽ làm kẹt người kia.)
    """
    raise NotImplementedError("TODO: _accept_loop")


def handle_connection(conn, addr, known_name=None):
    """Receiver thread của MỘT kết nối. Chạy cho tới khi kết nối đóng.

    known_name = None  -> kết nối do người khác gọi tới: frame đầu PHẢI là HI, lấy tên từ đó.
    known_name = "Minh" -> kết nối mình tự connect đi (connect_to): đã biết tên, không cần đợi HI.

    Việc cần làm:
      1. (nếu chưa biết tên) read_frame -> phải là ("HI", name), nếu không thì đóng + bỏ.
      2. Đăng ký state.connections[name] = conn (trong lock). Đã có kết nối cũ với tên này thì xử lý ra sao?
         (nhóm quyết: giữ kết nối cũ & đóng kết nối mới? ghi vào docs/PROTOCOL.md)
      3. Vòng lặp read_frame:
           ("MSG", text)  -> _on_message(name, text)
           ("BYE",)       -> thoát vòng lặp
           ("FILE", filename, size) -> đây là KẾT NỐI GỬI FILE: gọi filetransfer.receive_file(...)
                                       rồi kết thúc (kết nối file chỉ chở một file).
      4. Bắt ConnectionError/OSError/ValueError -> thoát vòng lặp (peer crash hoặc dữ liệu hỏng).
      5. finally: dọn dẹp (xóa khỏi connections nếu đúng là kết nối này, đóng conn, báo disconnected
         nếu đó là partner hiện tại thì current_partner = None).
    """
    raise NotImplementedError("TODO: handle_connection")


def _on_message(name, text):
    """Xử lý một tin vừa nhận từ `name`.

    - Ghi vào state.history[name].
    - Nếu name == state.current_partner: ui.show_message(f"[{name}] {text}")
    - Ngược lại: state.unread[name] += 1 rồi ui.show_message(f"[*] New message from {name} ({n} unread)")
    Nhớ: sửa dữ liệu TRONG lock, in màn hình NGOÀI lock. Bạn phải tự quyết thứ tự các bước cho đúng.
    """
    raise NotImplementedError("TODO: _on_message")


def connect_to(name):
    """Mở kết nối TCP tới peer `name`. Trả về socket, hoặc None nếu thất bại (đã in lỗi).

    Việc cần làm:
      1. Lấy ip + tcp_port của peer từ state.peers (trong lock, rồi ra khỏi lock). Không có -> báo lỗi.
      2. socket.create_connection((ip, port), timeout=config.CONNECT_TIMEOUT) trong try/except OSError.
      3. Sau khi connect: bỏ timeout (sock.settimeout(None)) vì receiver cần chờ vô hạn. Vì sao?
      4. protocol.send_hi(sock, state.my_name).
      5. Tạo thread chạy handle_connection(sock, addr, known_name=name).
    """
    raise NotImplementedError("TODO: connect_to")


def open_chat(name):
    """Thực hiện /chat <name>: dùng lại kết nối có sẵn hoặc connect_to(name); đặt state.current_partner.

    Sau khi mở: in "[*] Connected to Minh (192.168.1.12:6000)", in lại các tin chưa đọc trong
    state.history[name], đặt state.unread[name] = 0.
    Trả về True/False cho caller biết có mở được không.
    Tình huống cần xử lý: /chat chính mình; đang chat với người khác (chuyển partner có đóng kết nối cũ không? gợi ý: KHÔNG,
    chỉ đổi current_partner - để vẫn nhận tin nền và đếm unread).
    """
    raise NotImplementedError("TODO: open_chat")


def send_text(text):
    """Gửi một tin cho partner hiện tại. Chưa mở chat thì báo "[*] Hãy /chat <tên> trước".

    Gợi ý: lấy socket từ state.connections (trong lock) -> protocol.send_msg(sock, text) NGOÀI lock
    (gửi qua mạng có thể chậm, đừng giữ lock lúc đó). Lỗi gửi (OSError) -> báo + dọn kết nối.
    Hiển thị dòng "[Tên_mình] text" cho chính mình + ghi history.
    """
    raise NotImplementedError("TODO: send_text")


def leave_chat():
    """Thực hiện /leave: gửi BYE, đóng kết nối với partner hiện tại, current_partner = None.

    Hỏi trước khi code: sau /leave người kia còn gửi tin được không? (đóng socket -> không). Ghi lại quyết định.
    """
    raise NotImplementedError("TODO: leave_chat")


def close_all():
    """Dùng khi /quit: gửi BYE tới mọi kết nối đang mở, đóng hết socket (bắt lỗi từng cái - một cái hỏng
    không được làm các cái sau bị bỏ sót)."""
    raise NotImplementedError("TODO: close_all")
