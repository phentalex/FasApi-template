import os
import json
import csv


def save_to_json(data, work_id, path):
    if not os.path.exists(path):
        os.makedirs(JSON_SAVE_PATH)
    json_filename = os.path.join(path, f"{work_id}.json")
    if not os.path.exists(json_filename):
        with open(json_filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)


def append_to_csv(data, work_id, path):
    if not os.path.exists(path):
        os.makedirs(path)
    csv_filename = os.path.join(path, 'works.csv')

    file_exists = os.path.isfile(csv_filename)

    if file_exists:
        with open(csv_filename, 'r', newline='', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            if any(row[0] == work_id for row in reader):
                return

    with open(csv_filename, 'a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(data.keys())

        writer.writerow([work_id, *data.values()])