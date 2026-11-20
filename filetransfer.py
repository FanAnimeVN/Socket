"""
filetransfer.py - Gửi/nhận file qua TCP, có tiến độ %, chạy ở thread riêng để chat không bị đứng.

Người phụ trách giải thích khi vấn đáp: PHONG        Người review (teach-back): NGỌC
Điểm rubric liên quan: File transfer (15%), Error handling (10%)
Đọc trước: đề mục 3.4, 5.1 (bảng thread), 5.3; cập nhật 09/11 ("TCP receiver one per connection").
Test: tests/test_filetransfer.py. ĐỌC TIẾP: lanchat.py (cmd_send gọi send_file_async).

THIẾT KẾ: MỖI LẦN GỬI FILE = MỘT KẾT NỐI TCP RIÊNG
  Người gửi : connect -> HI|tên|file| -> FILE|tên_file|kích_thước| -> các khối byte -> đóng   (thread "file-sender")
  Người nhận: tcp_chat.handle_connection đọc HI kind "file" + frame FILE -> gọi receive_file() ở đây.
  Lợi ích: không đụng kết nối chat; không cần khóa gửi; chat chạy bình thường trong lúc gửi.
  Vì sao thread riêng? Nếu gửi ở main thread thì main thread kẹt, không gõ/nhận tin được tới khi gửi xong.

CÁC BẪY
  1. KHÔNG đọc cả file vào RAM: đọc từng khối config.FILE_CHUNK_SIZE (64 KB).
  2. Nhận ĐÚNG `size` byte: mỗi lần recv tối đa min(64 KB, còn_lại) để không đọc lẹm quá phần file.
  3. Tên file từ mạng KHÔNG đáng tin: "..\\..\\x.exe" có thể ghi ra ngoài downloads/ -> _safe_filename làm sạch;
     tên trùng thì đổi thành slides(1).pdf (mở file bằng chế độ "xb": chỉ tạo mới, không bao giờ ghi đè).
  4. Lỗi/đứt giữa chừng: đóng file, XÓA file dở (đề mục 5.3), báo lỗi. 30 s không có byte nào cũng coi là đứt.
  5. Tiến độ: chỉ in mỗi 10% (không in mỗi khối, sẽ spam và phá dòng nhập); in bằng ui.show_message.
  6. File 0 byte: phép chia % cho 0 -> _percent xử lý riêng (coi là 100%).
  7. "Done" nghĩa là đã đưa hết byte cho TCP gửi đi; bên nhận tự kiểm tra đủ byte và xóa file nếu thiếu.
  8. Tự kiểm tra đúng/sai: so hash file gốc và file nhận:   certutil -hashfile <file> SHA256   (Windows)
"""
import os
import threading

import config
import protocol
import state
import ui


# ======================================================================== phía GỬI
def send_file_async(peer_name, path):
    """/send <file>: kiểm tra nhanh (để báo lỗi tức thì) rồi chạy _send_file_worker ở thread mới; trả về NGAY.
    `peer_name` là người đang chat cùng (None nếu chưa /chat ai)."""
    if peer_name is None:
        ui.show_message("[*] No chat open. Use /chat <name|number> first, then /send <file>.")
        return
    if not os.path.isfile(path):
        ui.show_message(f"[!] File not found: {path}")
        return
    size = os.path.getsize(path)
    threading.Thread(target=_send_file_worker, args=(peer_name, path, size), daemon=True, name="file-sender").start()


def _send_file_worker(peer_name, path, size):
    """Thread gửi file: connect, gửi header, rồi gửi từng khối, báo % mỗi 10%."""
    filename = os.path.basename(path)             # chỉ gửi TÊN, không gửi đường dẫn đầy đủ của máy mình
    label = f"{filename} ({format_size(size)})"
    peer = state.get_peer(peer_name)
    if peer is None:
        ui.show_message(f"[!] Cannot send {filename}: {peer_name} is not online")
        return
    try:
        sock = protocol.connect_and_introduce(peer["ip"], peer["tcp_port"], state.get_name(), protocol.KIND_FILE)
    except OSError as error:
        ui.show_message(f"[!] Cannot send {filename} to {peer_name}: {error}")
        return
    try:
        protocol.send_file_header(sock, filename, size)
        ui.show_message(f"[*] Sending {label} ...")
        sent, last_reported = 0, 0
        with open(path, "rb") as source:
            while True:
                chunk = source.read(config.FILE_CHUNK_SIZE)       # đọc từng khối, KHÔNG nạp cả file vào RAM
                if not chunk:
                    break
                sock.sendall(chunk)
                sent += len(chunk)
                percent = _percent(sent, size)
                if percent < 100 and _should_report(percent, last_reported):
                    last_reported = percent
                    ui.show_message(f"[*] Sending {filename} ... {percent}%")
        if sent != size:                                          # file bị sửa/cắt trong lúc đang gửi
            raise OSError("the file changed while it was being sent")
        ui.show_message(f"[*] Sending {label} ... 100%  Done.")
    except OSError as error:
        ui.show_message(f"[!] Sending {filename} to {peer_name} failed: {error}")
    finally:
        protocol.close_quietly(sock)


