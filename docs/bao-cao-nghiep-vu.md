# BÁO CÁO NGHIỆP VỤ CHATBOT TƯ VẤN VAY MUA NHÀ

## 1. Bài toán

Thông tin về vay mua nhà bao gồm nhiều nội dung như điều kiện cấp tín dụng, hồ sơ, hạn mức, thời hạn, lãi suất, phí và bảo hiểm. Các nội dung này được công bố theo từng ngân hàng và sản phẩm, đồng thời có thể thay đổi theo thời điểm. Việc tiếp cận thông tin từ nhiều nguồn làm phát sinh khó khăn trong quá trình tổng hợp, so sánh và xác định phương án vay phù hợp.

Chatbot tư vấn vay mua nhà được xây dựng nhằm hỗ trợ người dùng tra cứu thông tin bằng tiếng Việt, giải thích các khái niệm nghiệp vụ và mô phỏng khoản trả nợ theo dữ liệu được cung cấp. Thông qua đó, hệ thống hỗ trợ người dùng chuẩn bị thông tin và hồ sơ trước khi làm việc với ngân hàng.

## 2. Đối tượng và phạm vi tư vấn

Đối tượng sử dụng là cá nhân có nhu cầu tìm hiểu khoản vay mua nhà tại Việt Nam. Phạm vi dữ liệu tham chiếu bao gồm các sản phẩm của Vietcombank, BIDV và Techcombank có trong kho tri thức của dự án.

| Nhóm nội dung | Phạm vi tư vấn |
|---|---|
| Điều kiện vay | Giải thích điều kiện chung và yêu cầu của từng sản phẩm theo nguồn dữ liệu |
| Hồ sơ vay | Hướng dẫn các nhóm giấy tờ về nhân thân, mục đích vay, nguồn trả nợ và tài sản bảo đảm |
| Hạn mức và thời hạn | Giải thích giới hạn sản phẩm; phân biệt giá mua với giá trị tài sản được thẩm định |
| Lãi suất và chi phí | Giải thích lãi suất ưu đãi, lãi suất điều chỉnh, phí trả trước hạn và bảo hiểm liên quan |
| Quy trình vay | Trình bày các bước từ chuẩn bị hồ sơ đến tất toán |
| So sánh sản phẩm | Đối chiếu các tiêu chí tương đương trên cơ sở nguồn và thời điểm công bố |
| Mô phỏng khoản vay | Ước tính khoản trả nợ theo số tiền vay, thời hạn, lãi suất và phương thức trả nợ được xác định |
| Hội thoại nhiều lượt | Tiếp nhận thông tin bổ sung, cập nhật số tiền hoặc thời hạn vay theo yêu cầu của người dùng |

Các nội dung phê duyệt tín dụng, xác định xác suất được vay, tra cứu CIC cá nhân, tiếp nhận thông tin xác thực ngân hàng, nộp hồ sơ và giải ngân thay khách hàng nằm ngoài phạm vi của hệ thống.

## 3. Quy trình vay và quy trình tư vấn

### 3.1. Quy trình vay mua nhà

Quy trình vay mua nhà được khái quát thành các giai đoạn sau:

1. **Chuẩn bị hồ sơ:** Khách hàng xác định nhu cầu vay và chuẩn bị tài liệu về nhân thân, mục đích sử dụng vốn, nguồn trả nợ và tài sản bảo đảm theo yêu cầu của ngân hàng.
2. **Tiếp nhận hồ sơ:** Ngân hàng tiếp nhận, kiểm tra thành phần hồ sơ và yêu cầu bổ sung khi cần thiết.
3. **Thẩm định:** Ngân hàng đánh giá điều kiện vay, khả năng trả nợ, phương án sử dụng vốn và tài sản bảo đảm.
4. **Phê duyệt:** Ngân hàng quyết định việc cấp tín dụng và các điều kiện áp dụng đối với khoản vay.
5. **Ký kết và hoàn thiện thủ tục:** Các bên ký hợp đồng, hoàn thiện hồ sơ và thủ tục bảo đảm theo yêu cầu.
6. **Giải ngân:** Ngân hàng thực hiện giải ngân theo điều kiện và phương thức đã thỏa thuận.
7. **Trả nợ và tất toán:** Khách hàng thực hiện nghĩa vụ thanh toán; khoản vay được tất toán sau khi hoàn thành các nghĩa vụ theo hợp đồng.

