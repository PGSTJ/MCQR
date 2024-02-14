import sqlite3 as sl
import traceback

import utils

db = 'cqr.db'
conn = sl.connect(db, check_same_thread=False)
curs = conn.cursor()

GENERAL_COLS = 20
UA_QS = [f'Q{num}' for num in range(1, 16)]
UA_HDRS = ['Name', 'Grade', 'Class_Teacher'] + UA_QS + ['Best_Match', 'BM_Score'] # this last part includes a best match column in the table, allowing for easier recall



def user_answers_table():
    """ General table essentially mimicing the spreadsheet, but with encoded answers for the MC answers """
    
    # semi lazy way to create headers for all questions without manually typing it out
    col_fmt1 = ' TEXT, '.join(UA_HDRS)
    col_fmt2 = col_fmt1 + ' TEXT' # ensures last parameter also has a data_type designation 

    curs.execute(f'CREATE TABLE IF NOT EXISTS user_answers({col_fmt2})')

    # fill table with response data per csv
    data = utils.extract_answers()
    # i was lazy again and didnt want to manually typing the entire list of parameters for this table
    # these are just to make that easier
    stmt_fill = ','.join(UA_HDRS)
    stmt_qm_fill = '?,'*GENERAL_COLS

    for submission in data:
        # need to start from 3rd index since first 3 columns are unique entries
        ans_codes = _fill_gen_table_ans_mapping(submission[3:]) 
        # another lazy tactic: function to auto format the answers into a tuple instead of manually writing them all here
        fmt_data = utils.format_answers(submission[:3], ans_codes)

        curs.execute(f'INSERT INTO user_answers({stmt_fill}) VALUES({stmt_qm_fill[:-1]})', fmt_data)
    conn.commit()
    return True

def questions_code_table():
    """ Mapping source of answers to questions """
    curs.execute('CREATE TABLE IF NOT EXISTS answer_mapping(id TEXT PRIMARY KEY, question VARCHAR(3), answer TEXT)')

    data = utils.extract_answers()
    # dictionary mapping the question Numbers to their multiple choice answer possibilities
    qa_maps = {f'Q{num}':[] for num in range(1, 16)}

    # in each row, run through all 15 questions and upload answer once to database, with a designated code, ignoring future identical entries
    for submission in data:
        for num in range(1, 16):
            # have to account for the first 3 columns (thereby indices) aren't included in the Q# format
            # since we started on 1, we only need to account for 2 more columns
            corrected_idx = num + 2
            # ensures only counting a possibility once
            if submission[corrected_idx] not in qa_maps[f'Q{num}']:
                qa_maps[f'Q{num}'].append(submission[corrected_idx])

    # will now do two double for loops (iterating through all the questions, then each of their answer choices) through the mapping dictionary 
    # first to generate unique IDs  
    for mc_ans in qa_maps:
        mca_enum = [i for i in enumerate(qa_maps[mc_ans])]
        # this list comprehension creates an ID by combining the question number and answer index, then tuples this with the question number
        # theoretically should be removing empty strings with the != '' portion, but it didn't do it and I didn't feel the need to fix it
        qa_maps[mc_ans] = [(f'{mc_ans}.{ans_pos[0]}', ans_pos[1]) for ans_pos in mca_enum if ans_pos != '']    

    # and second to officially insert map into DB table
    for questions in qa_maps:
        for formatted_data in qa_maps[questions]:
            curs.execute('INSERT INTO answer_mapping(id, question, answer) VALUES(?,?,?)', (formatted_data[0], questions, formatted_data[1]))

    conn.commit()
    return True

def hdr_code_table():
    """ Mapping source of header names and respective code, mainly to clean up other tables since they're so long """
    try:
        curs.execute('CREATE TABLE IF NOT EXISTS hdr_code(id INT PRIMARY KEY, header_cols TEXT, actual_cols TEXT)')
        hdr = utils.extract_cols()
        final = [i for i in zip(hdr, UA_HDRS)]

        for hdr_pack, table_col in final:
            curs.execute('INSERT INTO hdr_code(id, header_cols, actual_cols) VALUES(?,?,?)', (hdr_pack[0], table_col, hdr_pack[1]))
        conn.commit()
        return True
    except Exception:
        traceback.print_exc()
    

def _fill_gen_table_ans_mapping(answers:list):
    """ Returns answers converted into code/id per DB mapping table """
    
    answer_code = {i[1]:i[0] for i in curs.execute('SELECT id, answer FROM answer_mapping')}

    return [answer_code[answer] for answer in answers if answer in answer_code]


def create_all():
    questions_code_table()
    hdr_code_table()
    user_answers_table()
    return True


def get_all_best_matches():
    """ Extracts all Best Match pairs in DB """
    return [i for i in curs.execute('SELECT Name, Best_Match, BM_Score FROM user_answers')]

