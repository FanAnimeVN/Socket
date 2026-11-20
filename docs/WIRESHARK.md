# Hướng dẫn chụp Wireshark cho báo cáo

**Phụ trách:** Ngọc (cả nhóm hiểu để giải thích). Đề yêu cầu (mục 7): ảnh chụp cho thấy **gói UDP broadcast**
và **bắt tay 3 bước của TCP**, kèm giải thích ngắn.

## 0. Cài đặt
1. Tải Wireshark từ trang chính thức; trong lúc cài **chọn kèm Npcap** (thành phần bắt gói trên Windows).
2. Mở Wireshark. Chọn **đúng card mạng** đang dùng (Wi-Fi hoặc Ethernet), double-click để bắt đầu.
   - Chạy nhiều instance trên **một máy** thì gói đi qua card *loopback* (Npcap Loopback Adapter),
     nhìn khác với 2 máy thật. **Để chụp ảnh cho báo cáo, dùng 2 máy thật cùng mạng.**

## 1. Chụp UDP broadcast
1. Bắt đầu capture. Gõ filter (ô trên cùng) rồi Enter:  `udp.port == 9999`
2. Chạy `lanchat.py` trên 1 máy. Cứ mỗi 3 giây phải thấy một gói.
3. Bấm vào một gói và nhìn 3 vùng ở dưới:
   - *Internet Protocol*: **Destination** là địa chỉ broadcast (`255.255.255.255` hoặc `x.x.x.255`).
   - *User Datagram Protocol*: cổng đích **9999**.
   - *Data*: xem được chuỗi `HELLO|<name>|<port>|<status>`.
4. **Chụp màn hình** cả danh sách gói + 3 vùng chi tiết.
5. Viết giải thích 3-5 câu: vì sao đích là địa chỉ broadcast? vì sao chu kỳ 3 giây? vì sao UDP không cần "bắt tay"?

## 2. Chụp TCP three-way handshake
1. **Bắt đầu capture TRƯỚC khi gõ `/chat`.** Filter:  `tcp.port == 5000`   (đổi theo cổng của bạn)
   hoặc chỉ xem gói mở kết nối:  `tcp.flags.syn == 1`
2. Trên máy A gõ `/chat B`. Phải thấy **3 gói đầu tiên**:
   | # | Hướng | Cờ (Flags) | Ý nghĩa |
   |---|---|---|---|
   | 1 | A -> B | `SYN` | A xin mở kết nối |
   | 2 | B -> A | `SYN, ACK` | B đồng ý và xin mở lại chiều ngược |
   | 3 | A -> B | `ACK` | A xác nhận -> kết nối thiết lập |
3. Chụp màn hình có 3 gói này (nên bật cột *Flags* / cột Info hiện `[SYN]`, `[SYN, ACK]`, `[ACK]`).
4. Viết giải thích: mỗi gói làm gì, vì sao cần 3 bước (đồng bộ **số thứ tự** hai chiều - cột *Seq/Ack*).

## 3. (Cộng điểm hiểu bài) Xem khung dữ liệu của mình
- Chuột phải một gói TCP có dữ liệu -> **Follow -> TCP Stream**: thấy `HI|A|` rồi `MSG|5|Hello`.
  Đây là bằng chứng trực quan cho việc **framing** của nhóm.
- Gửi một tin có tiếng Việt: so con số `length` trong `MSG|<length>|` với số ký tự bạn gõ -> hiểu vì sao đếm BYTE.

## 4. Nơi lưu
- Ảnh chụp: `docs/img/udp_broadcast.png`, `docs/img/tcp_handshake.png`, (tùy chọn) `docs/img/tcp_stream.png`.
- Chèn vào `docs/BAO_CAO.md` **mục 7**: thay khối "CHƯA CÓ ẢNH" bằng ảnh (cú pháp ảnh Markdown, đường dẫn `img/tên_ảnh.png`),
  giữ nguyên phần "Giải thích chuẩn bị sẵn" bên dưới mỗi ảnh. Báo cáo không chứa code nên chỉ chèn ảnh + lời giải thích.
- Đối chiếu: byte thật chương trình gửi ra (không phải ảnh Wireshark) đã có ở `docs/evidence/wire_format.txt`; ảnh
  "Follow TCP Stream" của bạn phải cho thấy cùng nội dung (`HI|...|chat|`, `MSG|<số byte>|...`).
- File bắt gói `.pcapng` có thể rất lớn; đang bị `.gitignore` bỏ qua - giữ riêng trên máy.

## 5. Nếu không thấy gói nào
- Chọn nhầm card mạng (thử card khác trong danh sách).
- Bắt gói trên máy A nhưng gói broadcast không tới (Wi-Fi bật "client isolation"? Firewall?). Thử hotspot điện thoại.
- Filter sai cổng: xóa filter xem có gói nào chạy không.