Nội dung chi tiết được trình bày trong [Tài liệu quy trình vay mua nhà](quy-trinh-vay.md).

### 3.2. Quy trình tư vấn của chatbot

Quy trình tư vấn bắt đầu bằng việc xác định nhu cầu của người dùng, bao gồm tra cứu kiến thức, so sánh sản phẩm hoặc mô phỏng khoản vay. Hệ thống tiếp tục làm rõ các thông tin cần thiết, tra cứu tài liệu hoặc sử dụng công cụ tính toán phù hợp, sau đó trình bày kết quả kèm nguồn dữ liệu và các giả định liên quan.

Đối với hội thoại nhiều lượt, thông tin thay đổi được cập nhật theo yêu cầu mới nhất của người dùng. Các dữ kiện đã xác nhận được duy trì trong cùng tình huống; những thông tin còn thiếu hoặc mâu thuẫn cần được làm rõ trước khi đưa ra kết quả. Kết thúc quá trình tư vấn, hệ thống hướng dẫn người dùng chuẩn bị hồ sơ hoặc xác nhận điều kiện khoản vay trực tiếp với ngân hàng.

## 4. Nguồn dữ liệu

Dữ liệu nghiệp vụ được tổng hợp từ các trang sản phẩm chính thức của ngân hàng và văn bản pháp luật được dẫn chiếu trong kho tri thức. Các tài liệu trong dự án được sử dụng như sau:

| Tài liệu | Nội dung sử dụng |
|---|---|
| [Kho câu hỏi thường gặp](../data/faq.json) | 60 câu hỏi và câu trả lời về nghiệp vụ vay mua nhà; mỗi mục có thông tin nguồn và ngày cập nhật |
| [Quy trình vay mua nhà](quy-trinh-vay.md) | Các giai đoạn thực hiện khoản vay và nghĩa vụ liên quan |
| [Danh sách ngân hàng](danh-sach-ngan-hang.md) | Thông tin tham chiếu về ngân hàng trong phạm vi dự án |
| [Lược đồ dữ liệu](schema.md) | Cấu trúc và quy ước dữ liệu sản phẩm vay |

Thông tin nguồn và trường `last_updated` phục vụ truy xuất, đối chiếu dữ liệu. Ngày cập nhật dữ liệu được phân biệt với ngày hiệu lực của văn bản hoặc thời gian áp dụng của sản phẩm. Điều kiện khoản vay thực tế cần được xác nhận theo thông tin chính thức của ngân hàng tại thời điểm giao dịch.

## 5. Giới hạn và giá trị tham khảo

Kết quả tư vấn của chatbot có tính chất cung cấp thông tin và hỗ trợ chuẩn bị phương án vay. Hệ thống không thay thế hoạt động thẩm định, quyết định cấp tín dụng hoặc tư vấn pháp lý của cơ quan, tổ chức có thẩm quyền. Hạn mức quảng bá của sản phẩm không đồng nghĩa với số tiền được phê duyệt cho từng khách hàng.

Kết quả mô phỏng phụ thuộc vào dữ liệu đầu vào, phương thức trả nợ và giả định tính toán. Số tiền thực tế có thể khác do phương pháp tính lãi theo ngày, biến động lãi suất, phí và các điều khoản của hợp đồng. Các tỷ lệ hoặc mức lãi suất giả định trong tình huống minh họa không được xem là chính sách chung của ngân hàng.

Phạm vi trình diễn được giới hạn theo chức năng hiện có. Nội dung ân hạn nợ gốc trong hồ sơ mẫu được sử dụng để đối chiếu nghiệp vụ, do API ước tính hiện tại chưa tiếp nhận tham số ân hạn. Kịch bản trình diễn và các kết quả tham chiếu được trình bày tại [Kịch bản demo](kich-ban-demo.md); chưa có kết quả chạy thực tế để xác nhận thời lượng và mức độ đáp ứng của chatbot.
