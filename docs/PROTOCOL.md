# Giao thức LAN Chat (tài liệu thiết kế - cả nhóm chốt ở Day 0)

> Đề nói rõ: *"create your protocol by yourself"*. Dưới đây là **ĐỀ XUẤT** dựa trên mẫu của đề (mục 5.2).
> Nhóm đọc, thảo luận, sửa chỗ nào không đồng ý, rồi tick ✅. File này là nguồn sự thật: code phải khớp file này,
> và phần "Protocol" của báo cáo chép lại từ đây.
> Khi vấn đáp, bạn phải giải thích được **từng dòng** của file này.

## 1. UDP - thông báo hiện diện (discovery + status)

Một datagram, dạng text, gửi tới địa chỉ broadcast, cổng `9999`, mỗi **3 giây**:

```
HELLO|<name>|<tcp_port>|<status>
vd:  HELLO|Quan|5000|online
```

| Trường | Ý nghĩa | Ràng buộc |
|---|---|---|
| `name` | Tên hiển thị, **duy nhất** trong mạng | Không rỗng, **không chứa `|`** |
| `tcp_port` | Cổng TCP mà peer này đang nghe | số nguyên 1-65535 |
| `status` | `online` hoặc `away` | một trong hai giá trị |

Quy tắc bên nhận:
- [ ] Bỏ qua gói có `name` trùng tên mình (gói do chính mình phát).
- [ ] Gói sai định dạng: bỏ qua, không crash.
- [ ] IP của peer = địa chỉ nguồn của datagram (không có trong gói).
- [ ] Peer không nghe thấy trong **10 giây** -> coi như offline.
- [ ] Hai peer trùng `name`: nhóm quyết định -> `________________`

## 2. TCP - khung dữ liệu (framing)

TCP là dòng byte nên mọi gói đều có header. Trường trong header ngăn cách bằng `|`.

| Frame | Định dạng | Ghi chú |
|---|---|---|
| Giới thiệu | `HI|<name>|` | Frame **đầu tiên** của mọi kết nối TCP |
| Tin nhắn | `MSG|<length>|<nội dung>` | `length` = số **BYTE** UTF-8 (không phải số ký tự) |
| Gửi file | `FILE|<filename>|<size>|<byte của file>` | `size` = số byte; chỉ chứa **tên** file, không đường dẫn |
| Kết thúc | `BYE|` | Báo đóng chat lịch sự |

Cách bên nhận đọc (viết lại bằng lời của nhóm, đây là câu vấn đáp quan trọng):
1. Đọc từng byte tới `|` đầu tiên -> biết **loại** frame.
2. Tùy loại, đọc thêm các trường, mỗi trường kết thúc bằng `|`.
3. Với `MSG`: đọc **đúng `length` byte** (vòng lặp `recv`) rồi `decode("utf-8")`.
4. Với `FILE`: đọc **đúng `size` byte**, ghi ra file từng khối.

Quyết định thiết kế (điền):
- [ ] Header kết thúc bằng `|` (như đề) hay xuống dòng `\n`? -> `________________`
- [ ] Giới hạn `length`/`size` tối đa để chống dữ liệu rác? -> `________________`
- [ ] Ký tự `|` trong nội dung `MSG` có sao không? (gợi ý: vì dùng `length` nên không sao. Còn trong **filename** thì sao?) -> `________________`

## 3. Luồng hoạt động

**Mở chat** (A gõ `/chat B`):
```
A ---- TCP connect ----> B          (bắt tay 3 bước, thấy được trong Wireshark)
A ---- HI|A| ---------->  B         B biết "kết nối này của A", lưu state.connections["A"]
A <--- MSG|5|Hello ----> B          hai chiều, trên cùng một kết nối
A ---- BYE| ----------->  B         /leave hoặc /quit
```

**Gửi file** (kết nối RIÊNG, theo cập nhật 09/11 của đề):
```
A ---- TCP connect (kết nối mới) ----> B
A ---- HI|A| ---------------------->  B
A ---- FILE|slides.pdf|2516582| ---->  B
A ---- <2516582 byte> -------------->  B   (gửi theo khối, thread riêng)
A ---- đóng kết nối                    B   B kiểm tra đã nhận đủ size byte chưa
```

## 4. Xử lý lỗi theo giao thức (điền)

| Tình huống | Bên phát hiện | Cách xử lý |
|---|---|---|
| Peer đóng/crash giữa chat | `recv` trả `b""` hoặc ConnectionError | `________________` |
| Header sai / `length` không phải số | bên nhận | `________________` |
| File đứt giữa chừng | bên nhận (nhận thiếu) | xóa file dở + báo lỗi |
| Connect tới peer đã offline | bên gọi | `________________` |
