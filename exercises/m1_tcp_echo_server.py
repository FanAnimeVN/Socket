"""
exercises/m1_tcp_echo_server.py - BÀI M1.1: TCP echo SERVER (Milestone 1 của đề: "TCP echo client/server").

Echo = server nhận gì thì gửi lại đúng thế. Server phục vụ NHIỀU client cùng lúc, mỗi client một thread
(đây chính là ý "TCP receiver, one per connection" của đề).

Chạy:  python exercises/m1_tcp_echo_server.py      (terminal 1)
       python exercises/m1_tcp_echo_client.py      (terminal 2, mở thêm terminal 3 để thử 2 client)

Chú ý: đây là bài tập độc lập, KHÔNG thuộc chương trình chính nên dùng print() thoải mái.

THÍ NGHIỆM nên làm (ghi kết quả vào docs/NHAT_KY.md):
  - Client gửi "Xin chào": print(data) ra gì? print(data.decode("utf-8")) ra gì? len(data) là bao nhiêu?
  - Tắt client đột ngột (Ctrl+C): server có crash không? recv trả về gì? (b"" = bên kia đã đóng)
  - Bỏ dòng SO_REUSEADDR, tắt server rồi chạy lại ngay: có báo "Address already in use" không? (Windows và Linux khác nhau)

TỰ KIỂM TRA: Server có mấy socket? Socket nào dùng để nói chuyện với client?
             recv(1024) có đảm bảo nhận đủ 1024 byte không? Vì sao điều đó dẫn tới việc cần "framing"?
"""
import socket
import threading

PORT = 6000


def serve_one_client(conn, addr):
    """Chạy trong thread riêng: nhận gì gửi lại nấy cho tới khi client đóng kết nối."""
    print(f"[+] {addr} connected")
    with conn:
        while True:
            data = conn.recv(1024)          # CHẶN tới khi có dữ liệu
            if data == b"":                 # b"" nghĩa là client đã đóng kết nối
                break
            print(f"    {addr} sent {len(data)} bytes: {data.decode('utf-8', errors='replace')!r}")
            conn.sendall(data)              # sendall: gửi HẾT, không bỏ sót byte nào
    print(f"[-] {addr} disconnected")


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    # AF_INET = IPv4, SOCK_STREAM = TCP
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", PORT))          # 0.0.0.0 = nhận kết nối từ mọi card mạng
    server.listen()                         # bắt đầu nghe
    print(f"Echo server listening on port {PORT} (Ctrl+C to stop)")
    try:
        while True:
            conn, addr = server.accept()    # CHẶN tới khi có client. conn là socket RIÊNG để nói chuyện với client đó
            threading.Thread(target=serve_one_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        server.close()


if __name__ == "__main__":
    main()
