#!/usr/bin/env python3
"""
Script kiểm tra tính hợp lệ của file dữ liệu ngân hàng (data/banks_sample.json)
theo JSON Schema đã định nghĩa tại docs/schema.md.

Cách sử dụng:
    python scripts/check_banks.py
    python scripts/check_banks.py path/to/banks.json
    python scripts/check_banks.py --file data/banks_sample.json
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Đảm bảo in tiếng Việt trên console Windows không bị UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# JSON Schema chuẩn hóa từ docs/schema.md
BANK_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "BankLoanPackageList",
    "description": "Schema định dạng danh sách sản phẩm vay mua nhà của các ngân hàng thương mại",
    "type": "object",
    "required": ["version", "updated_at", "banks"],
    "properties": {
        "version": {"type": "string"},
        "updated_at": {"type": "string"},
        "description": {"type": "string"},
        "banks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "id",
                    "code",
                    "name",
                    "short_name",
                    "website",
                    "source_url",
                    "package_name",
                    "interest_rate",
                    "promotions",
                    "loan_limit",
                    "eligibility",
                    "repayment_methods",
                    "last_updated",
                    "disclaimer",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "code": {"type": "string"},
                    "name": {"type": "string"},
                    "short_name": {"type": "string"},
                    "logo_url": {"type": ["string", "null"]},
                    "website": {"type": "string"},
                    "source_url": {"type": "string"},
                    "package_name": {"type": "string"},
                    "interest_rate": {
                        "type": "object",
                        "required": [
                            "promo_rate",
                            "promo_duration_months",
                            "floating_margin",
                            "reference_rate_type",
                            "adjustment_frequency_months",
                        ],
                        "properties": {
                            "promo_rate": {"type": ["number", "null"], "minimum": 0},
                            "promo_duration_months": {"type": ["integer", "null"], "minimum": 1},
                            "floating_margin": {"type": ["number", "null"], "minimum": 0},
                            "floating_rate_estimated": {"type": ["number", "null"]},
                            "reference_rate_type": {"type": "string"},
                            "adjustment_frequency_months": {"type": "integer", "minimum": 1},
                            "rate_options": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["duration_months", "rate"],
                                    "properties": {
                                        "duration_months": {"type": "integer"},
                                        "rate": {"type": "number"},
                                        "conditions": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "promotions": {
                        "type": "object",
                        "required": ["summary", "grace_period_months", "early_repayment_penalty"],
                        "properties": {
                            "summary": {"type": "string"},
                            "grace_period_months": {"type": "integer", "minimum": 0},
                            "early_repayment_penalty": {
                                "type": "object",
                                "required": ["description", "tiers"],
                                "properties": {
                                    "description": {"type": "string"},
                                    "tiers": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "required": ["from_year", "to_year", "rate_percent"],
                                            "properties": {
                                                "from_year": {"type": "integer"},
                                                "to_year": {"type": "integer"},
                                                "rate_percent": {"type": "number"},
                                            },
                                        },
                                    },
                                },
                            },
                            "special_offers": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                    "loan_limit": {
                        "type": "object",
                        "required": ["max_ltv_percent", "max_loan_term_years"],
                        "properties": {
                            "max_ltv_percent": {"type": "number", "minimum": 1, "maximum": 100},
                            "max_ltv_note": {"type": "string"},
                            "max_loan_term_years": {"type": "integer", "minimum": 1, "maximum": 50},
                            "min_loan_term_years": {"type": "integer", "minimum": 1},
                            "max_loan_amount": {"type": ["number", "null"]},
                            "min_loan_amount": {"type": "number"},
                        },
                    },
                    "eligibility": {
                        "type": "object",
                        "required": [
                            "min_age",
                            "max_age_at_loan_end",
                            "borrower_scope",
                            "accepted_collateral",
                            "general_requirements",
                        ],
                        "properties": {
                            "min_age": {"type": "integer", "minimum": 18},
                            "max_age_at_loan_end": {"type": "integer", "maximum": 80},
                            "borrower_scope": {"type": "string"},
                            "min_monthly_income": {"type": ["number", "null"]},
                            "accepted_collateral": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "processing_time_days": {"type": "string"},
                            "general_requirements": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                    "repayment_methods": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["annuity", "reducing_balance"]},
                    },
                    "last_updated": {"type": "string"},
                    "disclaimer": {"type": "string"},
                },
            },
        },
    },
}

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_REGEX = re.compile(r"^https?://")


def is_valid_date(date_str: str) -> bool:
    """Kiểm tra chuỗi định dạng YYYY-MM-DD hợp lệ."""
    if not isinstance(date_str, str) or not DATE_REGEX.match(date_str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_valid_url(url_str: str) -> bool:
    """Kiểm tra đường dẫn web hợp lệ."""
    return isinstance(url_str, str) and bool(URL_REGEX.match(url_str.strip()))


def validate_with_jsonschema(data: Any) -> List[str]:
    """Kiểm tra dữ liệu qua thư viện jsonschema nếu có."""
    errors: List[str] = []
    try:
        import jsonschema

        validator = jsonschema.Draft7Validator(BANK_SCHEMA)
        for err in validator.iter_errors(data):
            path = " -> ".join(str(p) for p in err.absolute_path) or "root"
            errors.append(f"[JSONSchema] {path}: {err.message}")
    except ImportError:
        print("[CẢNH BÁO] Chưa cài jsonschema (pip install jsonschema), bỏ qua bước kiểm tra JSON Schema.")
    return errors


def validate_business_rules(data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Kiểm tra các ràng buộc nghiệp vụ chi tiết."""
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Kiểm tra trường gốc
    if not isinstance(data, dict):
        return ["[Root] File phải chứa một JSON Object."], warnings

    for req_field in ["version", "updated_at", "banks"]:
        if req_field not in data:
            errors.append(f"[Root] Thiếu trường bắt buộc '{req_field}'")

    updated_at = data.get("updated_at")
    if updated_at and not is_valid_date(updated_at):
        errors.append(f"[Root] Trường 'updated_at' ('{updated_at}') không đúng định dạng YYYY-MM-DD")

    banks = data.get("banks")
    if not isinstance(banks, list):
        errors.append("[Root] Trường 'banks' phải là danh sách (array)")
        return errors, warnings

    bank_count = len(banks)
    if bank_count < 5 or bank_count > 8:
        warnings.append(
            f"[BankCount] Số lượng ngân hàng hiện tại là {bank_count} (khuyến nghị đủ từ 5 đến 8 ngân hàng)."
        )

    seen_ids = set()
    seen_codes = set()

    for idx, bank in enumerate(banks):
        prefix = f"[Bank #{idx + 1}"
        bank_id = bank.get("id", f"idx_{idx}")
        bank_code = bank.get("code", "")
        prefix += f" ({bank_code or bank_id})]"

        # ID & Code duy nhất
        if bank_id in seen_ids:
            errors.append(f"{prefix} Trùng lặp id: '{bank_id}'")
        seen_ids.add(bank_id)

        if bank_code:
            if bank_code in seen_codes:
                errors.append(f"{prefix} Trùng lặp mã ngân hàng (code): '{bank_code}'")
            seen_codes.add(bank_code)

        # Kiểm tra website và source_url
        website = bank.get("website")
        if not website or not is_valid_url(website):
            errors.append(f"{prefix} Trường 'website' ('{website}') không hợp lệ (cần bắt đầu bằng http:// hoặc https://)")

        source_url = bank.get("source_url")
        if not source_url or not is_valid_url(source_url):
            errors.append(
                f"{prefix} Trường 'source_url' ('{source_url}') không hợp lệ hoặc bị thiếu (bắt buộc theo yêu cầu nghiệp vụ)"
            )

        # Kiểm tra last_updated
        last_updated = bank.get("last_updated")
        if not last_updated:
            errors.append(f"{prefix} Thiếu trường bắt buộc 'last_updated'")
        elif not is_valid_date(last_updated):
            errors.append(f"{prefix} Trường 'last_updated' ('{last_updated}') không đúng định dạng YYYY-MM-DD")

        # Lãi suất
        ir = bank.get("interest_rate", {})
        if isinstance(ir, dict):
            promo_rate = ir.get("promo_rate")
            promo_dur = ir.get("promo_duration_months")

            # Luật: promo_rate và promo_duration_months phải cùng có giá trị hoặc cùng null (phục vụ calculator.py)
            if (promo_rate is None and promo_dur is not None) or (promo_rate is not None and promo_dur is None):
                errors.append(
                    f"{prefix} 'promo_rate' và 'promo_duration_months' phải cùng có giá trị hoặc cùng null"
                )

            if promo_rate is not None:
                if not isinstance(promo_rate, (int, float)) or promo_rate < 0:
                    errors.append(f"{prefix} 'interest_rate.promo_rate' phải là số >= 0 hoặc null")
                elif promo_rate > 20:
                    warnings.append(f"{prefix} Lãi suất ưu đãi {promo_rate}%/năm có vẻ cao bất thường (>20%)")

            if promo_dur is not None:
                if not isinstance(promo_dur, int) or promo_dur <= 0:
                    errors.append(f"{prefix} 'interest_rate.promo_duration_months' phải là số nguyên dương hoặc null")

            margin = ir.get("floating_margin")
            if margin is not None and (not isinstance(margin, (int, float)) or margin < 0):
                errors.append(f"{prefix} 'interest_rate.floating_margin' phải là số >= 0 hoặc null")

            floating_est = ir.get("floating_rate_estimated")
            if floating_est is not None and not isinstance(floating_est, (int, float)):
                errors.append(f"{prefix} 'interest_rate.floating_rate_estimated' phải là số hoặc null")
        else:
            errors.append(f"{prefix} 'interest_rate' phải là object")

        # Hạn mức & thời hạn
        limit = bank.get("loan_limit", {})
        if isinstance(limit, dict):
            max_ltv = limit.get("max_ltv_percent")
            if max_ltv is None or not isinstance(max_ltv, (int, float)) or not (1 <= max_ltv <= 100):
                errors.append(f"{prefix} 'loan_limit.max_ltv_percent' ({max_ltv}) phải từ 1 đến 100")

            max_term = limit.get("max_loan_term_years")
            if max_term is None or not isinstance(max_term, int) or not (1 <= max_term <= 50):
                errors.append(f"{prefix} 'loan_limit.max_loan_term_years' ({max_term}) phải là số nguyên từ 1 đến 50")
        else:
            errors.append(f"{prefix} 'loan_limit' phải là object")

        # Phương thức trả nợ
        methods = bank.get("repayment_methods")
        if not isinstance(methods, list) or len(methods) == 0:
            errors.append(f"{prefix} 'repayment_methods' phải là danh sách không rỗng")
        else:
            valid_methods = {"annuity", "reducing_balance"}
            for m in methods:
                if m not in valid_methods:
                    errors.append(f"{prefix} Phương thức trả nợ '{m}' không hợp lệ (chỉ chấp nhận 'annuity', 'reducing_balance')")

        # Ưu đãi & phạt tất toán
        promotions = bank.get("promotions", {})
        if isinstance(promotions, dict):
            penalty = promotions.get("early_repayment_penalty", {})
            if isinstance(penalty, dict):
                tiers = penalty.get("tiers")
                if not isinstance(tiers, list):
                    errors.append(f"{prefix} 'early_repayment_penalty.tiers' phải là danh sách (array)")
                else:
                    for t_idx, tier in enumerate(tiers):
                        if not isinstance(tier, dict):
                            errors.append(f"{prefix} Bậc phí #{t_idx + 1} phải là object")
                        else:
                            for f in ["from_year", "to_year", "rate_percent"]:
                                if f not in tier:
                                    errors.append(f"{prefix} Bậc phí #{t_idx + 1} thiếu trường '{f}'")
            else:
                errors.append(f"{prefix} 'promotions.early_repayment_penalty' phải là object")
        else:
            errors.append(f"{prefix} 'promotions' phải là object")

    return errors, warnings


def check_banks_file(file_path: Path) -> bool:
    """Hàm chính kiểm tra file dữ liệu ngân hàng."""
    print(f"=== ĐANG KIỂM TRA FILE: {file_path.resolve()} ===")

    if not file_path.exists():
        print(f"[LỖI] Không tìm thấy file: {file_path}")
        return False

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"[LỖI] Cú pháp JSON không hợp lệ tại dòng {exc.lineno}, cột {exc.colno}: {exc.msg}")
        return False
    except Exception as exc:
        print(f"[LỖI] Không thể đọc file: {exc}")
        return False

    schema_errors = validate_with_jsonschema(data)
    biz_errors, warnings = validate_business_rules(data)

    all_errors = schema_errors + biz_errors

    # In cảnh báo (nếu có)
    if warnings:
        print("\n[CẢNH BÁO]:")
        for w in warnings:
            print(f"  * {w}")

    # In kết quả kiểm tra
    if all_errors:
        print(f"\n[THẤT BẠI] Tìm thấy {len(all_errors)} lỗi schema / dữ liệu:")
        for idx, err in enumerate(all_errors, start=1):
            print(f"  {idx}. {err}")
        return False

    banks = data.get("banks", [])
    print(f"\n[THÀNH CÔNG] File dữ liệu hoàn toàn hợp lệ theo Schema!")
    print(f"  * Phiên bản dữ liệu: {data.get('version')}")
    print(f"  * Ngày cập nhật chung (updated_at): {data.get('updated_at')}")
    print(f"  * Tổng số ngân hàng: {len(banks)}")
    print("\nChi tiết danh sách ngân hàng:")
    print(f"{'STT':<4} | {'Mã':<6} | {'Tên NH':<14} | {'Gói vay':<35} | {'Lãi suất':<10} | {'LTV':<6} | {'Thời hạn':<8} | {'Nguồn URL':<30}")
    print("-" * 125)
    for idx, b in enumerate(banks, start=1):
        ir = b.get("interest_rate", {})
        if ir.get("promo_rate") is not None:
            rate_str = f"{ir.get('promo_rate')}% ({ir.get('promo_duration_months')}T)"
        else:
            rate_str = "Chưa công bố"
        ltv_str = f"{b.get('loan_limit', {}).get('max_ltv_percent')}%"
        term_str = f"{b.get('loan_limit', {}).get('max_loan_term_years')} năm"
        source = b.get("source_url", "")
        if len(source) > 30:
            source = source[:27] + "..."
        pkg = b.get("package_name", "")
        if len(pkg) > 35:
            pkg = pkg[:32] + "..."
        print(f"{idx:<4} | {b.get('code', ''):<6} | {b.get('short_name', ''):<14} | {pkg:<35} | {rate_str:<10} | {ltv_str:<6} | {term_str:<8} | {source:<30}")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra schema và tính hợp lệ của dữ liệu ngân hàng")
    parser.add_argument(
        "file",
        nargs="?",
        default="data/banks_sample.json",
        help="Đường dẫn file dữ liệu json (mặc định: data/banks_sample.json)",
    )
    parser.add_argument(
        "--file",
        dest="file_flag",
        default=None,
        help="Đường dẫn file dữ liệu json thay thế",
    )
    args = parser.parse_args()

    target_file = Path(args.file_flag if args.file_flag else args.file)
    success = check_banks_file(target_file)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
