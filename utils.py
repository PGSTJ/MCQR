from typing import Tuple
import csv

# FILE = 'moriah_CQR\\Compatability_Quiz _Response.csv'
FILE = 'cqr.csv'

# CSV variation constants | Default: MODE=4 EXLUSION=2
MODE = 3
EXCLUSION = 1 # currently in cqr2 mode | TODO: set back to 2

def extract_cols() -> Tuple[list, list]:
    """ Extract the whole header as well headers of columns with unique answers. Primarily used for DB creation. """
    # encoding parameter is required when non-alphanumeric characters (such as Chinese) are included in the dataset
    with open(FILE, 'r', encoding='utf-8') as fn:
        # I chose not to use csv only to have more control on separating the header
        header = fn.readline().split(',')
        # columns with free texted answers (user input answers)
        # based on the spreadsheet, only columns 1, 2, and 4 have unique answers
        # header column tupled to the corresponding index number for easier filtering later
        unique_cols = [(header[num], num) for num in range(MODE) if num != EXCLUSION]

    return [i for i in enumerate(header)]

def extract_answers():
    with open(FILE, 'r', encoding='utf-8') as fn:
        fn.readline()
        data = csv.reader(fn)
        return [d for d in data]
    



def format_answers(uniques:list, questions:list) -> tuple:
    return tuple(uniques + questions + ['', ''])
    
    

    

if __name__ == '__main__':
    d = [1, 2, 3]
    e = ['1', 'a, ', 't']

    f = format_answers(d, e)
    print(f)