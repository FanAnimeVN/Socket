# Nhật ký vấn đề & kiến thức (cả nhóm cùng ghi)

> Đề yêu cầu báo cáo có mục **"problems faced and solutions"**. Ghi ngay lúc gặp lỗi (đừng để cuối mới nhớ):
> mất 2 phút lúc đó, đỡ mất 2 giờ lúc viết báo cáo. Đây cũng là tài liệu ôn vấn đáp tốt nhất.
> Mỗi dòng nên đủ để người khác hiểu: **triệu chứng -> nguyên nhân thật -> cách sửa -> bài học**.

## 1. Vấn đề gặp phải

| Ngày | Ai | Triệu chứng | Nguyên nhân thật | Cách sửa | Bài học / câu vấn đáp liên quan |
|---|---|---|---|---|---|
| (vd) D4 | Ngọc | Hai instance cùng máy: instance thứ 2 báo "Address already in use" | Chưa đặt SO_REUSEADDR trước bind | Thêm setsockopt trước bind | Ý nghĩa của SO_REUSEADDR với UDP |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |

## 2. Kiến thức học được (mỗi người ghi bằng lời của mình)

### Huy
-

### Ngọc
-

### Phong
-

## 3. Câu hỏi còn chưa chắc (đem ra họp nhóm / hỏi giảng viên)
- [ ]
- [ ]

## 4. Kết quả các thí nghiệm ở `exercises/`
| Thí nghiệm | Kết quả quan sát được | Giải thích |
|---|---|---|
| Gửi tiếng Việt: `len(data)` so với số ký tự |  |  |
| `sendall` hai lần liền: server `recv` thấy mấy lần? |  |  |
| Bỏ SO_REUSEADDR rồi mở 2 receiver UDP |  |  |
| Broadcast tới 127.255.255.255 / địa chỉ subnet / 255.255.255.255 |  |  |
| Chạy trên 2 máy thật: nhận được broadcast không? |  |  |
