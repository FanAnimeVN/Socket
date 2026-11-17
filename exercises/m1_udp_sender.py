"""
BÀI TẬP M1.4 - UDP BROADCAST SENDER   (CẢ 3 NGƯỜI TỰ LÀM, ngày D2)

Chạy receiver trước (m1_udp_receiver.py), rồi chạy file này.

CÁC BƯỚC:
  1. Tạo socket UDP; bật SO_BROADCAST (không bật thì sendto tới địa chỉ broadcast bị từ chối: thử xem lỗi gì).
  2. Dựng gói giống giao thức thật:  "HELLO|A|5001|online"  rồi .encode("utf-8")
  3. Vòng lặp: sendto(gói, ("255.255.255.255", 9999)); in "đã gửi"; chờ 3 giây (time.sleep(3)).
  4. Ctrl+C thì thoát gọn (bắt KeyboardInterrupt).

THÍ NGHIỆM:
  - 2 receiver cùng nhận được không? Vì sao (broadcast gửi cho "tất cả")?
  - Đổi địa chỉ đích thành "127.255.255.255" (trường hợp máy không có mạng, gợi ý của đề): có nhận không?
  - Đổi thành địa chỉ broadcast của mạng bạn (vd 192.168.1.255 nếu mạng là 192.168.1.x): có nhận không?
  - Trên 2 máy thật cùng Wi-Fi: máy kia có nhận được không? Nếu không -> Firewall? Wi-Fi bật "client isolation"?
    (Ghi lại: đây là rủi ro lớn nhất của buổi demo.)
  - Mở Wireshark (xem docs/WIRESHARK.md), filter  udp.port == 9999  -> thấy gói của bạn chưa? Địa chỉ đích là gì?

TỰ KIỂM TRA:
  - Broadcast khác unicast ở đâu? Vì sao router không chuyển tiếp broadcast ra Internet?
  - Vì sao đề chọn UDP (không phải TCP) cho việc "tôi đang online"?
"""
# TODO: viết code ở đây
