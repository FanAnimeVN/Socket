"""
config.py - Hằng số dùng chung. KHÔNG có logic ở đây, chỉ có "luật chơi" của đồ án.

Người phụ trách: cả nhóm (đổi giá trị nào thì BÁO cả nhóm)
Điểm rubric liên quan: UDP discovery (15%), Protocol (10%)

Vì sao tách riêng?
  - Cả nhóm nhìn thấy luật chơi ở MỘT chỗ (cổng UDP, chu kỳ 3 giây, timeout 10 giây...).
  - Khi vấn đáp bị hỏi "con số 3 giây / 10 giây lấy ở đâu?" -> chỉ vào đây + chỉ vào đề (mục 3.1).

Cách dùng ở file khác:
    import config
    ... config.UDP_PORT ...
(Dùng "import config" rồi gọi config.XXX cho dễ đọc, đừng "from config import *".)
"""

# ---- UDP (discovery + status) -- đề mục 3.1, 3.2 ----
UDP_PORT = 9999              # cổng UDP cố định, mọi peer cùng lắng nghe cổng này
BROADCAST_INTERVAL = 3       # giây: chu kỳ gửi HELLO
PEER_TIMEOUT = 10            # giây: quá lâu không nghe thấy peer -> coi như offline
DEFAULT_BCAST = "255.255.255.255"   # địa chỉ broadcast mặc định (có thể đổi bằng --bcast)

# ---- TCP (chat + file) -- đề mục 3.3, 3.4 ----
DEFAULT_TCP_PORT = 5000      # cổng TCP mặc định (chạy nhiều instance trên 1 máy thì đổi bằng --port)
CONNECT_TIMEOUT = 3          # giây: chờ tối đa khi connect tới peer (tránh treo khi peer đã offline)
ENCODING = "utf-8"           # mã hóa chữ <-> byte. Header và nội dung tin đều dùng cái này
HEADER_MAX_LEN = 512         # byte: giới hạn khi đọc header (đề phòng dữ liệu rác làm vòng đọc chạy mãi)

# ---- File transfer ----
DOWNLOAD_DIR = "downloads"   # thư mục lưu file nhận được
FILE_CHUNK_SIZE = 64 * 1024  # byte: mỗi lần đọc/gửi một "khối" (không đọc cả file vào RAM)
PROGRESS_STEP_PERCENT = 10   # in tiến độ mỗi 10% (đừng in mỗi khối, sẽ làm vỡ dòng nhập)

# ---- Trạng thái hợp lệ ----
STATUS_ONLINE = "online"
STATUS_AWAY = "away"
VALID_STATUS = (STATUS_ONLINE, STATUS_AWAY)
