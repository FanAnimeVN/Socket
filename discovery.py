"""
discovery.py - Phát hiện peer qua UDP: broadcast "mình đang online" + lắng nghe người khác.

Người phụ trách: NGỌC          Người review (teach-back): HUY
Điểm rubric liên quan: UDP discovery, online list, status (15%) ; Error handling (10%)
Đọc trước: đề mục 3.1, 3.2, 5.2; udp_broadcast_demo.py (file demo của đề); docs/PROTOCOL.md

----------------------------------------------------------------------------------------
HAI THREAD CỦA FILE NÀY
  * Broadcaster : cứ mỗi config.BROADCAST_INTERVAL (3 s) gửi   HELLO|<name>|<tcp_port>|<status>
  * Listener    : nhận HELLO của người khác, cập nhật state.peers, và XÓA người im quá config.PEER_TIMEOUT (10 s)
Thread nào đang chờ cái gì? (câu hỏi vấn đáp kinh điển)  Broadcaster chờ đồng hồ, Listener chờ gói UDP.

CÁC BẪY
  1. Nhiều instance chạy trên MỘT máy phải bind chung cổng 9999 -> cần SO_REUSEADDR TRƯỚC khi bind.
  2. Phải bật SO_BROADCAST thì mới gửi tới địa chỉ broadcast được.
  3. Bạn nhận lại chính gói broadcast của mình -> phải bỏ qua (so tên). Vì vậy tên phải duy nhất.
  4. recvfrom() chặn mãi nếu không có gói -> dùng sock.settimeout(1.0) để vòng lặp còn có dịp
     (a) kiểm tra state.stop_event  (b) dọn peer hết hạn, kể cả khi không ai gửi gì.
  5. Thông báo "online/offline" gọi ui.show_message NGOÀI data_lock (xem luật trong state.py).
  6. Trên Windows nhiều card mạng (VPN, WSL, Hyper-V...) thì 255.255.255.255 có thể đi sai card
     -> có tham số --bcast để đổi (vd 192.168.1.255). Thử trên 2 máy thật sớm (D6).
  7. Gói UDP lạ/rác không được làm chết thread: parse lỗi thì bỏ qua gói đó.
----------------------------------------------------------------------------------------
"""
import socket
import threading
import time

import config
import state
import ui


def start_discovery(name, tcp_port, bcast=config.DEFAULT_BCAST):
    """Khởi động 2 thread (broadcaster + listener) rồi trả về ngay (không chặn).

    Việc cần làm:
      1. Tạo socket UDP bằng _make_udp_socket().
      2. threading.Thread(target=..., daemon=True) cho _broadcaster_loop và _listener_loop; .start().
      daemon=True nghĩa là gì? Vì sao cần? (thoát chương trình mà thread vẫn chạy thì sao?)
    """
    raise NotImplementedError("TODO: start_discovery")


def _make_udp_socket():
    """Tạo + cấu hình socket UDP, trả về socket đã bind.

    Việc cần làm (xem udp_broadcast_demo.py, hàm make_socket, rồi TỰ viết lại và chú thích từng dòng):
      - socket.socket(AF_INET, SOCK_DGRAM)
      - setsockopt SO_REUSEADDR (và SO_REUSEPORT nếu hệ điều hành có)  -- TRƯỚC bind
      - setsockopt SO_BROADCAST
      - bind(("", config.UDP_PORT))        # "" nghĩa là gì?
    """
    raise NotImplementedError("TODO: _make_udp_socket")


def _broadcaster_loop(sock, name, tcp_port, bcast):
    """Thread 1: gửi HELLO định kỳ cho tới khi state.stop_event được set.

    Việc cần làm:
      - Mỗi vòng: ghép  "HELLO|name|tcp_port|status"  (status lấy từ state.my_status, ĐỌC TRONG LOCK!)
        -> encode -> sock.sendto(dữ_liệu, (bcast, config.UDP_PORT)).
      - Chờ 3 giây giữa các lần. Gợi ý: state.stop_event.wait(config.BROADCAST_INTERVAL)
        (khác gì time.sleep(3)? -> thoát được ngay khi /quit).
      - Bọc try/except OSError: mạng chập chờn thì in cảnh báo, không chết thread.
    """
    raise NotImplementedError("TODO: _broadcaster_loop")


