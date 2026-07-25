"""
Excel file reader for insurance sales reports.
Auto-detects insurance type from sheet name and parses accordingly.

Supported insurance types:
  - CarSalesBNVer  → بیمه شخص ثالث
  - CarBdBNVer     → بیمه بدنه
  - OmraniBNVer    → بیمه مسئولیت عمرانی
  - MadaniBNVer    → بیمه مسئولیت مدنی
  - BldBNVer       → بیمه مسئولیت ساختمانی
  - TzBNVer        → بیمه عیوب اساسی
  - KarfarmaBNVer  → بیمه مسئولیت کارفرما
  - FireBNVer      → بیمه آتش‌سوزی
"""
import re
import pandas as pd
import jdatetime
from typing import Dict, List, Optional, Tuple

# ──────────────────────────────────────────────
# Sheet name → Insurance type mapping
# ──────────────────────────────────────────────
SHEET_TO_TYPE = {
    'CarSalesBNVer': ('third_party', 'بیمه شخص ثالث'),
    'CarBdBNVer': ('body', 'بیمه بدنه'),
    'OmraniBNVer': ('liability_construction', 'بیمه مسئولیت عمرانی'),
    'MadaniBNVer': ('liability_civil', 'بیمه مسئولیت مدنی'),
    'BldBNVer': ('liability_building', 'بیمه مسئولیت ساختمانی'),
    'TzBNVer': ('defects', 'بیمه عیوب اساسی'),
    'KarfarmaBNVer': ('liability_employer', 'بیمه مسئولیت کارفرما'),
    'FireBNVer': ('fire', 'بیمه آتش‌سوزی'),
}

# ──────────────────────────────────────────────
# Column mappings for each insurance type
# ──────────────────────────────────────────────

# Base columns shared across ALL types
BASE_COLUMNS = {
    'کد رایانه بیمه نامه': 'policy_code',
    'شماره بيمه نامه': 'policy_number',
    'بيمه گذار': 'policyholder',
    'شماره قرارداد': 'contract_number',
    'وضعيت': 'status',
    'مدت': 'duration_days',
    'ماليات ارزش افزوده': 'vat',
    'معرف': 'agent_name',
}

# Third-party (CarSalesBNVer) - has vehicle fields
THIRD_PARTY_COLUMNS = {
    **BASE_COLUMNS,
    'كل حق بيمه': 'total_premium',
    'تاريخ شروع از ساعت 24 روز': 'start_date',
    'تاريخ انقضاء تا ساعت 24 روز': 'end_date',
    'حق بيمه با ماليات و عوارض': 'total_with_tax',
    'شماره پلاک': 'plate_number',
    'نوع وسيله نقليه': 'vehicle_type',
    'سال ساخت وسيله نقليه': 'vehicle_year',
    'پوشش بدني (ميليون ريال) ': 'body_coverage',
    'پوشش مالي (ميليون ريال)': 'financial_coverage',
    'تاريخ صدور': 'issue_date',
    'شماره بایگانی': 'archive_number',
    'شرح قراداد': 'contract_description',
}

# Body/Casco (CarBdBNVer)
BODY_COLUMNS = {
    **BASE_COLUMNS,
    'كل حق بيمه': 'total_premium',
    'تاريخ شروع': 'start_date',
    'تاريخ پایان': 'end_date',
    'حق بیمه با مالیات': 'total_with_tax',
    'شماره پلاک': 'plate_number',
    'نوع وسيله نقليه': 'vehicle_type',
    'سال ساخت وسيله نقليه': 'vehicle_year',
    'ارزش وسيله نقليه': 'vehicle_value',
    'تاريخ صدور': 'issue_date',
    'شماره بایگانی': 'archive_number',
    'شرح قراداد': 'contract_description',
}

# All liability types use the same column pattern
LIABILITY_COLUMNS = {
    **BASE_COLUMNS,
    'حق بيمه': 'total_premium',
    'حق بيمه كل (با ماليات و عوارض)': 'total_with_tax',
    'تاریخ شروع': 'start_date',
    'تاریخ پایان': 'end_date',
    'تاريخ صدور': 'issue_date',
    'شماره بایگانی': 'archive_number',
}

# Fire (FireBNVer)
FIRE_COLUMNS = {
    **BASE_COLUMNS,
    'حق بيمه كل': 'total_premium',
    'حق بيمه كل (با ماليات و عوارض)': 'total_with_tax',
    'تاریخ شروع': 'start_date',
    'تاریخ پایان': 'end_date',
    'تاريخ صدور': 'issue_date',
    'شماره بایگانی': 'archive_number',
}

# Defects / عیوب اساسی (TzBNVer) - uses different column names
DEFECTS_COLUMNS = {
    **BASE_COLUMNS,
    'حق بیمه کل': 'total_premium',
    'تاریخ شروع': 'start_date',
    'تاریخ پایان': 'end_date',
    'تاريخ صدور': 'issue_date',
    'شماره بایگانی': 'archive_number',
}

# Map sheet name to its column mapping
SHEET_COLUMNS = {
    'CarSalesBNVer': THIRD_PARTY_COLUMNS,
    'CarBdBNVer': BODY_COLUMNS,
    'OmraniBNVer': LIABILITY_COLUMNS,
    'MadaniBNVer': LIABILITY_COLUMNS,
    'BldBNVer': LIABILITY_COLUMNS,
    'TzBNVer': DEFECTS_COLUMNS,
    'KarfarmaBNVer': LIABILITY_COLUMNS,
    'FireBNVer': FIRE_COLUMNS,
}

