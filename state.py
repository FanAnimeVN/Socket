"""
state.py - DỮ LIỆU DÙNG CHUNG giữa các thread, và LOCK bảo vệ chúng.

Người phụ trách giải thích khi vấn đáp: Huy chốt cấu trúc, cả nhóm dùng
Điểm rubric liên quan: TCP chat (20%) và "Shared data phải có lock" (đề mục 5.1)
ĐỌC TIẾP: protocol.py (khung tin TCP), rồi discovery.py (nơi ghi danh sách online).

VÌ SAO CẦN FILE NÀY?
  Nhiều thread cùng đọc/ghi các dữ liệu dưới đây (UDP listener ghi danh sách online, main thread đọc để /list,
  thread nhận tin ghi số tin chưa đọc...). Không có lock thì hai thread có thể sửa cùng lúc -> dữ liệu hỏng.

CÁCH DÙNG:  import state   rồi gọi hàm, ví dụ  state.get_name()  state.record_incoming(...)
  Dữ liệu nằm trong biến bắt đầu bằng "_" (riêng tư): chỉ đọc/ghi qua hàm của file này. Mỗi hàm TỰ lấy
  _data_lock, nên nơi khác gọi hàm là an toàn, không cần tự khóa.

3 LUẬT (vi phạm là treo hoặc lỗi khó tìm):
  1. Hàm ở đây KHÔNG in ra màn hình. In là việc của nơi gọi (ui.show_message), SAU khi hàm đã trả về (lock đã nhả).
  2. Hàm ở đây không gọi hàm khác của file này khi đang giữ lock. threading.Lock KHÔNG "reentrant":
     đang giữ lock mà xin lock lần nữa thì thread tự chờ chính mình mãi mãi (deadlock).
  3. Hàm trả về BẢN SAO (list/dict copy), không trả thẳng dữ liệu gốc, để bên ngoài duyệt thoải mái
     trong lúc thread khác đang sửa (tránh lỗi "dictionary changed size during iteration").

4 NHÓM DỮ LIỆU:
  1. Thông tin của MÌNH      : tên, cổng TCP, trạng thái online/away
  2. Người đang ONLINE       : _peers[name] = {ip, tcp_port, status, last_seen}   (khóa là tên vì chạy nhiều
                               instance trên MỘT máy thì IP giống hệt nhau)
  3. CHAT                    : kết nối đang mở, người đang chat cùng (partner), tin chưa đọc, lịch sử
  4. Cờ DỪNG                 : bật khi /quit để mọi thread nền tự thoát
"""
import threading
import time

import config

_data_lock = threading.Lock()          # bảo vệ TẤT CẢ dữ liệu bên dưới
_stop_event = threading.Event()        # "công tắc" mà mọi thread cùng nhìn được

# ---- 1. thông tin của mình ----
_name = ""
_tcp_port = 0
_status = config.STATUS_ONLINE

# ---- 2. người đang online (do discovery.py ghi) ----
_peers = {}

# ---- 3. chat (do tcp_chat.py quản lý) ----
_connections = {}      # _connections[name] = socket đang nối với người đó (MỘT kết nối chat cho mỗi người)
_partner = None        # tên người đang chat cùng; None = chưa mở chat nào
_unread = {}           # _unread[name] = số tin chưa đọc
_history = {}          # _history[name] = list các dòng đã hiện (cả tin gửi lẫn tin nhận)


# ======================================================================== 1. thông tin của mình
def set_identity(name, tcp_port):
    """Lưu tên và cổng TCP của mình (gọi một lần lúc khởi động)."""
    global _name, _tcp_port
    with _data_lock:
        _name = name
        _tcp_port = tcp_port


def get_name():
    with _data_lock:
        return _name


def get_tcp_port():
    with _data_lock:
        return _tcp_port


def get_status():
    with _data_lock:
        return _status


def set_status(status):
    """Đổi trạng thái. Trả về True nếu hợp lệ (online/away); False nếu không (và không đổi gì)."""
    global _status
    if status not in config.VALID_STATUS:
        return False
    with _data_lock:
        _status = status
    return True


