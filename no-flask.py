import database


match_data = database.get_all_best_matches()
match_details = database.get_match_details(match_data)

print('Name | Match | Match Score')
for line in match_data:
    print(line)