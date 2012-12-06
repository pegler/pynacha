import datetime
from decimal import Decimal

def _nacha_render_string(data, max_length, padding=' '):
    s = str(data)[:max_length]
    if len(s) < max_length:
        _pad = (str(padding)*(max_length - len(s)))
        if padding == ' ':
            s = s+_pad
        else:
            s = _pad+s
    return s

class NachaFile(object):
    batches = []
    
    def __init__(self, bank_routing_number, file_id, file_id_modifier, origination_bank, company_name, creation_datetime=None, reference_code=''):
        self.bank_routing_number = bank_routing_number
        self.file_id = file_id
        self.file_id_modifier = file_id_modifier
        self.origination_bank = origination_bank
        self.company_name = company_name
        self.creation_datetime = creation_datetime or datetime.datetime.now()
        self.reference_code = reference_code
        
    def add_batch(self, batch):
        batch.batch_number = len(self.batches)+1
        batch.set_bank_routing_number(self.bank_routing_number)
        self.batches.append(batch)
    
    def render(self):
        lines = []
        
        s = ''
        s += _nacha_render_string('1', 1)
        s += _nacha_render_string('01', 2)
        s += _nacha_render_string(' '+self.bank_routing_number, 10)
        s += _nacha_render_string(self.file_id, 10)
        s += _nacha_render_string(self.creation_datetime.strftime('%y%m%d'), 6)
        s += _nacha_render_string(self.creation_datetime.strftime('%H%M'), 4)
        s += _nacha_render_string(self.file_id_modifier, 1)
        s += _nacha_render_string('094', 3)
        s += _nacha_render_string('10', 2)
        s += _nacha_render_string('1', 1)
        s += _nacha_render_string(self.origination_bank.upper(), 23)
        s += _nacha_render_string(self.company_name.upper(), 23)
        s += _nacha_render_string(self.reference_code, 8)
        assert len(s) == 94
        lines.append(s)
        
        entry_count = 0
        entry_hash = 0
        total_debit = 0
        total_credit = 0
        
        for batch in self.batches:
            d = batch.render()
            entry_count += d['entry_count']
            entry_hash += d['entry_hash']
            total_debit += d['total_debit']
            total_credit += d['total_credit']
            lines.extend(d['lines'])
        
        s = ''
        s += _nacha_render_string('9', 1)
        s += _nacha_render_string(len(self.batches), 6, '0')
        s += _nacha_render_string(len(lines)+1, 6, '0')
        s += _nacha_render_string(entry_count, 8, '0')
        s += _nacha_render_string(str(entry_hash)[:10], 10, '0')
        
        debits = total_debit.quantize(Decimal('.01'))*100
        debits = debits.quantize(Decimal('0'))
        debits = str(debits)
        
        s += _nacha_render_string(debits, 12, '0')
        
        credits = total_credit.quantize(Decimal('.01'))*100
        credits = credits.quantize(Decimal('0'))
        credits = str(credits)
        
        s += _nacha_render_string(credits, 12, '0')
        s += _nacha_render_string('', 39, ' ')
        assert len(s) == 94
        lines.append(s)
        
        return '\n'.join(lines)
        
        
    
    
