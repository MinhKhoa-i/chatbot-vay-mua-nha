# KỊCH BẢN DEMO CHATBOT TƯ VẤN VAY MUA NHÀ

## 1. Mục tiêu và thời lượng

Kịch bản được xây dựng nhằm minh họa khả năng hướng dẫn hồ sơ vay, mô phỏng khoản trả nợ, cập nhật thông tin qua nhiều lượt hội thoại và giải thích các điều kiện của khoản vay mua nhà. Thời lượng dự kiến là 5 phút. Hồ sơ KH-01 được sử dụng trong phần trình diễn chính; các hồ sơ còn lại phục vụ tình huống đối chiếu nghiệp vụ và kiểm thử.

Các kết quả trong tài liệu là kết quả tham chiếu theo giả định, chưa phải kết quả chạy thực tế của chatbot. Thời lượng trình diễn chưa được xác nhận qua chạy thử.

## 2. Hồ sơ khách hàng mẫu

Bốn hồ sơ dưới đây được xây dựng bằng dữ liệu giả lập. Đơn vị tiền tệ là đồng Việt Nam; thu nhập là thu nhập ròng của hộ gia đình theo tháng, nợ hiện tại là nghĩa vụ trả nợ hằng tháng.

| Mã hồ sơ | Đặc điểm | Thu nhập/tháng | Giá nhà | Vốn tự có | Số tiền vay | Thời hạn | Chi tiêu/tháng | Nợ hiện tại/tháng |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| KH-01 | Vợ chồng nhận lương, mua căn hộ đầu tiên | 40 triệu | 3 tỷ | 1,5 tỷ | 1,5 tỷ | 20 năm | 18 triệu | 0 |
| KH-02 | Người nhận lương, có nhu cầu vay toàn bộ giá mua | 25 triệu | 2,5 tỷ | 0 | 2,5 tỷ | 25 năm | 15 triệu | 2 triệu |
| KH-03 | Hộ kinh doanh, xem xét giới hạn vay theo tài sản | 60 triệu | 3 tỷ | 800 triệu | 2,2 tỷ | 20 năm | 25 triệu | 5 triệu |
| KH-04 | Gia đình có nhu cầu tìm hiểu ân hạn nợ gốc | 35 triệu | 2,5 tỷ | 1,3 tỷ | 1,2 tỷ | 20 năm | 18 triệu | 0 |

Vốn tự có trong bảng chỉ được đối chiếu với giá mua, chưa bao gồm thuế, phí và quỹ dự phòng. Dữ liệu hồ sơ không được sử dụng để kết luận khả năng được phê duyệt tín dụng.

Đối với các tình huống có yêu cầu tính toán, giả định được xác định riêng trong lời thoại: lãi suất cố định 9%/năm, lãi suất tháng bằng lãi suất năm chia 12, gốc trả đều và chưa bao gồm phí. Mức lãi suất này chỉ phục vụ minh họa. Tình huống chưa cung cấp lãi suất hoặc phương thức trả nợ phải được làm rõ trước khi tính toán.

## 3. Kịch bản trình diễn 5 phút

Các lượt trao đổi trong phần trình diễn chính được thực hiện trong cùng một phiên hội thoại.

| Thời gian dự kiến | Nội dung trình diễn | Kết quả tham chiếu |
|---|---|---|
| 00:00–00:30 | Người trình bày giới thiệu: “Chatbot hỗ trợ tìm hiểu thông tin vay mua nhà và mô phỏng khoản trả nợ. Hồ sơ và lãi suất sử dụng trong phần trình diễn là dữ liệu giả lập.” | Xác định mục tiêu và tính chất tham khảo của nội dung trình diễn |
| 00:30–01:15 | Người dùng: “Tôi nhận lương chuyển khoản, muốn vay mua căn hộ. Cần chuẩn bị những nhóm giấy tờ nào?” | Trình bày các nhóm hồ sơ: đề nghị vay, nhân thân, mục đích vay, nguồn trả nợ và tài sản bảo đảm; kèm nguồn tham chiếu |
| 01:15–02:15 | Người dùng: “Tôi muốn mô phỏng khoản vay 1,5 tỷ trong 20 năm, lãi suất giả định cố định 9%/năm, gốc trả đều hằng tháng và lãi giảm dần, không ưu đãi, không ân hạn. Lãi tháng bằng lãi năm chia 12. Tháng đầu trả bao nhiêu?” | Gốc tháng đầu 6,25 triệu đồng; lãi 11,25 triệu đồng; tổng thanh toán 17,5 triệu đồng |
| 02:15–03:00 | Người dùng: “Tôi đổi thành vay 1,2 tỷ, giữ các điều kiện khác. Tính lại tháng đầu.” | Cập nhật số tiền vay thành 1,2 tỷ đồng; giữ các giả định còn lại. Gốc tháng đầu 5 triệu đồng; lãi 9 triệu đồng; tổng thanh toán 14 triệu đồng |
| 03:00–03:45 | Người dùng: “Ngân hàng quảng bá cho vay đến 100% giá trị nhà thì có nghĩa tôi chắc chắn được vay đủ và không cần vốn tự có không?” | Giải thích giới hạn sản phẩm, yêu cầu về bảo đảm và thẩm định; không khẳng định khách hàng được phê duyệt toàn bộ nhu cầu vay |
| 03:45–04:30 | Người dùng: “Nếu trả trước một phần gốc, tiền lãi và lịch trả nợ thay đổi thế nào?” | Giải thích lãi được xác định theo dư nợ còn lại sau hạch toán; phí và lịch trả nợ điều chỉnh phụ thuộc thỏa thuận của khoản vay |
| 04:30–05:00 | Người trình bày giới thiệu nguồn và ngày cập nhật của câu trả lời; kết thúc: “Kết quả hỗ trợ khách hàng chuẩn bị hồ sơ và trao đổi với ngân hàng về điều kiện vay chính thức.” | Xác định giá trị tham khảo và giới hạn của kết quả tư vấn |

