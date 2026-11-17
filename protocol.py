"""
protocol.py - Đóng gói / đọc gói tin TCP (message framing).

Người phụ trách: HUY          Người review (teach-back): PHONG
Điểm rubric liên quan: Protocol design & framing (10%), TCP chat (20%)
Đọc trước: đề mục 5.2; Beej's Guide phần "Son of Data Encapsulation"; docs/PROTOCOL.md

----------------------------------------------------------------------------------------
TẠI SAO CẦN FRAMING?
  TCP là "dòng byte", KHÔNG có ranh giới tin nhắn. Bạn gửi "Hello" rồi "World" có thể bên kia
  recv() được "HelloWo" rồi "rld". Vì vậy mỗi gói phải có HEADER cho biết loại và độ dài,
  bên nhận đọc ĐÚNG số byte đó.

CÁC FRAME (đề xuất, xem/ghi quyết định cuối trong docs/PROTOCOL.md):
    HI|<name>|                         # frame đầu tiên của MỌI kết nối: "tôi là <name>"
    MSG|<length>|<nội dung utf-8>      # tin nhắn chat, <length> = SỐ BYTE của nội dung
    FILE|<filename>|<size>|<byte file> # gửi file, <size> = số byte của file
    BYE|                               # đóng chat lịch sự

=== BẪY #1 (hay bị hỏi vấn đáp) ===
  len("Việt") = 4 ký tự, nhưng len("Việt".encode("utf-8")) = 6 byte. Header PHẢI ghi số BYTE.
  Quy trình gửi: text -> encode -> đo len(bytes) -> gửi header -> gửi bytes.
  Quy trình nhận: đọc header -> đọc ĐÚNG n byte -> decode.

=== BẪY #2 ===
  sock.recv(n) có thể trả về ÍT HƠN n byte; trả b"" nghĩa là peer đã đóng kết nối.
  => cần hàm recv_exact lặp tới khi đủ.

Cách test file này MÀ KHÔNG cần mạng thật: dùng socket.socketpair() -> xem tests/test_protocol.py
----------------------------------------------------------------------------------------
"""
import config


def recv_exact(sock, n):
    """Đọc ĐÚNG n byte từ sock rồi trả về (kiểu bytes).

    Việc cần làm:
      1. Chuẩn bị nơi chứa dữ liệu đã nhận (gợi ý: bytearray hoặc list rồi b"".join).
      2. Lặp trong khi còn thiếu byte: gọi sock.recv(số_byte_còn_thiếu).
      3. Nếu recv trả về b"" -> peer đã đóng giữa chừng -> raise ConnectionError("...").
      4. Gom dữ liệu; đủ n thì trả về.
    Tự hỏi: vì sao yêu cầu recv(còn_thiếu) chứ không phải recv(4096)? (nếu recv dư sẽ nuốt mất frame sau!)
    """
    raise NotImplementedError("TODO: recv_exact")


def recv_until(sock, delimiter=b"|"):
    """Đọc TỪNG BYTE cho tới khi gặp `delimiter`, trả về phần trước delimiter (bytes, không gồm delimiter).

    Dùng để đọc header (vì độ dài header không cố định, ví dụ tên file dài ngắn khác nhau).
    Việc cần làm:
      1. Lặp: recv_exact(sock, 1).
      2. Gặp delimiter thì dừng; chưa gặp thì gom vào.
      3. Nếu đã đọc quá config.HEADER_MAX_LEN byte mà chưa thấy delimiter -> raise ValueError (dữ liệu rác).
    Đọc từng byte nghe chậm nhưng header chỉ vài chục byte, nên chấp nhận được. (Vấn đáp: vì sao không
    đọc nguyên 1024 byte rồi tách? -> vì có thể đọc lẹm sang phần nội dung/frame kế tiếp.)
    """
    raise NotImplementedError("TODO: recv_until")


def send_hi(sock, name):
    """Gửi frame HI|<name>|  (giới thiệu mình là ai). Gọi ngay sau khi connect thành công.

    Gợi ý: dựng chuỗi -> .encode(config.ENCODING) -> sock.sendall(...). (Vì sao sendall chứ không send?)
    """
    raise NotImplementedError("TODO: send_hi")


def send_msg(sock, text):
    """Gửi frame MSG|<length>|<text>. length = số BYTE của text sau khi encode utf-8.

    Việc cần làm: 1) text -> bytes  2) header = "MSG|{len}|" -> bytes  3) sendall(header + body).
    Test bắt buộc: gửi "Xin chào, tôi tên Huy" (có dấu) và nhận lại đúng nguyên văn.
    """
    raise NotImplementedError("TODO: send_msg")


def send_bye(sock):
    """Gửi frame BYE|  (báo sắp đóng chat)."""
    raise NotImplementedError("TODO: send_bye")


def send_file_header(sock, filename, size):
    """Gửi header của file: FILE|<filename>|<size>|  (CHỈ header).

    Phần byte của file do filetransfer.py gửi nối tiếp theo bằng vòng lặp đọc-theo-khối,
    vì file có thể rất lớn, không thể nạp hết vào bộ nhớ rồi gửi một lần.
    """
    raise NotImplementedError("TODO: send_file_header")


def read_frame(sock):
    """Đọc MỘT frame từ sock, trả về tuple mô tả frame. Ném ConnectionError nếu peer đóng.

    Kết quả trả về (gợi ý, nhóm có thể đổi nhưng phải thống nhất & ghi vào docs/PROTOCOL.md):
        ("HI",   name)
        ("MSG",  text)                  # đã đọc đủ và decode
        ("BYE",)
        ("FILE", filename, size)        # CHỈ trả header; phần byte file CHƯA đọc.
                                        # Người gọi (tcp_chat -> filetransfer.receive_file) đọc tiếp
                                        # theo từng khối và ghi ra đĩa.
    Việc cần làm:
      1. loại = recv_until(sock) rồi decode.
      2. Tùy loại, đọc thêm các trường theo đúng thứ tự (mỗi trường kết thúc bằng '|').
      3. Với MSG: đọc length -> int(...) -> recv_exact(sock, length) -> decode.
      4. Loại lạ / length không phải số / length âm hoặc quá lớn -> raise ValueError (đừng để crash khó hiểu).
    """
    raise NotImplementedError("TODO: read_frame")
