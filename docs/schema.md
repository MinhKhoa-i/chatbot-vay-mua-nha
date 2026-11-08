# Schema dữ liệu Gói vay mua nhà của các Ngân hàng

> **Tài liệu phục vụ Dự án:** Chatbot Tư vấn Vay Mua Nhà  
> **Người thực hiện:** Vương (Nhóm Dữ liệu)  
> **Ngày ban hành:** 31/10/2026  
> **Tập tin mẫu áp dụng:** `data/banks_sample.json`  
> **Trạng thái:** Hoàn thành thiết kế schema (Task 12)

---

## 1. Mục đích và phạm vi thiết kế

Schema này định nghĩa cấu trúc dữ liệu chuẩn hóa cho các sản phẩm/gói vay mua nhà cá nhân tại các ngân hàng thương mại Việt Nam.

Cấu trúc schema được thiết kế nhằm đáp ứng:
1. **Chatbot Retrieval & Prompt Context:** Cung cấp thông tin chính xác về lãi suất, hạn mức, điều kiện để chatbot trả lời các thắc mắc của người dùng.
2. **Công cụ so sánh & Tính toán khoản vay:** Cung cấp các thông số định lượng (`promo_rate`, `floating_margin`, `max_ltv_percent`, `max_loan_term_years`) để tính toán lịch trả nợ (niên kim hoặc gốc đều lãi giảm dần) và so sánh giữa các ngân hàng.
3. **Tính minh bạch & Tra cứu nguồn gốc:** Bắt buộc có thông tin nguồn (`source_url`) và ngày cập nhật (`last_updated`) để đảm bảo người dùng nắm rõ tính thời điểm của dữ liệu.

---

## 2. Đặc tả các trường dữ liệu (Field Dictionary)

Một bản ghi gói vay ngân hàng (`BankLoanPackage`) bao gồm 6 nhóm trường dữ liệu chính:

### 2.1. Nhóm Thông tin Ngân hàng (`bank_info`)
| Tên trường | Kiểu dữ liệu | Bắt buộc | Mô tả & Ý nghĩa nghiệp vụ | Ví dụ |
|:---|:---:|:---:|:---|:---|
| `id` | `string` | **Có** | Mã định danh duy nhất (kebab-case) dùng làm khóa định danh. | `"vietcombank"`, `"bidv"` |
| `code` | `string` | **Có** | Mã viết tắt/giao dịch của ngân hàng (chữ in hoa). | `"VCB"`, `"BIDV"` |
| `name` | `string` | **Có** | Tên đầy đủ có dấu của ngân hàng. | `"Ngân hàng TMCP Ngoại thương Việt Nam"` |
| `short_name` | `string` | **Có** | Tên thương mại phổ biến ngắn gọn. | `"Vietcombank"`, `"Techcombank"` |
| `logo_url` | `string` | Không | Đường dẫn URL hoặc asset icon/logo của ngân hàng. | `"/assets/banks/vcb.svg"` |
| `website` | `string` | **Có** | Địa chỉ website chính thức của ngân hàng. | `"https://www.vietcombank.com.vn"` |
| `source_url` | `string` | **Có** | Địa chỉ URL trang sản phẩm vay mua nhà làm nguồn đối soát. | `"https://www.vietcombank.com.vn/vi-VN/KHCN/SPDV/Vay/Vay-mua-nha-dat"` |
| `package_name` | `string` | **Có** | Tên sản phẩm hoặc gói tín dụng nhà ở cụ thể. | `"Vay mua nhà ở, đất ở (Gói Nhà Mới Thành Đạt)"` |

---

### 2.2. Nhóm Lãi suất (`interest_rate`)
| Tên trường | Kiểu dữ liệu | Bắt buộc | Mô tả & Ý nghĩa nghiệp vụ | Ví dụ |
|:---|:---:|:---:|:---|:---|
| `promo_rate` | `number` | **Có** | Lãi suất ưu đãi tiêu chuẩn năm (%/năm) áp dụng trong kỳ đầu. | `5.2`, `6.8` |
| `promo_duration_months` | `integer` | **Có** | Thời gian cố định lãi suất ưu đãi (số tháng). | `12`, `24` |
| `floating_margin` | `number` | **Có** | Biên độ lãi suất cộng thêm sau khi hết thời gian ưu đãi (%/năm). | `3.5` |
| `floating_rate_estimated` | `number` | Không | Mức lãi suất thả nổi ước tính hiện tại (%/năm = Lãi suất cơ sở + Biên độ). | `9.5`, `10.2` |
| `reference_rate_type` | `string` | **Có** | Tên loại lãi suất tham chiếu dùng để tính lãi suất thả nổi. | `"LSTK 12T trả sau"`, `"Lãi suất cơ sở Techcombank"` |
| `adjustment_frequency_months` | `integer` | **Có** | Chu kỳ điều chỉnh lãi suất thả nổi (thường 3 hoặc 6 tháng). | `3`, `6` |
| `rate_options` | `array[object]`| Không | Danh sách các phương án lựa chọn lãi suất ưu đãi khác nhau của gói vay. | Xem mục 2.2.1 |

