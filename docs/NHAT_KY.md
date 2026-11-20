# Nhật ký vấn đề & kiến thức (cả nhóm cùng ghi)

> Đề yêu cầu báo cáo có mục **"problems faced and solutions"**. Ghi ngay lúc gặp lỗi (đừng để cuối mới nhớ):
> mất 2 phút lúc đó, đỡ mất 2 giờ lúc viết báo cáo. Đây cũng là tài liệu ôn vấn đáp tốt nhất.
> Mỗi dòng nên đủ để người khác hiểu: **triệu chứng -> nguyên nhân thật -> cách sửa -> bài học**.
> Cột "Loại": **Đã quan sát** = có chạy thử và thấy thật; **Phòng ngừa** = rủi ro biết trước khi thiết kế, đã xử lý nhưng chưa tự gây ra lỗi để xem.

## 1. Vấn đề gặp phải

| Ngày | Ai | Loại | Triệu chứng | Nguyên nhân thật | Cách sửa | Bài học / câu vấn đáp liên quan |
|---|---|---|---|---|---|---|
| 20/11 | Claude (viết code) | Đã quan sát | Trên Windows, hai chương trình cùng `--port` đều nghe được, không báo lỗi | Với TCP, `SO_REUSEADDR` trên Windows cho phép bind lần hai thành công (kết nối đến có thể đi lạc) | Dùng `SO_EXCLUSIVEADDRUSE` trên Windows: lần bind thứ hai báo lỗi 10048 (có test `test_same_tcp_port_is_refused`) | `SO_REUSEADDR` khác nhau giữa Windows và Linux/macOS |
| 20/11 | Claude | Đã quan sát | Tin "Xin chào" dài 8 ký tự nhưng gửi đi 9 byte | `à` chiếm 2 byte trong UTF-8 | Header `MSG` ghi số BYTE (bằng chứng: `docs/evidence/wire_format.txt`) | Vì sao `length` tính bằng byte |
| 20/11 | Claude | Đã quan sát | Test "phá cố ý" cho thấy 5 lỗi quan trọng đều bị bắt (độ dài ký tự, đọc thiếu byte, không xóa file dở, không vẽ lại chữ dở, hiện mọi tin) | - | - | Test phải thử phá để chắc nó có tác dụng |
| 20/11 | Claude | Phòng ngừa | (chưa gây ra) Treo vĩnh viễn nếu chạy lệnh khi còn giữ khóa màn hình | `threading.Lock` không cho xin lại khóa đang giữ | `ui._take_line` chỉ lấy dòng ra trong khóa; lệnh chạy ngoài khóa | Deadlock là gì, nhóm tránh thế nào |
| 20/11 | Claude | Phòng ngừa | (chưa gây ra) Thread nhận tin báo "mất kết nối" sai khi mình chủ động `/leave` | Đóng socket từ thread khác | `/leave` gỡ kết nối khỏi `state` trước khi đóng; thread nhận thấy "không còn là kết nối đang lưu" nên im lặng | Thread nào đóng socket, thread nào đang chờ `recv` |
| 20/11 | Claude | Phòng ngừa | (chưa gây ra) Kết nối gửi file bị nhầm với kết nối chat | `accept()` không cho biết mục đích kết nối | Frame `HI` có thêm trường `kind` (chat/file) | Vì sao giao thức có trường `kind` |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |

*Dòng trống để nhóm ghi các vấn đề thật khi test trên 2 máy (firewall, Wi-Fi, địa chỉ broadcast...).*

## 2. Kiến thức học được (mỗi người ghi bằng lời của mình)

### Huy
-

### Ngọc
-

### Phong
-

## 3. Câu hỏi còn chưa chắc (đem ra họp nhóm / hỏi giảng viên)
- [ ] Quy định "tự code" của môn có cho dùng code do AI viết không? (Code hiện tại do Claude viết theo yêu cầu của nhóm; cần đọc hiểu để vấn đáp.)
- [ ]

## 4. Kết quả các thí nghiệm ở `exercises/`
| Thí nghiệm | Kết quả quan sát được | Giải thích |
|---|---|---|
| Gửi tiếng Việt: `len(data)` so với số ký tự | "Xin chào": 8 ký tự, 9 byte (`wire_format.txt`) | UTF-8: ký tự có dấu chiếm nhiều byte |
| `sendall` hai lần liền: server `recv` thấy mấy lần? |  |  |
| Bỏ SO_REUSEADDR rồi mở 2 receiver UDP |  |  |
| Broadcast tới 127.255.255.255 / 255.255.255.255 trên MỘT máy Windows 11 | Cả hai đều nhận được: các chương trình thấy nhau online | Broadcast gửi tới mọi socket đang nghe cổng 9999 trên máy |
| Broadcast tới địa chỉ mạng con (ví dụ 192.168.1.255) |  |  |
| Chạy trên 2 máy thật: nhận được broadcast không? |  |  |
