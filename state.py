"""
state.py - Dữ liệu DÙNG CHUNG giữa các thread.

Người phụ trách: Huy chốt cấu trúc, cả nhóm dùng      Người review: cả nhóm
Điểm rubric liên quan: TCP chat (20%) và "Shared data phải có lock" (đề mục 5.1)

Vì sao cần file này?
  Nhiều thread cùng đọc/ghi các biến dưới đây (UDP listener ghi `peers`, main thread đọc để /list,
  TCP receiver ghi `unread`...). Nếu không có lock thì hai thread có thể sửa cùng lúc -> dữ liệu hỏng.

=== 3 LUẬT BẮT BUỘC (vi phạm là treo/lỗi khó tìm) ===
  1. Mọi truy cập vào peers / connections / unread / history / current_partner / my_status
     phải nằm trong:   with state.data_lock:  ...
  2. KHÔNG in ra màn hình (ui.show_message) khi đang giữ data_lock.
     Cách làm: trong lock chỉ lấy/sửa dữ liệu, ra khỏi lock rồi mới in.
  3. threading.Lock KHÔNG "reentrant": đang giữ lock mà gọi hàm khác cũng xin lock đó
     -> thread tự chờ chính mình, treo vĩnh viễn (deadlock). Đừng lồng hàm có lock trong hàm có lock.

=== CÁI BẪY PYTHON ===
  Biến số/chuỗi gán lại (current_partner = "Minh") phải viết   state.current_partner = "Minh"
  Nếu viết   from state import current_partner   rồi gán, bạn chỉ đổi bản sao cục bộ,
  module khác vẫn thấy giá trị cũ. => Luôn   import state   rồi dùng   state.xxx
  (dict/list như peers thì sửa nội dung bên trong được, nhưng giữ thói quen dùng state.xxx cho thống nhất).
"""
import threading

# ---- Thông tin của chính mình (lanchat.py gán lúc khởi động) ----
my_name = ""
my_tcp_port = 0
my_status = "online"          # "online" | "away"  (đổi bằng /status)

# ---- Người đang online: do discovery.py ghi, nơi khác đọc ----
# Cấu trúc gợi ý (nhóm có thể đổi, nhưng phải ghi lại vào docs/PROTOCOL.md):
#   peers[name] = {"ip": "192.168.1.12", "tcp_port": 6000, "status": "online", "last_seen": <time.time()>}
# Khóa là `name` vì chạy nhiều instance trên MỘT máy thì IP trùng nhau.
peers = {}

# ---- Kết nối chat đang mở: do tcp_chat.py quản lý ----
# connections[name] = socket đang nối với người đó (chỉ MỘT kết nối chat cho mỗi người)
connections = {}

# ---- Tin chưa đọc và lịch sử: dùng cho "[*] New message from Huy (1 unread)" ----
unread = {}      # unread[name] = số tin chưa đọc (int)
history = {}     # history[name] = list các dòng đã hiển thị/lưu (str)

# ---- Đang chat với ai? None = chưa mở chat ----
current_partner = None

# ---- Công cụ đồng bộ ----
data_lock = threading.Lock()     # bảo vệ TẤT CẢ dữ liệu ở trên
stop_event = threading.Event()   # đặt (set) khi /quit để các thread nền biết đường dừng