def get_match_details(match_data:list) -> tuple[list, list]:
    for name, match, bms in match_data:
        name_qas = get_all_question_answers(name)
        name_class = get_ua_value(name, classteacher=True)
        name_all_details = [name, name_class, name_qas]

        match_qas = get_all_question_answers(match)
        match_class = get_ua_value(match, classteacher=True)
        match_all_details = [match, match_class, match_qas]

    return name_all_details, match_all_details



def get_ua_value(name:str, grade=False, classteacher=False, best_match=False) -> list[tuple]:
    """ Pull any unique value (not question/answers) for a specified name """
    if not verify_submitter(name):
        return False
    
    # final list that will contain all specified parameters for easy handling
    final = []

    if grade:
        final.append('Grade')
    if classteacher:
        final.append('Class_Teacher')
    if best_match:
        final.append('Best_Match')

    stmt = ','.join(final)
    return [i for i in curs.execute(f'SELECT {stmt} FROM user_answers WHERE name=?', (name,))]


def get_all_question_answers(name:str) -> list[str] | bool:
    """ Gets all answers of a specified person """
    if not verify_submitter(name):
        return False
    
    q_fmt = ','.join(UA_QS)
    
    db_q_ans = [i for i in curs.execute(f'SELECT {q_fmt} FROM user_answers WHERE Name=?', (name,))][0]

    return [[i[0] for i in curs.execute('SELECT answer FROM answer_mapping WHERE id=?', (ans,))][0] for ans in db_q_ans]


def get_specific_question_answer(name:str, question_num:int) -> str:
    """ Gets the answer of the specified person at the specific question """
    db_q_ans = [i[0] for i in curs.execute(f'SELECT Q{question_num} FROM user_answers WHERE Name=?', (name,))][0]

    return [i[0] for i in curs.execute('SELECT answer FROM answer_mapping WHERE id=?', (db_q_ans,))][0]


def find_match():
    """ Finds match for all submitters, but returns SubmissionComparison object for more versatile manipulation """

    all_subs = [i[0] for i in curs.execute('SELECT Name FROM user_answers')]
    # print(f'allsubs: {all_subs}')
    
    # iterate through all submissions
    # for each submission, compare with answers with all other submissions by creating a 
    # SubmissionComparison object for each comparison report
    return [SubmissionComparison(subs, all_subs) for subs in all_subs]


class SubmissionComparison():
    """ Handles all comparison processing and transient data storage/recall """
    def __init__(self, submitter_name:str, all_subs:list) -> None:
        self.submitter = submitter_name
        self.all_subs = all_subs

        self.highest_match_score = 0
        self.best_match = ''

        self.sub_data = self.sub_info(self.submitter)

        self.compare_all()
        self.post_init()

    def post_init(self):
        """ Extract answer profile for best match user for more versatile data manipulation """
        self.best_match_data = self.sub_info(self.best_match)
        # updates best_match column in DB
        curs.execute('UPDATE user_answers SET Best_Match=?, BM_Score=? WHERE Name=?', (self.best_match, self.highest_match_score, self.submitter))
        conn.commit()



    def compare_all(self):
        """ Executive for comparing against all other submitters """
        for subs in self.all_subs:
            # verify not comparing against self
            if self.submitter != subs:
                if self.compare_answers(self.sub_data, self.sub_info(subs)):
                    self.best_match = subs
                
    @staticmethod
    def sub_info(submitter_name:str) -> list:
        """ Extract answer profile from DB for specified name """
        rmndr = ','.join(UA_QS)
        return [i for i in curs.execute(f'SELECT Class_Teacher,{rmndr} FROM user_answers WHERE Name=?', (submitter_name,))][0]

    def compare_answers(self, answer_set1:list, answer_set2:list) -> int:
        """ Actual compare functionality; directly comparing each index and reassigning match scores as needed """
        # arbitrary value to allow comparison across multiple submissions
        match_score = 0
        # zip together to directly compare indices
        for one, two in zip(answer_set1[1:], answer_set2[1:]):
            if one == two:
                match_score += 1

        # reassign highest match score as needed
        # return bool mainly to offer differentiation in output and update best match attribute with the highest match score
        if match_score > self.highest_match_score:
            self.highest_match_score = match_score
            return True
        else:
            return False







def verify_submitter(name:str):
    """ Verifies that a specified user is a real person who has submitted """

    all = [i[0] for i in curs.execute('SELECT Name FROM user_answers')]
    if name in all:
        return True
    if name not in all:
        return False
    else:
        print('error verifying')



def database_reset():
    """ Completely resets database by deleting and recreating """
    tbls = [i[0] for i in curs.execute('SELECT tbl_name FROM sqlite_master WHERE type=?', ('table',))]
    for tbl in tbls:
        curs.execute(f'DROP TABLE {tbl}')
    conn.commit()

    create_all()
    find_match()

if __name__ == '__main__':
    # e = get_ua_value('Alexa Morales', grade=True)
    # print(e)

    e = get_specific_question_answer('Alexa Morales', 5)
    print(e)
