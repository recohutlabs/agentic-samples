"""Notice cleanup preserves zero; compensation stores source subtotals separately."""
import unittest
from models.employment import Compensation, EmploymentExitRule

class EmploymentFixTests(unittest.TestCase):
    def test_missing_notice_clears_units_but_zero_is_preserved(self):
        payload=dict(initiated_by='either',grounds='Expiry',applies_during='Fixed-term expiry',notice_duration=None,notice_unit='days',day_basis='unspecified',payment_in_lieu=None,conditions=None)
        rule=EmploymentExitRule(**payload)
        self.assertIsNone(rule.notice_unit)
        self.assertIsNone(rule.day_basis)
        payload.update(notice_duration=0,day_basis='calendar')
        rule=EmploymentExitRule(**payload)
        self.assertEqual(rule.notice_unit,'days')
        self.assertEqual(rule.day_basis,'calendar')

    def test_subtotals_are_separate_and_optional_for_old_outputs(self):
        payload=dict(currency='INR',base_salary='600000',salary_period='annual',annual_ctc='1500000',components=None,bonus_terms=None,benefits=None,payment_schedule=None,deductions=None)
        old=Compensation(**payload)
        self.assertIsNone(old.annual_fixed_gross_salary)
        self.assertIsNone(old.annual_fixed_ctc)
        new=Compensation(**payload,annual_fixed_gross_salary='1200000',annual_fixed_ctc='1320000')
        self.assertEqual(new.annual_fixed_gross_salary,1200000)
        self.assertEqual(new.annual_fixed_ctc,1320000)
