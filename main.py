import os
from flask import (Flask, redirect, render_template, request, send_file, session, url_for)

import database

# if database.create_all():
#     print('done')


app = Flask(__name__)

@app.route('/')
def home():
    match_data = database.get_all_best_matches()
    match_details = database.get_match_details(match_data)

    return render_template('home.html', all_matches=match_data, m_details=match_details)


# def all_best_matches():
#     """
#     Finds best match of each submitted entry

#     database.find_match() returns a Comparison Report Object, you can access the following attributes:
    
#         .submitter
#         .best_match
#         .sub_data
#         .best_match_data

#     """
#     all_matches = database.get_all_best_matches()
    

if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    app.run(debug=True)
