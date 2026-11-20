"""
protocol.py - NÓI CHUYỆN TCP: đóng/đọc gói tin (message framing), mở kết nối, đóng kết nối.

Người phụ trách giải thích khi vấn đáp: HUY          Người review (teach-back): PHONG
Điểm rubric liên quan: Protocol design & framing (10%), TCP chat (20%)
Đọc trước: đề mục 5.2; docs/PROTOCOL.md. Test: tests/test_protocol.py (dùng socket.socketpair(), không cần mạng).
ĐỌC TIẾP: tcp_chat.py (nơi dùng các hàm này để chat), filetransfer.py (gửi/nhận file).

TẠI SAO CẦN FRAMING?
  TCP là "dòng byte", KHÔNG có ranh giới tin nhắn. Bạn gửi "Hello" rồi "World" thì bên kia có thể recv() được
  "HelloWo" rồi "rld". Vì vậy mỗi gói có HEADER cho biết loại và độ dài; bên nhận đọc ĐÚNG số byte đó.

CÁC FRAME (chi tiết và lý do: docs/PROTOCOL.md):
    HI|<name>|<kind>|                    frame ĐẦU TIÊN của mọi kết nối; kind = "chat" hoặc "file"
    MSG|<length>|<nội dung utf-8>        tin nhắn chat; <length> = SỐ BYTE của nội dung
    FILE|<filename>|<size>|<byte file>   gửi file; <size> = số byte; phần byte do filetransfer.py gửi nối theo
    BYE|                                 đóng chat lịch sự

HAI BẪY (hay bị hỏi vấn đáp):
  #1 len("Việt") = 4 ký tự nhưng len("Việt".encode("utf-8")) = 6 byte. Header PHẢI ghi số BYTE.
  #2 sock.recv(n) có thể trả về ÍT HƠN n byte; trả b"" nghĩa là peer đã đóng -> cần recv_exact (lặp tới khi đủ).
"""
import socket

import config

KIND_CHAT = "chat"
KIND_FILE = "file"


# ======================================================================== đọc
def recv_exact(sock, n):
    """Đọc ĐÚNG n byte từ sock rồi trả về (kiểu bytes). Peer đóng giữa chừng -> ConnectionError.
    Vì sao recv(còn_thiếu) mà không phải recv(4096)? Đọc dư sẽ nuốt mất đầu frame kế tiếp!"""
    chunks = []
    remaining = n
    while remaining > 0:
        chunk = sock.recv(remaining)
        if chunk == b"":
            raise ConnectionError("the other side closed the connection")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def recv_until(sock, delimiter=b"|"):
    """Đọc TỪNG BYTE tới khi gặp `delimiter`; trả về phần đứng trước nó (không gồm delimiter).
    Dùng cho header vì độ dài header không cố định (tên file dài ngắn khác nhau). Đọc từng byte nghe chậm
    nhưng header chỉ vài chục byte; đổi lại không bao giờ đọc lẹm sang phần nội dung."""
    data = bytearray()
    while True:
        byte = recv_exact(sock, 1)
        if byte == delimiter:
            return bytes(data)
        data += byte
        if len(data) > config.HEADER_MAX_LEN:
            raise ValueError("header too long (garbage data?)")


def _read_text_field(sock):
    """Đọc một trường header dạng chữ."""
    return recv_until(sock).decode(config.ENCODING, errors="replace")


def _read_int_field(sock):
    """Đọc một trường header dạng số nguyên không âm. Không phải số -> ValueError."""
    text = _read_text_field(sock)
    if not text.isdigit():
        raise ValueError(f"expected a number in the header, got {text!r}")
    return int(text)


def read_frame(sock):
    """Đọc MỘT frame, trả về tuple mô tả frame:
        ("HI", name, kind)
        ("MSG", text)                # đã đọc đủ và decode
        ("BYE",)
        ("FILE", filename, size)     # CHỈ header; phần byte của file CHƯA đọc (filetransfer.receive_file sẽ đọc)
    Peer đóng -> ConnectionError. Dữ liệu rác / loại lạ / length quá lớn -> ValueError."""
    frame_type = _read_text_field(sock)

    if frame_type == "HI":
        name = _read_text_field(sock)
        kind = _read_text_field(sock)
        if name == "" or kind not in (KIND_CHAT, KIND_FILE):
            raise ValueError("bad HI frame")
        return ("HI", name, kind)

    if frame_type == "MSG":
        length = _read_int_field(sock)
        if length > config.MAX_MSG_BYTES:
            raise ValueError(f"message too long ({length} bytes)")
        body = recv_exact(sock, length)                 # đọc ĐÚNG `length` byte
        return ("MSG", body.decode(config.ENCODING))    # decode sai -> UnicodeDecodeError (là một ValueError)

    if frame_type == "FILE":
        filename = _read_text_field(sock)
        size = _read_int_field(sock)
        return ("FILE", filename, size)

    if frame_type == "BYE":
        return ("BYE",)

    raise ValueError(f"unknown frame type {frame_type!r}")


# ======================================================================== gửi
def send_hi(sock, name, kind):
    """Gửi HI|<name>|<kind>|  ngay sau khi connect. sendall (không phải send) vì sendall gửi HẾT mọi byte."""
    sock.sendall(f"HI|{name}|{kind}|".encode(config.ENCODING))


def send_msg(sock, text):
    """Gửi MSG|<length>|<text>. Quy trình: text -> bytes -> đo len(bytes) -> ghép header -> gửi một lần."""
    body = text.encode(config.ENCODING)
    header = f"MSG|{len(body)}|".encode(config.ENCODING)
    sock.sendall(header + body)


def send_bye(sock):
    """Gửi BYE|  (báo sắp đóng chat)."""
    sock.sendall(b"BYE|")


def send_file_header(sock, filename, size):
    """Gửi CHỈ header của file: FILE|<filename>|<size>|  . Dấu '|' trong tên file bị đổi thành '_' vì '|'
    là dấu ngăn cách của header. Các byte của file do filetransfer.py gửi nối tiếp (theo từng khối)."""
    safe_name = filename.replace("|", "_")
    sock.sendall(f"FILE|{safe_name}|{size}|".encode(config.ENCODING))


# ======================================================================== mở / đóng kết nối
def connect_and_introduce(ip, port, my_name, kind):
    """Connect tới (ip, port) rồi gửi HI để tự giới thiệu. Trả về socket, hoặc ném OSError nếu không kết nối được.
    Chỉ chờ config.CONNECT_TIMEOUT (3 s) để không treo khi peer đã offline; connect xong thì bỏ timeout
    (settimeout(None)) vì thread nhận tin cần chờ vô hạn."""
    sock = socket.create_connection((ip, port), timeout=config.CONNECT_TIMEOUT)
    try:
        send_hi(sock, my_name, kind)
        sock.settimeout(None)
    except OSError:
        close_quietly(sock)
        raise
    return sock


def close_quietly(sock):
    """Đóng socket êm ái, không bao giờ ném lỗi. Hai bước:
      1. shutdown(): báo hai đầu "ngừng gửi/nhận"; còn ĐÁNH THỨC thread đang kẹt ở recv() trên socket đó.
      2. close(): trả socket lại cho hệ điều hành. Socket có thể đã đóng sẵn nên bỏ qua lỗi."""
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass
