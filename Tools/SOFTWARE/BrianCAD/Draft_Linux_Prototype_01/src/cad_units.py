"""Drawing display units and a bounded arithmetic parser (no Python evaluation)."""
import math
import re

UNITS={'in':('Inches',1.),'mm':('Millimeters',1/25.4),'cm':('Centimeters',1/2.54),
       'm':('Meters',100/2.54),'ft':('Feet',12.)}
ALIASES={'in':'in','inch':'in','inches':'in','"':'in','mm':'mm','millimeter':'mm','millimeters':'mm','millimetre':'mm','millimetres':'mm',
         'cm':'cm','centimeter':'cm','centimeters':'cm','centimetre':'cm','centimetres':'cm',
         'm':'m','meter':'m','meters':'m','metre':'m','metres':'m','ft':'ft','foot':'ft','feet':'ft',"'":'ft'}
NUMBER=r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
TOKEN=re.compile(r'\s*('+NUMBER+r'|[A-Za-z]+|["\'°]|[()+*/-])')


def field_kind(key):return 'angle' if key in ('angle','start','sweep') else 'scalar' if key in ('factor','sides') else 'length'


def display_value(value,unit='in',kind='length'):return value/UNITS[unit][1] if kind=='length' else value


def format_value(value,unit='in',kind='length'):return f'{display_value(value,unit,kind):.12g}'


def parse_number(text,unit='in',kind='length'):
    if unit not in UNITS:raise ValueError('Choose a supported drawing unit.')
    if isinstance(text,bool):raise ValueError('Enter a number or arithmetic expression.')
    text=str(text).strip().replace('″','"').replace('”','"').replace('′',"'").replace('−','-').replace('×','*').replace('÷','/')
    if not text or len(text)>1024:raise ValueError('Enter a number or arithmetic expression.')
    text=re.sub(r'(?<![\w.])(\d+)\s+(\d+)\s*/\s*(\d+)',r'(\1+\2/\3)',text)
    # A suffix on a numeric fraction applies to the whole fraction: 5/8".
    text=re.sub(r'(?<![\w.])('+NUMBER+r'\s*/\s*'+NUMBER+r')\s*([A-Za-z]+|["\'])',
                lambda m:'('+m[1]+')'+m[2] if m[2].lower() in ALIASES or m[2].lower() in ('deg','degrees','rad','radians') else m[0],text)
    tokens=[];position=0
    while position<len(text):
        match=TOKEN.match(text,position)
        if not match:raise ValueError('Use numbers, unit suffixes, +, -, *, / and parentheses.')
        tokens.append(match.group(1));position=match.end()
        if len(tokens)>256:raise ValueError('The expression is too long.')
    index=0;depth=0
    def primary():
        nonlocal index,depth
        depth+=1
        if depth>32:raise ValueError('Too many nested operations.')
        if index>=len(tokens):raise ValueError('Incomplete numeric expression.')
        token=tokens[index];index+=1
        if token in ('+','-'):value=primary()*(1 if token=='+' else -1)
        elif token=='(':
            value=expression()
            if index>=len(tokens) or tokens[index]!=')':raise ValueError('Check expression parentheses.')
            index+=1
        elif re.fullmatch(NUMBER,token):value=float(token)
        else:raise ValueError('Expected a number.')
        if index<len(tokens) and (tokens[index][0].isalpha() or tokens[index] in ('"',"'",'°')):
            suffix=tokens[index].lower();index+=1
            if kind=='length' and suffix in ALIASES:value*=UNITS[ALIASES[suffix]][1]/UNITS[unit][1]
            elif kind=='angle' and suffix in ('deg','degree','degrees','°'):pass
            elif kind=='angle' and suffix in ('rad','radian','radians'):value*=180/math.pi
            else:raise ValueError('Unknown or incompatible unit suffix.')
        depth-=1;return value
    def product():
        nonlocal index
        value=primary()
        while index<len(tokens) and tokens[index] in ('*','/'):
            op=tokens[index];index+=1;right=primary()
            value=value*right if op=='*' else value/right
        return value
    def expression():
        nonlocal index
        value=product()
        while index<len(tokens) and tokens[index] in ('+','-'):
            op=tokens[index];index+=1;right=product();value=value+right if op=='+' else value-right
        return value
    try:
        value=expression()
        if index!=len(tokens):raise ValueError('Check expression operators and unit suffixes.')
        if kind=='length':value*=UNITS[unit][1]
        if not math.isfinite(value):raise ValueError('Enter a finite numeric value.')
        return value
    except (ZeroDivisionError,OverflowError,RecursionError) as ex:raise ValueError('Invalid arithmetic or division by zero.') from ex
