import csv
import argparse
import os
import sys

def make_dictionary(csvreader, exclude_groups=[]):
    required_fields = [ "Place", "Lane", "Times", "Speed (MPH)",\
            "Last Name", "First Name", "Car#", "Group" ]
    #read lines until we find our required fields
    row = next(csvreader, None)
    while row != None:
        #print(row)
        sanitized_row = sanitize_row(row)
        found_all_fields = True
        for field in required_fields:
            if not field in sanitized_row:
                found_all_fields = False
                break
        if found_all_fields:
            #print("Found header line")
            break
        row = next(csvreader, None)
    if row == None:
        raise Exception("Improperly formatted CSV")
    sanitized_row = sanitize_row(row)[1:] #remove the heat name column
    custom_field = None
    for column in sanitized_row:
        if not column in required_fields:
            custom_field = column
            break
    
    if custom_field == None:
        raise Exception("Unable to determine custom field name")

    #print("Custom field is '%s'" % custom_field)

    row = next(csvreader, None)
    heat = None
    group = None
    category_dict = {}
    group_list = []
    while row != None:
        if row[0]:
            heat = int(row[0])
            group = row[1]
            group_list.append(group)
        if group in exclude_groups:
            row = next(csvreader, None)
            continue
        category = row[6]
        if not category in category_dict:
            category_entry = {}
            category_dict[category] = category_entry
        else:
            category_entry = category_dict[category]
        if not group in category_entry:
            group_entry = {}
            category_entry[group] = group_entry
        else:
            group_entry = category_entry[group]
        car_num = int(row[5])
        if not car_num in group_entry:
            car_entry = { "_meta" : { "lastname" : row[3], "firstname" : row[4] }}
            car_entry["heats"] = []
            group_entry[car_num] = car_entry
        else:
            car_entry = group_entry[car_num]
        heat_dict = { "heat" : heat, "time" : float(row[7]), "place" : int(row[8]) }
        car_entry["heats"].append(heat_dict)


        row = next(csvreader, None)
    for excluded in exclude_groups:
        if excluded not in group_list:
            raise Exception("Cannot exclude '%s', no such group" % excluded)
    return category_dict    

def make_ranking_dict(race_dict, dropped_cars=1, cars_per_group=1, lane_count=4):
    ranking_dict = {}
    group_count = 0
    group_list = []
    for category, category_dict in race_dict.items():
        if group_count < len(category_dict):
            group_count = len(category_dict)
        for group in category_dict:
            if not group in group_list:
                group_list.append(group)

    for category, category_dict in race_dict.items():
        if len(category_dict) < group_count - dropped_cars:
            continue #disqualified
        if category not in ranking_dict:
            category_result_dict = {}
            ranking_dict[category] = category_result_dict
        else:
            category_result_dict = ranking_dict[category]
        #for group, group_dict in category_dict.items():
        for group in group_list:
            if group in category_dict:
                group_dict = category_dict[group]
            else:
                category_result_dict[group] = 9.9 * lane_count
                continue
            if len(group_dict) != cars_per_group:
                raise Exception("Found %s cars in group %s: Expected %s" %\
                        (len(group_dict), group, cars_per_group))
            cum_time = 0.0
            for car, car_dict in group_dict.items():
                for heat in car_dict["heats"]:
                    cum_time = cum_time + heat["time"]
            category_result_dict[group] = cum_time

    for category, category_result_dict in ranking_dict.items():
        time_list = list(category_result_dict.values())
        time_list.sort()
        raw_total = 0.0
        adjusted_total = 0.0
        for i in range(len(time_list)):
            raw_total = raw_total + time_list[i]
            if i < (group_count - dropped_cars):
                adjusted_total = adjusted_total + time_list[i]
        calc_dict = {
                "raw_total" : raw_total,
                "adjusted_total" : adjusted_total
        }
        category_result_dict["totals"] = calc_dict

    return ranking_dict


def get_ranks(csv_file_path, exclude_groups=[], dropped_cars=1, cars_per_group=1, lanes=4):
    print("Excluding groups: %s" % ", ".join(exclude_groups))
    print("Dropping the worst %s group(s)" % dropped_cars)
    print("Each group contains %s car(s)" % cars_per_group)
    print("Each car runs on %s lanes\n" % lanes)
    with open(csv_file_path, newline='') as csv_file:
        reader = csv.reader(csv_file)
        race_dict = make_dictionary(reader, exclude_groups)
        rank_dict = make_ranking_dict(race_dict, dropped_cars, cars_per_group, lanes)
        rank_keys = list(rank_dict.keys())
        sorted_rank_keys = sorted(rank_keys, key=lambda key:rank_dict[key]['totals']['adjusted_total'])
        for i in range(len(sorted_rank_keys)):
            key = sorted_rank_keys[i]
            print("#%s %s, cumulative time: %s seconds" %\
                    (i + 1, key, rank_dict[key]['totals']['adjusted_total']))
            print(rank_dict[key])
            print("\n")
            

def sanitize_row(line):
    return [ " ".join(entry.split()) for entry in line ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a CSV file from GPRM v17+ to calculate team standings")
    parser.add_argument('--drop', type=int, default=1, help="The number of groups to drop the worst scores of")
    parser.add_argument('--exclude', default="", help="A comma-separated list of groups to exclude from the calculations")
    parser.add_argument('--lanes', type=int, default=4, help="The number of lanes on the track")
    parser.add_argument('csv_path')
    args = parser.parse_args()
    if(args.exclude):
        exclude_list = args.exclude.split(",")
    else:
        exclude_list = []
    try:
        get_ranks(os.path.abspath(args.csv_path), exclude_list, args.drop, 1, args.lanes)
    except Exception as e:
        sys.stderr.write("Error: %s\n" % e)




