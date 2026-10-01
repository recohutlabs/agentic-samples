"""Source-authored predicates; absent keys never count as explicit null."""
from decimal import Decimal, InvalidOperation
import re
MISSING=object()
def value_at(data,path):
    try:
        for key in path.split('.'):data=data[int(key)] if isinstance(data,list) else data[key]
        return data
    except (KeyError,IndexError,TypeError,ValueError):return MISSING

def money_equal(a,b):
    if a is None or a is MISSING:return False
    try:return Decimal(str(a))==Decimal(str(b))
    except InvalidOperation:return False

def evaluate_check(data,c):
    a=value_at(data,c['path']);b=c['expected'];op=c['op'];passed=False
    if a is not MISSING:
        if op=='equals':passed=a==b
        elif op=='money':passed=money_equal(a,b)
        elif op=='name':passed=re.sub(r'\s*\([^)]*\)','',str(a)).strip().rstrip('.')==b
        elif op=='has_amount':passed=isinstance(a,list) and any(money_equal(x.get('amount'),b) for x in a)
        elif op=='no_amounts':passed=isinstance(a,list) and not any(money_equal(x.get('amount'),n) for x in a for n in b)
        elif op=='has_notice_days':passed=isinstance(a,list) and all(any(x.get('notice_duration')==n and x.get('notice_unit')=='days' and x.get('day_basis')=='calendar' for x in a) for n in b)
        elif op=='salary_pair':passed=isinstance(a,dict) and any(money_equal(a.get('base_salary'),x['base_salary']) and a.get('salary_period')==x['salary_period'] for x in b)
        else:raise ValueError('Unknown predicate')
    return {**c,'actual':None if a is MISSING else a,'missing':a is MISSING,'passed':passed}

def grade(data,checks):return [evaluate_check(data,c) for c in checks]