# Number fields that should be converted to int
INT_FIELDS = {
    'total_premium', 'vat', 'total_with_tax', 'body_coverage',
    'financial_coverage', 'vehicle_value', 'duration_days', 'vehicle_year',
}

# Date fields
DATE_FIELDS = {'start_date', 'end_date', 'issue_date'}


def detect_insurance_type(file_path: str) -> Tuple[str, str, str]:
    """
    Detect insurance type from Excel file by checking sheet names.

    Returns:
        (type_slug, type_name, sheet_name)
    """
    xls = pd.ExcelFile(file_path)
    for sheet in xls.sheet_names:
        if sheet in SHEET_TO_TYPE:
            slug, name = SHEET_TO_TYPE[sheet]
            return slug, name, sheet
    # Fallback: try to detect from column patterns
    for sheet in xls.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet, nrows=1)
        cols = set(df.columns.str.strip())
        if 'پوشش بدني (ميليون ريال) ' in cols or 'پوشش بدني' in cols:
            return 'third_party', 'بیمه شخص ثالث', sheet
        if 'ارزش وسيله نقليه' in cols:
            return 'body', 'بیمه بدنه', sheet
    return 'unknown', 'سایر', xls.sheet_names[0]


def parse_excel(file_path: str) -> List[Dict]:
    """
    Parse the Excel file, auto-detecting insurance type.

    Args:
        file_path: Path to the .xlsx file

    Returns:
        List of dictionaries with policy data ready for DB insertion
    """
    type_slug, type_name, sheet_name = detect_insurance_type(file_path)
    column_map = SHEET_COLUMNS.get(sheet_name, BASE_COLUMNS)

    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df.columns = df.columns.str.strip()

    policies = []
    for _, row in df.iterrows():
        # Skip records without policy number (مورد ۵)
        policy_number = row.get('شماره بيمه نامه')
        try:
            has_number = not (pd.isna(policy_number) or str(policy_number).strip() in ('', 'nan', 'None'))
        except Exception:
            has_number = False
        if not has_number:
            continue

        policy = {
            '_insurance_type_slug': type_slug,
            '_insurance_type_name': type_name,
        }
        raw_data = {}

        for excel_col, model_field in column_map.items():
            value = row.get(excel_col)
            raw_data[excel_col] = _serialize_value(value)

            if pd.isna(value) or value is None:
                policy[model_field] = None
                continue

            if model_field in INT_FIELDS:
                try:
                    policy[model_field] = int(float(value))
                except (ValueError, TypeError):
                    policy[model_field] = None
            elif model_field in DATE_FIELDS:
                policy[model_field] = _normalize_date(str(value))
            elif model_field == 'policy_code':
                try:
                    policy[model_field] = str(int(float(value)))
                except (ValueError, TypeError):
                    policy[model_field] = str(value)
            elif model_field == 'policy_number':
                try:
                    # Remove trailing ".0" from floats like 524.0 → 524
                    num = float(value)
                    if num == int(num):
                        policy[model_field] = str(int(num))
                    else:
                        policy[model_field] = str(num)
                except (ValueError, TypeError):
                    policy[model_field] = str(value).strip() if isinstance(value, str) else str(value)
            else:
                policy[model_field] = (
                    str(value).strip() if isinstance(value, str) else str(value)
                )

        # Clean policyholder name (remove trailing code: "نام کد 12345")
        if policy.get('policyholder'):
            name = policy['policyholder']
            match = re.match(r'^(.+?)\s+کد\s+\d+$', name)
            if match:
                policy['policyholder_clean'] = match.group(1).strip()

        policy['raw_data'] = raw_data
        policies.append(policy)

    return policies


def _serialize_value(value):
    """Convert numpy types to Python native types for JSON serialization"""
    if pd.isna(value) or value is None:
        return None
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if hasattr(value, 'item'):
        return value.item()
    if isinstance(value, (float, int)):
        return value
    return str(value)


def _normalize_date(date_str: str) -> Optional[str]:
    """Normalize date string to 'YYYY/MM/DD' format"""
    if not date_str or date_str in ('NaT', 'nan', 'None', ''):
        return None
    date_str = str(date_str).split()[0]
    if re.match(r'^\d{4}/\d{2}/\d{2}$', date_str):
        return date_str
    try:
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%Y%m%d']:
            try:
                from datetime import datetime
                dt = datetime.strptime(date_str, fmt)
                jalali = jdatetime.date.fromgregorian(
                    year=dt.year, month=dt.month, day=dt.day
                )
                return jalali.strftime('%Y/%m/%d')
            except ValueError:
                continue
    except Exception:
        pass
    return date_str


def preview_excel(file_path: str) -> Tuple[List[Dict], int, List[str], str, str]:
    """
    Preview Excel file contents without saving to DB.

    Returns:
        (policies, count, column_keys, type_slug, type_name)
    """
    policies = parse_excel(file_path)
    if policies:
        type_slug = policies[0].get('_insurance_type_slug', 'unknown')
        type_name = policies[0].get('_insurance_type_name', 'سایر')
    else:
        type_slug, type_name = 'unknown', 'سایر'
    return policies, len(policies), list(BASE_COLUMNS.keys()), type_slug, type_name
