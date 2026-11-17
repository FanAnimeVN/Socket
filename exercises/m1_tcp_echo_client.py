"""
BÀI TẬP M1.2 - TCP echo CLIENT   (CẢ 3 NGƯỜI TỰ LÀM, ngày D1)

Chạy server (m1_tcp_echo_server.py) trước, rồi chạy file này.

CÁC BƯỚC:
  1. Tạo socket TCP (giống server).
  2. connect(("127.0.0.1", 6000))     # 127.0.0.1 là địa chỉ gì? Sang máy khác thì thay bằng gì?
     Thử connect khi server CHƯA chạy: lỗi gì (ConnectionRefusedError)? -> sau này chính là
     tình huống "chat với người đã offline", bạn sẽ bắt lỗi này bằng try/except.
  3. Vòng lặp: input("> ") -> encode("utf-8") -> sendall -> recv(1024) -> decode -> in ra.
  4. Gõ "quit" (hoặc Ctrl+C) thì đóng socket.

THÍ NGHIỆM (ghi kết quả vào docs/NHAT_KY.md, mục "kiến thức học được"):
  - Gửi 1 câu rất dài (> 5000 ký tự): recv(1024) nhận được mấy lần? Dữ liệu có bị cắt không?
  - Gọi sendall hai lần liên tiếp ("Hello" rồi "World") không dừng: server recv có thể thấy 1 hay 2 lần? Vì sao?
    (Đây là lý do TCP "không có ranh giới tin nhắn" -> bài toán framing trong protocol.py.)
  - Dùng socket.settimeout(2) rồi để server không trả lời: chuyện gì xảy ra? (socket.timeout)

TỰ KIỂM TRA:
  - sendall khác send ở điểm nào?
  - Vì sao connect có thể thành công dù server chưa gọi accept()? (gợi ý: hàng đợi của listen)
"""
# TODO: viết code ở đây