def _listener_loop(sock, my_name):
    """Thread 2: nhận HELLO, cập nhật state.peers, dọn người hết hạn.

    Việc cần làm (mỗi vòng):
      1. sock.settimeout(1.0) (đặt một lần trước vòng lặp). recvfrom(1024) -> (data, addr).
         Bắt socket.timeout -> không có gói, vẫn đi tiếp xuống bước dọn dẹp.
      2. Gói đến: _parse_hello(data). Hợp lệ và tên != my_name thì:
           - trong data_lock: nếu tên CHƯA có trong peers -> đánh dấu là "người mới"
           - cập nhật peers[name] = {ip: addr[0], tcp_port, status, last_seen: time.time()}
           - ra khỏi lock rồi mới ui.show_message("[*] Minh is online")
         (Khi status đổi online<->away có cần thông báo không? Nhóm tự quyết, ghi vào PROTOCOL.md.)
      3. _cleanup_expired(): xóa người có time.time() - last_seen > config.PEER_TIMEOUT,
         rồi thông báo "[*] Minh went offline" (nhớ: thông báo NGOÀI lock).
      4. Dừng khi state.stop_event.is_set().
    """
    raise NotImplementedError("TODO: _listener_loop")


def _parse_hello(data):
    """Bytes -> (name, tcp_port:int, status) hoặc None nếu gói không hợp lệ.

    Việc cần làm: decode (errors="replace"), split("|"), kiểm tra đủ 4 phần, phần đầu == "HELLO",
    tcp_port đổi được sang int, status thuộc config.VALID_STATUS. Sai chỗ nào -> return None.
    Test riêng hàm này bằng vài chuỗi tay (gói thiếu trường, port là chữ, status lạ...) trước khi ghép.
    """
    raise NotImplementedError("TODO: _parse_hello")


def _cleanup_expired():
    """Xóa peer hết hạn khỏi state.peers, trả về list tên đã bị xóa (để caller thông báo ngoài lock)."""
    raise NotImplementedError("TODO: _cleanup_expired")


def get_peers_sorted():
    """Trả về list [(name, info_dict_copy), ...] sắp theo tên - một BẢN SAO, lấy trong data_lock.

    Vì sao phải copy rồi trả về? (nếu trả thẳng state.peers, bên ngoài duyệt trong lúc thread khác sửa
    -> lỗi "dictionary changed size during iteration".)
    Sắp theo tên để số thứ tự trong /list ổn định, /chat <số> dùng lại đúng thứ tự đó.
    """
    raise NotImplementedError("TODO: get_peers_sorted")


def find_peer(arg):
    """arg là tên hoặc số thứ tự (chuỗi, 1-based) -> trả về tên peer, hoặc None nếu không có/ngoài phạm vi.

    Gợi ý: thử arg.isdigit() trước; dùng get_peers_sorted(). So tên: nên phân biệt hoa/thường hay không? Nhóm quyết.
    """
    raise NotImplementedError("TODO: find_peer")


def format_peer_list():
    """Trả về list các dòng để in cho /list, đúng mẫu của đề:
         "  1. Minh   (192.168.1.12)  online"
    Danh sách rỗng thì trả về một dòng thông báo kiểu "[*] Chưa thấy ai online".
    Gợi ý căn cột: str.ljust(độ_rộng).
    """
    raise NotImplementedError("TODO: format_peer_list")


def set_status(status):
    """Đổi trạng thái của mình: "online" | "away" -> state.my_status (trong lock).

    Việc cần làm: kiểm tra status hợp lệ (config.VALID_STATUS), sai thì báo lỗi. Gói HELLO KẾ TIẾP sẽ mang
    status mới (trễ tối đa 3 giây) - hoặc (tùy chọn) gửi một HELLO ngay. Ghi quyết định vào report.
    """
    raise NotImplementedError("TODO: set_status")