# ======================================================================== phía NHẬN
def receive_file(conn, sender_name, filename, size):
    """Nhận ĐÚNG `size` byte từ conn và lưu thành file trong downloads/. (Chạy trong thread của kết nối.)"""
    try:
        out_file, path = _open_download(filename)
    except OSError as error:                                      # ví dụ không tạo được thư mục downloads/
        ui.show_message(f"[!] Cannot save {filename} from {sender_name}: {error}")
        return
    saved_name = os.path.basename(path)
    ok = False
    try:
        ui.show_message(f"[*] Receiving {saved_name} ({format_size(size)}) from {sender_name} ...")
        received, last_reported = 0, 0
        while received < size:
            chunk = conn.recv(min(config.FILE_CHUNK_SIZE, size - received))
            if chunk == b"":
                raise ConnectionError("the sender closed the connection before the file was complete")
            out_file.write(chunk)
            received += len(chunk)
            percent = _percent(received, size)
            if percent < 100 and _should_report(percent, last_reported):
                last_reported = percent
                ui.show_message(f"[*] Receiving {saved_name} ... {percent}%")
        ok = True
    except OSError as error:                                      # gồm ConnectionError và socket.timeout
        ui.show_message(f"[!] Receiving {filename} from {sender_name} failed: {error}. Partial file deleted.")
    finally:
        out_file.close()
        if not ok:
            _delete_file(path)                                    # file dở: xóa
    if ok:
        folder = os.path.basename(config.DOWNLOAD_DIR)
        ui.show_message(f"[*] Received {saved_name} ({format_size(size)}) from {sender_name} - saved in {folder}/")


# ======================================================================== tên file, đĩa, tiến độ
_FORBIDDEN_CHARS = '<>:"/\\|?*'           # ký tự Windows không cho phép trong tên file
_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
_MAX_NAME_LEN = 150


def _safe_filename(filename):
    """Làm sạch tên file nhận từ mạng để không ghi ra ngoài downloads/.
    Ví dụ:  "..\\..\\evil.exe" -> "evil.exe"   |   "a/b/c.txt" -> "c.txt"   |   "" -> "received_file" """
    name = filename.replace("\\", "/").split("/")[-1]                                       # 1. chỉ giữ phần tên cuối
    name = "".join("_" if (c in _FORBIDDEN_CHARS or ord(c) < 32) else c for c in name)      # 2. thay ký tự cấm
    name = name.strip().rstrip(". ")                                                        # 3. Windows không thích dấu chấm/khoảng trắng cuối
    if name == "":
        name = "received_file"
    if name.split(".")[0].upper() in _RESERVED_NAMES:                                       # 4. tên dành riêng của Windows (CON, NUL...)
        name = "_" + name
    if len(name) > _MAX_NAME_LEN:                                                           # 5. giới hạn độ dài, giữ nguyên đuôi
        stem, ext = os.path.splitext(name)
        name = stem[: _MAX_NAME_LEN - len(ext)] + ext
    return name


def _open_download(filename):
    """Tạo file mới trong downloads/ để ghi dữ liệu nhận được. Trả về (file_object, đường_dẫn).
    Trùng tên thì thử slides(1).pdf, slides(2).pdf... Mở chế độ "xb" (chỉ tạo mới) nên không bao giờ ghi đè."""
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    safe = _safe_filename(filename)
    stem, ext = os.path.splitext(safe)
    number = 0
    while True:
        candidate = safe if number == 0 else f"{stem}({number}){ext}"
        path = os.path.join(config.DOWNLOAD_DIR, candidate)
        try:
            return open(path, "xb"), path
        except FileExistsError:
            number += 1


def _delete_file(path):
    """Xóa file nhận dở. Không có file hoặc không xóa được thì bỏ qua."""
    try:
        os.remove(path)
    except OSError:
        pass


def _percent(done_bytes, total_bytes):
    """Phần trăm 0..100. File 0 byte thì coi là 100% (tránh chia cho 0)."""
    if total_bytes <= 0:
        return 100
    return min(100, done_bytes * 100 // total_bytes)


def _should_report(percent, last_reported):
    """True nếu tiến độ đã tăng >= config.PROGRESS_STEP_PERCENT (10%) kể từ lần báo trước.
    Dùng chung cho gửi và nhận. (100% được báo riêng ở cuối, nên ở đây chỉ xét < 100.)"""
    return percent - last_reported >= config.PROGRESS_STEP_PERCENT


def format_size(num_bytes):
    """2516582 -> "2.4 MB" (đề dùng dạng này trong ví dụ "Sending slides.pdf (2.4 MB)")."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
