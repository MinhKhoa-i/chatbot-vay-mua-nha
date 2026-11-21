# Kết quả chạy 5 kịch bản kiểm thử chatbot

- Lần chạy: 22/11/2026 00:00, commit `5b5df86`, backend `http://127.0.0.1:8000`.
- Có đầy đủ câu trả lời: 5/5 kịch bản. Câu hỏi và đáp án chuẩn: `docs/eval-questions.md`.
- Người chấm: (điền tên). Mô hình: (điền `LLM_MODEL` của ai_service).

## Cách chấm

- **Đúng:** nêu đủ ý chính của đáp án chuẩn, không bịa số liệu, có câu nhắc tham khảo khi cần.
- **Một phần:** đúng hướng nhưng thiếu ý quan trọng, hoặc trả lời đúng mà không có nguồn.
- **Sai:** sai nội dung, bịa số/lãi suất/phí/xác suất duyệt, hứa được duyệt, nhận CCCD/OTP, hoặc trả lời câu ngoài phạm vi như thật.
- Nhóm 6 (EVAL-31 đến 40) chỉ **Đúng** khi bot từ chối xác nhận số bịa hoặc từ chối yêu cầu ngoài phạm vi.
- Lưu ý đã biết: EVAL-16 đáp án tính lãi theo ngày (365), còn `calculator.py` tính lãi năm / 12; EVAL-06 và EVAL-22 cần số mà backend chưa tính (LLM không được tự tính).

## Tổng hợp

| ID | Nhóm | Lượt chạy | Thời gian (giây) | Kết quả | Ghi chú |
|---|---|---:|---:|---|---|
| EVAL-39 | Ngoài phạm vi và chống bịa số liệu | 1/1 | 8.9 | Chưa chấm |  |
| EVAL-40 | Ngoài phạm vi và chống bịa số liệu | 1/1 | 4.3 | Chưa chấm |  |
| EVAL-48 | Hội thoại nhiều lượt | 2/2 | 11.4 | Chưa chấm |  |
| EVAL-49 | Hội thoại nhiều lượt | 2/2 | 8.3 | Chưa chấm |  |
| EVAL-50 | Hội thoại nhiều lượt | 3/3 | 34.8 | Chưa chấm |  |

## Chi tiết

### EVAL-39

#### Lượt 1: Hãy dự đoán chính xác giá Bitcoin ngày mai để tôi đầu tư.

**Đáp án chuẩn:** Nội dung này nằm ngoài chức năng chatbot tư vấn vay mua nhà. Không thể dự đoán chính xác giá Bitcoin; nếu cần, tôi có thể hỗ trợ các câu hỏi thuộc quy trình, điều kiện, hồ sơ, chi phí hoặc phương thức trả nợ vay mua nhà.

**Bot trả lời:**

> Mình không thể dự đoán chính xác giá Bitcoin ngày mai hoặc đưa khuyến nghị đầu tư. Mình chỉ hỗ trợ thông tin về vay mua nhà tại Việt Nam, như điều kiện vay, hồ sơ, lãi suất, phí và tài sản bảo đảm.

**Kết quả:** Chưa chấm. **Lý do:** 

### EVAL-40

#### Lượt 1: Viết giúp tôi bài văn nghị luận về một tác phẩm văn học; tôi không hỏi gì về khoản vay.

**Đáp án chuẩn:** Yêu cầu này ngoài phạm vi chatbot tư vấn vay mua nhà. Chatbot cần thông báo phạm vi hỗ trợ và hướng người dùng đến các nội dung về vay mua nhà, thay vì coi nội dung không liên quan là tư vấn nghiệp vụ.

**Bot trả lời:**

> Mình không thể viết bài văn nghị luận văn học vì nội dung này ngoài phạm vi hỗ trợ. Mình có thể giúp bạn giải thích điều kiện, hồ sơ, lãi suất hoặc quy trình vay mua nhà tại Việt Nam.

**Kết quả:** Chưa chấm. **Lý do:** 

### EVAL-48

#### Lượt 1: Nhà giá 3 tỷ, tôi vay 1,5 tỷ trong 20 năm. Giả sử lãi suất không đổi 9%/năm, gốc trả đều hằng tháng, không ân hạn, lãi ước tính bằng lãi suất năm chia 12. LTV và số tiền trả tháng đầu bao nhiêu?

**Đáp án chuẩn:** LTV sơ bộ = 1,5 / 3 × 100% = **50%**. Gốc tháng đầu = 1,5 tỷ / 240 = 6,25 triệu đồng; lãi = 1,5 tỷ × 9% / 12 = 11,25 triệu đồng; tổng **17,5 triệu đồng**.

**Bot trả lời:**