## 4. Tình huống theo hồ sơ mẫu

### 4.1. Hồ sơ KH-01: Thay đổi số tiền và thời hạn vay

**Nội dung hội thoại**

1. “Nhà giá 3 tỷ, tôi vay 1,5 tỷ trong 20 năm. Giả sử lãi cố định 9%/năm, gốc trả đều hằng tháng, không ân hạn, lãi năm chia 12. LTV sơ bộ và tháng đầu trả bao nhiêu?”
2. “Tôi chỉ vay 1,2 tỷ. Giữ nguyên các điều kiện khác, tính lại.”
3. “Đổi thời hạn còn 15 năm, các điều kiện khác giữ nguyên.”

**Kết quả tham chiếu**

| Lượt | Số tiền vay | Thời hạn | LTV theo giá mua | Khoản trả tháng đầu |
|---|---:|---:|---:|---:|
| 1 | 1,5 tỷ đồng | 20 năm | 50% | 17.500.000 đồng |
| 2 | 1,2 tỷ đồng | 20 năm | 40% | 14.000.000 đồng |
| 3 | 1,2 tỷ đồng | 15 năm | 40% | Khoảng 15.666.667 đồng |

LTV sơ bộ được tính bằng số tiền vay chia cho giá mua. Tỷ lệ này không thay thế tỷ lệ tính theo giá trị thẩm định của ngân hàng. Các lượt tiếp theo sử dụng dữ kiện đã cập nhật và giữ nguyên các giả định không thay đổi.

### 4.2. Hồ sơ KH-02: Nhu cầu vay 100% giá mua

**Nội dung hội thoại**

1. “Tôi thu nhập 25 triệu/tháng, nợ trả 2 triệu/tháng, nhà 2,5 tỷ và muốn vay toàn bộ 2,5 tỷ trong 25 năm. Ngân hàng quảng bá 100% thì chắc chắn duyệt đúng không?”
2. “Vậy tiền trả tháng đầu là bao nhiêu?”

**Kết quả tham chiếu**

Tỷ lệ nhu cầu vay trên giá mua là 100%. Mức tài trợ được công bố không bảo đảm hồ sơ được phê duyệt; cần xem xét sản phẩm, giá trị tài sản bảo đảm, khả năng trả nợ và các điều kiện liên quan. Đối với lượt thứ hai, chưa đủ dữ kiện để xác định khoản trả tháng đầu. Cần làm rõ lãi suất, phương thức trả nợ và điều kiện ưu đãi hoặc ân hạn nếu có.

### 4.3. Hồ sơ KH-03: Giới hạn vay theo giá trị thẩm định

**Nội dung hội thoại**

1. “Nhà giá 3 tỷ nhưng được định giá bảo đảm 2,5 tỷ. Giả sử chỉ tài trợ tối đa 80% giá định giá. Tôi muốn vay 2,2 tỷ trong 20 năm. Giới hạn theo tài sản và phần thiếu là bao nhiêu?”
2. “BIDV hay Vietcombank có chi phí vay thấp nhất hiện nay? Tôi chưa có báo giá.”

**Kết quả tham chiếu**

Theo giả định, giới hạn vay theo tài sản là 2,5 tỷ × 80% = 2 tỷ đồng. Nhu cầu vay vượt giới hạn này 200 triệu đồng. Phần giá mua cần được tài trợ ngoài khoản vay là 1 tỷ đồng, cao hơn vốn tự có của hồ sơ 200 triệu đồng, chưa bao gồm chi phí giao dịch. Đây là giới hạn theo giả định về tài sản, chưa phải hạn mức phê duyệt.

Đối với yêu cầu so sánh ngân hàng, chưa đủ cơ sở xác định bên có chi phí thấp nhất. Việc so sánh cần dựa trên báo giá cùng điều kiện, bao gồm lãi suất ưu đãi, lãi suất sau ưu đãi, phương pháp tính lãi và các khoản phí liên quan.

### 4.4. Hồ sơ KH-04: Ân hạn nợ gốc

**Nội dung hội thoại**

“Vay 1,2 tỷ trong 20 năm, ân hạn gốc 12 tháng nằm trong 20 năm, lãi cố định giả định 9%/năm; trả lãi hằng tháng và sau ân hạn trả gốc đều, lãi năm chia 12. Tháng ân hạn và tháng đầu sau ân hạn trả bao nhiêu?”

**Kết quả tham chiếu**

Trong 12 tháng đầu, tiền lãi mỗi tháng là 1,2 tỷ × 9% / 12 = 9 triệu đồng. Sau thời gian ân hạn, kỳ hạn trả gốc còn 228 tháng; gốc mỗi tháng khoảng 5.263.158 đồng. Tổng thanh toán tháng đầu sau ân hạn khoảng 14.263.158 đồng. Ân hạn nợ gốc không đồng nghĩa với miễn lãi.

Hồ sơ KH-04 được sử dụng để đối chiếu nghiệp vụ, không thuộc phần mô phỏng trực tiếp trong kịch bản 5 phút, do API ước tính hiện tại chưa tiếp nhận tham số ân hạn.
