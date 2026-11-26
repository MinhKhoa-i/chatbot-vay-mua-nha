# Danh sách 8 ngân hàng thương mại và nguồn dữ liệu vay mua nhà

> **Tài liệu phục vụ Dự án:** Chatbot Tư vấn Vay Mua Nhà  
> **Người thực hiện:** Vương (Nhóm Dữ liệu)  
> **Ngày rà soát & cập nhật:** 16/11/2026 (cập nhật phiên bản 1.3.0 ngày 25/11/2026)  
> **Trạng thái:** Hoàn thành Phần A (Việc 12 tuần 3: thêm fee_published, rate_is_upper_bound và chuẩn hóa LTV VCB 70%)

---

## 1. Cập nhật và đối chiếu lãi suất, phí ngày 16/11/2026

Tất cả thông số đã được đối chiếu trực tiếp từ website chính thức của 8 ngân hàng tại ngày rà soát 16/11/2026. Lãi suất không đủ kỳ ưu đãi/điều kiện hoặc không có lãi sau ưu đãi để mô hình hóa được ghi rõ là **không công bố đủ dữ liệu**; không dùng số ước lượng tổng hợp cũ làm dữ liệu hiện hành. `source_url` và `last_updated` trong JSON áp dụng ở cấp bản ghi ngân hàng. Biểu phí ghi `tiers` khi nguồn công bố theo năm. Nếu nguồn đưa ra một khoảng phí, `rate_percent` lưu mức trần của khoảng và `description` nêu rõ đây là mức trần; kết quả ranking cho biết phí đó là mức trần. `tiers` rỗng nghĩa là chưa công bố biểu chi tiết, không phải miễn phí.

### Bảng đối chiếu chi tiết 8 ngân hàng:

| STT | Ngân hàng | Ngày rà soát | Link trang sản phẩm đã xem | Thông tin lãi suất và phí chính thức | Tình trạng dữ liệu & Lý do |
|:---:|---|:---:|---|---|---|
| 1 | **Vietcombank** | 16/11/2026 | [vietcombank.com.vn](https://www.vietcombank.com.vn/vi-VN/KHCN/Truy-cap-nhanh/Tin-noi-bat/Articles/2026/10/15/Nha-moi-an-cu) | Gói Nhà Mới An Cư: lãi suất cố định 9,0%/năm trong 12 tháng đầu (áp dụng HĐ ký mới từ 14/10/2026 cho nhà dự án có GCN). Không công bố lãi sau ưu đãi. | `promo_rate = 9.0`, `promo_duration_months = 12`. Lãi thả nổi `null` do nguồn không công bố. Biểu phí chi tiết không công bố (`tiers = []`). |
| 2 | **BIDV** | 16/11/2026 | [bidv.com.vn](https://bidv.com.vn/bidv/ca-nhan/khuyen-mai/san-pham-vay/bidv-trien-khai-goi-vay-uu-dai-ngoi-nha-dau-tien-danh-cho-khach-hang-ca-nhan) | Gói Ngôi nhà đầu tiên (công bố 17/09/2026, đối soát còn hiệu lực ngày 16/11/2026): 9,0%/12 tháng (kỳ hạn vay tối thiểu 36 tháng); 9,5%/18 tháng; 10,0%/24 tháng (tối thiểu 60 tháng). | `promo_rate = 9.0`, `promo_duration_months = 12` (kèm 3 `rate_options`). Lãi thả nổi `null` do nguồn không công bố. Biểu phí chi tiết không công bố (`tiers = []`). |
| 3 | **Techcombank** | 16/11/2026 | [techcombank.com](https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o) | Nêu "lãi suất cố định chỉ từ 3,99%/năm", "thời gian cố định linh hoạt lên đến 24 tháng" dành cho hội viên Inspire/Priority. Trang **không công bố lãi suất ưu đãi tiêu chuẩn cố định cụ thể** gắn với kỳ hạn nào. | Để `null` các trường lãi suất. Bản trước ghi 6.8%/12 tháng là số ước lượng/gói cũ không còn trên trang sản phẩm hiện hành. Phí trả trước từ 1%, miễn từ năm 6 (`tiers = []` do thiếu biểu chi tiết). |
| 4 | **VietinBank** | 16/11/2026 | [vietinbank.vn](https://www.vietinbank.vn/ca-nhan/san-pham-dich-vu/cho-vay/cho-vay-nhan-quyen-su-dung-dat-mua-xay-dung-sua-chua-nha-va-hoac-cong-trinh-xay-dung-30-html) | Trang sản phẩm chỉ nêu "lãi suất cạnh tranh theo quy định từng thời kỳ", **không công bố lãi suất ưu đãi hay lãi thả nổi cụ thể**. | Để `null` các trường lãi suất do ngân hàng không công bố trên trang sản phẩm. Biểu phí chi tiết không công bố (`tiers = []`). |
| 5 | **Agribank** | 16/11/2026 | [agribank.com.vn](https://www.agribank.com.vn/vn/ca-nhan/san-pham-dich-vu/vay-von-agribank/vay-nha-o-thuong-mai) | Trang sản phẩm **không công bố lãi suất ưu đãi cho gói vay mua nhà**. Bảng lãi chung tháng 7/2026 ghi mức tối thiểu 7,8%/năm nhưng là cho vay thông thường, không phải ưu đãi mua nhà. | Để `null` các trường lãi suất. Có biểu phí phạt tất toán công khai: năm 1 trần 4%, năm 2 trần 3%, từ năm 3 trần 2% (`tiers` có 3 bậc). |
| 6 | **MB Bank** | 16/11/2026 | [mbbank.com.vn](https://www.mbbank.com.vn/26/36/san-pham/cho-vay) | Gói MB Dream Home chỉ nêu đặc điểm chung (hạn mức 80%, thời hạn 35 năm), **không công bố mức lãi suất ưu đãi hoặc biên độ thả nổi cụ thể**. | Để `null` các trường lãi suất do ngân hàng không công bố trên trang sản phẩm. Biểu phí chi tiết không công bố (`tiers = []`). |
| 7 | **VPBank** | 16/11/2026 | [vpbank.com.vn](https://www.vpbank.com.vn/uu-dai/retail/loans-promotion-category/vay-uu-dai-mua-nha-cho-nguoi-tre-duoi-35-tuoi) | Chương trình ưu đãi người trẻ: nêu "lãi suất từ 5,2%/năm", cố định linh hoạt đến 24 tháng, thời hạn tối đa 25 năm, **không công bố thời hạn tối thiểu và không ghép mức 5,2% với kỳ cố định cụ thể**. | Để `null` các trường lãi suất. `min_loan_term_years` để `null` (không có quy định tối thiểu). Phí trả trước tối đa 2,5% (năm 1-4) và 0% (từ năm 5) (`tiers` có 2 bậc). |
| 8 | **ACB** | 16/11/2026 | [acb.com.vn](https://acb.com.vn/vay-von/vay-mua-nha-dat) | Trang sản phẩm nêu phương thức trả linh hoạt, **không công bố mức lãi suất ưu đãi, biên độ thả nổi hay biểu phí phạt cụ thể**. | Để `null` các trường lãi suất do ngân hàng không công bố trên trang sản phẩm. Biểu phí chi tiết không công bố (`tiers = []`). |

---

## 2. Tiêu chí lựa chọn ngân hàng

Để phục vụ đối tượng khách hàng cá nhân có nhu cầu vay mua nhà ở (nhà phố, căn hộ dự án, đất ở) tại Việt Nam, danh sách 8 ngân hàng được lựa chọn dựa trên 4 tiêu chí cốt lõi:

1. **Thị phần & Uy tín tín dụng bất động sản:** Gồm nhóm 4 ngân hàng thương mại có vốn Nhà nước (Big 4: Vietcombank, BIDV, VietinBank, Agribank) và nhóm 4 ngân hàng TMCP tư nhân hàng đầu có quy mô gói vay bán lẻ lớn (Techcombank, MB Bank, VPBank, ACB).
2. **Tính công khai & Minh bạch của nguồn dữ liệu:** Ngân hàng có cổng thông tin điện tử chính thức, đăng tải công khai biểu mẫu, quy trình, điều kiện vay, hạn mức, thời hạn và lãi suất các gói vay mua nhà.
3. **Đa dạng về chính sách vay:** Bao gồm các gói vay với đa dạng phương thức trả nợ (gốc đều lãi giảm dần, niên kim cố định), thời hạn vay từ 20 đến 35 năm, tỷ lệ tài trợ LTV từ 70% đến 100%.
4. **Sự tương thích với dữ liệu hiện có của dự án:** Kết nối liền mạch với các tài liệu quy trình vay ([quy-trinh-vay.md](quy-trinh-vay.md)) và bộ câu hỏi thường gặp ([faq.json](../data/faq.json)).

---

## 3. Bảng tổng hợp danh sách 8 ngân hàng và nguồn dữ liệu

| STT | Mã NH | Tên thương mại | Tên đầy đủ | Tên sản phẩm / Gói vay | Nguồn website chính thức (Trang sản phẩm) | Lãi suất ưu đãi tham khảo* | LTV tối đa | Thời hạn tối đa |
|:---:|:---:|:---|:---|:---|:---|:---:|:---:|:---:|
| 1 | **VCB** | Vietcombank | Ngân hàng TMCP Ngoại thương Việt Nam | Nhà Mới An Cư (nhà tại dự án đã có Giấy chứng nhận) | [vietcombank.com.vn](https://www.vietcombank.com.vn/vi-VN/KHCN/Truy-cap-nhanh/Tin-noi-bat/Articles/2026/10/15/Nha-moi-an-cu) | 9,0%/năm (12 tháng đầu, điều kiện chương trình) | 70% TSBĐ chính (tới 100% nếu có TSBĐ độc lập bổ sung) | 35 năm |
| 2 | **BIDV** | BIDV | Ngân hàng TMCP Đầu tư và Phát triển Việt Nam | Vay nhu cầu nhà ở (Gói Ngôi nhà đầu tiên) | [bidv.com.vn](https://bidv.com.vn/bidv/ca-nhan/khuyen-mai/san-pham-vay/bidv-trien-khai-goi-vay-uu-dai-ngoi-nha-dau-tien-danh-cho-khach-hang-ca-nhan) | 9,0%/12T; 9,5%/18T; 10,0%/24T (kèm điều kiện kỳ hạn tối thiểu) | 80% TSBĐ (100% nếu có TSBĐ bổ sung) | 30 năm |
| 3 | **TCB** | Techcombank | Ngân hàng TMCP Kỹ Thương Việt Nam | Vay mua bất động sản có Giấy chứng nhận | [techcombank.com](https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o) | Nêu "từ 3,99%/năm", không công bố lãi suất chuẩn theo kỳ | 80% TSBĐ | 35 năm |
| 4 | **CTG** | VietinBank | Ngân hàng TMCP Công Thương Việt Nam | Cho vay nhận quyền sử dụng đất, mua, xây dựng, sửa chữa nhà | [vietinbank.vn](https://www.vietinbank.vn/ca-nhan/san-pham-dich-vu/cho-vay/cho-vay-nhan-quyen-su-dung-dat-mua-xay-dung-sua-chua-nha-va-hoac-cong-trinh-xay-dung-30-html) | Chưa công bố lãi suất cụ thể trên web | 70% TSBĐ (100% nếu có TSBĐ bổ sung) | 35 năm |
| 5 | **VBA** | Agribank | Ngân hàng Nông nghiệp và PTNT Việt Nam | Vay mua nhà ở thương mại | [agribank.com.vn](https://www.agribank.com.vn/vn/ca-nhan/san-pham-dich-vu/vay-von-agribank/vay-nha-o-thuong-mai) | Chưa công bố lãi suất gói mua nhà trên web | 70% TSBĐ (100% nếu có TSBĐ bổ sung) | 35 năm |
| 6 | **MB** | MB Bank | Ngân hàng TMCP Quân Đội | Cho vay mua nhà đất, căn hộ dự án (Gói MB Dream Home) | [mbbank.com.vn](https://www.mbbank.com.vn/26/36/san-pham/cho-vay) | Chưa công bố lãi suất cụ thể trên web | 80% TSBĐ | 30 năm |
| 7 | **VPB** | VPBank | Ngân hàng TMCP Việt Nam Thịnh Vượng | Ưu đãi vay mua nhà VPBank (chương trình khách hàng trẻ) | [vpbank.com.vn](https://www.vpbank.com.vn/uu-dai/retail/loans-promotion-category/vay-uu-dai-mua-nha-cho-nguoi-tre-duoi-35-tuoi) | Nêu "từ 5,2%/năm", không ghép mức với kỳ cố định cụ thể | 80% giá trị căn nhà | 25 năm (không quy định tối thiểu) |
| 8 | **ACB** | ACB | Ngân hàng TMCP Á Châu | Vay Mua Nhà Đất | [acb.com.vn](https://acb.com.vn/vay-von/vay-mua-nha-dat) | Chưa công bố lãi suất cụ thể trên web | 80% TSBĐ | 30 năm |

*\*Lưu ý: Mức "từ" chỉ mang tính tham khảo trong phạm vi chương trình. Nếu không đủ dữ liệu lãi suất sau ưu đãi thì không thể tính tổng chi phí toàn kỳ theo đúng chuẩn tài chính.*

---

## 4. Chi tiết từng ngân hàng và phương thức khai thác dữ liệu

### 4.1. Vietcombank (VCB)
* **Đặc điểm chính:** Ngân hàng thương mại hàng đầu, mạng lưới rộng, quy trình thẩm định chặt chẽ, hỗ trợ thời hạn vay tối đa lên đến 35 năm đối với chương trình Nhà Mới An Cư (sản phẩm vay mua nhà thông thường trên trang sản phẩm chung áp dụng thời hạn tối đa 30 năm), hạn mức vay tối đa 50 tỷ đồng. Hỗ trợ cho vay mua nhà cho bản thân hoặc người thân (bố, mẹ, vợ, chồng, con).
* **Nguồn dữ liệu trực tiếp:**
  * Trang chương trình: [Vietcombank Nhà Mới An Cư](https://www.vietcombank.com.vn/vi-VN/KHCN/Truy-cap-nhanh/Tin-noi-bat/Articles/2026/10/15/Nha-moi-an-cu) (kiểm tra ngày 16/11/2026)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: 9,0%/năm trong 12 tháng đầu theo chương trình Nhà Mới An Cư cho nhà dự án đã có Giấy chứng nhận (áp dụng HĐ ký mới từ 14/10/2026).
  * Lãi suất sau ưu đãi: Trang chương trình không công bố biên độ hay lãi thả nổi cụ thể → để `null`.
  * Hạn mức: Tối đa 70% giá trị TSBĐ là chính ngôi nhà mua; lên tới 100% nếu có thêm TSBĐ độc lập bổ sung.
  * Thời hạn vay: Tối đa 35 năm, tối thiểu 3 năm.
  * Phí trả nợ trước hạn: Nguồn không công bố biểu chi tiết theo từng năm → `tiers = []`.

---

### 4.2. BIDV (BIDV)
* **Đặc điểm chính:** Gói vay đa dạng, thời gian phê duyệt cam kết tối đa 05 ngày làm việc. Chương trình nổi bật: "Ngôi nhà đầu tiên".
* **Nguồn dữ liệu trực tiếp:**
  * Thông báo gói ưu đãi: [BIDV Gói vay ưu đãi Ngôi nhà đầu tiên](https://bidv.com.vn/bidv/ca-nhan/khuyen-mai/san-pham-vay/bidv-trien-khai-goi-vay-uu-dai-ngoi-nha-dau-tien-danh-cho-khach-hang-ca-nhan) (kiểm tra ngày 16/11/2026, thông tin gốc ban hành 17/09/2026)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: 9,0%/12 tháng (kỳ hạn vay tối thiểu 36 tháng); 9,5%/18 tháng hoặc 10,0%/24 tháng (kỳ hạn vay tối thiểu 60 tháng).
  * Lãi suất sau ưu đãi: Nguồn chương trình không công bố lãi suất thả nổi hoặc biên độ → để `null`.
  * Hạn mức: Tối đa 80% giá trị tài sản bảo đảm, lên tới 100% phương án nếu có TSBĐ độc lập bổ sung.
  * Thời hạn vay: Tối đa 30 năm (360 tháng), tối thiểu 3 năm.
  * Phí trả nợ trước hạn: Nguồn không công bố biểu chi tiết theo từng năm → `tiers = []`.

---

### 4.3. Techcombank (TCB)
* **Đặc điểm chính:** Đón đầu công nghệ phê duyệt trực tuyến, thời hạn vay lên tới 35 năm, ân hạn nợ gốc lên tới 24 tháng.
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [Techcombank Vay mua bất động sản có GCN](https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o) (kiểm tra ngày 16/11/2026)
* **Lý do để lãi suất null:** Trang sản phẩm hiện chỉ quảng bá câu từ "lãi suất cố định chỉ từ 3,99%/năm" và "thời gian cố định linh hoạt lên đến 24 tháng" áp dụng cho khách hàng phân hạng hội viên. Trang **không công bố lãi suất ưu đãi chuẩn** áp dụng phổ thông, không ghép mức 3,99% với kỳ hạn cụ thể và không công bố lãi suất sau ưu đãi. Bản dữ liệu cũ (6.8%/12 tháng) là số liệu ước lượng trước đây không còn hiện diện trên trang web; để tuân thủ nguyên tắc "không tự ước lượng", toàn bộ trường lãi suất để `null`.
* **Phí trả nợ trước hạn:** Nguồn chỉ nêu chung "từ 1% và miễn phí từ năm thứ 6", không có biểu chi tiết từng năm → `tiers = []`.

---

### 4.4. VietinBank (CTG)
* **Đặc điểm chính:** Ngân hàng thương mại Nhà nước lớn, mạng lưới phòng giao dịch phủ rộng toàn quốc.
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [VietinBank Cho vay nhận QSDĐ, mua, xây dựng nhà](https://www.vietinbank.vn/ca-nhan/san-pham-dich-vu/cho-vay/cho-vay-nhan-quyen-su-dung-dat-mua-xay-dung-sua-chua-nha-va-hoac-cong-trinh-xay-dung-30-html) (kiểm tra ngày 16/11/2026)
* **Lý do để lãi suất null:** Trang sản phẩm chính thức **không công bố bất kỳ mức lãi suất ưu đãi hay biên độ thả nổi cụ thể nào** (chỉ ghi chung chung "theo quy định từng thời kỳ"). Để đảm bảo tính trung thực của dữ liệu chuẩn hóa, trường `interest_rate` để `null`.
* **Phí trả nợ trước hạn:** Không công bố biểu chi tiết trên trang sản phẩm → `tiers = []`.

---

### 4.5. Agribank (VBA)
* **Đặc điểm chính:** Mạng lưới phủ rộng tới cấp huyện, xã trên cả nước, chính sách an toàn, thủ tục quen thuộc với khách hàng cá nhân.
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [Agribank Cho vay mua nhà ở thương mại](https://www.agribank.com.vn/vn/ca-nhan/san-pham-dich-vu/vay-von-agribank/vay-nha-o-thuong-mai) (kiểm tra ngày 16/11/2026)
  * Biểu phí cho vay công khai: [Quyết định 1356/QĐ-HĐTV-KHDN ban hành biểu phí cho vay Agribank](https://www.agribank.com.vn/wcm/connect/05371a26-a0b1-4670-a5db-15046d1517f4/Bieu%2Bphi%2Blien%2Bquan%2Bhoat%2Bdong%2Bcho%2Bvay%2BQD%2B1356%2Bthay%2Bthe%2BQD%2B09%2Bngay%2B090123.pdf) (kiểm tra ngày 16/11/2026)
* **Lý do để lãi suất null:** Trang sản phẩm gói vay mua nhà **không công bố lãi suất ưu đãi**. Bảng lãi suất công bố chung kỳ tháng 7/2026 có mức 7,8%/năm nhưng là sàn cho vay trung/dài hạn thông thường, không phải lãi suất ưu đãi của gói mua nhà.
* **Biểu phí trả nợ trước hạn công khai (3 bậc):**
  * Năm thứ 1: mức trần 4,0% (khoảng công bố 2–4%).
  * Năm thứ 2: mức trần 3,0% (khoảng công bố 1,5–3%).
  * Từ năm thứ 3 đến hết kỳ hạn (năm 35): mức trần 2,0% (khoảng công bố 1–2%).
  * *Lưu ý:* `rate_percent` lưu mức trần; mức thực thu do chi nhánh quyết định theo hợp đồng tín dụng.

---

### 4.6. MB Bank (MB)
* **Đặc điểm chính:** Ngân hàng số phát triển mạnh, quy trình xử lý hồ sơ nhanh, nhiều gói hợp tác với các chủ đầu tư lớn.
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [MBBank Cho vay mua nhà đất, căn hộ (MB Dream Home)](https://www.mbbank.com.vn/26/36/san-pham/cho-vay) (kiểm tra ngày 16/11/2026)
* **Lý do để lãi suất null:** Trang sản phẩm MB Dream Home **hoàn toàn không đăng tải biểu lãi suất ưu đãi hay lãi suất thả nổi công khai**. Mức lãi suất áp dụng theo phê duyệt riêng của từng khoản vay.
* **Phí trả nợ trước hạn:** Không công bố biểu chi tiết → `tiers = []`.

---

### 4.7. VPBank (VPB)
* **Đặc điểm chính:** Phê duyệt nhanh, tiêu chí chứng minh thu nhập linh hoạt, giải pháp vay mua nhà chuyên biệt cho người trẻ dưới 35 tuổi.
* **Nguồn dữ liệu trực tiếp:**
  * Trang ưu đãi: [VPBank Vay ưu đãi mua nhà cho người trẻ dưới 35 tuổi](https://www.vpbank.com.vn/uu-dai/retail/loans-promotion-category/vay-uu-dai-mua-nha-cho-nguoi-tre-duoi-35-tuoi) (kiểm tra ngày 16/11/2026)
* **Làm rõ thời hạn tối thiểu (Issue #39 / STT 11):** Trang sản phẩm công bố: *"thời hạn vay tối đa 25 năm"* và **hoàn toàn không quy định thời hạn vay tối thiểu**. Phiên bản trước ghi `min_loan_term_years: 25` là do đọc nhầm câu quảng bá "thời hạn vay linh hoạt từ 25 đến 35 năm" trên trang giới thiệu cũ thành thời hạn tối thiểu. Dữ liệu chuẩn hóa đã bỏ trường này (`min_loan_term_years: null`), đảm bảo khoản vay 20 năm không bị loại sai vì thời hạn.
* **Lý do để lãi suất null:** Trang chỉ nêu "lãi suất từ 5,2%/năm", thời gian cố định linh hoạt đến 24 tháng nhưng không ghép mức 5,2% với kỳ hạn cụ thể và không công bố lãi suất thả nổi sau ưu đãi.
* **Biểu phí trả nợ trước hạn công khai (2 bậc):**
  * Năm 1 đến năm 4: mức trần 2,5% (nguồn nêu "không quá 2,5%").
  * Từ năm thứ 5 đến năm thứ 25: 0,0% (miễn phí trả trước hạn).

---

### 4.8. ACB (ACB)
* **Đặc điểm chính:** Dịch vụ bán lẻ cá nhân uy tín, hỗ trợ nhiều phương thức trả góp linh hoạt (góp đều, góp bậc thang tăng dần 10–20%/năm).
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [ACB Vay Mua Nhà Đất](https://acb.com.vn/vay-von/vay-mua-nha-dat) (kiểm tra ngày 16/11/2026)
* **Lý do để lãi suất null:** Trang sản phẩm chính thức **không công bố mức lãi suất ưu đãi, kỳ ưu đãi hay biên độ thả nổi cụ thể**.
* **Phí trả nợ trước hạn:** Không công bố biểu chi tiết trên trang sản phẩm → `tiers = []`.

---

## 5. Khuyến cáo và nguyên tắc cập nhật nguồn dữ liệu

1. **Tính biến động của lãi suất:** Các mức lãi suất ưu đãi, biên độ thả nổi và chính sách chương trình tín dụng của ngân hàng thường thay đổi theo từng tháng/quý căn cứ vào định hướng điều hành của Ngân hàng Nhà nước và thanh khoản thị trường.
2. **Xác thực trực tiếp:** Mọi thông số thu thập từ website ngân hàng có giá trị tham khảo tại thời điểm cập nhật (`last_updated`). Chatbot cần hiển thị rõ ngày cập nhật và khuyến nghị khách hàng kiểm tra lại với chi nhánh/phòng giao dịch ngân hàng trước khi ký kết hồ sơ tín dụng chính thức.
3. **Cảnh báo bản ghi cũ hơn 30 ngày:** Script `check_banks.py` tự động so sánh trường `last_updated` của từng bản ghi trong `data/banks_sample.json` với ngày hiện tại; nếu chênh lệch vượt quá 30 ngày, script in cảnh báo kèm tên ngân hàng và ngày cập nhật cuối. Người phụ trách dữ liệu cần truy cập lại trang sản phẩm chính thức (theo `source_url` tương ứng), rà soát thông số lãi suất, phí và điều kiện vay, cập nhật `last_updated` thành ngày rà soát mới nhất và điều chỉnh `source_url` nếu trang đã thay đổi. Việc cập nhật phải hoàn tất và được xác nhận trước khi mở Pull Request vào nhánh chính.
4. **Tuân thủ quy định pháp luật:** Tuyệt đối không đưa các điều kiện ép mua bảo hiểm nhân thọ vào điều kiện bắt buộc, đảm bảo phù hợp với **Khoản 5 Điều 15 Luật Các tổ chức tín dụng số 32/2024/QH15** (có hiệu lực từ ngày 01/07/2024), nghiêm cấm: *"Tổ chức tín dụng, chi nhánh ngân hàng nước ngoài, người quản lý, người điều hành, nhân viên của tổ chức tín dụng, chi nhánh ngân hàng nước ngoài gắn việc bán sản phẩm bảo hiểm không bắt buộc với việc cung ứng sản phẩm, dịch vụ ngân hàng dưới mọi hình thức."* Chatbot cần trích dẫn chính xác nguyên văn điều khoản này khi tư vấn cho người dùng.