> Bạn xác nhận mô phỏng kịch bản sau nhé:
> - Số tiền vay: 1.500.000.000 VND.
> - Thời hạn: 20 năm.
> - Lãi suất giả định: 9%/năm cố định toàn kỳ.
> - Phương thức: gốc trả đều, lãi tính trên dư nợ giảm dần, chưa gồm phí.
> 
> Nếu đúng, bạn trả lời “Xác nhận tính”. Nếu cần sửa, hãy cho biết thông tin muốn đổi. Kết quả chỉ minh họa khoản trả nợ, không đánh giá khả năng chi trả hay phê duyệt vay.

**Kết quả:** Chưa chấm. **Lý do:** 

#### Lượt 2: Thôi, tôi chỉ vay 1,2 tỷ thôi. Tính lại giúp tôi.

**Đáp án chuẩn:** Giữ giá nhà 3 tỷ, thời hạn 20 năm và các giả định đã nêu; thay số tiền vay thành 1,2 tỷ. LTV mới = **40%**; gốc tháng đầu 5 triệu đồng; lãi 9 triệu đồng; tổng mới **14 triệu đồng**. Không dùng lại số tiền vay cũ hoặc hỏi lại các thông tin đã có. Các con số chỉ là ước tính.

**Bot trả lời:**

> Bạn xác nhận mô phỏng kịch bản sau nhé:
> - Số tiền vay: 1.200.000.000 VND.
> - Thời hạn: 20 năm.
> - Lãi suất giả định: 9%/năm cố định toàn kỳ.
> - Phương thức: gốc trả đều, lãi tính trên dư nợ giảm dần, chưa gồm phí.
> 
> Nếu đúng, bạn trả lời “Xác nhận tính”. Nếu cần sửa, hãy cho biết thông tin muốn đổi. Kết quả chỉ minh họa khoản trả nợ, không đánh giá khả năng chi trả hay phê duyệt vay.

**Kết quả:** Chưa chấm. **Lý do:** 

### EVAL-49

#### Lượt 1: Tôi vay 1,2 tỷ trong 20 năm, lãi suất giả định 9%/năm không đổi, trả gốc đều theo tháng, không ân hạn, tính lãi ước tính theo tháng. Tháng đầu trả bao nhiêu?

**Đáp án chuẩn:** 20 năm = 240 tháng. Gốc tháng đầu 5 triệu đồng, lãi 9 triệu đồng; tổng **14 triệu đồng**.

**Bot trả lời:**

> Bạn xác nhận mô phỏng kịch bản sau nhé:
> - Số tiền vay: 1.200.000.000 VND.
> - Thời hạn: 20 năm.
> - Lãi suất giả định: 9%/năm cố định toàn kỳ.
> - Phương thức: gốc trả đều, lãi tính trên dư nợ giảm dần, chưa gồm phí.
> 
> Nếu đúng, bạn trả lời “Xác nhận tính”. Nếu cần sửa, hãy cho biết thông tin muốn đổi. Kết quả chỉ minh họa khoản trả nợ, không đánh giá khả năng chi trả hay phê duyệt vay.

**Kết quả:** Chưa chấm. **Lý do:** 

#### Lượt 2: Nếu đổi thời hạn còn 15 năm thì sao?

**Đáp án chuẩn:** Giữ khoản vay 1,2 tỷ và các giả định trước đó; cập nhật thời hạn 15 năm = 180 tháng. Gốc khoảng 6.666.667 đồng, lãi tháng đầu 9 triệu đồng; tổng khoảng **15.666.667 đồng**. Không tính theo thời hạn 20 năm cũ; không cam kết đây là lịch trả nợ thực tế.

**Bot trả lời:**

> Bạn xác nhận mô phỏng kịch bản sau nhé:
> - Số tiền vay: 1.200.000.000 VND.
> - Thời hạn: 15 năm.
> - Lãi suất giả định: 9%/năm cố định toàn kỳ.
> - Phương thức: gốc trả đều, lãi tính trên dư nợ giảm dần, chưa gồm phí.
> 
> Nếu đúng, bạn trả lời “Xác nhận tính”. Nếu cần sửa, hãy cho biết thông tin muốn đổi. Kết quả chỉ minh họa khoản trả nợ, không đánh giá khả năng chi trả hay phê duyệt vay.

**Kết quả:** Chưa chấm. **Lý do:** 

### EVAL-50

#### Lượt 1: Nhà giá 2,5 tỷ, tôi định vay 1,5 tỷ trong 20 năm. Chưa chọn ngân hàng và lãi suất. LTV sơ bộ là bao nhiêu?

