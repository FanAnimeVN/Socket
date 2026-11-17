"""
filetransfer.py - Gửi/nhận file qua TCP, có tiến độ %, chạy ở thread riêng để chat không bị đứng.

Người phụ trách: PHONG        Người review (teach-back): NGỌC
Điểm rubric liên quan: File transfer (15%), Error handling (10%)
Đọc trước: đề mục 3.4, 5.1 (bảng thread), 5.3; cập nhật 09/11 ("TCP receiver one per connection")

----------------------------------------------------------------------------------------
THIẾT KẾ ĐỀ XUẤT: MỖI LẦN GỬI FILE = MỘT KẾT NỐI TCP RIÊNG
  Người gửi : connect tới peer -> HI|tên| -> FILE|tên_file|kích_thước| -> các khối byte -> đóng.
  Người nhận: tcp_chat.handle_connection đọc HI, thấy frame FILE -> gọi receive_file(...) ở đây.
  Lợi ích: không đụng kết nối chat; không cần lock gửi; chat chạy bình thường trong lúc gửi.

CÁC BẪY
  1. KHÔNG đọc cả file vào RAM. Đọc từng khối (config.FILE_CHUNK_SIZE) bằng open(path, "rb").
  2. Nhận: phải nhận ĐÚNG `size` byte. Mỗi lần recv tối đa min(CHUNK, còn_lại) để không nuốt dữ liệu thừa.
  3. Tên file từ mạng KHÔNG đáng tin: "..\\..\\x.exe" có thể ghi ra ngoài downloads/.
     => chỉ giữ phần tên cuối (os.path.basename) và loại ký tự lạ. Tên trùng -> đổi tên (file(1).pdf...).
  4. Lỗi/đứt giữa chừng: đóng file, XÓA file dở (đề mục 5.3), báo lỗi cho người dùng.
  5. Tiến độ: chỉ in khi tăng thêm mỗi config.PROGRESS_STEP_PERCENT (10%) - in mỗi khối sẽ spam và phá dòng nhập.
     In bằng ui.show_message (không print trực tiếp!).
  6. File kích thước 0 byte: phép chia % cho 0 -> xử lý riêng.
  7. Tự kiểm tra đúng/sai: so hash file gốc và file nhận:   certutil -hashfile <file> SHA256   (Windows)
----------------------------------------------------------------------------------------
"""
import os
import socket
import threading

import config
import protocol
import state
import ui


def send_file_async(peer_name, path):
    """Thực hiện /send <file>: kiểm tra nhanh rồi chạy _send_file_worker trong thread mới, trả về ngay.

    Việc cần làm (làm ĐỒNG BỘ, trước khi tạo thread, để báo lỗi tức thì):
      1. path có phải file thật không? (os.path.isfile) Không -> ui.show_message("[!] File not found: ...") rồi return.
      2. Có đang chat với ai không? (peer_name None -> nhắc /chat).
      3. size = os.path.getsize(path).
      4. threading.Thread(target=_send_file_worker, args=(...), daemon=True).start()
    """
    raise NotImplementedError("TODO: send_file_async")


def _send_file_worker(peer_name, path, size):
    """Thread gửi file.

    Việc cần làm:
      1. Lấy ip/port của peer từ state.peers (trong lock). Peer không còn -> báo lỗi.
      2. Connect (timeout config.CONNECT_TIMEOUT) -> protocol.send_hi -> protocol.send_file_header(filename, size).
         filename gửi đi chỉ là tên (os.path.basename), KHÔNG gửi đường dẫn đầy đủ của máy mình.
      3. Mở file "rb"; vòng lặp: read(config.FILE_CHUNK_SIZE) -> sendall -> cộng sent -> báo tiến độ.
      4. Hết file: in "[*] Sending slides.pdf (2.4 MB) ... 100%  Done."
      5. try/except OSError: đứt kết nối giữa chừng -> báo lỗi rõ ràng.
      6. finally: đóng socket (và file nếu không dùng with).
    Vì sao cần thread riêng? Nếu gửi ở main thread thì chuyện gì xảy ra với việc gõ/nhận tin?
    """
    raise NotImplementedError("TODO: _send_file_worker")


def receive_file(conn, sender_name, filename, size):
    """Nhận `size` byte từ conn và lưu thành file trong config.DOWNLOAD_DIR. (Chạy trong receiver thread.)

    Việc cần làm:
      1. os.makedirs(config.DOWNLOAD_DIR, exist_ok=True).
      2. safe = _safe_filename(filename); đường dẫn đích = _unique_path(...) để không ghi đè file cũ.
      3. Mở file "wb"; lặp tới khi nhận đủ size: recv(min(CHUNK, còn_lại)) ; chunk rỗng -> peer đứt -> lỗi.
      4. Ghi từng khối + báo tiến độ (cùng quy tắc 10%).
      5. Nhận đủ -> in "[*] Received slides.pdf from Minh (saved to downloads/)".
      6. Có lỗi (ConnectionError/OSError) -> đóng file, os.remove file dở, in lỗi.
    """
    raise NotImplementedError("TODO: receive_file")


def _safe_filename(filename):
    """Làm sạch tên file nhận từ mạng. Gợi ý: os.path.basename, thay ký tự cấm trên Windows (< > : " / \\ | ? *),
    tên rỗng thì đặt tên mặc định. Tự viết vài ví dụ kiểm tra: "..\\..\\evil.exe", "a/b/c.txt", "".
    """
    raise NotImplementedError("TODO: _safe_filename")


def _unique_path(directory, filename):
    """Nếu directory/filename đã tồn tại thì thử filename(1), filename(2)... (giữ nguyên đuôi mở rộng:
    os.path.splitext). Trả về đường dẫn chưa tồn tại."""
    raise NotImplementedError("TODO: _unique_path")


def format_size(num_bytes):
    """12345678 -> "11.8 MB". Dùng để in "(2.4 MB)" như ví dụ của đề. Gợi ý: chia dần cho 1024."""
    raise NotImplementedError("TODO: format_size")


def _should_report(percent, last_reported):
    """Trả về True nếu nên in tiến độ lúc này (đã tăng >= PROGRESS_STEP_PERCENT kể từ lần in trước).
    Tách thành hàm nhỏ để dùng chung cho gửi và nhận, và dễ tự test bằng tay."""
    raise NotImplementedError("TODO: _should_report")