# ======================================================================== 2. người đang online
def update_peer(name, ip, tcp_port, status):
    """Ghi nhận vừa nghe HELLO từ `name`. Trả về:
        "new"    người mới xuất hiện
        "status" đã có nhưng đổi trạng thái (online <-> away)
        "same"   không có gì mới (chỉ làm mới last_seen)"""
    with _data_lock:
        old = _peers.get(name)
        _peers[name] = {"ip": ip, "tcp_port": tcp_port, "status": status, "last_seen": time.time()}
    if old is None:
        return "new"
    if old["status"] != status:
        return "status"
    return "same"


def remove_expired_peers(timeout, now=None):
    """Xóa người im lặng quá `timeout` giây. Trả về list tên vừa bị xóa (để nơi gọi báo "offline")."""
    if now is None:
        now = time.time()
    with _data_lock:
        gone = [name for name, info in _peers.items() if now - info["last_seen"] > timeout]
        for name in gone:
            del _peers[name]
    return sorted(gone)


def get_peers_sorted():
    """[(name, info_copy), ...] sắp theo tên. Số thứ tự trong /list lấy từ thứ tự này nên /chat <số> luôn khớp."""
    with _data_lock:
        ordered = sorted(_peers.items(), key=lambda item: item[0].lower())
        return [(name, dict(info)) for name, info in ordered]


def get_peer(name):
    """Bản sao thông tin của `name`, hoặc None nếu không online."""
    with _data_lock:
        info = _peers.get(name)
        return dict(info) if info is not None else None


# ======================================================================== 3. chat
def add_connection(name, sock):
    """Lưu kết nối với `name`. Nếu đã có kết nối cũ thì kết nối MỚI thay thế và hàm trả về socket cũ để nơi gọi
    đóng nó (kết nối cũ thường đã chết, ví dụ đối phương vừa khởi động lại)."""
    with _data_lock:
        old = _connections.get(name)
        _connections[name] = sock
        return old


def get_connection(name):
    with _data_lock:
        return _connections.get(name)


def remove_connection(name, sock):
    """Bỏ kết nối `sock` của `name` - NHƯNG chỉ khi nó vẫn là kết nối đang được lưu. Trả về (was_registered, was_partner):
      was_registered = False: kết nối này đã bị thay thế hoặc đã dọn rồi -> nơi gọi nên im lặng, đừng báo lại.
      was_partner    = True : `name` đang là partner (và partner được đặt lại thành None)."""
    global _partner
    with _data_lock:
        if _connections.get(name) is not sock:
            return False, False
        del _connections[name]
        was_partner = _partner == name
        if was_partner:
            _partner = None
        return True, was_partner


def pop_all_connections():
    """Lấy ra mọi kết nối rồi xóa sạch (dùng khi /quit). Trả về [(name, sock), ...]."""
    global _partner
    with _data_lock:
        items = list(_connections.items())
        _connections.clear()
        _partner = None
        return items


def set_partner(name):
    """Đặt người đang chat cùng (None = không ai)."""
    global _partner
    with _data_lock:
        _partner = name


def get_partner():
    with _data_lock:
        return _partner


def record_incoming(name, line):
    """Ghi một tin vừa NHẬN từ `name`. Trả về (is_partner, unread_count):
       is_partner = True  -> hiện tin ngay.
       is_partner = False -> tính là chưa đọc; unread_count là tổng số chưa đọc của người đó.
    Làm cả hai việc trong MỘT lần lấy lock để kết quả luôn nhất quán."""
    with _data_lock:
        _history.setdefault(name, []).append(line)
        if _partner == name:
            return True, 0
        _unread[name] = _unread.get(name, 0) + 1
        return False, _unread[name]


def record_outgoing(name, line):
    """Ghi một tin mình vừa GỬI cho `name` vào lịch sử."""
    with _data_lock:
        _history.setdefault(name, []).append(line)


def unread_count(name):
    with _data_lock:
        return _unread.get(name, 0)


def take_unread(name):
    """Trả về số tin chưa đọc của `name` rồi đặt về 0 (gọi khi mở chat với người đó)."""
    with _data_lock:
        return _unread.pop(name, 0)


def history_tail(name, count):
    """`count` dòng gần nhất trong lịch sử với `name` (bản sao). count <= 0 -> list rỗng."""
    if count <= 0:
        return []
    with _data_lock:
        return list(_history.get(name, [])[-count:])


# ======================================================================== 4. cờ dừng
def request_stop():
    """Bật cờ: mọi thread nền sẽ dừng ở vòng lặp kế tiếp (gọi khi /quit)."""
    _stop_event.set()


def is_stopped():
    return _stop_event.is_set()
