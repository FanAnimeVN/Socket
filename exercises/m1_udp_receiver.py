"""
BÀI TẬP M1.3 - UDP RECEIVER   (CẢ 3 NGƯỜI TỰ LÀM, ngày D2)

Mục tiêu: hiểu UDP và broadcast - nền của discovery.py. Tham khảo udp_broadcast_demo.py (file demo của đề):
ĐỌC HIỂU trước, rồi TỰ VIẾT LẠI bằng tay, đừng copy.

Chạy 2-3 terminal receiver (đặt tên khác nhau) + 1 sender:
    python exercises/m1_udp_receiver.py B
    python exercises/m1_udp_receiver.py C
    python exercises/m1_udp_sender.py A

CÁC BƯỚC:
  1. Đọc tên từ dòng lệnh: sys.argv[1]  (hoặc argparse nếu bạn muốn luyện).
  2. Tạo socket UDP: socket.socket(AF_INET, SOCK_DGRAM)   # khác TCP chỗ nào?
  3. setsockopt SO_REUSEADDR = 1  TRƯỚC bind  -> thử bỏ đi rồi mở receiver thứ 2: lỗi gì?
  4. bind(("", 9999))     # "" = mọi card mạng. Thử "127.0.0.1" thay vào: còn nhận được broadcast không?
  5. Vòng lặp: data, addr = recvfrom(1024); in ra tên mình, nội dung (decode), địa chỉ gửi.
  6. (nâng cao) settimeout(1.0): sau mỗi giây không có gói thì in "." để thấy vòng lặp vẫn "sống".
     Đây chính là kỹ thuật để discovery.py vừa nhận gói vừa dọn peer hết hạn.

TỰ KIỂM TRA:
  - UDP không có connect/accept: vì sao recvfrom lại trả về addr?
  - Mất gói UDP thì sao? Vì sao với discovery thì điều đó chấp nhận được (đề mục 1)?
"""
# TODO: viết code ở đây