class NachaBatch(object):
    MIXED = '200'
    CREDITS_ONLY = '220'
    DEBITS_ONLY = '225'
    
    PPD = 'PPD' #Prearranged payment and deposit entries
    CCD = 'CCD' #Corporate credit or debit
    CTX = 'CTX' #Corporate trade exchange
    
    entries = []
    bank_routing_number = None
    batch_number = None
    
    def __init__(self, service_class, company_name, company_id, sec_code, description, entry_date=None, company_discressionary_data=''):
        self.service_class = service_class
        self.company_name = company_name
        self.company_id = company_id
        self.sec_code = sec_code
        self.description = description
        self.entry_date = entry_date or datetime.date.today()
        self.company_discressionary_data = company_discressionary_data
        
    def set_bank_routing_number(self, bank_routing_number):
        self.bank_routing_number = bank_routing_number
        for entry in self.entries:
            entry.set_bank_routing_number(bank_routing_number)
    
    def add_entry(self, entry):
        entry.set_bank_routing_number(self.bank_routing_number)
        entry.entry_number = len(self.entries)+1
        self.entries.append(entry)
        
    def render(self):
        lines = []
        
        s = ''
        s += _nacha_render_string('5', 1)
        s += _nacha_render_string(self.service_class, 3, '0')
        s += _nacha_render_string(self.company_name.upper(), 16)
        s += _nacha_render_string(self.company_discressionary_data, 20)
        s += _nacha_render_string(self.company_id, 10, '0')
        s += _nacha_render_string(self.sec_code, 3, '0')
        s += _nacha_render_string(self.description.upper(), 10)
        s += _nacha_render_string('', 6)
        s += _nacha_render_string(self.entry_date.strftime('%y%m%d'), 6)
        s += _nacha_render_string('', 3)
        s += _nacha_render_string('1', 1)
        s += _nacha_render_string(self.bank_routing_number, 8, ' ')
        s += _nacha_render_string(self.batch_number, 7, '0')
        assert len(s) == 94
        lines.append(s)
        
        entry_hash = Decimal(0)
        total_debit = Decimal(0)
        total_credit = Decimal(0)
        for entry in self.entries:
            s = entry.render()
            if entry.transaction_code in NachaEntry.CREDIT_OPTIONS:
                total_credit += entry.amount
            elif entry.transaction_code in NachaEntry.DEBIT_OPTIONS:
                total_debit += entry.amount
            entry_hash += int(s[3:11])
            
            lines.append(s)
            
        s = ''
        s += _nacha_render_string('8', 1)
        s += _nacha_render_string(self.service_class, 3, '0')
        s += _nacha_render_string(len(self.entries), 6, '0')
        s += _nacha_render_string(str(entry_hash)[:10], 10, '0')
        
        debits = total_debit.quantize(Decimal('.01'))*100
        debits = debits.quantize(Decimal('0'))
        debits = str(debits)
        
        s += _nacha_render_string(debits, 12, '0')
        
        credits = total_credit.quantize(Decimal('.01'))*100
        credits = credits.quantize(Decimal('0'))
        credits = str(credits)
        
        s += _nacha_render_string(credits, 12, '0')
        s += _nacha_render_string(self.company_id, 10, '0')
        s += _nacha_render_string('', 19)
        s += _nacha_render_string('', 6)
        s += _nacha_render_string(self.bank_routing_number, 8, '0')
        s += _nacha_render_string(self.batch_number, 7, '0')
        assert len(s) == 94
        lines.append(s)
        
        return {
                'lines': lines,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'entry_hash': entry_hash,
                'entry_count': len(self.entries),
                }
        
class NachaEntry(object):
    
    CHECKING_CREDIT = '22'
    CHECKING_PRENOTE_CREDIT = '23'
    CHECKING_DEBIT = '27'
    CHECKING_PRENOTE_DEBIT = '28'
    SAVINGS_CREDIT = '32'
    SAVINGS_PRENOTE_CREDIT = '33'
    SAVINGS_DEBIT = '37'
    SAVINGS_PRENOTE_DEBIT = '38'
    
    CREDIT_OPTIONS = (CHECKING_CREDIT, CHECKING_PRENOTE_CREDIT, SAVINGS_CREDIT, SAVINGS_PRENOTE_CREDIT)
    DEBIT_OPTIONS = (CHECKING_DEBIT, CHECKING_PRENOTE_DEBIT, SAVINGS_DEBIT, SAVINGS_PRENOTE_DEBIT)
    
    bank_routing_number = None
    
    def __init__(self, transaction_code, routing_number, account_number, amount, individual_name):
        self.transaction_code = str(transaction_code)
        self.routing_number = str(routing_number)
        self.account_number = str(account_number)
        self.individual_name = individual_name.upper()
        
        if not isinstance(amount, Decimal):
            raise Exception
        
        self.amount = amount
    
    def set_bank_routing_number(self, bank_routing_number):
        self.bank_routing_number = bank_routing_number
        
    def render(self):
        s = ''
        s += _nacha_render_string(6, 1)
        s += _nacha_render_string(self.transaction_code, 2)
        s += _nacha_render_string(self.routing_number[:-1], 8, '0')
        s += _nacha_render_string(self.routing_number[-1], 1)
        s += _nacha_render_string(self.account_number, 17, ' ')
        
        amt = self.amount.quantize(Decimal('.01'))*100
        amt = amt.quantize(Decimal('0'))
        amt = str(amt)
        
        s += _nacha_render_string(amt, 10, '0')
        s += _nacha_render_string('', 16)
        s += _nacha_render_string(self.individual_name, 21)
        s += _nacha_render_string('', 2)
        s += _nacha_render_string(0, 1)
        s += _nacha_render_string(self.bank_routing_number, 8, '0')
        s += _nacha_render_string(self.entry_number, 7, '0')
        assert len(s) == 94
        return s
    
    
if __name__=="__main__":
    file = NachaFile('091000019', '2123456789', 'A', 'WELLS FARGO', 'teamup sports, inc')
    batch = NachaBatch(NachaBatch.CREDITS_ONLY, 'teamup sports, inc', '2123456789', NachaBatch.CCD, 'Weekly deposit')
    file.add_batch(batch)
    
    entry = NachaEntry(NachaEntry.CHECKING_CREDIT, '071923213', '0558769606', Decimal('11.99'), 'Matthew Pegler')
    batch.add_entry(entry)
    
    
    
    print file.render()