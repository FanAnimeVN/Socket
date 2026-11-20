"""
config.py - Hằng số dùng chung. KHÔNG có logic ở đây, chỉ có "luật chơi" của đồ án.

VIỆC CỦA FILE NÀY: gom mọi con số/chuỗi cố định (cổng, chu kỳ, timeout...) vào MỘT chỗ.
AI DÙNG: hầu hết các file khác.   Cách dùng:  import config  rồi gọi  config.UDP_PORT
ĐỌC TIẾP: lanchat.py (điểm vào của chương trình).

Khi vấn đáp bị hỏi "con số 3 giây / 10 giây lấy ở đâu?" -> chỉ vào đây + chỉ vào đề (mục 3.1).
"""
import os

# Thư mục chứa dự án (để lưu file nhận được đúng chỗ dù chạy lệnh từ thư mục nào)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- UDP (discovery + status) -- đề mục 3.1, 3.2 ----
UDP_PORT = 9999              # cổng UDP cố định, mọi peer cùng lắng nghe cổng này
BROADCAST_INTERVAL = 3       # giây: chu kỳ gửi HELLO
PEER_TIMEOUT = 10            # giây: quá lâu không nghe thấy peer -> coi như offline
DEFAULT_BCAST = "255.255.255.255"   # địa chỉ broadcast mặc định (đổi bằng --bcast)
UDP_BUFFER_SIZE = 1024       # byte: kích thước tối đa của một gói HELLO nhận được
NAME_CHECK_SECONDS = 3.5     # giây: lúc khởi động, nghe xem có ai đã dùng tên mình chưa (> chu kỳ 3 s)

# ---- TCP (chat + file) -- đề mục 3.3, 3.4 ----
DEFAULT_TCP_PORT = 5000      # cổng TCP mặc định (chạy nhiều instance trên 1 máy thì đổi bằng --port)
CONNECT_TIMEOUT = 3          # giây: chờ tối đa khi connect tới peer (tránh treo khi peer đã offline)
HANDSHAKE_TIMEOUT = 5        # giây: kết nối mới đến phải gửi xong frame HI trong thời gian này
ENCODING = "utf-8"           # mã hóa chữ <-> byte. Header và nội dung tin đều dùng cái này
HEADER_MAX_LEN = 1024        # byte: giới hạn khi đọc header (đề phòng dữ liệu rác làm vòng đọc chạy mãi)
MAX_MSG_BYTES = 1024 * 1024  # byte: tin nhắn tối đa 1 MB (chống dữ liệu rác báo length khổng lồ)

# ---- Tên người dùng ----
MAX_NAME_LEN = 20            # ký tự: độ dài tối đa của --name

# ---- File transfer ----
DOWNLOAD_DIR = os.path.join(PROJECT_DIR, "downloads")   # thư mục lưu file nhận được
FILE_CHUNK_SIZE = 64 * 1024  # byte: mỗi lần đọc/gửi một "khối" (không đọc cả file vào RAM)
PROGRESS_STEP_PERCENT = 10   # in tiến độ mỗi 10% (đừng in mỗi khối, sẽ làm vỡ dòng nhập)
FILE_STALL_TIMEOUT = 30      # giây: đang nhận file mà 30 s không có byte nào -> coi như đứt, xóa file dở

# ---- Chat ----
HISTORY_REPLAY_LINES = 5     # khi /chat lại một người: in lại tối đa chừng này tin gần nhất

# ---- Trạng thái hợp lệ ----
STATUS_ONLINE = "online"
STATUS_AWAY = "away"
VALID_STATUS = (STATUS_ONLINE, STATUS_AWAY)