#### 2.2.1. Cấu trúc một phần tử trong `rate_options`:
* `duration_months` (`integer`): Số tháng ưu đãi (ví dụ: `6`, `12`, `24`, `36`).
* `rate` (`number`): Lãi suất tương ứng (%/năm, ví dụ: `5.5`, `6.5`, `7.5`).
* `conditions` (`string`): Điều kiện đi kèm (ví dụ: *"Yêu cầu thời gian vay tối thiểu bằng 2 lần thời gian ưu đãi"*).

---

### 2.3. Nhóm Ưu đãi & Chính sách (`promotions`)
| Tên trường | Kiểu dữ liệu | Bắt buộc | Mô tả & Ý nghĩa nghiệp vụ | Ví dụ |
|:---|:---:|:---:|:---|:---|
| `summary` | `string` | **Có** | Tóm tắt các điểm nổi bật của chính sách ưu đãi. | `"Lãi suất ưu đãi 5.2% trong 12 tháng, ân hạn gốc 12 tháng"` |
| `grace_period_months` | `integer` | **Có** | Thời gian ân hạn trả nợ gốc tối đa (số tháng). Nhập `0` nếu không có. | `12`, `24` |
| `early_repayment_penalty` | `object` | **Có** | Quy định mức phí phạt khi tất toán hoặc trả nợ trước hạn. | Xem mục 2.3.1 |
| `special_offers` | `array[string]`| Không | Các quà tặng, giảm phí dịch vụ hoặc chương trình kết nối đối tác. | `["Tặng tài khoản số đẹp", "Miễn phí thẩm định giá"]` |

#### 2.3.1. Cấu trúc `early_repayment_penalty`:
* `description` (`string`): Diễn giải tổng quan phí phạt.
* `tiers` (`array[object]`): Chi tiết mức phí theo từng năm vay:
  * `from_year` (`integer`): Từ năm thứ.
  * `to_year` (`integer`): Đến năm thứ.
  * `rate_percent` (`number`): Tỷ lệ phí tính trên số tiền nợ gốc trả trước (%): `1.5`, `1.0`, `0.5`, hoặc `0.0` (miễn phí).

---

### 2.4. Nhóm Hạn mức & Thời hạn (`loan_limit`)
| Tên trường | Kiểu dữ liệu | Bắt buộc | Mô tả & Ý nghĩa nghiệp vụ | Ví dụ |
|:---|:---:|:---:|:---|:---|
| `max_ltv_percent` | `number` | **Có** | Tỷ lệ cho vay tối đa so với giá trị tài sản bảo đảm (Loan-to-Value %). | `70.0`, `80.0`, `100.0` |
| `max_ltv_note` | `string` | Không | Ghi chú điều kiện đạt được LTV tối đa (ví dụ nếu bổ sung BĐS khác). | `"Tối đa 100% nếu có TSBĐ độc lập bổ sung, 70% nếu TSBĐ là chính ngôi nhà"` |
| `max_loan_term_years` | `integer` | **Có** | Thời hạn vay vốn tối đa (số năm). | `30`, `35`, `45` |
| `min_loan_term_years` | `integer` | Không | Thời hạn vay vốn tối thiểu (số năm). | `3`, `5` |
| `max_loan_amount` | `number` hoặc `null` | Không | Hạn mức số tiền vay tối đa (VND). Để `null` nếu không giới hạn trần cố định. | `50000000000` (50 tỷ VND) |
| `min_loan_amount` | `number` | Không | Số tiền cho vay tối thiểu (VND). | `100000000` (100 triệu VND) |

---

### 2.5. Nhóm Điều kiện Vay (`eligibility`)
| Tên trường | Kiểu dữ liệu | Bắt buộc | Mô tả & Ý nghĩa nghiệp vụ | Ví dụ |
|:---|:---:|:---:|:---|:---|
| `min_age` | `integer` | **Có** | Độ tuổi tối thiểu của khách hàng tại thời điểm vay (năm). | `18` |
| `max_age_at_loan_end` | `integer` | **Có** | Độ tuổi tối đa của khách hàng khi kết thúc thời hạn vay (năm). | `70`, `75` |
| `borrower_scope` | `string` | **Có** | Đối tượng khách hàng được vay vốn. | `"Công dân Việt Nam, vay mua nhà cho bản thân hoặc người thân"` |
| `min_monthly_income` | `number` hoặc `null` | Không | Mức thu nhập tối thiểu hàng tháng được khuyến nghị (VND). | `10000000` (10 triệu VND) |
| `accepted_collateral` | `array[string]`| **Có** | Các loại tài sản được ngân hàng chấp nhận làm tài sản bảo đảm. | `["BĐS có Sổ đỏ/Sổ hồng", "HĐMB nhà ở dự án"]` |
| `processing_time_days` | `string` | Không | Thời gian xử lý & phê duyệt hồ sơ tham khảo. | `"05 ngày làm việc kể từ khi nhận đủ hồ sơ"` |
| `general_requirements` | `array[string]`| **Có** | Danh sách các điều kiện tiên quyết cần đáp ứng. | `["Lịch sử CIC không có nợ xấu nhóm 2 trở lên", "Nguồn thu nhập ổn định"]` |

