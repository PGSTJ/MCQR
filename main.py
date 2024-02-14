import database

# if database.create_all():
#     print('done')

def best_matches():
    """
    Finds best match of each submitted entry

    database.find

    """
    all_matches = database.find_match()
    e = [matches.submitter for matches in all_matches]
    

if __name__ == '__main__':
    matches()