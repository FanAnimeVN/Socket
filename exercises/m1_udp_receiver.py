"""
exercises/m1_udp_receiver.py - BÀI M1.3: UDP RECEIVER (nền của discovery.py).

Chạy 2-3 receiver (đặt tên khác nhau) + 1 sender, mỗi cái một terminal:
    python exercises/m1_udp_receiver.py B
    python exercises/m1_udp_receiver.py C
    python exercises/m1_udp_sender.py A

THÍ NGHIỆM (ghi kết quả vào docs/NHAT_KY.md):
  - Bỏ dòng SO_REUSEADDR rồi mở receiver thứ 2: lỗi gì?
  - Đổi bind(("", 9999)) thành bind(("127.0.0.1", 9999)): còn nhận được broadcast không?

TỰ KIỂM TRA: UDP không có connect/accept - vì sao recvfrom lại trả về addr?
             Mất gói UDP thì sao? Vì sao với discovery thì điều đó chấp nhận được (đề mục 1)?
"""
import socket
import sys

PORT = 9999


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "receiver"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)       # SOCK_DGRAM = UDP
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)    # cho nhiều chương trình cùng bind một cổng; PHẢI trước bind
    if hasattr(socket, "SO_REUSEPORT"):                           # macOS/Linux cần thêm
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(("", PORT))                                         # "" = mọi card mạng
    sock.settimeout(1.0)                                          # mỗi 1 giây không có gói thì thoát recvfrom để in "."
    print(f"[{name}] listening on UDP {PORT} (Ctrl+C to stop)")
    try:
        while True:
            try:
                data, addr = sock.recvfrom(1024)                  # addr = (IP, cổng) của người gửi
            except socket.timeout:
                print(".", end="", flush=True)                    # vòng lặp vẫn "sống": đây là cách udp_listener dọn peer hết hạn
                continue
            print(f"\n[{name}] got {data.decode('utf-8', errors='replace')!r} from {addr[0]}:{addr[1]}")
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
