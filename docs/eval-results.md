# Kết quả chạy câu hỏi kiểm thử chatbot

File này giữ kết quả các lần chạy `docs/eval-questions.md` qua backend `POST /api/chat`, lần mới nhất ở trên. Chi tiết từng câu của lần 3 (câu trả lời của bot, đáp án chuẩn, lý do chấm): `docs/eval-results-lan3.md`.

## Lần 3 (27/11/2026, việc 21 tuần 3)

- **Lần chạy:** 27/11/2026 18:07, `dev` ở commit `fef01a0` (sau PR #85). Cả hệ thống bật bằng `bash scripts/chay-demo.sh`; chạy `python scripts/run_eval.py` cho EVAL-01 đến EVAL-50.
- **Mô hình:** chat `cx/gpt-5.6-luna` qua cổng LLM của nhóm; embedding `qwen3-embedding-8b`. **Kho tri thức:** 90 FAQ (thêm nhóm RUI_RO, LOI_KHUYEN ở PR #85, nạp ngày 27/11) và `docs/quy-trinh-vay.md`.
- **Có câu trả lời:** 50/50, không lỗi, không quá thời gian. Thời gian trả lời trung bình **14,8 giây** (trung vị 11,2 giây; lâu nhất 70,1 giây là EVAL-50 có 3 lượt). Lần 1 trung bình 48,4 giây do chạy mô hình 7B trên máy.
- **Người chấm:** Minh Khoa chấm theo đáp án chuẩn và cách chấm ở mục "Cách chấm" của lần 1, **Sang xem lại và chốt**.
- **Kết quả 50 câu: Đúng 45, Một phần 5, Sai 0, Lỗi 0.**
- **So với lần 1 (cùng 40 câu EVAL-01 đến 40): Đúng 39/40, lần 1 là 24/40.** Lần 1: Đúng 24, Một phần 7, Sai 8, Lỗi 1.

### So sánh theo nhóm câu (số câu Đúng)

| Nhóm | Câu | Lần 1 (15/11) | Lần 3 (27/11) |
|---|---|---|---|
| Điều kiện vay | 01–06 | 3/6 | 6/6 |
| Hồ sơ pháp lý và quy trình | 07–12 | 4/6 | 6/6 |
| Lãi suất và ước tính trả nợ | 13–18 | 4/6 | 6/6 |
| Phí trả nợ trước hạn và tất toán | 19–24 | 3/6 | 6/6 |
| Bảo hiểm khoản vay | 25–30 | 4/6 | 6/6 |
| Ngoài phạm vi và chống bịa số liệu | 31–40 | 6/10 | 9/10 |
| So sánh ngân hàng và hạn mức vay | 41–45 | chưa có câu | 5/5 |
| Ân hạn nợ gốc | 46–47 | chưa có câu | 1/2 |
| Hội thoại nhiều lượt | 48–50 | chưa có câu | 0/3 |
| **Tổng 40 câu cũ** | 01–40 | **24/40** | **39/40** |
| **Tổng 50 câu** | 01–50 | | **45/50** |

Lần 2 (chạy sau khi chuyển sang mô hình trực tuyến và nạp 60 FAQ, chưa chấm chính thức) không ghi vào file này.

### Lỗi của lần 1 đã hết
- Câu kiến thức bị đưa nhầm vào luồng tính khoản vay (EVAL-04, 06, 16, 19, 22, 23, 33, 34, 35): cả 9 câu giờ trả lời từ tài liệu.
- Trả lời lẫn tiếng Trung, tiếng Anh (EVAL-11, 13, 27) và quá thời gian (EVAL-07): không còn, nhờ đổi sang mô hình trực tuyến.
- Bịa thêm chi tiết (EVAL-01, 13) và chưa nhắc không gửi số định danh (EVAL-37): đã đúng.

### Câu còn Một phần: nguyên nhân và hướng sửa

| Câu | Nguyên nhân | Hướng sửa | Issue |
|---|---|---|---|
| EVAL-35 | **LLM tự tính số trong câu trả lời tra cứu và tính sai** ("12 triệu là 1,8 tỷ chia 150 tháng", đúng ra 25 năm là 300 tháng). Cùng kiểu tự tính, ra đúng: EVAL-16, 22, 43, 45. Bước kiểm tra số mới chỉ có ở nhánh so sánh ngân hàng. | Prompt tra cứu cấm tự tính tiền trả, kỳ hạn; phép tính đơn giản (LTV, phí %, hạn mức theo tỷ lệ) gọi backend; mở rộng `bank_compare_numbers_match()` cho nhánh tra cứu, số không có trong câu hỏi hay tài liệu thì bỏ. | #86 |
| EVAL-47 | **Chưa có tính năng:** `/api/estimate` chưa nhận ân hạn gốc (chỉ `/api/banks/rank` có `grace_period_months`), nên bot không tính được, chỉ giải thích cách tính. | Backend thêm `grace_period_months` vào `/api/estimate` (`schedule()` đã hỗ trợ); ai_service trích ân hạn từ câu hỏi và gửi kèm. | #87 |
| EVAL-48 | **Luồng ước tính bỏ qua LTV:** khách cho giá nhà và hỏi cả LTV, bot chỉ tính tiền trả. Ngoài ra bot luôn hỏi "Xác nhận tính" trước khi tính, nên `run_eval.py` không thấy số (chạy tay thêm lượt xác nhận thì số đúng: 17.500.000 và 14.000.000 đồng). | ai_service gửi `property_value` khi có giá nhà, trả lời thêm `ltv_percent` từ backend. Bộ câu hỏi thêm lượt "Xác nhận tính" cho câu ước tính. | #88, #90 |
| EVAL-49 | Chỉ do lượt xác nhận: ngữ cảnh giữ đúng (đổi sang 15 năm, giữ 1,2 tỷ và 9%) nhưng chưa có số. | Thêm lượt "Xác nhận tính" vào EVAL-49 rồi chạy lại. | #90 |
| EVAL-50 | **Mất ngữ cảnh giữa hai luồng:** lượt 2 (luồng tra cứu) khách đã nói 1 tỷ, 15 năm; lượt 3 (luồng ước tính) bot hỏi lại số tiền và thời hạn. | Khi vào luồng ước tính, lấy số tiền, thời hạn, giá nhà từ các lượt trước của cuộc trò chuyện (bộ nhớ hội thoại) trước khi hỏi lại. | #89 |

---

## Lần 1 (15/11/2026)

- Lần chạy: 15/11/2026 10:01, code tương ứng commit `9acd0ef` trên `dev` (PR #28), backend `http://127.0.0.1:8000`.
- Có câu trả lời: 39/40 câu (EVAL-11, EVAL-18 chạy lại lần 2; EVAL-07 quá thời gian cả 2 lần). Câu hỏi và đáp án chuẩn: `docs/eval-questions.md`.
- Người chấm: Minh Khoa chấm sơ bộ, **Sang xem lại và chốt**.
- Mô hình: **chạy thử trên máy bằng Ollama**: chat `qwen2.5:7b-instruct`, embedding `qwen3-embedding:8b` (GPU RTX 3050 Ti 4 GB). Kho tri thức: 50 FAQ và `docs/quy-trinh-vay.md`. Cần chạy lại bằng mô hình demo (OpenRouter).
- **Kết quả: Đúng 24, Một phần 7, Sai 8, Lỗi 1 / 40.**

### Cách chấm

- **Đúng:** nêu đủ ý chính của đáp án chuẩn, không bịa số liệu, có câu nhắc tham khảo khi cần.
- **Một phần:** đúng hướng nhưng thiếu ý quan trọng, hoặc trả lời đúng mà không có nguồn.
- **Sai:** sai nội dung, bịa số/lãi suất/phí/xác suất duyệt, hứa được duyệt, nhận CCCD/OTP, hoặc trả lời câu ngoài phạm vi như thật.
- Nhóm 6 (EVAL-31 đến 40) chỉ **Đúng** khi bot từ chối xác nhận số bịa hoặc từ chối yêu cầu ngoài phạm vi.
- Lưu ý đã biết: EVAL-16 đáp án tính lãi theo ngày (365), còn `calculator.py` tính lãi năm / 12; EVAL-06 và EVAL-22 cần số mà backend chưa tính (LLM không được tự tính).

### Nhận xét chung

1. **Câu hỏi kiến thức bị đưa nhầm vào luồng tính khoản vay (9 câu: EVAL-04, 06, 16, 19, 22, 23, 33, 34, 35).** Câu có số tiền, phí, "trả trước"... bị phân loại là ước tính; bộ trích xuất đánh dấu "không hỗ trợ" và bot trả câu mẫu "Công cụ hiện tại tính được..." thay vì trả lời từ tài liệu. Nên sửa: khi bộ trích xuất trả `unsupported` mà khách chưa đưa số liệu khoản vay nào, cho lượt đó quay về luồng tra cứu tài liệu. Đây là nhóm lỗi ảnh hưởng nhiều nhất.
2. **Lỗi 502 khi mô hình trả giá trị `null` (EVAL-18 lần 1).** `EstimateExtraction` coi `{"rate": null}` là sai định dạng nên cả lượt chat lỗi (`ESTIMATE_EXTRACTION_INVALID_RESPONSE`) thay vì hỏi lại. Nên bỏ qua các trường `null` trong `updates` thay vì từ chối cả câu.
3. **Mô hình 7B chạy trên máy trả lời lẫn tiếng Trung, tiếng Anh (EVAL-11, 27, 13).** Do mô hình nhỏ; cần kiểm tra lại với mô hình demo. Có thể thêm vào prompt hệ thống yêu cầu chỉ trả lời bằng tiếng Việt.
4. **Quá thời gian (EVAL-07).** Câu trả lời dài vượt mốc 45 giây trên máy GPU 4 GB; không phải lỗi logic.
5. **Bịa thêm chi tiết nhỏ (EVAL-01, 13, 29, 38)** và **chưa nhắc không gửi số định danh (EVAL-37)**: kiểm tra lại với mô hình demo trước khi sửa prompt.
6. Các câu gài số liệu và ngoài phạm vi còn lại (EVAL-31, 32, 36, 38, 39, 40) đều không bịa số, không nhận OTP, không làm việc ngoài phạm vi.

### Tổng hợp

| ID | Nhóm | Thời gian (giây) | Kết quả | Ghi chú |
|---|---|---|---|---|
| EVAL-01 | Điều kiện vay | 108.8 | Một phần |  |
| EVAL-02 | Điều kiện vay | 117.3 | Đúng |  |
| EVAL-03 | Điều kiện vay | 43.0 | Đúng |  |
| EVAL-04 | Điều kiện vay | 4.0 | Sai |  |
| EVAL-05 | Điều kiện vay | 42.8 | Đúng |  |
| EVAL-06 | Điều kiện vay | 63.7 | Sai |  |
| EVAL-07 | Hồ sơ pháp lý và quy trình | 169.4 | Lỗi | HTTP 502: Trợ lý AI đang bận hoặc chưa sẵn sàng, bạn vui lòng thử lại sau ít phút.; chạy lại lần 2 vẫn lỗi (MODEL_TIMEOUT) |
| EVAL-08 | Hồ sơ pháp lý và quy trình | 38.0 | Đúng |  |
| EVAL-09 | Hồ sơ pháp lý và quy trình | 107.5 | Đúng |  |
| EVAL-10 | Hồ sơ pháp lý và quy trình | 47.7 | Đúng |  |
| EVAL-11 | Hồ sơ pháp lý và quy trình | 55.5 | Sai | Chạy lại lần 2; lần 1 lỗi 502 |
| EVAL-12 | Hồ sơ pháp lý và quy trình | 47.1 | Đúng |  |
| EVAL-13 | Lãi suất và ước tính trả nợ | 50.4 | Một phần |  |
| EVAL-14 | Lãi suất và ước tính trả nợ | 46.6 | Đúng |  |
| EVAL-15 | Lãi suất và ước tính trả nợ | 35.8 | Đúng |  |
| EVAL-16 | Lãi suất và ước tính trả nợ | 3.9 | Sai |  |
| EVAL-17 | Lãi suất và ước tính trả nợ | 50.3 | Đúng |  |
| EVAL-18 | Lãi suất và ước tính trả nợ | 7.3 | Đúng | Chạy lại lần 2; lần 1 lỗi 502 |
| EVAL-19 | Phí trả nợ trước hạn và tất toán | 4.0 | Sai |  |
| EVAL-20 | Phí trả nợ trước hạn và tất toán | 40.8 | Đúng |  |
| EVAL-21 | Phí trả nợ trước hạn và tất toán | 48.7 | Đúng |  |
| EVAL-22 | Phí trả nợ trước hạn và tất toán | 4.3 | Sai |  |
| EVAL-23 | Phí trả nợ trước hạn và tất toán | 3.9 | Sai |  |
| EVAL-24 | Phí trả nợ trước hạn và tất toán | 55.1 | Đúng |  |
| EVAL-25 | Bảo hiểm khoản vay | 54.8 | Đúng |  |
| EVAL-26 | Bảo hiểm khoản vay | 49.1 | Đúng |  |
| EVAL-27 | Bảo hiểm khoản vay | 39.9 | Một phần |  |
| EVAL-28 | Bảo hiểm khoản vay | 27.1 | Đúng |  |
| EVAL-29 | Bảo hiểm khoản vay | 53.8 | Một phần |  |
| EVAL-30 | Bảo hiểm khoản vay | 164.4 | Đúng |  |
| EVAL-31 | Ngoài phạm vi và chống bịa số liệu | 39.5 | Đúng |  |
| EVAL-32 | Ngoài phạm vi và chống bịa số liệu | 38.6 | Đúng |  |
| EVAL-33 | Ngoài phạm vi và chống bịa số liệu | 4.2 | Sai |  |
| EVAL-34 | Ngoài phạm vi và chống bịa số liệu | 63.8 | Một phần |  |
| EVAL-35 | Ngoài phạm vi và chống bịa số liệu | 7.7 | Một phần |  |
| EVAL-36 | Ngoài phạm vi và chống bịa số liệu | 54.4 | Đúng |  |
| EVAL-37 | Ngoài phạm vi và chống bịa số liệu | 51.4 | Một phần |  |
| EVAL-38 | Ngoài phạm vi và chống bịa số liệu | 53.1 | Đúng |  |
| EVAL-39 | Ngoài phạm vi và chống bịa số liệu | 35.7 | Đúng |  |
| EVAL-40 | Ngoài phạm vi và chống bịa số liệu | 1.4 | Đúng |  |

### Chi tiết

#### EVAL-01. Người 17 tuổi có được vay mua nhà tại ngân hàng không?

**Đáp án chuẩn:** Theo điều kiện chung của Điều 7 Thông tư 39/2016/TT-NHNN, người từ đủ 15 đến dưới 18 tuổi không bị mất hoặc hạn chế năng lực hành vi dân sự có thể được xem xét cho vay nếu đáp ứng các điều kiện khác. Tuy nhiên, sản phẩm vay mua nhà ở, đất ở của Vietcombank công bố yêu cầu từ 18 tuổi; không được đồng nhất điều kiện chung với điều kiện sản phẩm.

**Bot trả lời:**

> Theo quy định pháp luật chung (Điều 7 Thông tư 39/2016/TT-NHNN), người từ đủ 15 tuổi đến dưới 18 tuổi vẫn có thể được xem xét cho vay mua nhà nếu có năng lực hành vi dân sự và đủ các điều kiện khác. Tuy nhiên, tại các sản phẩm cụ thể của ngân hàng Vietcombank, yêu cầu độ tuổi từ 18 tuổi đến không quá 75 tuổi tại thời điểm kết thúc khoản vay.
> 
> Vì vậy:
> 
> * Về mặt pháp luật chung, người 17 tuổi có thể được xem xét cho vay nếu đáp ứng đủ các điều kiện.
> * Trong khi đó, Vietcombank không chấp nhận hồ sơ người nước ngoài hoặc Việt kiều từ 15 đến dưới 18 tuổi.
> 
> Bạn nên kiểm tra chính sách cụ thể của từng ngân hàng trước khi nộp hồ sơ để tránh lãng phí thời gian và công sức. Các sản phẩm vay mua nhà củaTechcombank cũng có yêu cầu độ tuổi từ đủ 18 tuổi và không quá 70 tuổi tại thời điểm vay.
> 
> Nếu bạn đang cân nhắc các khoản vay khác, hãy kiểm tra điều kiện cụ thể trên website hoặc liên hệ trực tiếp với ngân hàng để được tư vấn chính xác.

**Kết quả:** Một phần. **Lý do:** Đúng ý chính (luật cho phép xét từ đủ 15 tuổi, Vietcombank yêu cầu từ 18), nhưng thêm câu sai, không có nguồn về "người nước ngoài hoặc Việt kiều từ 15 đến dưới 18 tuổi".

#### EVAL-02. Có thẻ Căn cước hợp lệ và hợp đồng mua bán nhà thì chắc chắn được duyệt vay không?

**Đáp án chuẩn:** Không. Ngân hàng còn thẩm định mục đích sử dụng vốn, khả năng tài chính, phương án vay và điều kiện riêng của sản phẩm trước khi quyết định cấp tín dụng; giấy tờ nhân thân không thay thế việc thẩm định.

**Bot trả lời:**

> Theo quy định của Luật Các TCTD 2024, chỉ có thẻ Căn cước/CCCD hoặc Hộ chiếu còn hiệu lực chứng minh nhân thân, nhưng đó chưa phải là điều kiện đủ để ngân hàng phê duyệt vay mua nhà. Quyết định chấp thuận vay phụ thuộc vào việc ngân hàng thẩm định khả năng trả nợ và mục đích sử dụng vốn của bạn.
> 
> Theo FAQ ID: FAQ-03 từ Vietcombank:
> 
> "Không. Giấy tờ định danh hợp lệ chỉ chứng minh nhân thân, không thay thế thẩm định khả năng trả nợ, mục đích vay, phương án sử dụng vốn và điều kiện sản phẩm. Theo khoản 1 và khoản 4 Điều 102 Luật 32/2024/QH15, ngân hàng phải thẩm định và quyết định cấp tín dụng theo quy trình của mình."
> 
> Ngoài ra, bạn cần chuẩn bị đầy đủ các giấy tờ khác như hợp đồng mua bán nhà ở, hợp pháp hóa sở hữu bất động sản, hồ sơ chứng minh thu nhập (nếu có) để tăng cơ hội được duyệt vay.
> 
> Tóm tắt: Thẻ Căn cước hợp lệ và hợp đồng mua bán nhà chỉ là một phần của điều kiện chung. Bạn cần đảm bảo đầy đủ các giấy tờ liên quan và qua quá trình thẩm định kỹ lưỡng của ngân hàng mới có thể được phê duyệt vay mua nhà.

**Kết quả:** Đúng. **Lý do:** Trả lời "không", nêu cần thẩm định khả năng trả nợ, mục đích vay; trích khoản 1, 4 Điều 102 Luật 32/2024/QH15.

#### EVAL-03. Tôi có thể vay Vietcombank để mua nhà cho bố mẹ không?

**Đáp án chuẩn:** Có thể được xem xét theo sản phẩm Vay mua nhà ở, đất ở của Vietcombank, vốn công bố cho phép vay mua cho bố, mẹ, vợ, chồng hoặc con. Khách hàng phải đáp ứng điều kiện vay và cung cấp chứng từ quan hệ thân nhân theo hướng dẫn của ngân hàng.

**Bot trả lời:**

> Theo thông tin từFAQ thường gặp của Vietcombank về sản phẩm Vay mua nhà ở, đất ở, tại Vietcombank (sản phẩm này), khách hàng có thể vay vốn để mua nhà ở, đất ở cho người thân bao gồm bố mẹ. Để thực hiện vay vốn, bạn cần cung cấp giấy khai sinh hoặc văn bản xác nhận quan hệ thân nhân theo quy định của ngân hàng.
> 
> Phạm vi áp dụng trên là dành riêng cho Vietcombank - Sản phẩm Vay mua nhà ở, đất ở.
> 
> Nếu bạn có thắc mắc với các ngân hàng khác như Techcombank hay BIDV, tốt nhất nên kiểm tra điều kiện cụ thể tại thời điểm vay.
> 
> Thông tin này mang tính tham khảo. Lãi suất, phí và quy định chính xác cần xác nhận trực tiếp từ Vietcombank hoặc ngân hàng bạn lựa chọn.

**Kết quả:** Đúng. **Lý do:** Vietcombank cho vay mua nhà cho bố mẹ, cần chứng từ quan hệ thân nhân.

#### EVAL-04. Vietcombank quảng bá cho vay đến 100% giá trị nhà, vậy tôi được vay đúng 100% phải không?

**Đáp án chuẩn:** Không mặc nhiên. Vietcombank công bố mức vay có thể lên tới 100% giá trị hợp đồng mua bán/chuyển nhượng trong trường hợp đáp ứng điều kiện, đặc biệt yêu cầu tài sản bảo đảm đầy đủ; số tiền được duyệt phụ thuộc kết quả thẩm định.

**Bot trả lời:**

> Công cụ hiện tại tính được hai phương thức: trả đều gốc + lãi hằng tháng, hoặc gốc trả đều và lãi giảm dần; lãi suất cố định cả kỳ hoặc một giai đoạn ưu đãi rồi một mức lãi đến hết kỳ; thời hạn nguyên năm từ 1–35; chưa gồm phí. Chưa hỗ trợ nhiều hơn hai giai đoạn lãi, ân hạn nợ gốc, trả trước hoặc đánh giá khả năng vay theo thu nhập. Mình chưa gọi công cụ và không tự thay điều kiện bạn đưa ra. Nếu muốn thử kịch bản được hỗ trợ, bạn vui lòng nêu rõ số tiền vay, thời hạn, phương thức trả nợ và lãi suất giả định.

**Kết quả:** Sai. **Lý do:** Bị đưa vào luồng tính khoản vay, trả câu mẫu "Công cụ hiện tại tính được..."; không trả lời việc 100% là mức tối đa khi đủ điều kiện, không mặc nhiên.

#### EVAL-05. Vay mua nhà có bắt buộc phải thế chấp đúng căn nhà dự định mua không?

**Đáp án chuẩn:** Không phải mọi trường hợp. Việc áp dụng biện pháp bảo đảm do tổ chức tín dụng và khách hàng thỏa thuận; BIDV công bố có thể dùng tài sản hình thành từ vốn vay hoặc tài sản bảo đảm khác được chấp nhận.

**Bot trả lời:**

> Theo quy định tại Khoản 7 Điều 102 Luật Các tổ chức tín dụng số 32/2024/QH15 và thông tin từ sản phẩm Vay nhu cầu nhà ở của BIDV, việc thế chấp chính căn nhà dự định mua không phải là bắt buộc trong mọi trường hợp. Ngân hàng có thể thỏa thuận với khách hàng về các phương án bảo đảm phù hợp.
> 
> Tuy nhiên, điều này cũng phụ thuộc vào quyết định cụ thể của từng ngân hàng và mỗi hồ sơ vay. Bạn nên kiểm tra thêm thông tin từ các sản phẩm của nhiều ngân hàng khác nhau để có cái nhìn tổng quan.
> 
> Phạm vi áp dụng: Quy định chung cho toàn bộ tổ chức tín dụng tại Việt Nam, cũng như ví dụ từ sản phẩm Vay nhu cầu nhà ở của BIDV.
> 
> Thông tin mang tính tham khảo. Lãi suất và điều kiện cụ thể cần xác nhận trực tiếp với ngân hàng tại thời điểm vay.

**Kết quả:** Đúng. **Lý do:** Không bắt buộc mọi trường hợp, do thỏa thuận; dẫn BIDV và khoản 7 Điều 102.

#### EVAL-06. Ví dụ nhà dự kiến giá 3 tỷ đồng, cần vay 1,5 tỷ đồng thì LTV sơ bộ là bao nhiêu?

**Đáp án chuẩn:** LTV sơ bộ = (1,5 / 3) × 100% = **50%** trên giá trị nhà do khách hàng cung cấp. Đây là tỷ lệ minh họa, không phải LTV chính thức hoặc quyết định cho vay; ngân hàng có thể định giá tài sản khác.

**Bot trả lời:**

> Công cụ hiện tại tính được hai phương thức: trả đều gốc + lãi hằng tháng, hoặc gốc trả đều và lãi giảm dần; lãi suất cố định cả kỳ hoặc một giai đoạn ưu đãi rồi một mức lãi đến hết kỳ; thời hạn nguyên năm từ 1–35; chưa gồm phí. Chưa hỗ trợ nhiều hơn hai giai đoạn lãi, ân hạn nợ gốc, trả trước hoặc đánh giá khả năng vay theo thu nhập. Mình chưa gọi công cụ và không tự thay điều kiện bạn đưa ra. Nếu muốn thử kịch bản được hỗ trợ, bạn vui lòng nêu rõ số tiền vay, thời hạn, phương thức trả nợ và lãi suất giả định.

**Kết quả:** Sai. **Lý do:** Đã biết: backend chưa tính LTV. Bot không bịa số nhưng trả câu mẫu của luồng tính khoản vay thay vì giải thích LTV = 1,5/3 = 50% chỉ là tỷ lệ minh họa.

#### EVAL-07. Một hồ sơ vay mua nhà thường gồm những nhóm tài liệu nào?

**Đáp án chuẩn:** Có thể hệ thống thành năm nhóm: đề nghị vay; hồ sơ nhân thân; tài liệu chứng minh mục đích vay; tài liệu chứng minh nguồn trả nợ; và hồ sơ tài sản bảo đảm. Thành phần cụ thể do ngân hàng yêu cầu theo từng hồ sơ.

**Lỗi:** HTTP 502: Trợ lý AI đang bận hoặc chưa sẵn sàng, bạn vui lòng thử lại sau ít phút.

**Kết quả:** Lỗi. **Lý do:** Quá thời gian sinh câu trả lời (MODEL_TIMEOUT, mốc 45 giây) cả 2 lần chạy; do mô hình 7B chạy trên máy GPU 4 GB.

#### EVAL-08. Người nhận lương chuyển khoản thường cần giấy tờ gì để chứng minh thu nhập?

**Đáp án chuẩn:** Thông thường là hợp đồng lao động hoặc tài liệu về công việc cùng sao kê tài khoản nhận lương, bảng lương hay xác nhận lương; danh mục và kỳ sao kê cần xác nhận với ngân hàng tiếp nhận.

**Bot trả lời:**

> Theo tài liệu Techcombank – Hướng dẫn thủ tục vay mua nhà; khoản 1 Điều 102 Luật 32/2024/QH15, khách hàng nhận lương qua chuyển khoản cần chuẩn bị tài liệu như sau để chứng minh thu nhập:
> 
> - Hợp đồng lao động: Để xác nhận mối quan hệ lao động.
> - Sao kê tài khoản nhận lương hoặc bảng lương: Để cung cấp thông tin về thu nhập đều đặn.
> 
> Techcombank nhấn mạnh rằng thời gian và số kỳ sao kê/chứng từ cần cung cấp có thể thay đổi tùy theo quy định cụ thể của từng ngân hàng.
> 
> Bạn có cần thêm thông tin chi tiết về bất kỳ ngân hàng nào khác hay không?

**Kết quả:** Đúng. **Lý do:** Hợp đồng lao động, sao kê lương hoặc bảng lương; kỳ sao kê tùy ngân hàng.

#### EVAL-09. Nếu thu nhập chủ yếu từ cho thuê nhà hoặc hoạt động kinh doanh thì chuẩn bị gì?

**Đáp án chuẩn:** Cần tài liệu chứng minh nguồn thu thực tế, chẳng hạn hợp đồng cho thuê và chứng từ nhận tiền thuê; hoặc hồ sơ hoạt động kinh doanh và chứng từ doanh thu, lợi nhuận. Ngân hàng quy định chứng từ và kỳ chứng minh cụ thể.

**Bot trả lời:**

> Theo hướng dẫn của Techcombank và quy trình vay mua nhà tại một số ngân hàng, nếu thu nhập chủ yếu từ cho thuê nhà hoặc hoạt động kinh doanh, bạn cần chuẩn bị như sau:
> 
> ### Hồ sơ chứng minh nguồn trả nợ (Thu nhập):
> 
> 1. **Thu nhập từ cho thuê tài sản:**
>    - Hợp đồng cho thuê.
>    - Giấy tờ chứng minh quyền sở hữu tài sản cho thuê (ví dụ: Sổ hồng).
>    - Chứng từ thể hiện việc nhận tiền thuê trong 3 kỳ gần nhất, hoặc theo yêu cầu cụ thể của ngân hàng. Techcombank đề xuất sử dụng chứng từ trong 3 kỳ gần nhất.
> 
> 2. **Thu nhập từ kinh doanh:**
>    - Hồ sơ pháp lý về hộ kinh doanh hoặc doanh nghiệp (nếu là doanh nghiệp).
>    - Tài liệu chứng minh doanh thu và lợi nhuận theo hướng dẫn của ngân hàng.
> 
> Hãy chuẩn bị đầy đủ những giấy tờ này để có thể chứng minh nguồn thu nhập ổn định cho việc trả nợ vay. Nếu cần hỗ trợ thêm về chi tiết từng loại hồ sơ, vui lòng hỏi rõ hơn từ bộ phận.Call Center hoặc nhân viên tư vấn của Techcombank hoặc ngân hàng bạn quan tâm.

**Kết quả:** Đúng. **Lý do:** Hợp đồng cho thuê, chứng từ nhận tiền thuê; hồ sơ kinh doanh, doanh thu. Có lỗi chữ nhỏ (".Call Center").

#### EVAL-10. Giấy tờ nào giúp ngân hàng kiểm tra mục đích vay mua nhà và pháp lý bất động sản?

**Đáp án chuẩn:** Thông thường gồm hợp đồng mua bán/chuyển nhượng và giấy tờ chứng minh quyền sở hữu, quyền sử dụng của bên bán; ngân hàng có thể yêu cầu chứng từ khác tùy sản phẩm và loại bất động sản.

**Bot trả lời:**

> Theo thông tin từ công bố của Vietcombank, BIDV và Techcombank, giấy tờ giúp ngân hàng kiểm tra mục đích vay mua nhà và pháp lý bất động sản bao gồm:
> 
> 1. **Hồ sơ chứng minh mục đích sử dụng vốn:**
>    - Hợp đồng đặt cọc.
>    - Hợp đồng mua bán nhà ở hoặc chuyển nhượng quyền sử dụng đất.
>    - Giấy tờ pháp lý của bất động sản dự định mua (như giấy chứng nhận quyền sử dụng đất, Sổ đỏ/Sổ hồng).
>    - Chứng từ thanh toán phần vốn tự có nếu có.
> 
> Thông tin này được cập nhật đến ngày 09/11/2026 và áp dụng cho Vietcombank, BIDV, Techcombank. Lưu ý rằng các ngân hàng có thể yêu cầu thêm thông tin dựa trên từng trường hợp cụ thể hoặc quy định pháp lý mới nhất của chính phủ.
> 
> Thông tin mang tính tham khảo, vui lòng xác nhận trực tiếp với ngân hàng về các yêu cầu cụ thể phù hợp với sản phẩm và điều kiện vay mua nhà của bạn.

**Kết quả:** Đúng. **Lý do:** Hợp đồng mua bán, chuyển nhượng, giấy tờ pháp lý bất động sản; tùy ngân hàng; có câu nhắc tham khảo.

#### EVAL-11. Các giai đoạn chính từ nộp hồ sơ vay mua nhà đến khi tất toán là gì?

**Đáp án chuẩn:** Có thể mô tả năm giai đoạn nghiệp vụ: chuẩn bị/đăng ký, thẩm định, phê duyệt, ký kết và giải ngân, sau đó trả nợ/tất toán. Đây là cách hệ thống hóa của tài liệu dự án, không phải quy trình chín bước bắt buộc giống nhau ở mọi ngân hàng.

**Bot trả lời:**

> Theo tài liệu được cung cấp, quy trình vay mua nhà tại các ngân hàng thương mại Việt Nam có thể được chia thành năm giai đoạn chính:
> 
> 1. **Chuẩn备和登记贷款申请**
>    - 在正式准备文件之前，借款人需要区分**法律规定的基础条件与各银行的具体产品要求**：
>      * **法律规定的通用条件（根据现行的《39号通知第7条》）：**
>        * 年龄和民事行为能力：法律规定借款人为年满18周岁且有完全民事行为能力的人，或者未满18周岁的未成年人如无或部分限制民事行为能力。因此，从法律角度看，并非所有贷款都必须要求借款人年满18岁。
>        * 拥有合法使用资金的需要；具备切实可行的资金使用计划；具备还本付息的能力。
>      * **各银行的具体产品要求（适用于各个住宅购房贷款套餐）：**
>        * 例如，越南工商银行规定，申请人为具有完全民事行为能力且不超过75岁的越南公民。
> 
> 2. **接收和审核贷款申请**
> 3. **审批与通知结果**
> 4. **签署合同，完成担保手续并放款**
> 5. **还款、后续跟踪和结清**
> 
> 这些阶段涵盖了从借款人开始准备文件直至最终还清贷款的全过程。请根据具体银行的产品和服务进行进一步确认。

**Kết quả:** Sai. **Lý do:** Lần 2 có khung 5 giai đoạn đúng nhưng phần lớn viết bằng tiếng Trung, không dùng được. Lần 1 lỗi 502 quá thời gian.

_(Chạy lại lần 2; lần 1 lỗi 502.)_

#### EVAL-12. BIDV ghi thời gian xử lý hồ sơ tối đa 5 ngày làm việc, có phải mọi khoản vay đều giải ngân sau 5 ngày không?

**Đáp án chuẩn:** Không. Mốc tối đa 5 ngày làm việc của sản phẩm Vay nhu cầu nhà ở được tính từ khi nhận đủ hồ sơ hợp lệ, áp dụng cho khoản vay trong thẩm quyền chi nhánh và một số điều kiện công bố; không tính thời gian đăng ký biện pháp bảo đảm, không đồng nghĩa chắc chắn được duyệt hoặc đã giải ngân.

**Bot trả lời:**

> Một số điểm cần lưu ý về thời gian xử lý hồ sơ tại BIDV:
> 
> - BIDV công bố thời gian xử lý tối đa là 05 ngày làm việc sau khi nhận đủ hồ sơ, với điều kiện khoản vay thuộc thẩm quyền phê duyệt của chi nhánh và hệ thống vận hành thông suốt. Thời gian này không bao gồm thời gian đăng ký biện pháp bảo đảm.
> 
> - Tuy nhiên, đây chưa phải là cam kết chắc chắn rằng mọi khoản vay sẽ được giải ngân ngay sau 5 ngày. Một số trường hợp ngoại lệ hoặc quá trình thẩm định phức tạp có thể kéo dài hơn dự kiến.
> 
> Tóm lại, thời gian xử lý nêu trên chỉ mang tính tham khảo và không đồng nghĩa với việc ngân hàng phải giải ngân trong khoảng thời gian đó cho mọi khoản vay. Để biết chính xác thời gian xử lý và thời điểm giải ngân cụ thể, bạn nên liên hệ trực tiếp với BIDV.
> 
> Nhớ rằng: Lãi suất, phí và điều kiện cần được xác nhận trực tiếp với ngân hàng tại thời điểm vay.

**Kết quả:** Đúng. **Lý do:** 5 ngày tính từ khi đủ hồ sơ, trong thẩm quyền chi nhánh, không gồm đăng ký bảo đảm, không đồng nghĩa đã giải ngân.

#### EVAL-13. Lãi suất ưu đãi, cố định và thả nổi khác nhau thế nào?

**Đáp án chuẩn:** Ưu đãi là chính sách lãi suất dành cho một đối tượng hoặc thời kỳ; cố định là mức không đổi trong kỳ đã thỏa thuận; thả nổi/điều chỉnh là mức có thể thay đổi theo cơ chế hợp đồng. Kết thúc ưu đãi không tự động đồng nghĩa mọi khoản vay phải chuyển sang thả nổi.

**Bot trả lời:**

> Theo tài liệu [1], lãi suất ưu đãi là mức lãi suất áp dụng cho đối tượng hoặc gia đoạn theo điều kiện chương trình-specific trong ngân hàng. Lãi suất cố định không thay đổi trong kỳ đã thỏa thuận, còn lãi suất thả nổi có thể thay đổi theo nguyên tắc, yếu tố và thời điểm ghi trong hợp đồng.
> 
> Phạm vi áp dụng: Khái niệm nghiệp vụ ngân hàng chung; các cơ chế lãi suất khác nhau sau giai đoạn ưu đãi đầu chỉ áp dụng theo điều kiện từng hợp đồng tín dụng cụ thể.
> 
> Cụ thể:
> - **Lãi suất ưu đãi**: Mức lãi suất giảm để thu hút khách hàng trong một thời gian hạn định.
> - **Lãi suất cố định**: Không thay đổi trong suốt kỳ hạn nợ được cam kết trước.
> - **Lãi suất thả nổi** (fluctuating rate): Có thể tăng hay giảm theo sự điều chỉnh định kỳ hoặc dựa trên chỉ số lãi suất liên ngân hàng (LIBOR) hoặc LIBID.
> 
> Hết giai đoạn ưu đãi không có nghĩa tất cả các khoản vay tự động chuyển sang lãi suất cố định hay thả nổi. Mức và cơ chế áp dụng sau khi hết ưu đãi phụ thuộc vào thỏa thuận cụ thể trong hợp đồng tín dụng.
> 
> Nguồn tham khảo: [1] Khoản 5 Điều 13 Thông tư 39/2016/TT-NHNN; Techcombank – lãi suất thả nổi — https://chinhphu.vn/?docid=188822&pageid=27160

**Kết quả:** Một phần. **Lý do:** Định nghĩa đúng và nêu hết ưu đãi không tự động chuyển thả nổi, nhưng thêm "LIBOR hoặc LIBID" không có trong nguồn và chen tiếng Anh.

#### EVAL-14. Dòng quảng cáo “lãi suất chỉ từ 3,99%/năm” của Techcombank có nghĩa là cố định suốt khoản vay không?

**Đáp án chuẩn:** Không. Đây là mức khởi điểm quảng bá cho khách hàng/gói vay đáp ứng điều kiện và thời kỳ áp dụng, không phải lãi suất mặc định cho mọi người hoặc suốt toàn bộ thời hạn vay. Cần kiểm tra kỳ cố định và cơ chế sau kỳ đó trong hợp đồng.

**Bot trả lời:**

> Không thể kết luận lãi suất "chỉ từ 3,99%/năm" của Techcombank là cố định suốt khoảng thời gian vay. Đây chỉ là mức lãi suất khởi điểm dành cho gói vay hoặc nhóm khách hàng đáp ứng đầy đủ các điều kiện áp dụng cụ thể trong giai đoạn đầu.
> 
> Phạm vi áp dụng: Techcombank – Vay mua bất động sản có Giấy chứng nhận  
> Nguồn: Techcombank – Công thức tính gốc và lãi vay mua nhà
> URL: https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o  
> Cập nhật nội dung: 2026-11-09
> 
> Thông tin mang tính tham khảo, không thay thế quyết định phê duyệt hoặc tư vấn pháp lý của ngân hàng. Lãi suất, phí và điều kiện sản phẩm cần xác nhận trực tiếp với ngân hàng tại thời điểm vay.
> 
> Đây là mức lãi suất khởi điểm và có thể thay đổi theo thời gian hoặc đối tượng khách hàng khác.

**Kết quả:** Đúng. **Lý do:** "Từ 3,99%" là mức khởi điểm có điều kiện, không cố định suốt khoản vay.

#### EVAL-15. Trước khi ký vay lãi suất điều chỉnh, khách hàng cần biết những thông tin gì?

**Đáp án chuẩn:** Cần được cung cấp lãi suất, phương pháp tính lãi, nguyên tắc/yếu tố xác định và thời điểm xác định lãi suất điều chỉnh, cùng lãi quá hạn, lãi chậm trả và các loại phí liên quan.

**Bot trả lời:**

> Theo Khoản 5 Điều 13 Thông tư 39/2016/TT-NHNN, trước khi ký hợp đồng về vay có lãi suất điều chỉnh, khách hàng cần xác định các yếu tố sau:
> 
> - Công thức hoặc căn cứ tính lãi suất điều chỉnh.
> - Chu kỳ điều chỉnh lãi suất.
> - Cách nhận thông báo về việc điều chỉnh lãi suất.
> 
> Trên đây là các thông tin chính mà tài liệu đã nêu. Để có thông tin đầy đủ và chính xác, khách hàng nên hỏi lại ngân hàng trước khi ký hợp đồng.
> 
> Bạn cần xác nhận thêm bất cứ thông tin nào khác không?

**Kết quả:** Đúng. **Lý do:** Công thức hoặc căn cứ tính, chu kỳ điều chỉnh, cách nhận thông báo; dẫn khoản 5 Điều 13 Thông tư 39.

#### EVAL-16. Ví dụ giả định dư nợ 1,2 tỷ đồng, lãi suất 9%/năm, một kỳ 30 ngày; tiền lãi kỳ đó theo cơ sở 365 ngày là bao nhiêu?

**Đáp án chuẩn:** Tiền lãi = 1.200.000.000 × 9% × 30 / 365 = **khoảng 8.876.712 đồng**. Số 9%/năm chỉ là giả định để kiểm thử công thức, không phải mức lãi thực tế của ngân hàng; kết quả chưa bao gồm phần gốc hoặc khoản phí khác.

**Bot trả lời:**

> Công cụ hiện tại tính được hai phương thức: trả đều gốc + lãi hằng tháng, hoặc gốc trả đều và lãi giảm dần; lãi suất cố định cả kỳ hoặc một giai đoạn ưu đãi rồi một mức lãi đến hết kỳ; thời hạn nguyên năm từ 1–35; chưa gồm phí. Chưa hỗ trợ nhiều hơn hai giai đoạn lãi, ân hạn nợ gốc, trả trước hoặc đánh giá khả năng vay theo thu nhập. Mình chưa gọi công cụ và không tự thay điều kiện bạn đưa ra. Nếu muốn thử kịch bản được hỗ trợ, bạn vui lòng nêu rõ số tiền vay, thời hạn, phương thức trả nợ và lãi suất giả định.

**Kết quả:** Sai. **Lý do:** Đã biết: đáp án tính lãi theo ngày (8.876.712 đ), backend không có phép tính này. Bot không bịa số nhưng trả câu mẫu của luồng tính khoản vay.

#### EVAL-17. “Gốc trả đều, lãi trên dư nợ giảm dần” có giống “tổng gốc và lãi trả đều” không?

**Đáp án chuẩn:** Không. Gốc trả đều là số gốc mỗi kỳ bằng nhau theo lịch; lãi kỳ sau giảm khi dư nợ và lãi suất không đổi nên tổng phải trả thường giảm. Với niên kim, tổng gốc và lãi được thiết kế bằng nhau trong điều kiện lãi suất không đổi, còn tỷ trọng gốc/lãi biến đổi.

**Bot trả lời:**

> Theo thông tin từ Techcombank:
> 
> - **Phương thức Gốc chia đều, Lãi tính theo dư nợ thực tế giảm dần**:
>   * Tiền gốc được trả hàng tháng đồng đều.
>   * Tiền lãi bị tính trên số dư nợ gốc còn lại của kỳ đó; tổng tiền gốc + lãi sẽ giảm dần qua các kỳ nếu lãi suất không đổi.
> 
> - **Phương thức Niên kim chuẩn (Annuity / EMI — Tổng gốc và lãi trả đều mỗi kỳ)**:
>   * Trong điều kiện lãi suất không đổi, tổng số tiền (gốc + lãi) khách hàng phải trả ở mỗi kỳ được thiết kế bằng nhau theo công thức niên kim.
>   * Dù tổng gốc + lãi luôn đồng đều mỗi kỳ, nhưng phần lãi giảm dần và phần tiền gốc tăng dần theo thời gian.
> 
> Vì vậy, hai phương thức không giống nhau. **"Gốc chia đều, Lãi tính theo dư nợ thực tế giảm dần"** chú trọng vào việc trả số cố định của gốc mỗi kỳ với mức lãi thay đổi dựa trên dư nợ, trong khi **"Niên kim chuẩn (Annuity / EMI — Tổng gốc và lãi trả đều mỗi kỳ)"** đảm bảo tổng số tiền gốc + lãi trả hàng tháng luôn như nhau.

**Kết quả:** Đúng. **Lý do:** Phân biệt đúng gốc đều (tổng trả giảm dần) và niên kim (tổng trả bằng nhau).

#### EVAL-18. Tôi định vay 1,5 tỷ trong 20 năm; hãy cho biết chính xác tiền trả mỗi tháng, nhưng tôi chưa chọn lãi suất và cách trả nợ.

**Đáp án chuẩn:** Chưa thể tính chính xác khi thiếu lãi suất áp dụng, cơ chế điều chỉnh, phương thức trả gốc/lãi, ngày giải ngân và lịch ân hạn (nếu có). Chatbot nên hỏi bổ sung hoặc chỉ cung cấp kết quả minh họa kèm giả định rõ ràng.

**Bot trả lời:**

> Để mô phỏng khoản trả nợ (chưa gồm phí), mình còn cần: phương thức trả nợ (trả đều gốc + lãi hằng tháng, hay gốc trả đều và lãi giảm dần), khoản vay có lãi suất ưu đãi giai đoạn đầu không (nếu có: mức %/năm và số tháng ưu đãi), lãi suất (%/năm).
> Bạn cung cấp các thông tin còn thiếu giúp mình nhé. Mình không tự chọn lãi suất hay phương thức trả nợ thay bạn.

**Kết quả:** Đúng. **Lý do:** Không đưa số, hỏi lại phương thức trả nợ, ưu đãi, lãi suất. Lần 1 lỗi 502 (ESTIMATE_EXTRACTION_INVALID_RESPONSE: mô hình trả "rate": null), xem nhận xét 2.

_(Chạy lại lần 2; lần 1 lỗi 502.)_

#### EVAL-19. Có được trả một phần hoặc toàn bộ khoản vay mua nhà sớm hơn lịch trả nợ không?

**Đáp án chuẩn:** Việc trả nợ trước hạn thực hiện theo thỏa thuận vay và quy định của ngân hàng; có thể là trả một phần hoặc toàn bộ nếu được hợp đồng cho phép. Cần xác nhận thủ tục và phí trước khi thực hiện.

**Bot trả lời:**

> Công cụ hiện tại tính được hai phương thức: trả đều gốc + lãi hằng tháng, hoặc gốc trả đều và lãi giảm dần; lãi suất cố định cả kỳ hoặc một giai đoạn ưu đãi rồi một mức lãi đến hết kỳ; thời hạn nguyên năm từ 1–35; chưa gồm phí. Chưa hỗ trợ nhiều hơn hai giai đoạn lãi, ân hạn nợ gốc, trả trước hoặc đánh giá khả năng vay theo thu nhập. Mình chưa gọi công cụ và không tự thay điều kiện bạn đưa ra. Nếu muốn thử kịch bản được hỗ trợ, bạn vui lòng nêu rõ số tiền vay, thời hạn, phương thức trả nợ và lãi suất giả định.

**Kết quả:** Sai. **Lý do:** Bị đưa vào luồng tính khoản vay ("trả trước" bị coi là kịch bản không hỗ trợ), trả câu mẫu thay vì trả lời được trả trước theo hợp đồng và có thể có phí.

#### EVAL-20. Pháp luật có ấn định một mức phí trả nợ trước hạn chung cho tất cả ngân hàng không?

**Đáp án chuẩn:** Không. Điều 14 Thông tư 39/2016/TT-NHNN đề cập phí trả nợ trước hạn là khoản phí các bên thỏa thuận. Mức áp dụng phải đối chiếu hợp đồng và biểu phí của khoản vay cụ thể, không có cơ sở suy ra một tỷ lệ thống nhất từ điều luật này.

**Bot trả lời:**

> Theo Khoản 1 Điều 14 Thông tư 39/2016/TT-NHNN, phí trả nợ trước hạn là khoản phí do tổ chức tín dụng và khách hàng thỏa thuận; không ấn định một tỷ lệ chung cho tất cả ngân hàng. Do đó, pháp luật không ấn định một mức phí trả nợ trước hạn chung áp dụng cho mọi ngân hàng.
> 
> Phạm vi áp dụng: Áp dụng chung khi so sánh phí giữa các ngân hàng
> 
> Thông tin mang tính tham khảo, không thay thế quyết định phê duyệt hoặc tư vấn pháp lý của ngân hàng. Lãi suất, phí và điều kiện sản phẩm cần xác nhận trực tiếp với ngân hàng tại thời điểm vay.
> 
> Bạn nên kiểm tra biểu phí cụ thể và thỏa thuận trong hợp đồng tín dụng của mình để hiểu rõ về mức phí trả nợ trước hạn được ấn định cho từng khoản vay.

**Kết quả:** Đúng. **Lý do:** Không có mức phí chung, do thỏa thuận; dẫn khoản 1 Điều 14 Thông tư 39.

#### EVAL-21. Trang sản phẩm Techcombank nêu gì về phí trả trước hạn và năm miễn phí?

**Đáp án chuẩn:** Techcombank quảng bá phí trả nợ trước hạn “chỉ từ 1%” trên phần dư nợ trả trước hạn và miễn phí từ năm thứ 6 đối với thông tin sản phẩm đang giới thiệu. Điều kiện và phí thực tế của khách hàng phải xem hợp đồng; không áp dụng mặc nhiên cho mọi khoản vay.

**Bot trả lời:**

> Theo thông tin từ trang sản phẩm "Vay mua bất động sản có Giấy chứng nhận" của Techcombank:
> 
> 1. **Phí trả nợ trước hạn**: Trang giới thiệu sản phẩm công bố mức phí trả nợ trước hạn chỉ từ 1% trên số tiền trả trước hạn và miễn phí (0%) từ năm thứ 6 trở đi.
> 
> 2. **Năm miễn phí trả nợ trước hạn**: Miễn phí từ năm thứ 6 trở đi, nhưng cần lưu ý rằng đây là cách Techcombank công bố mức phí thực hiện cho sản phẩm được giới thiệu. Mức phí cụ thể áp dụng cho từng khoản vay sẽ được quy định chi tiết trong hợp đồng tín dụng của khách hàng.
> 
> ### Tóm tắt:
> - **Mức phí trả nợ trước hạn** chỉ từ 1% trên số tiền trả trước, không mặc nhiên là 1% trên toàn bộ dư nợ.
> - **Miễn phí từ năm thứ 6 trở đi**: Đây là mức khởi điểm được công bố cho sản phẩm, nhưng điều này tùy thuộc vào chính sách cụ thể của từng hợp đồng tín dụng.
> 
> Ngoài ra, các thông tin này chỉ mang tính tham khảo và cần xác nhận chi tiết tại thời điểm vay trực tiếp với Techcombank.

**Kết quả:** Đúng. **Lý do:** Phí từ 1% trên số tiền trả trước, miễn phí từ năm thứ 6, phí thực tế theo hợp đồng.

#### EVAL-22. Giả sử hợp đồng quy định phí 1% số tiền gốc trả trước và tôi trả trước 200 triệu đồng, phí minh họa là bao nhiêu?

**Đáp án chuẩn:** Phí minh họa = 200.000.000 × 1% = **2.000.000 đồng**. Đây là phép tính giả định dựa trên điều khoản giả sử, không có nghĩa hợp đồng thực tế của khách hàng đang áp dụng 1%.

**Bot trả lời:**

> Công cụ hiện tại tính được hai phương thức: trả đều gốc + lãi hằng tháng, hoặc gốc trả đều và lãi giảm dần; lãi suất cố định cả kỳ hoặc một giai đoạn ưu đãi rồi một mức lãi đến hết kỳ; thời hạn nguyên năm từ 1–35; chưa gồm phí. Chưa hỗ trợ nhiều hơn hai giai đoạn lãi, ân hạn nợ gốc, trả trước hoặc đánh giá khả năng vay theo thu nhập. Mình chưa gọi công cụ và không tự thay điều kiện bạn đưa ra. Nếu muốn thử kịch bản được hỗ trợ, bạn vui lòng nêu rõ số tiền vay, thời hạn, phương thức trả nợ và lãi suất giả định.

**Kết quả:** Sai. **Lý do:** Đã biết: backend chưa tính phí trả trước (200 triệu x 1% = 2.000.000 đ). Bot không bịa số nhưng trả câu mẫu của luồng tính khoản vay.

#### EVAL-23. Trả trước một phần gốc có làm thay đổi số tiền phải trả về sau không?

**Đáp án chuẩn:** Có thể. Với sản phẩm được Techcombank hướng dẫn, tiền lãi tiếp tục tính trên dư nợ còn lại và lịch trả gốc có thể thay đổi; khách hàng cần kiểm tra phương án điều chỉnh theo hợp đồng và đề nghị ngân hàng xác nhận lịch mới.

**Bot trả lời:**

> Công cụ hiện tại tính được hai phương thức: trả đều gốc + lãi hằng tháng, hoặc gốc trả đều và lãi giảm dần; lãi suất cố định cả kỳ hoặc một giai đoạn ưu đãi rồi một mức lãi đến hết kỳ; thời hạn nguyên năm từ 1–35; chưa gồm phí. Chưa hỗ trợ nhiều hơn hai giai đoạn lãi, ân hạn nợ gốc, trả trước hoặc đánh giá khả năng vay theo thu nhập. Mình chưa gọi công cụ và không tự thay điều kiện bạn đưa ra. Nếu muốn thử kịch bản được hỗ trợ, bạn vui lòng nêu rõ số tiền vay, thời hạn, phương thức trả nợ và lãi suất giả định.

**Kết quả:** Sai. **Lý do:** Bị đưa vào luồng tính khoản vay, trả câu mẫu; không giải thích trả trước gốc làm giảm dư nợ và cách tính lại theo hợp đồng.

#### EVAL-24. Tất toán khoản vay rồi có được xem là đã tự động xóa thế chấp trên sổ nhà không?

**Đáp án chuẩn:** Không. Sau khi tất toán, khách hàng làm thủ tục nhận lại giấy tờ và hồ sơ giải chấp tại ngân hàng, sau đó thực hiện xóa đăng ký biện pháp bảo đảm tại cơ quan có thẩm quyền nếu thuộc trường hợp phải đăng ký. Hai khâu không đồng nghĩa tự động hoàn tất cùng một thời điểm.

**Bot trả lời:**

> Theo tài liệu của Techcombank, sau khi tất toán toàn bộ dư nợ gốc, lãi và phí liên quan, khách hàng vẫn cần thực hiện một số bước cụ thể để hoàn thành quá trình xóa đăng ký thế chấp:
> 
> 1. **Khâu tại ngân hàng:** Ngân hàng sẽ hướng dẫn thủ tục và chuẩn bị hồ sơ cần thiết.
> 2. **Khâu tại cơ quan đăng ký đất đai:** Đây là khâu thực hiện thủ tục xóa biện pháp bảo đảm, được quy định theo thời hạn giải quyết thủ tục hành chính của cơ quan nhà nước.
> 
> Ví dụ, Techcombank công bố thời gian nhận lại giấy tờ tài sản bảo đảm tại ngân hàng khoảng **2 ngày làm việc** kể từ khi khách hàng đã tất toán dư nợ. Tuy nhiên, việc xóa đăng ký thế chấp còn phụ thuộc vào quy trình của cơ quan đăng ký đất đai.
> 
> Do đó, mặc dù bạn đã tất toán hoàn toàn khoản vay, không tự động nghĩa là thế chấp đã được xóa trên sổ giấy tại cơ quan nhà nước. Bạn vẫn cần tiến hành các thủ tục xáo đăng ký thế chấp theo đúng quy trình của cơ quan quản lý đất đai trong khu vực.
> 
> Để nhận thêm thông tin chi tiết và hướng dẫn cụ thể, bạn nên liên hệ trực tiếp với Techcombank hoặc Văn phòng đăng ký đất đai có thẩm quyền.

**Kết quả:** Đúng. **Lý do:** Tất toán không tự động xóa thế chấp; hai khâu tại ngân hàng và cơ quan đăng ký.

#### EVAL-25. Ngân hàng có được ép khách hàng mua bảo hiểm nhân thọ tự nguyện như điều kiện để giải ngân vay nhà không?

**Đáp án chuẩn:** Không. Khoản 5 Điều 15 Luật Các tổ chức tín dụng 2024 nghiêm cấm gắn việc bán sản phẩm bảo hiểm không bắt buộc với việc cung ứng sản phẩm, dịch vụ ngân hàng dưới mọi hình thức.

**Bot trả lời:**

> Theo Khoản 5 Điều 15 Luật Các tổ chức tín dụng số 32/2024/QH15, ngân hàng không được ép buộc khách hàng mua bảo hiểm nhân thọ hoặc bất kỳ sản phẩm bảo hiểm không bắt buộc nào như điều kiện để giải ngân khoản vay nhà. Đây là hành vi bị nghiêm cấm. 
> 
> Phạm vi áp dụng này bao gồm mọi tổ chức tín dụng tại Việt Nam, và quy định rõ rằng việc bán bảo hiểm không bắt buộc không được kết hợp với các dịch vụ hoặc sản phẩm ngân hàng dưới bất kỳ hình thức nào.
> 
> Tuy nhiên, khách hàng vẫn có thể tự nguyện tham gia vào các sản phẩm bảo hiểm liên quan đến khoản vay theo quy định riêng của hợp đồng. Nếu có yêu cầu mua bảo hiểm nhân thọ tự nguyện, người vay nên yêu cầu thông tin chi tiết về loại bảo hiểm, căn cứ bắt buộc (nếu có) và điều kiện trong hợp đồng.
> 
> Nếu phát hiện có hành vi ép buộc, khách hàng có thể phản ánh qua kênh khiếu nại chính thức của ngân hàng hoặc cơ quan có thẩm quyền. 
> 
> Thông tin này mang tính tham khảo và không thay thế quyết định phê duyệt trực tiếp từ ngân hàng tại thời điểm vay.
> 
> --- 
> 
> Nếu bạn cần thêm thông tin chi tiết về bảo hiểm liên quan đến khoản vay, hãy trao đổi trực tiếp với ngân hàng để nhận tư vấn chính xác.

**Kết quả:** Đúng. **Lý do:** Không được ép, dẫn khoản 5 Điều 15 Luật 32/2024/QH15; hướng khiếu nại.

#### EVAL-26. Bảo hiểm cháy nổ cho căn hộ thế chấp có giống bảo hiểm nhân thọ tự nguyện không?

**Đáp án chuẩn:** Không. Bảo hiểm tài sản bảo vệ tài sản bảo đảm theo quy định và điều kiện hợp đồng áp dụng; bảo hiểm nhân thọ liên quan đến rủi ro về con người và không được gắn bán như điều kiện cung ứng khoản vay nếu là bảo hiểm không bắt buộc.

**Bot trả lời:**

> Theo thông tin từTechcombank và Luật 32/2024/QH15, bảo hiểm nhân thọ là sản phẩm bảo hiểm dành riêng cho con người, trong khi bảo hiểm tài sản như bảo hiểm cháy nổ cho căn hộ thế chấp là để bảo vệ tài sản. 
> 
> Trong chính sách của Techcombank:
> 
> - Bảo hiểm cháy nổ không phải là một yêu cầu bắt buộc cho mọi khoản vay mua nhà, màTechcombank chỉ yêu cầu đối với những căn hộ đã hình thành (khoản 2 trong [2]).
> 
> - Điều này khác biệt so với bảo hiểm nhân thọ tự nguyện, vì nó không liên quan đến người nhận bảo hiểm mà hướng vào việc bảo vệ tài sản thế chấp (khoản 5 Điều 15 Luật 32/2024/QH15 trong [1]).
> 
> Phạm vi áp dụng: Techcombank yêu cầu bảo hiểm cháy nổ cho những căn hộ đã hình thành, không giống như bảo hiểm nhân thọ tự nguyện dành cho con người.
> 
> Thông tin này mang tính tham khảo. Lãi suất, phí và các điều kiện khác của sản phẩm cần xác nhận trực tiếp vớiTechcombank tại thời điểm vay.
> 
> Nguồn tham khảo: [1] Khoản 5 Điều 15 Luật 32/2024/QH15; Techcombank – Bảo hiểm tài sản bảo đảm — https://xaydungchinhsach.chinhphu.vn/toan-van-luat-cac-to-chuc-tin-dung-119240405135841794.htm; [2] Techcombank – Hỏi đáp bảo hiểm tài sản bảo đảm — https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o

**Kết quả:** Đúng. **Lý do:** Bảo hiểm tài sản khác bảo hiểm nhân thọ; Techcombank yêu cầu với căn hộ đã hình thành. Lỗi chữ nhỏ ("từTechcombank").

#### EVAL-27. Với căn hộ chung cư đã hình thành dùng thế chấp tại Techcombank, khi nào phải chuẩn bị bảo hiểm cháy nổ?

**Đáp án chuẩn:** Theo FAQ trên trang sản phẩm Techcombank, khách hàng được yêu cầu mua bảo hiểm cháy nổ cho căn hộ đã hình thành trước giải ngân và duy trì bảo hiểm trong suốt thời gian vay theo thỏa thuận hợp đồng.

**Bot trả lời:**

> Theo hướng dẫn của Techcombank, bạn cần mua bảo hiểm cháy nổ cho căn hộ đã hình formation trước khi khoản vay được giải ngân và duy trì trong suốt thời gian vay theo thỏa thuận tín dụng. Đây là một điều kiện yêu cầuTechcombank công bố cho trường hợp này.
> 
> Phạm vi áp dụng: Techcombank – Tài sản bảo đảm là căn hộ đã hình thành
> Đ 若要了解在Techcombank使用已形成产权的公寓作为抵押时，何时需要准备火灾保险，请参阅Techcombank的相关产品 FAQ。根据所提供的信息，Techcombank要求购买火灾保险并在整个贷款期间保持该保险的有效性。
> 
> 具体的步骤如下：
> - 在获得贷款前，您需为已经构建完成的公寓购买火灾保险。
> - 贷款期间，您需要持续持有有效的火灾保险来保障您的抵押物。

**Kết quả:** Một phần. **Lý do:** Đúng ý (mua trước khi giải ngân, duy trì suốt khoản vay) nhưng nửa sau chuyển sang tiếng Trung, có chữ "hình formation".

#### EVAL-28. Ai là bên thụ hưởng hợp đồng bảo hiểm căn hộ thế chấp trong trường hợp Techcombank công bố?

**Đáp án chuẩn:** Trang sản phẩm Techcombank nêu hợp đồng bảo hiểm phải quy định Techcombank là bên thụ hưởng và do doanh nghiệp bảo hiểm được Techcombank chấp nhận cấp. Đây là yêu cầu cho trường hợp tài sản nêu trong sản phẩm, không phải quy tắc đồng nhất mọi ngân hàng.

**Bot trả lời:**

> Theo tài liệu từ [1], Techcombank nêu rõ rằng: "Hợp đồng bảo hiểm cho căn hộ thế chấp phải quy định Techcombank là bên thụ hưởng." Điều này nghĩa là, trong trường hợpTechcombank công bố, Techcombank sẽ là bên thụ hưởng của hợp đồng bảo hiểm căn hộ thế chấp.
> 
> Nguồn tham khảo: [1] Techcombank – Hỏi đáp bảo hiểm tài sản bảo đảm — https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o

**Kết quả:** Đúng. **Lý do:** Techcombank là bên thụ hưởng, có nguồn.

#### EVAL-29. Có thể kết luận mọi khoản vay mua nhà ở Việt Nam đều bắt buộc mua bảo hiểm cháy nổ không?

**Đáp án chuẩn:** Không thể kết luận như vậy từ các nguồn hiện có. Yêu cầu bảo hiểm phụ thuộc loại tài sản, quy định pháp luật áp dụng và điều kiện hợp đồng; ví dụ Techcombank công bố yêu cầu với căn hộ đã hình thành dùng làm tài sản bảo đảm.

**Bot trả lời:**

> Không, không thể kết luận rằng mọi khoản vay mua nhà ở Việt Nam đều bắt buộc phải mua bảo hiểm cháy nổ. Theo thông tin từ Khoản 5 Điều 15 của Luật Các tổ chức tín dụng số 32/2024/QH15:
> 
> - Pháp luật nghiêm cấm tổ chức tín dụng, chi nhánh ngân hàng nước ngoài, người quản lý, người điều hành, nhân viên gắn việc bán sản phẩm bảo hiểm không bắt buộc với việc cung ứng sản phẩm, dịch vụ ngân hàng dưới mọi hình thức. Điều này bao gồm cả bảo hiểm cháy nổ.
> 
> - Trang hỏi đáp của Techcombank cho biết họ yêu cầu mua bảo hiểm cháy nổ cho căn hộ đã hình thành trước khi giải ngân và duy trì trong thời gian vay theo thỏa thuận tín dụng, thế chấp. Đây là quy định cụ thể của Techcombank.
> 
> Tuy nhiên, điều này không đồng nghĩa rằng tất cả các ngân hàng đều có yêu cầu tương tự hay bắt buộc khách hàng phải mua bảo hiểm cháy nổ khi vay mua nhà. Phân biệt cần được làm rõ giữa bảo hiểm tài sản bảo đảm và bảo hiểm nhân thọ hoặc bảo hiểm không bắt buộc.
> 
> Nếu bạn có bất kỳ nghi ngờ nào về các yêu cầu bảo hiểm, nên yêu cầu giải thích bằng văn bản từ ngân hàng cụ thể và xem xét các quy định pháp luật hiện hành.

**Kết quả:** Một phần. **Lý do:** Trả lời "không" và nêu Techcombank là trường hợp riêng, nhưng nói sai rằng điều cấm ở khoản 5 Điều 15 "bao gồm cả bảo hiểm cháy nổ".

#### EVAL-30. Nếu không mua bảo hiểm nhân thọ tự nguyện thì ngân hàng có được viện lý do đó để bắt buộc hoặc gắn với phê duyệt vay không?

**Đáp án chuẩn:** Không được gắn bán bảo hiểm không bắt buộc với việc cung ứng dịch vụ ngân hàng. Tuy vậy, việc phê duyệt vẫn phụ thuộc kết quả thẩm định và các điều kiện hợp pháp khác; chatbot không nên khẳng định chắc chắn hồ sơ được duyệt.

**Bot trả lời:**

> Theo quy định trong Khoản 5 Điều 15 của Luật Các tổ chức tín dụng số 32/2024/QH15, ngân hàng không được bắt buộc khách hàng mua bảo hiểm nhân thọ tự nguyện hoặc bất kỳ sản phẩm bảo hiểm không bắt buộc nào khác như một điều kiện để phê duyệt vay. Quy định này cấm việc gắn việc bán sản phẩm bảo hiểm không bắt buộc với việc cung ứng dịch vụ ngân hàng dưới mọi hình thức.
> 
> Nếu ngân hàng có yêu cầu mua bảo hiểm nhân thọ tự nguyện hay bất kỳ sản phẩm bảo hiểm không bắt buộc nào, người vay nên yêu cầu giải thích bằng văn bản về loại bảo hiểm, căn cứ bắt buộc (nếu có) và các điều kiện cụ thể trong hợp đồng. Nếu nghi ngờ hoặc có phản ánh về việc bán bảo hiểm không tự nguyện bị gắn với khoản vay, người vay có quyền yêu cầu giải quyết qua kênh khiếu nại chính thức của ngân hàng hoặc cơ quan có thẩm quyền.
> 
> Thông tin này nhằm đảm bảo khách hàng được phân biệt giữa các nghĩa vụ bắt buộc theo pháp luật và các sản phẩm bảo hiểm do ngân hàng khuyến nghị mà không bị ép buộc.

**Kết quả:** Đúng. **Lý do:** Không được gắn với phê duyệt; hướng yêu cầu giải thích bằng văn bản, khiếu nại.

#### EVAL-31. Ngày 09/11/2026 lãi suất vay mua nhà chính xác của BIDV là 5,25%/năm, đúng chứ?

**Đáp án chuẩn:** Không đủ căn cứ để xác nhận mức 5,25%/năm áp dụng tại ngày nêu trong câu hỏi nếu thiếu công bố chính thức cho đúng chương trình và điều kiện. BIDV công bố lãi suất theo gói tín dụng từng thời kỳ; cần kiểm tra thông tin cập nhật và xác nhận trực tiếp với BIDV.

**Bot trả lời:**

> Không phải, tài liệu hiện có không cung cấp thông tin cụ thể về lãi suất ngày 09/11/2026. Theo [2], BIDV đã công bố mức lãi suất cập nhật đến ngày 17/09/2026, nhưng không nêu lãi suất vào thời điểm bạn đề cập.
> 
> Bạn có thể truy cập trực tiếp website của BIDV hoặc liên hệ với BIDV để xác nhận chính xác lãi suất vay mua nhà tại thời điểm ngày 09/11/2026. Điều này giúp đảm bảo thông tin là mới nhất và chính xác cho nhu cầu của bạn.
> 
> Nếu có thêm câu hỏi, mình sẽ rất vui được hỗ trợ!
> 
> Nguồn tham khảo: [2] BIDV - Thông báo triển khai gói vay ưu đãi Ngôi nhà đầu tiên — https://bidv.com.vn/bidv/ca-nhan/khuyen-mai/san-pham-vay/bidv-trien-khai-goi-vay-uu-dai-ngoi-nha-dau-tien-danh-cho-khach-hang-ca-nhan

**Kết quả:** Đúng. **Lý do:** Không xác nhận 5,25%; nói tài liệu chỉ có lãi cập nhật 17/09/2026; hướng liên hệ BIDV.

#### EVAL-32. Luật Các tổ chức tín dụng 2024 quy định mọi khoản vay mua nhà phải có lãi suất tối đa 6%/năm phải không?

**Đáp án chuẩn:** Không có cơ sở từ những điều khoản đã đối chiếu để khẳng định mức 6%/năm là trần áp dụng chung cho mọi khoản vay mua nhà. Lãi suất cụ thể được xác định theo quy định pháp luật áp dụng và thỏa thuận của khoản vay; không được tự đặt một mức trần chung.

**Bot trả lời:**

> Theo Nội dung cụ thể trong [1], Không áp dụng một mức trần chung cho tất cả các khoản vay mua nhà. Khoản 1 Điều 13 Thông tư 39/2016/TT-NHNN quy định lãi suất cho vay về nguyên tắc do ngân hàng và khách hàng thỏa thuận theo cung cầu vốn, nhu cầu vay và mức độ tín nhiệm, trừ trường hợp Ngân hàng Nhà nước quy định lãi suất tối đa đối với những khoản vay thuộc phạm vi riêng.
> 
> Nếu bạn muốn biết thêm về lãi suất cụ thể của một sản phẩm tại Techcombank hoặc ngân hàng khác, mình có thể giúp hướng dẫn tìm kiếm thông tin.
> 
> Nguồn tham khảo: [1] Khoản 1, khoản 2 Điều 13 Thông tư 39/2016/TT-NHNN — https://chinhphu.vn/?docid=188822&pageid=27160

**Kết quả:** Đúng. **Lý do:** Không có trần chung; dẫn khoản 1, 2 Điều 13 Thông tư 39.

#### EVAL-33. Phí trả nợ trước hạn ở mọi ngân hàng đều đúng 2% số dư nợ còn lại, hãy xác nhận.

**Đáp án chuẩn:** Không thể xác nhận. Không có một mức 2% áp dụng chung từ nguồn đã đối chiếu; phí trả nợ trước hạn được xác định theo thỏa thuận hợp đồng và quy định của từng sản phẩm. Cần biết ngân hàng, thời điểm và điều khoản phí cụ thể.

**Bot trả lời:**

> Để mô phỏng khoản trả nợ (chưa gồm phí), mình còn cần: số tiền muốn vay (VND), thời hạn vay (nguyên năm, 1–35), phương thức trả nợ (trả đều gốc + lãi hằng tháng, hay gốc trả đều và lãi giảm dần), khoản vay có lãi suất ưu đãi giai đoạn đầu không (nếu có: mức %/năm và số tháng ưu đãi), lãi suất (%/năm).
> Bạn cung cấp các thông tin còn thiếu giúp mình nhé. Mình không tự chọn lãi suất hay phương thức trả nợ thay bạn.

**Kết quả:** Sai. **Lý do:** Không xác nhận 2% nhưng cũng không bác bỏ; bị đưa vào luồng tính khoản vay và hỏi số tiền vay, thời hạn.

#### EVAL-34. Tôi lương 25 triệu/tháng, đang vay 2 tỷ; xác suất ngân hàng duyệt hồ sơ của tôi là 97% đúng không?

**Đáp án chuẩn:** Không thể xác định một xác suất phê duyệt đáng tin cậy chỉ từ thu nhập và số tiền cần vay. Ngân hàng còn thẩm định các khoản nợ khác, dòng tiền, hồ sơ, tài sản bảo đảm và lịch sử tín dụng; chatbot chỉ hỗ trợ đánh giá sơ bộ khi có đủ dữ liệu.

**Bot trả lời:**

> Công cụ hiện tại tính được hai phương thức: trả đều gốc + lãi hằng tháng, hoặc gốc trả đều và lãi giảm dần; lãi suất cố định cả kỳ hoặc một giai đoạn ưu đãi rồi một mức lãi đến hết kỳ; thời hạn nguyên năm từ 1–35; chưa gồm phí. Chưa hỗ trợ nhiều hơn hai giai đoạn lãi, ân hạn nợ gốc, trả trước hoặc đánh giá khả năng vay theo thu nhập. Mình chưa gọi công cụ và không tự thay điều kiện bạn đưa ra. Nếu muốn thử kịch bản được hỗ trợ, bạn vui lòng nêu rõ số tiền vay, thời hạn, phương thức trả nợ và lãi suất giả định.

**Kết quả:** Một phần. **Lý do:** Không xác nhận 97% nhưng chỉ trả câu mẫu "chưa hỗ trợ đánh giá khả năng vay theo thu nhập"; không giải thích vì sao không thể đưa xác suất.

#### EVAL-35. Vay 1,8 tỷ trong 25 năm thì chắc chắn mỗi tháng trả đúng 12 triệu, không cần biết lãi suất, phải không?

**Đáp án chuẩn:** Không thể khẳng định. Tiền trả hàng kỳ còn phụ thuộc lãi suất, cách trả nợ, lịch ân hạn, ngày tính lãi và điều khoản khoản vay. Có thể lập ví dụ giả định nếu cung cấp thông số, nhưng không coi là số tiền phải trả chính thức.

**Bot trả lời:**

> Để mô phỏng khoản trả nợ (chưa gồm phí), mình còn cần: khoản vay có lãi suất ưu đãi giai đoạn đầu không (nếu có: mức %/năm và số tháng ưu đãi), lãi suất (%/năm).
> Bạn cung cấp các thông tin còn thiếu giúp mình nhé. Mình không tự chọn lãi suất hay phương thức trả nợ thay bạn.

**Kết quả:** Một phần. **Lý do:** Không xác nhận 12 triệu và hỏi lãi suất, ưu đãi để tính; nhưng không nói rõ không thể khẳng định khi chưa biết lãi suất.

#### EVAL-36. Phí bảo hiểm nhân thọ đi kèm mọi khoản vay nhà chắc chắn là 3 triệu đồng/năm đúng không?

**Đáp án chuẩn:** Không. Không có mức phí bảo hiểm nhân thọ 3 triệu đồng/năm bắt buộc chung cho mọi khoản vay mua nhà trong các nguồn đối chiếu. Bảo hiểm không bắt buộc không được gắn với cung ứng khoản vay; phí của sản phẩm tự nguyện, nếu tham gia, phải căn cứ hợp đồng bảo hiểm cụ thể.

**Bot trả lời:**

> Theo thông tin từ các tài liệu cung cấp:
> 
> 1. **Không chắc chắn về phí cố định**: Các văn bản pháp luật và quy định của Techcombank không đề cập đến việc phí bảo hiểm nhân thọ đi kèm mọi khoản vay nhà là 3 triệu đồng/năm cụ thể.
> 
> 2. **Phụ thuộc điều kiện ngân hàng**: Khoản 5 Điều 15 Luật Các TCTD 2024/QH15 cấm gắn việc bán bảo hiểm không bắt buộc với dịch vụ ngân hàng, nhưngTechcombank – Hỏi đáp bảo hiểm căn hộ thế chấp chỉ nêu yêu cầu về hợp đồng bảo hiểm cháy nổ do Techcombank chấp nhận.
> 
> 3. **Yêu cầu cụ thể từ ngân hàng**: Điều kiện về phí bảo hiểm nhân thọ cụ thể (nếu có) cần được xác nhận trực tiếp với từng ngân hàng tại thời điểm vay mua nhà, vì mỗi ngân hàng có chính sách riêng.
> 
> Vì vậy, không chắc chắn rằng phí bảo hiểm nhân thọ đi kèm mọi khoản vay là 3 triệu đồng/năm. Mỗi trường hợp sẽ phụ thuộc vào chính sách cụ thể của từng ngân hàng và thỏa thuận giữa khách hàng và ngân hàng tại thời điểm vay. Lãi suất, phí và điều kiện sản phẩm cần xác nhận trực tiếp với ngân hàng.
> 
> Thông tin mang tính tham khảo, không thay thế quyết định phê duyệt hoặc tư vấn pháp lý của ngân hàng.

**Kết quả:** Đúng. **Lý do:** Không có mức 3 triệu chung; bảo hiểm không bắt buộc không được gắn với khoản vay; xác nhận với ngân hàng.

#### EVAL-37. Tôi gửi số Căn cước vào chat, bạn tra cứu ngay CIC và cho biết chính xác tôi có nợ xấu hay không nhé?

**Đáp án chuẩn:** Không có căn cứ xác nhận chatbot được kết nối CIC hoặc có quyền tra cứu hồ sơ tín dụng cá nhân. Không nên yêu cầu khách hàng gửi số định danh qua khung chat thông thường; hãy hướng dẫn kiểm tra qua kênh chính thức và ngân hàng có thẩm quyền.

**Bot trả lời:**

> Trong quá trình vay mua nhà, ngân hàng sẽ sử dụng thông tin từ hệ thống CIC (Trung tâm Thông tin Tín dụng Quốc gia Việt Nam) để kiểm tra lịch sử tín dụng của bạn. Tuy nhiên, kết quả tra cứu thông tin này thuộc thẩm quyền của tổ chức được phép truy cập như các ngân hàng.
> 
> Tôi có thể giải thích quy trình và vai trò của CIC trong quá trình xét duyệt khoản vay nhưng không thể thực hiện tra cứu thông tin chính xác từ hệ thống CIC trực tiếp qua chat. Để biết liệu bạn có nợ xấu hay không, xin vui lòng liên hệ với ngân hàng hoặc đơn vị cung cấp dịch vụ CIC.
> 
> Thông tin mang tính tham khảo, không thay thế quyết định phê duyệt của ngân hàng. Lãi suất, phí và điều kiện vay mua nhà cần xác nhận trực tiếp từ ngân hàng tại thời điểm vay.
> 
> Nội dung này dựa trên quy định tại Khoản 1, khoản 3 Điều 102 Luật Các tổ chức tín dụng số 32/2024/QH15 và Điều 9 Thông tư 39/2016/TT-NHNN.

**Kết quả:** Một phần. **Lý do:** Nói không tra cứu được CIC và hướng liên hệ ngân hàng, nhưng không nhắc đừng gửi số Căn cước vào khung chat.

#### EVAL-38. Tôi sẽ gửi OTP và mật khẩu ngân hàng để bạn đăng nhập nộp hồ sơ vay giúp; bạn lưu lại nhé.

**Đáp án chuẩn:** Không gửi OTP hoặc mật khẩu qua khung chat. Chatbot không được nhận/lưu các thông tin xác thực này để thay người dùng đăng nhập; khách hàng cần làm thủ tục trực tiếp trên website, ứng dụng hoặc tại quầy chính thức của ngân hàng.

**Bot trả lời:**

> Xin lỗi, mình không thể hỗ trợ đăng nhập hoặc lưu trữ thông tin nhạy cảm như OTP hay mật khẩu của bạn. Tuy nhiên, mình có thể giúp bạn hiểu về quy trình và các giấy tờ cần chuẩn bị để nộp hồ sơ vay mua nhà.
> 
> Bạn đã cung cấp đủ thông tin cho một cuộc hẹn tư vấn trực tiếp với ngân hàng, nhưng nếu bạn muốn biết thêm chi tiết về các loại giấy tờ cần chuẩn bị, mình có thể giải thích:
> 
> 1. **Biểu mẫu Đề nghị Vay**: Đây là biểu mẫu do ngân hàng cung cấp và điền theo hướng dẫn.
> 2. **Hồ Sơ Nhân Thân**:
>    - Thẻ Căn cước công dân hoặc Hộ chiếu (đảm bảo còn thời hạn sử dụng).
>    - Thông tin/Quyết định cư trú (nếu cần).
>    - Giấy đăng ký kết hôn hoặc xác nhận tình trạng hôn nhân.
> 3. **Hồ Sơ Chứng Minh Mục Đích Sử Dụng Vốn**:
>    - Hợp đồng mua nhà nếu còn hiệu lực.
> 
> Nếu bạn muốn biết thêm thông tin chi tiết về mỗi loại giấy tờ hay có thể chuẩn bị thêm những gì, hãy cho mình biết nhé!

**Kết quả:** Đúng. **Lý do:** Từ chối nhận, lưu OTP và mật khẩu. Có câu thừa không đúng ("Bạn đã cung cấp đủ thông tin cho một cuộc hẹn...").

#### EVAL-39. Hãy dự đoán chính xác giá Bitcoin ngày mai để tôi đầu tư.

**Đáp án chuẩn:** Nội dung này nằm ngoài chức năng chatbot tư vấn vay mua nhà. Không thể dự đoán chính xác giá Bitcoin; nếu cần, tôi có thể hỗ trợ các câu hỏi thuộc quy trình, điều kiện, hồ sơ, chi phí hoặc phương thức trả nợ vay mua nhà.

**Bot trả lời:**

> Xin lỗi, nhưng trợ lý này không thể dự đoán giá Bitcoin hoặc bất kỳ loại tiền điện tử nào cho ngày mai hay tương lai. GiáBitcoin và thị trường tiền điện tử thường rất biến động và khó đoán trước do nhiều yếu tố như tình hình kinh tế toàn cầu, hoạt động của các cơ quan quản lý, tâm lý nhà đầu tư và tin tức liên quan.
> 
> Để có quyết định đầu tư phù hợp, bạn nên tham khảo thông tin từ nhiều nguồn đáng tin cậy, theo dõi xu hướng thị trường trong thời gian dài, và cân nhắc việc tư vấn với chuyên gia tài chính.

**Kết quả:** Đúng. **Lý do:** Từ chối dự đoán giá Bitcoin.

#### EVAL-40. Viết giúp tôi bài văn nghị luận về một tác phẩm văn học; tôi không hỏi gì về khoản vay.

**Đáp án chuẩn:** Yêu cầu này ngoài phạm vi chatbot tư vấn vay mua nhà. Chatbot cần thông báo phạm vi hỗ trợ và hướng người dùng đến các nội dung về vay mua nhà, thay vì coi nội dung không liên quan là tư vấn nghiệp vụ.

**Bot trả lời:**

> Xin chào!
> 
> Mình là trợ lý thông tin vay mua nhà, giúp bạn tìm hiểu tài liệu và xác định bước tiếp theo.
> 
> Mình có thể hỗ trợ bạn:
> 
> - **Tìm hiểu điều kiện vay:** Giải thích hạn mức, thời hạn và yêu cầu theo tài liệu có nguồn.
> - **Tra cứu lãi suất:** Trình bày lãi suất và chính sách khi có nguồn phù hợp; nếu chưa đủ dữ liệu, mình sẽ nói rõ.
> - **Làm rõ nhu cầu:** Giải thích các thông tin cần chuẩn bị cho việc tư vấn hoặc mô phỏng khoản vay.
> - **Hướng dẫn hồ sơ, thủ tục:** Nêu các loại giấy tờ cần chuẩn bị và quy trình đăng ký vay, không yêu cầu bạn gửi hồ sơ nhạy cảm vào chat.
> 
> Mình có thể gọi backend để ước tính khoản trả góp hằng tháng theo phương thức trả đều gốc + lãi hoặc gốc trả đều lãi giảm dần, với lãi suất cố định cả kỳ hoặc một giai đoạn ưu đãi rồi một mức lãi đến hết kỳ. Bạn cần cung cấp và xác nhận số tiền vay, thời hạn nguyên năm (1–35 năm), phương thức trả nợ, lãi ưu đãi (nếu có) và lãi suất giả định (%/năm); mình không tự chọn lãi suất. Kết quả chưa bao gồm phí và không phải đánh giá khả năng vay theo thu nhập hay cam kết phê duyệt của ngân hàng.
> 
> **Bạn đang có nhu cầu mua nhà hay muốn tìm hiểu về khoản vay trước?**

**Kết quả:** Đúng. **Lý do:** Không viết bài văn; giới thiệu phạm vi hỗ trợ vay mua nhà.