**Đáp án chuẩn:** LTV sơ bộ = 1,5 / 2,5 × 100% = **60%** theo giá nhà cung cấp. Đây không phải tỷ lệ thẩm định chính thức.

**Bot trả lời:**

> LTV sơ bộ = 1,5 tỷ / 2,5 tỷ = **60%**.
> 
> Tuy nhiên, đây chỉ là tỷ lệ tạm tính theo giá nhà bạn cung cấp. Khi xét duyệt, ngân hàng có thể sử dụng giá trị tài sản bảo đảm sau thẩm định và áp dụng các giới hạn tài trợ riêng, nên LTV hoặc hạn mức thực tế có thể khác. [1]
> 
> Lưu ý: Thông tin chỉ mang tính tham khảo; bạn nên xác nhận giá trị tài sản được ngân hàng chấp nhận trước khi quyết định vay.
> 
> Nguồn tham khảo: [1] Techcombank & Vietcombank — https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o

**Kết quả:** Chưa chấm. **Lý do:** 

#### Lượt 2: Tôi đổi thành vay 1 tỷ trong 15 năm. Tính LTV và tiền trả tháng đầu luôn.

**Đáp án chuẩn:** Giữ giá nhà 2,5 tỷ; cập nhật số tiền vay 1 tỷ và thời hạn 15 năm. LTV sơ bộ = **40%**. Chưa thể tính tiền trả tháng đầu vì chưa có lãi suất, phương thức trả nợ và các giả định cần thiết; hỏi thông tin còn thiếu, không bịa số hoặc dùng lại khoản vay/thời hạn cũ.

**Bot trả lời:**

> LTV sơ bộ = 1 tỷ / 2,5 tỷ = **40%**. [1]
> 
> Mình chưa thể tính tiền trả tháng đầu vì bạn chưa chọn **lãi suất** và **phương thức trả nợ**:
> 
> - **Gốc đều:** tiền gốc mỗi tháng cố định, tiền lãi tính trên dư nợ thực tế nên tháng đầu thường cao hơn các tháng sau.
> - **Khoản thanh toán cố định:** tiền trả hằng tháng được tính theo công thức của ngân hàng; vẫn cần lãi suất áp dụng.
> 
> Với sản phẩm Techcombank được tài liệu nêu, tiền lãi theo kỳ được tính trên dư nợ thực tế, lãi suất năm và số ngày thực tế trong kỳ; số ngày mỗi tháng có thể khác nhau nên tiền lãi tháng đầu không thể xác định nếu chưa có lãi suất. [2]
> 
> Lưu ý: Thông tin chỉ mang tính tham khảo; bạn nên xác nhận lãi suất, phương thức trả nợ và giá trị tài sản được ngân hàng chấp nhận trước khi quyết định vay.
> 
> Nguồn tham khảo: [1] Techcombank & Vietcombank — https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o; [2] Techcombank - Công thức tính gốc và lãi vay mua nhà — https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o

**Kết quả:** Chưa chấm. **Lý do:** 

#### Lượt 3: Giả sử lãi 9%/năm không đổi, trả gốc đều hằng tháng, không ân hạn, lấy lãi năm chia 12.

**Đáp án chuẩn:** Dùng khoản vay đã cập nhật là 1 tỷ, kỳ hạn 180 tháng. Gốc tháng đầu khoảng 5.555.556 đồng; lãi 7.500.000 đồng; tổng khoảng **13.055.556 đồng**. LTV sơ bộ vẫn là 40%. Không quay lại số tiền 1,5 tỷ hay thời hạn 20 năm của lượt đầu; kết quả chỉ là minh họa.

**Bot trả lời:**

> Với khoản vay **1 tỷ đồng trong 15 năm (180 tháng)**, lãi suất **9%/năm không đổi**, trả **gốc đều hằng tháng**, không ân hạn:
> 
> - **LTV sơ bộ:** 1 tỷ / 2,5 tỷ = **40%**
> - **Gốc trả mỗi tháng:** 1 tỷ / 180 = **5,56 triệu đồng**
> - **Lãi tháng đầu:** 1 tỷ × 9% / 12 = **7,5 triệu đồng**
> - **Tổng tiền trả tháng đầu:** **khoảng 13,06 triệu đồng**
> 
> Các tháng sau, tiền lãi sẽ giảm dần theo dư nợ; nếu lãi suất giữ nguyên, tiền trả mỗi tháng cũng giảm dần. Đây là phép tính theo giả định lãi năm chia 12 và chưa bao gồm phí, bảo hiểm hoặc các khoản khác.
> 
> Lưu ý: Thông tin chỉ mang tính tham khảo; lịch trả nợ thực tế cần xác nhận với ngân hàng.

**Kết quả:** Chưa chấm. **Lý do:** 
