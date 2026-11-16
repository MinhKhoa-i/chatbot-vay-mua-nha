# Danh sách 8 ngân hàng thương mại và nguồn dữ liệu vay mua nhà

> **Tài liệu phục vụ Dự án:** Chatbot Tư vấn Vay Mua Nhà  
> **Người thực hiện:** Vương (Nhóm Dữ liệu)  
> **Ngày rà soát & cập nhật:** 16/11/2026
> **Trạng thái:** Hoàn thành nhiệm vụ chọn 5–8 ngân hàng và xác định nguồn dữ liệu website (Task 11)

---

## 1. Cập nhật lãi suất và phí ngày 16/11/2026

Các mức cũ trong tài liệu đã được đối chiếu lại theo nguồn ngân hàng chính thức. Lãi suất không đủ kỳ ưu đãi/điều kiện hoặc không có lãi sau ưu đãi để mô hình hóa được ghi rõ là chưa đủ dữ liệu; không dùng số tổng hợp cũ làm dữ liệu hiện hành. `source_url` và `last_updated` trong JSON áp dụng ở cấp bản ghi ngân hàng. Biểu phí ghi tiers khi nguồn công bố theo năm. Nếu nguồn đưa ra một khoảng phí, `rate_percent` lưu mức trần của khoảng và `description` nêu rõ đây là mức trần; kết quả ranking cho biết phí đó là mức trần. Tiers rỗng nghĩa là chưa công bố biểu chi tiết, không phải miễn phí.

| Ngân hàng | Thông tin lãi suất chính thức đã đối chiếu | Tình trạng dùng để xếp hạng |
|---|---|---|
| Vietcombank | Nhà Mới An Cư: từ 9,0%/năm trong 12 tháng đầu; nhà tại dự án đã có Giấy chứng nhận; hợp đồng ký mới từ 14/10/2026; kỳ hạn đến 35 năm. | Thiếu lãi suất sau ưu đãi nên không đủ tính toàn kỳ. |
| BIDV | Ngôi nhà đầu tiên: từ 9,0%/12 tháng (kỳ hạn vay tối thiểu 36 tháng); 9,5%/18 tháng và 10,0%/24 tháng (tối thiểu 60 tháng); BIDV ghi mức cập nhật 17/09/2026. | Thiếu lãi suất sau ưu đãi. |
| Techcombank | Từ 3,99%/năm; kỳ cố định lên đến 24 tháng, ưu đãi cho hội viên. Trang không ghép mức 3,99% với kỳ hạn cụ thể. | Để null vì chưa đủ mức/kỳ hạn tương ứng và lãi sau ưu đãi. |
| VPBank | Ưu đãi đến 31/12/2030 nêu lãi suất từ 5,2%/năm, cố định linh hoạt đến 24 tháng; phí trả trước tối đa 2,5%, miễn phí từ năm thứ 5. Không nêu kỳ cố định tương ứng với 5,2% hoặc phí chính xác cho từng năm 1–4. Gói ưu đãi cho thời hạn tối đa 25 năm, không nêu thời hạn tối thiểu. | Cho phép kỳ hạn 20 năm; giữ lãi suất có cấu trúc null vì thiếu kỳ áp dụng và lãi sau ưu đãi. |
| Agribank | Lãi suất thông thường trung/dài hạn tối thiểu 7,8%/năm trong bảng tháng 7/2026; không phải mức ưu đãi riêng của sản phẩm mua nhà. | Giữ các trường lãi suất sản phẩm là null; phí công khai lưu theo mức trần. |
| VietinBank, MB, ACB | Trang sản phẩm được rà soát không công bố đủ lãi suất áp dụng chung để mô hình hóa cả kỳ ưu đãi và sau ưu đãi. | Để null; không tự ước lượng. |

## 2. Tiêu chí lựa chọn ngân hàng

Để phục vụ đối tượng khách hàng cá nhân có nhu cầu vay mua nhà ở (nhà phố, căn hộ dự án, đất ở) tại Việt Nam, danh sách 8 ngân hàng được lựa chọn dựa trên 4 tiêu chí cốt lõi:

