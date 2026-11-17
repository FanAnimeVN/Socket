"""
BÀI TẬP M1.1 - TCP echo SERVER   (CẢ 3 NGƯỜI TỰ LÀM, ngày D1 - xem docs/KE_HOACH.md)

Mục tiêu: hiểu vòng đời socket TCP phía server. Đây là Milestone 1 của đề: "TCP echo client/server".
Echo = server nhận gì thì gửi lại đúng thế.

Chạy:  python exercises/m1_tcp_echo_server.py      (terminal 1)
       python exercises/m1_tcp_echo_client.py      (terminal 2)

CÁC BƯỚC (tự viết code, mỗi bước chú thích 1 dòng bằng lời của bạn):
  1. import socket
  2. Tạo socket TCP: socket.socket(socket.AF_INET, socket.SOCK_STREAM)
     AF_INET là gì? SOCK_STREAM là gì? (so với SOCK_DGRAM)
  3. setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)  -> thử bỏ dòng này, tắt rồi chạy lại ngay: chuyện gì xảy ra?
  4. bind(("0.0.0.0", 6000))     # gắn socket với địa chỉ + cổng. "0.0.0.0" nghĩa là gì?
  5. listen()                    # bắt đầu nghe
  6. conn, addr = accept()       # CHẶN tới khi có client. conn khác socket server ở chỗ nào? addr là gì?
  7. Vòng lặp: data = conn.recv(1024) ; nếu data == b"" thì client đã đóng -> thoát vòng lặp ;
     ngược lại conn.sendall(data)
  8. Đóng conn (và socket server).

BẮT BUỘC thử và ghi lại nhận xét:
  - Client gửi "Xin chào" (tiếng Việt): print(data) ra gì? print(data.decode("utf-8")) ra gì? len(data) là bao nhiêu?
  - Tắt client đột ngột (Ctrl+C) lúc server đang chạy: server có crash không? recv trả về gì?

NÂNG CAO (cần làm trước D3, vì chat thật có nhiều peer):
  - Cho server phục vụ NHIỀU client cùng lúc: mỗi lần accept xong tạo threading.Thread(target=..., args=(conn,), daemon=True).
    Mở 2 client cùng lúc. Chạy được thì mới hiểu vì sao đề yêu cầu "TCP receiver (one per connection)".

TỰ KIỂM TRA (giải thích bằng lời của mình, không nhìn tài liệu):
  1. Server có mấy socket? Socket nào dùng để nói chuyện với client?
  2. recv(1024) có đảm bảo nhận đủ 1024 byte không? Vì sao điều đó dẫn tới việc cần "framing"?
"""
# TODO: viết code ở đây