---

### 2.6. Nhóm Phương thức Trả nợ & Metadata (`repayment_methods` & `metadata`)
| Tên trường | Kiểu dữ liệu | Bắt buộc | Mô tả & Ý nghĩa nghiệp vụ | Ví dụ |
|:---|:---:|:---:|:---|:---|
| `repayment_methods` | `array[string]`| **Có** | Các phương thức trả nợ hỗ trợ: `"annuity"` (niên kim cố định gốc + lãi), `"reducing_balance"` (gốc đều, lãi giảm dần). | `["reducing_balance", "annuity"]` |
| `last_updated` | `string` | **Có** | Ngày rà soát & cập nhật thông số theo định dạng chuẩn `YYYY-MM-DD`. | `"2026-10-31"` |
| `is_sample` | `boolean` | **Có** | Đánh dấu đây là dữ liệu mẫu đối soát (`true`) hay dữ liệu động trên hệ thống (`false`). | `false` |
| `disclaimer` | `string` | **Có** | Lời khuyến cáo pháp lý và tính chất tham khảo của dữ liệu. | `"Thông tin mang tính tham khảo..."` |

---

## 3. JSON Schema định dạng chuẩn (JSON Schema Draft-07)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "BankLoanPackageList",
  "description": "Schema định dạng danh sách sản phẩm vay mua nhà của các ngân hàng thương mại",
  "type": "object",
  "required": ["version", "updated_at", "banks"],
  "properties": {
    "version": { "type": "string" },
    "updated_at": { "type": "string", "format": "date" },
    "description": { "type": "string" },
    "banks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "code",
          "name",
          "short_name",
          "source_url",
          "package_name",
          "interest_rate",
          "promotions",
          "loan_limit",
          "eligibility",
          "repayment_methods",
          "last_updated"
        ],
        "properties": {
          "id": { "type": "string" },
          "code": { "type": "string" },
          "name": { "type": "string" },
          "short_name": { "type": "string" },
          "logo_url": { "type": ["string", "null"] },
          "website": { "type": "string", "format": "uri" },
          "source_url": { "type": "string", "format": "uri" },
          "package_name": { "type": "string" },
          "interest_rate": {
            "type": "object",
            "required": [
              "promo_rate",
              "promo_duration_months",
              "floating_margin",
              "reference_rate_type",
              "adjustment_frequency_months"
            ],
            "properties": {
              "promo_rate": { "type": "number", "minimum": 0 },
              "promo_duration_months": { "type": "integer", "minimum": 1 },
              "floating_margin": { "type": "number", "minimum": 0 },
              "floating_rate_estimated": { "type": "number" },
              "reference_rate_type": { "type": "string" },
              "adjustment_frequency_months": { "type": "integer", "minimum": 1 },
              "rate_options": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["duration_months", "rate"],
                  "properties": {
                    "duration_months": { "type": "integer" },
                    "rate": { "type": "number" },
                    "conditions": { "type": "string" }
                  }
                }
              }
            }
          },
          "promotions": {
            "type": "object",
            "required": ["summary", "grace_period_months", "early_repayment_penalty"],
            "properties": {
              "summary": { "type": "string" },
              "grace_period_months": { "type": "integer", "minimum": 0 },
              "early_repayment_penalty": {
                "type": "object",
                "required": ["description", "tiers"],
                "properties": {
                  "description": { "type": "string" },
                  "tiers": {
                    "type": "array",
                    "items": {
                      "type": "object",
                      "required": ["from_year", "to_year", "rate_percent"],
                      "properties": {
                        "from_year": { "type": "integer" },
                        "to_year": { "type": "integer" },
                        "rate_percent": { "type": "number" }
                      }
                    }
                  }
                }
              },
              "special_offers": {
                "type": "array",
                "items": { "type": "string" }
              }
            }
          },
          "loan_limit": {
            "type": "object",
            "required": ["max_ltv_percent", "max_loan_term_years"],
            "properties": {
              "max_ltv_percent": { "type": "number", "minimum": 1, "maximum": 100 },
              "max_ltv_note": { "type": "string" },
              "max_loan_term_years": { "type": "integer", "minimum": 1, "maximum": 50 },
              "min_loan_term_years": { "type": "integer", "minimum": 1 },
              "max_loan_amount": { "type": ["number", "null"] },
              "min_loan_amount": { "type": "number" }
            }
          },
          "eligibility": {
            "type": "object",
            "required": [
              "min_age",
              "max_age_at_loan_end",
              "borrower_scope",
              "accepted_collateral",
              "general_requirements"
            ],
            "properties": {
              "min_age": { "type": "integer", "minimum": 18 },
              "max_age_at_loan_end": { "type": "integer", "maximum": 80 },
              "borrower_scope": { "type": "string" },
              "min_monthly_income": { "type": ["number", "null"] },
              "accepted_collateral": {
                "type": "array",
                "items": { "type": "string" }
              },
              "processing_time_days": { "type": "string" },
              "general_requirements": {
                "type": "array",
                "items": { "type": "string" }
              }
            }
          },
          "repayment_methods": {
            "type": "array",
            "items": { "type": "string", "enum": ["annuity", "reducing_balance"] }
          },
          "last_updated": { "type": "string", "format": "date" },
          "disclaimer": { "type": "string" }
        }
      }
    }
  }
}
```

---

## 4. Ví dụ cấu trúc dữ liệu JSON mẫu

```json
{
  "id": "vietcombank",
  "code": "VCB",
  "name": "Ngân hàng TMCP Ngoại thương Việt Nam",
  "short_name": "Vietcombank",
  "website": "https://www.vietcombank.com.vn",
  "source_url": "https://www.vietcombank.com.vn/vi-VN/KHCN/SPDV/Vay/Vay-mua-nha-dat",
  "package_name": "Vay mua nhà ở, đất ở (Gói Nhà Mới Thành Đạt)",
  "interest_rate": {
    "promo_rate": 5.2,
    "promo_duration_months": 12,
    "floating_margin": 3.5,
    "floating_rate_estimated": 9.2,
    "reference_rate_type": "Lãi suất tiết kiệm 12 tháng trả sau",
    "adjustment_frequency_months": 3,
    "rate_options": [
      { "duration_months": 12, "rate": 5.2, "conditions": "Áp dụng năm đầu" },
      { "duration_months": 24, "rate": 6.5, "conditions": "Thời hạn vay tối thiểu 48 tháng" }
    ]
  },
  "promotions": {
    "summary": "Lãi suất chỉ từ 5.2%/năm, thời hạn vay đến 30 năm, hạn mức 50 tỷ đồng",
    "grace_period_months": 12,
    "early_repayment_penalty": {
      "description": "Phí phạt giảm dần từ năm 1 đến năm 5, miễn phí từ năm thứ 6",
      "tiers": [
        { "from_year": 1, "to_year": 1, "rate_percent": 1.5 },
        { "from_year": 2, "to_year": 3, "rate_percent": 1.0 },
        { "from_year": 4, "to_year": 5, "rate_percent": 0.5 },
        { "from_year": 6, "to_year": 30, "rate_percent": 0.0 }
      ]
    },
    "special_offers": [
      "Miễn phí duy trì dịch vụ VCB Digibank",
      "Tặng tài khoản số đẹp theo ngày sinh/số điện thoại"
    ]
  },
  "loan_limit": {
    "max_ltv_percent": 70.0,
    "max_ltv_note": "Tối đa 70% giá trị TSBĐ là chính ngôi nhà, lên đến 100% nếu có TSBĐ độc lập bổ sung",
    "max_loan_term_years": 30,
    "min_loan_term_years": 3,
    "max_loan_amount": 50000000000,
    "min_loan_amount": 100000000
  },
  "eligibility": {
    "min_age": 18,
    "max_age_at_loan_end": 75,
    "borrower_scope": "Công dân Việt Nam, vay mua nhà cho bản thân hoặc người thân (vợ/chồng/bố/mẹ/con)",
    "min_monthly_income": 10000000,
    "accepted_collateral": [
      "Nhà ở, đất ở có Giấy chứng nhận (Sổ đỏ/Sổ hồng)",
      "Căn hộ chung cư hình thành trong tương lai thuộc dự án hợp tác",
      "Giấy tờ có giá, sổ tiết kiệm do VCB phát hành"
    ],
    "processing_time_days": "3 - 5 ngày làm việc",
    "general_requirements": [
      "Có nguồn thu nhập ổn định và đủ năng lực trả nợ gốc, lãi",
      "Không có lịch sử nợ xấu tại CIC tại thời điểm thẩm định"
    ]
  },
  "repayment_methods": ["reducing_balance", "annuity"],
  "last_updated": "2026-10-31",
  "disclaimer": "Thông tin chỉ mang tính tham khảo, chi tiết phụ thuộc phê duyệt tín dụng của Vietcombank."
}
```