1. **Thị phần & Uy tín tín dụng bất động sản:** Gồm nhóm 4 ngân hàng thương mại có vốn Nhà nước (Big 4: Vietcombank, BIDV, VietinBank, Agribank) và nhóm 4 ngân hàng TMCP tư nhân hàng đầu có quy mô gói vay bán lẻ lớn (Techcombank, MB Bank, VPBank, ACB).
2. **Tính công khai & Minh bạch của nguồn dữ liệu:** Ngân hàng có cổng thông tin điện tử chính thức, đăng tải công khai biểu mẫu, quy trình, điều kiện vay, hạn mức, thời hạn và lãi suất các gói vay mua nhà.
3. **Đa dạng về chính sách vay:** Bao gồm các gói vay với đa dạng phương thức trả nợ (gốc đều lãi giảm dần, niên kim cố định), thời hạn vay từ 20 đến 35-45 năm, tỷ lệ tài trợ LTV từ 70% đến 100%.
4. **Sự tương thích với dữ liệu hiện có của dự án:** Kết nối liền mạch với các tài liệu quy trình vay ([quy-trinh-vay.md](quy-trinh-vay.md)) và bộ câu hỏi thường gặp ([faq.json](../data/faq.json)).

---

## 3. Bảng tổng hợp danh sách 8 ngân hàng và nguồn dữ liệu

