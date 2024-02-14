import sqlite3 as sl
import traceback

import utils

db = 'cqr.db'
conn = sl.connect(db, check_same_thread=False)
curs = conn.cursor()


UA_QS = [f'Q{num}' for num in range(1, 16)]
UA_HDRS = ['Name', 'Grade', 'Class_Teacher'] + UA_QS


class DataHandling():
    def __init__(self, submission_entry:list) -> None:
        pass




def user_answers_table():
    """ General table essentially mimicing the spreadsheet, but with encoded answers for the MC answers """
    
    # semi lazy way to create headers for all questions without manually typing it out
    col_fmt1 = ' TEXT, '.join(UA_HDRS)
    col_fmt2 = col_fmt1 + ' TEXT' # ensures last parameter also has a data_type designation 

    curs.execute(f'CREATE TABLE IF NOT EXISTS user_answers({col_fmt2})')

    # fill table
    data = utils.extract_answers()
    stmt_fill = ','.join(UA_HDRS)
    stmt_qm_fill = '?,'*18

    for submission in data:
        ans_codes = _fill_gen_table_ans_mapping(submission[3:]) # need to start from 3rd index since first 3 columns are unique entries

        curs.execute(f'INSERT INTO user_answers({stmt_fill}) VALUES({stmt_qm_fill[:-1]})', (submission[0].title(), submission[1], submission[2], ans_codes[0], ans_codes[1], ans_codes[2], ans_codes[3], ans_codes[4], ans_codes[5], ans_codes[6], ans_codes[7], ans_codes[8], ans_codes[9], ans_codes[10], ans_codes[11], ans_codes[12], ans_codes[13], ans_codes[14]))
    conn.commit()
    return True

def questions_code_table():
    """ Mapping source of answers to questions """
    curs.execute('CREATE TABLE IF NOT EXISTS answer_mapping(id TEXT PRIMARY KEY, question VARCHAR(3), answer TEXT)')

    data = utils.extract_answers()
    # in each row, run through all 15 questions and upload answer once to database, with a designated code, ignoring future identical entries

    qa_maps = {f'Q{num}':[] for num in range(1, 16)}
    for submission in data:
        for num in range(1, 16):
            corrected_idx = num + 2
            if submission[corrected_idx] not in qa_maps[f'Q{num}']:
                qa_maps[f'Q{num}'].append(submission[corrected_idx])
    
    # iterate through all answer possibilities, generate unique IDs, then insert to DB
    # first iterate through all questions (all multiple choice answers)    
    for mc_ans in qa_maps:
        mca_enum = [i for i in enumerate(qa_maps[mc_ans])]
        # then iterate through each answer possibility for each question
        # this list comprehension creates an ID by combining the question number and answer index, then tuples this with the question number
        # theoretically should be removing empty strings with the != '' portion, but it didn't do it and I didn't feel the need to fix it
        qa_maps[mc_ans] = [(f'{mc_ans}.{ans_pos[0]}', ans_pos[1]) for ans_pos in mca_enum if ans_pos != '']    

    # the final double for loop to officially insert map into DB table
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

def _get_class(name:str):
    return [i[0] for i in curs.execute('SELECT Class_Teacher FROM user_answers WHERE Name=?', (name,))][0]



def find_match():
    """ Finds match for given submitter, but returns SubmissionComparison object for more versatile manipulation """

    all_subs = [i[0] for i in curs.execute('SELECT Name FROM user_answers')]
    # print(f'allsubs: {all_subs}')
    
    # iterate through all submissions
    # for each submission, compare with answers with all other submissions
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



    def compare_all(self):
        """ Executive for comparing against all other submitters """
        for subs in self.all_subs:
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


if __name__ == '__main__':
    d = _get_class("Alexa Morales")
    print(d)
    
