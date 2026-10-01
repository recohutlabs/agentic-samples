"""Calibrate each deterministic predicate against valid and invalid results."""
import unittest
from evaluation.grading import evaluate_check

class GradingTests(unittest.TestCase):
    def check(self,op,expected,good,bad):
        c={'path':'field','op':op,'expected':expected,'source_page':1}
        self.assertTrue(evaluate_check({'field':good},c)['passed'])
        self.assertFalse(evaluate_check({'field':bad},c)['passed'])
        self.assertFalse(evaluate_check({},c)['passed'])

    def test_predicates(self):
        self.check('equals',None,None,'invented')
        self.check('money','12','12.00','13')
        self.check('name','Aarav Mehta','Aarav Mehta (fictional)','Aarav Sharma')
        self.check('has_amount','10',[{'amount':'10.00'}],[{'amount':None}])
        self.check('no_amounts',['20'],[{'amount':None}],[{'amount':'20'}])
        self.check('salary_pair',[{'base_salary':'50000','salary_period':'monthly'}],{'base_salary':'50000.00','salary_period':'monthly'},{'base_salary':'50000','salary_period':'annual'})
        self.check('has_notice_days',[15,60],[{'notice_duration':15,'notice_unit':'days','day_basis':'calendar'},{'notice_duration':60,'notice_unit':'days','day_basis':'calendar'}],[{'notice_duration':60,'notice_unit':'months','day_basis':'calendar'}])