| STT | Mã NH | Tên thương mại | Tên đầy đủ | Tên sản phẩm / Gói vay | Nguồn website chính thức (Trang sản phẩm) | Lãi suất ưu đãi tham khảo* | LTV tối đa | Thời hạn tối đa |
|:---:|:---:|:---|:---|:---|:---|:---:|:---:|:---:|
| 1 | **VCB** | Vietcombank | Ngân hàng TMCP Ngoại thương Việt Nam | Nhà Mới An Cư (nhà tại dự án đã có Giấy chứng nhận) | [vietcombank.com.vn](https://www.vietcombank.com.vn/vi-VN/KHCN/Truy-cap-nhanh/Tin-noi-bat/Articles/2026/10/15/Nha-moi-an-cu) | Từ 9,0%/năm (12 tháng, điều kiện chương trình) | Tới 100% căn nhà | 35 năm |
| 2 | **BIDV** | BIDV | Ngân hàng TMCP Đầu tư và Phát triển Việt Nam | Vay nhu cầu nhà ở (Ngôi nhà đầu tiên) | [bidv.com.vn](https://bidv.com.vn/bidv/ca-nhan/khuyen-mai/san-pham-vay/bidv-trien-khai-goi-vay-uu-dai-ngoi-nha-dau-tien-danh-cho-khach-hang-ca-nhan) | 9,0%/12 tháng; 9,5%/18 tháng; 10,0%/24 tháng, kèm kỳ hạn tối thiểu | Theo điều kiện hồ sơ | 30 năm |
| 3 | **TCB** | Techcombank | Ngân hàng TMCP Kỹ Thương Việt Nam | Vay mua bất động sản có Giấy chứng nhận | [techcombank.com](https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o) | Từ 3,99%/năm; kỳ cố định lên đến 24 tháng, điều kiện hội viên | 80% TSBĐ | 35 – 45 năm |
| 4 | **CTG** | VietinBank | Ngân hàng TMCP Công Thương Việt Nam | Cho vay mua, xây dựng, sửa chữa nhà ở | [vietinbank.vn](https://www.vietinbank.vn/vn/ca-nhan/cho-vay/mua-xay-dung-sua-chua-nha-o-nhan-chuyen-nhuong-qsd-dat-20150529141014.html) | Chưa công bố đủ dữ liệu để mô hình hóa | 80% TSBĐ | 30 năm |
| 5 | **VBA** | Agribank | Ngân hàng Nông nghiệp và PTNT Việt Nam | Cho vay mua nhà ở, chuyển nhượng QSDĐ ở | [agribank.com.vn](https://www.agribank.com.vn/vn/ca-nhan/san-pham/vay-von-tin-dung/cho-vay-mua-nha-o) | Chưa công bố đủ dữ liệu để mô hình hóa | 85% TSBĐ | 25 – 30 năm |
| 6 | **MB** | MB Bank | Ngân hàng TMCP Quân Đội | Cho vay mua nhà đất, căn hộ dự án | [mbbank.com.vn](https://www.mbbank.com.vn/ca-nhan/vay/vay-mua-nha-dat/4) | Chưa công bố đủ dữ liệu để mô hình hóa | 80% TSBĐ | 30 năm |
| 7 | **VPB** | VPBank | Ngân hàng TMCP Việt Nam Thịnh Vượng | Ưu đãi vay mua nhà VPBank (chương trình khách hàng trẻ) | [vpbank.com.vn](https://www.vpbank.com.vn/uu-dai/retail/loans-promotion-category/vay-uu-dai-mua-nha-cho-nguoi-tre-duoi-35-tuoi) | Từ 5,2%/năm (kỳ cố định cụ thể chưa công bố) | 80% giá trị căn nhà | Tối đa 25 năm |
| 8 | **ACB** | ACB | Ngân hàng TMCP Á Châu | Vay mua nhà, đất ở | [acb.com.vn](https://acb.com.vn/khach-hang-ca-nhan/vay/vay-mua-nha-dat) | Chưa công bố đủ dữ liệu để mô hình hóa | 80% TSBĐ | 25 – 30 năm |

*Lưu ý: Mức “từ” chỉ có ý nghĩa trong phạm vi chương trình và điều kiện được nêu; không đủ dữ liệu cho lãi suất sau ưu đãi thì không thể tính tổng chi phí toàn kỳ.*

---

## 3. Chi tiết từng ngân hàng và phương thức khai thác dữ liệu

### 3.1. Vietcombank (VCB)
* **Đặc điểm chính:** Lãi suất cạnh tranh, quy trình thẩm định chặt chẽ, hỗ trợ thời hạn vay dài đến 30 năm, hạn mức vay tối đa 50 tỷ đồng/khoản vay. Hỗ trợ cho vay mua nhà cho người thân (bố, mẹ, vợ, chồng, con).
* **Nguồn dữ liệu trực tiếp:**
  * Trang giới thiệu sản phẩm: [Vietcombank Nhà Mới An Cư](https://www.vietcombank.com.vn/vi-VN/KHCN/Truy-cap-nhanh/Tin-noi-bat/Articles/2026/10/15/Nha-moi-an-cu)
  * Trang chương trình ưu đãi "Nhà Mới Thành Đạt": [Nhà Mới Thành Đạt VCB](https://www.vietcombank.com.vn/vi-VN/KHCN/SPDV/Vay/Nha-moi-thanh-dat)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: 9,0%/năm trong 12 tháng đầu theo chương trình Nhà Mới An Cư cho nhà đã có Giấy chứng nhận; xem điều kiện tại phần cập nhật 16/11/2026.
  * Lãi suất sau ưu đãi chưa được công bố trong nguồn của chương trình này; không đưa biên độ cũ từ gói khác vào dữ liệu hiện hành.
  * Hạn mức: Tối đa 70% giá trị tài sản bảo đảm (TSBĐ), lên đến 100% nếu có thêm TSBĐ bổ sung.
  * Nguồn chương trình được rà soát không công bố biểu phí trả trước hạn chi tiết.

---

### 3.2. BIDV (BIDV)
* **Đặc điểm chính:** Gói vay đa dạng, mốc thời gian thẩm định phê duyệt công bố tối đa 05 ngày làm việc (khi đủ hồ sơ hợp lệ tại chi nhánh). Chương trình nổi bật: "Ngôi nhà đầu tiên".
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [BIDV Vay nhu cầu nhà ở](https://bidv.com.vn/bidv/privatecustomer/dichvunganhang/tindung/vaynhucaunhao)
  * Thông báo gói ưu đãi: [BIDV Gói vay ưu đãi Ngôi nhà đầu tiên](https://bidv.com.vn/bidv/ca-nhan/khuyen-mai/san-pham-vay/bidv-trien-khai-goi-vay-uu-dai-ngoi-nha-dau-tien-danh-cho-khach-hang-ca-nhan)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: 9,0%/12 tháng (kỳ hạn tối thiểu 36 tháng); 9,5%/18 tháng hoặc 10,0%/24 tháng (kỳ hạn tối thiểu 60 tháng), theo cập nhật BIDV 17/09/2026.
  * Lãi suất sau ưu đãi của lựa chọn đang trích chưa được nguồn chương trình công bố đủ để tính; không dùng biên độ cũ làm dữ liệu hiện hành.
  * Hạn mức: Tối đa 100% nhu cầu vốn vay (phụ thuộc giá trị tài sản bảo đảm).
  * Thời hạn vay: Tối đa 30 năm (360 tháng).

---

### 3.3. Techcombank (TCB)
* **Đặc điểm chính:** Đón đầu công nghệ phê duyệt trực tuyến, thời hạn vay lên tới 35 năm (bất động sản thổ cư đủ điều kiện có thể lên đến 45 năm), ân hạn nợ gốc lên tới 24 tháng, minh bạch công thức tính gốc/lãi theo ngày thực tế.
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [Techcombank Vay mua bất động sản có GCN](https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o)
  * Hướng dẫn thủ tục: [Techcombank Blog Thủ tục vay ngân hàng mua nhà](https://techcombank.com/thong-tin/blog/thu-tuc-vay-ngan-hang-mua-nha)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi tiêu chuẩn: Từ 3,99%/năm; kỳ cố định lên đến 24 tháng dành cho hội viên, nhưng trang không nêu kỳ cố định cụ thể tương ứng với mức 3,99%; không đưa mức này vào dữ liệu xếp hạng.
  * Lãi suất sau ưu đãi chưa công bố trong trang sản phẩm được rà soát.
  * Hạn mức: Tối đa 80% giá trị định giá tài sản bảo đảm.
  * Độ tuổi: Từ đủ 18 tuổi và không quá 70 tuổi tại thời điểm kết thúc thời hạn vay (đáo hạn).
  * Phí trả nợ trước hạn từ 1%, miễn phí từ năm thứ 6; nguồn không nêu biểu chi tiết theo từng năm nên không khai báo tiers.

---

### 3.4. VietinBank (CTG)
* **Đặc điểm chính:** Ngân hàng quốc doanh mạng lưới rộng lớn, lãi suất ổn định, điều kiện giải ngân linh hoạt cho các phương án nhà ở hình thành trong tương lai hoặc có sẵn Sổ đỏ/Sổ hồng.
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [VietinBank Cho vay mua, xây dựng, sửa chữa nhà ở](https://www.vietinbank.vn/vn/ca-nhan/cho-vay/mua-xay-dung-sua-chua-nha-o-nhan-chuyen-nhuong-qsd-dat-20150529141014.html)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: Trang sản phẩm rà soát không công bố lãi suất ưu đãi cụ thể đủ điều kiện để mô hình hóa; để null trong dữ liệu.
  * Hạn mức: Tối đa 80% tổng nhu cầu vốn hoặc 70% giá trị tài sản bảo đảm.
  * Thời hạn: Tối đa 30 năm (nhà ở xây dựng/mua mới), 15 năm (sửa chữa).

---

### 3.5. Agribank (VBA)
* **Đặc điểm chính:** Thế mạnh mạng lưới phủ kín từ thành thị đến nông thôn, mức độ an toàn cao, lãi suất ổn định, thủ tục đơn giản cho hộ gia đình và khách hàng cá nhân.
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [Agribank Cho vay mua nhà ở](https://www.agribank.com.vn/vn/ca-nhan/san-pham/vay-von-tin-dung/cho-vay-mua-nha-o)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: Trang sản phẩm rà soát không công bố lãi suất ưu đãi cụ thể đủ điều kiện để mô hình hóa; để null trong dữ liệu.
  * Hạn mức: Tối đa 85% giá trị định giá TSBĐ hoặc chi phí thực tế.
  * Thời hạn: Lên tới 25–30 năm.
  * Phí tất toán vay trung/dài hạn: Năm 1: 2–4%; năm 2: 1,5–3%; từ năm 3: 1–2%. Dữ liệu `rate_percent` lưu mức trần lần lượt 4%, 3%, 2%; mức thực thu do chi nhánh quyết định theo hợp đồng. [Biểu phí Agribank](https://www.agribank.com.vn/wcm/connect/05371a26-a0b1-4670-a5db-15046d1517f4/Bieu%2Bphi%2Blien%2Bquan%2Bhoat%2Bdong%2Bcho%2Bvay%2BQD%2B1356%2Bthay%2Bthe%2BQD%2B09%2Bngay%2B090123.pdf).

---

### 3.6. MB Bank (MB)
* **Đặc điểm chính:** Ứng dụng ngân hàng số mạnh mẽ, thủ tục giải ngân nhanh, có các gói liên kết chủ đầu tư uy tín (Vinhomes, Novaland, Masterise...).
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [MBBank Vay mua nhà đất](https://www.mbbank.com.vn/ca-nhan/vay/vay-mua-nha-dat/4)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: Trang sản phẩm rà soát không công bố lãi suất ưu đãi hoặc biên độ cụ thể; để null trong dữ liệu.
  * Lãi suất sau ưu đãi và biên độ áp dụng chung chưa được trang sản phẩm rà soát công bố.
  * Hạn mức: Tối đa 80% giá trị TSBĐ.
  * Thời hạn: Tối đa 30 năm (360 tháng).

---

### 3.7. VPBank (VPB)
* **Đặc điểm chính:** Phê duyệt nhanh, tiêu chí chứng minh thu nhập linh hoạt (chấp nhận thu nhập từ kinh doanh, cho thuê, góp vốn), hạn mức vay cao.
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [VPBank ưu đãi vay mua nhà](https://www.vpbank.com.vn/uu-dai/retail/loans-promotion-category/vay-uu-dai-mua-nha-cho-nguoi-tre-duoi-35-tuoi)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất và phí: Ưu đãi áp dụng đến 31/12/2030 công bố lãi suất từ 5,2%/năm, cố định linh hoạt đến 24 tháng; không nêu kỳ cố định ứng với mức 5,2%, nên trường lãi suất có cấu trúc để null. Phí trả trước tối đa 2,5% trong 4 năm đầu, miễn phí từ năm thứ 5; tiers ghi mức trần 2,5% và mức 0% đã công bố.
  * Hạn mức: Tối đa 80% giá trị căn nhà.
  * Thời hạn của ưu đãi: Tối đa 25 năm; trang không nêu thời hạn tối thiểu.

---

### 3.8. ACB (ACB)
* **Đặc điểm chính:** Dịch vụ chăm sóc khách hàng cá nhân chu đáo, lãi suất minh bạch, hỗ trợ đa dạng phương thức trả gốc linh hoạt (theo tháng hoặc theo quý).
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [ACB Vay mua nhà, đất ở](https://acb.com.vn/khach-hang-ca-nhan/vay/vay-mua-nha-dat)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: Trang sản phẩm rà soát không công bố mức lãi suất/kỳ ưu đãi cụ thể; để null trong dữ liệu.
  * Lãi suất sau ưu đãi và biên độ áp dụng chung chưa được trang sản phẩm rà soát công bố.
  * Hạn mức: Tối đa 80% giá trị tài sản bảo đảm.
  * Thời hạn: Tối đa 25 – 30 năm.

---

## 4. Khuyến cáo và nguyên tắc cập nhật nguồn dữ liệu

1. **Tính biến động của lãi suất:** Các mức lãi suất ưu đãi, biên độ thả nổi và chính sách chương trình tín dụng của ngân hàng thường thay đổi theo từng tháng/quý căn cứ vào định hướng điều hành của Ngân hàng Nhà nước và thanh khoản thị trường.
2. **Xác thực trực tiếp:** Mọi thông số thu thập từ website ngân hàng có giá trị tham khảo tại thời điểm cập nhật (`last_updated`). Chatbot cần hiển thị rõ ngày cập nhật và khuyến nghị khách hàng kiểm tra lại với chi nhánh/phòng giao dịch ngân hàng trước khi ký kết hồ sơ tín dụng chính thức.
3. **Cảnh báo bản ghi cũ hơn 30 ngày:** Script `check_banks.py` tự động so sánh trường `last_updated` của từng bản ghi trong `data/banks_sample.json` với ngày hiện tại; nếu chênh lệch vượt quá 30 ngày, script in cảnh báo kèm tên ngân hàng và ngày cập nhật cuối. Người phụ trách dữ liệu cần truy cập lại trang sản phẩm chính thức (theo `source_url` tương ứng), rà soát thông số lãi suất, phí và điều kiện vay, cập nhật `last_updated` thành ngày rà soát mới nhất và điều chỉnh `source_url` nếu trang đã thay đổi. Việc cập nhật phải hoàn tất và được xác nhận trước khi mở Pull Request vào nhánh chính.
4. **Tuân thủ quy định pháp luật:** Tuyệt đối không đưa các điều kiện ép mua bảo hiểm nhân thọ vào điều kiện bắt buộc, đảm bảo phù hợp với **Khoản 5 Điều 15 Luật Các tổ chức tín dụng số 32/2024/QH15** (có hiệu lực từ ngày 01/07/2024), nghiêm cấm: *"Tổ chức tín dụng, chi nhánh ngân hàng nước ngoài, người quản lý, người điều hành, nhân viên của tổ chức tín dụng, chi nhánh ngân hàng nước ngoài gắn việc bán sản phẩm bảo hiểm không bắt buộc với việc cung ứng sản phẩm, dịch vụ ngân hàng dưới mọi hình thức."* Chatbot cần trích dẫn chính xác nguyên văn điều khoản này khi tư vấn cho người dùng.
