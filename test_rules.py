import sys
sys.path.insert(0, 'src')
from rules import RulesManager
from models import Rule
from datetime import datetime

print('Starting test...')
rm = RulesManager()
print('RulesManager created')

rules = rm.load_rules()
print(f'Loaded {len(rules)} rules')

test_rule = Rule(
    vendor='Test Vendor',
    keywords=['test', 'vendor'],
    debit_account='Test Expense',
    credit_account='Test Vendor (Payable)',
    tds_applicable=True,
    learned_at=datetime.now(),
    applied_count=0
)
print('Rule object created')

print('About to save rule...')
rm.save_rule(test_rule)
print('Rule saved successfully!')

# Test loading again
rules = rm.load_rules()
print(f'Now loaded {len(rules)} rules')

# Test find matching
found = rm.find_matching('Test Vendor', ['test'])
if found:
    print(f'Found matching rule: {found.vendor}')
else:
    print('No matching rule found')