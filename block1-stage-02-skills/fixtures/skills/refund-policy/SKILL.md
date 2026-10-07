---
name: refund-policy
description: Tra cứu chính sách hoàn tiền và xác định điều kiện hoàn theo ngày mua, ngày yêu cầu hoàn và trạng thái kích hoạt. Dùng khi người dùng hỏi có được hoàn tiền không, thời hạn hoặc phí hoàn tiền.
---

# Tra cứu chính sách hoàn tiền

1. Trước khi kết luận, cần đủ ba thông tin do người dùng cung cấp: ngày mua, ngày yêu cầu hoàn và trạng thái kích hoạt. Nếu thiếu, hỏi rõ thông tin còn thiếu và chờ trả lời; không đưa ra kết luận cuối cùng hay tự giả định "chưa kích hoạt". Nếu ngày không hợp lệ, mơ hồ hoặc ngày yêu cầu trước ngày mua, hỏi lại.
2. Dùng `list_files` với `data/policies/` để khám phá tài liệu hiện có. Không đoán, ghi cố định hoặc suy luận phạm vi hiệu lực từ tên file.
3. Dùng `read_file` đọc các tài liệu chính sách được tìm thấy qua đường dẫn trong kết quả liệt kê. Xác định phạm vi ngày áp dụng từ NỘI DUNG từng tài liệu, bao gồm điều kiện có/không bao gồm ngày biên. Nếu tool lỗi, tài liệu thiếu hoặc phạm vi mâu thuẫn/chồng lấn, báo rõ và hỏi thêm trước khi kết luận.
4. Chọn chính sách có phạm vi hiệu lực chứa NGÀY MUA của khách hàng. Không chọn theo ngày yêu cầu hoàn.
5. Đọc `references/answer-template.md`, tức `skills/refund-policy/references/answer-template.md`, bằng `read_file` và làm theo cấu trúc trả lời.
6. Tính số ngày lịch đã qua = ngày yêu cầu hoàn trừ ngày mua. Dùng ngày yêu cầu hoàn trong câu hỏi; không dùng ngày hiện tại của máy.
7. Áp dụng chính xác thời hạn, điều kiện kích hoạt và phí theo tài liệu đã chọn. Số ngày bằng đúng giới hạn vẫn đạt điều kiện thời gian. Không suy diễn thêm quy định hoặc phí.
8. Trả lời theo reference và dẫn đúng đường dẫn tài liệu thực tế đã đọc làm bằng chứng, kể cả sau khi đổi tên.
9. Chỉ dùng các file tool được cấp. Không dùng Bash, shell hoặc script.
