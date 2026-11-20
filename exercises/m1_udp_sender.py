"""
exercises/m1_udp_sender.py - BÀI M1.4: UDP BROADCAST SENDER (nền của discovery.py).

Chạy receiver trước (m1_udp_receiver.py), rồi chạy file này:
    python exercises/m1_udp_sender.py A                    (broadcast 255.255.255.255)
    python exercises/m1_udp_sender.py A 127.255.255.255    (máy không có mạng: gợi ý của đề)
    python exercises/m1_udp_sender.py A 192.168.1.255      (địa chỉ broadcast của mạng bạn)

THÍ NGHIỆM (ghi kết quả vào docs/NHAT_KY.md):
  - 2 receiver cùng nhận được không? Vì sao (broadcast gửi cho "tất cả")?
  - Bỏ dòng SO_BROADCAST: sendto tới địa chỉ broadcast báo lỗi gì?
  - Trên 2 máy thật cùng Wi-Fi: máy kia có nhận được không? Nếu không -> Firewall? Wi-Fi bật "client isolation"?
  - Mở Wireshark (docs/WIRESHARK.md), filter  udp.port == 9999: thấy gói chưa? Địa chỉ đích là gì?

TỰ KIỂM TRA: Broadcast khác unicast ở đâu? Vì sao router không chuyển tiếp broadcast ra Internet?
             Vì sao đề chọn UDP (không phải TCP) cho việc "tôi đang online"?
"""
import socket
import sys
import time

PORT = 9999


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "sender"
    bcast = sys.argv[2] if len(sys.argv) > 2 else "255.255.255.255"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)    # bắt buộc bật thì mới gửi tới địa chỉ broadcast được
    packet = f"HELLO|{name}|5001|online".encode("utf-8")          # gói giống giao thức thật
    print(f"[{name}] broadcasting {packet.decode()} to {bcast}:{PORT} every 3 s (Ctrl+C to stop)")
    try:
        while True:
            sock.sendto(packet, (bcast, PORT))
            print(f"[{name}] sent")
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
