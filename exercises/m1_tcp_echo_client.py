"""
exercises/m1_tcp_echo_client.py - BÀI M1.2: TCP echo CLIENT.

Chạy server (m1_tcp_echo_server.py) trước, rồi chạy file này:
    python exercises/m1_tcp_echo_client.py                 (server ở cùng máy)
    python exercises/m1_tcp_echo_client.py 192.168.1.12    (server ở máy khác)
Gõ chữ rồi Enter để gửi, gõ "quit" để thoát.

THÍ NGHIỆM (ghi kết quả vào docs/NHAT_KY.md):
  - Chạy client khi server CHƯA chạy: lỗi gì? (ConnectionRefusedError) -> chính là tình huống "chat với người đã
    offline" của chương trình thật, nơi ta bắt lỗi này bằng try/except.
  - Gửi một câu rất dài (> 5000 ký tự): recv(1024) nhận được mấy lần? Dữ liệu có bị cắt không?
  - Gọi sendall hai lần liên tiếp ("Hello" rồi "World"): bên kia recv thấy 1 hay 2 lần? (TCP không có ranh giới tin nhắn)

TỰ KIỂM TRA: sendall khác send ở điểm nào? Vì sao connect có thể thành công dù server chưa gọi accept()?
"""
import socket
import sys

PORT = 6000


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"    # 127.0.0.1 = chính máy này
    try:
        sock = socket.create_connection((host, PORT), timeout=3)   # timeout 3 giây để không treo nếu server không có
    except OSError as error:
        print(f"Cannot connect to {host}:{PORT}: {error}")
        return
    sock.settimeout(None)
    print(f"Connected to {host}:{PORT}. Type text, or 'quit' to exit.")
    with sock:
        while True:
            text = input("> ")
            if text == "quit":
                break
            sock.sendall(text.encode("utf-8"))          # chữ -> byte
            data = sock.recv(1024)                      # chờ server gửi lại
            if data == b"":
                print("Server closed the connection.")
                break
            print("echo:", data.decode("utf-8", errors="replace"), f"({len(data)} bytes)")


if __name__ == "__main__":
    main()
