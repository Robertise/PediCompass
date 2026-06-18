import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.age_utils import extract_age_days_from_text, map_age_to_group, resolve_age_days, AgeGroup

def test_extract_age_days_from_text():
    assert extract_age_days_from_text("my 2 week old has a fever") == 14
    assert extract_age_days_from_text("3-month-old") == 90
    assert extract_age_days_from_text("newborn baby") == 14
    assert extract_age_days_from_text("con tôi 3 tháng tuổi") == 90
    assert extract_age_days_from_text("my child is sick") is None

def test_map_age_to_group():
    assert map_age_to_group(10) == AgeGroup.NEWBORN
    assert map_age_to_group(45) == AgeGroup.YOUNG_INFANT
    assert map_age_to_group(100) == AgeGroup.INFANT

def test_resolve_age_days():
    # Provide DOB
    # assuming today is 2026-06-18, a DOB of 2026-06-04 is 14 days ago
    from datetime import date, timedelta
    dob = (date.today() - timedelta(days=14)).isoformat()
    assert resolve_age_days("my child", dob) == 14
    assert resolve_age_days("my 2 month old", dob) == 14 # DOB takes precedence
    assert resolve_age_days("my 2 month old", None) == 60
