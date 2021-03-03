"""Module for parsing .csv stimuli-parameter files"""

from collections import namedtuple
import os
from parse import *

#CSV_FILENAME = '../../stimuli-params/full.csv'

Entry = namedtuple("Entry", "sheet_id table_id entry_id link start end codec t_init rul rdl dul ddl")

file = []


def set_file(file_path, is_relative_path):
    """Loads the specified file globally"""
    global file
    if is_relative_path:
        file_dir = os.path.dirname(os.path.realpath('__file__'))
        file_path = os.path.join(file_dir, file_path)
        file = open(file_path).read().split("\n")
    else:
        file = open(file_path).read().split("\n")


def get_sheet_ids():
    """Returns a list of all sheet id's within the file"""
    sheet_ids = []

    next_line_has_id = False

    for line in file:

        if next_line_has_id:
            next_line_has_id = False
            sheet_id = line.split(";")[0].split("-")[0]
            if sheet_id not in sheet_ids:
                sheet_ids.append(sheet_id)

        if line.startswith("Stimulus-ID"):
            next_line_has_id = True

    return sheet_ids


def get_table_ids(sheet_id):
    """Returns a list of all table id's belonging to the specified sheet"""
    table_ids = []

    next_line_has_id = False

    for line in file:

        if next_line_has_id:
            next_line_has_id = False
            if line.split(";")[0].split("-")[0] == sheet_id:
                id = line.split(";")[0].split("-")[1]
                if id not in table_ids:
                    table_ids.append(line.split(";")[0].split("-")[1])

        if line.startswith("Stimulus-ID"):
            next_line_has_id = True

    return table_ids


def get_entry_ids(sheet_id, table_id):
    "Returns a list of the entry id's belonging to the specified sheet"
    entry_ids = []

    for line in file:
        if line.startswith(f"{sheet_id}-{table_id}"):
            search_string = f"{sheet_id}-{table_id}-" + "{}"
            id = search(search_string, line)[0]
            if id not in entry_ids:
                entry_ids.append(id)

    return entry_ids


def get_link(sheet_id, table_id, entry_id):
    """Returns the link belonging to the entry"""
    if sheet_id == "VS":

        link = None
        link_found = False

        for line in file:

            if link_found:
                if line.startswith(f"{sheet_id}-{table_id}"):
                    return link

            if line.startswith("Resolution"):
                link = line.split(";")[1]
                link_found = True

        return ""

    if sheet_id == "WB":
        table_found = False
        for line in file:

            if line.startswith(f"{sheet_id}-{table_id}"):
                table_found = True

            if table_found:
                if "https:" in line:
                    result = search("https:{})", line)
                    if result is None:
                        result = search("https:{};", line)
                    return "https:" + result[0]
        return


def get_start(sheet_id, table_id, entry_id):
    """Returns the video start time of an entry"""
    if sheet_id == "WB":
        return None

    start_found = False
    start = None

    for line in file:

        if start_found:
            if line.startswith(f"{sheet_id}-{table_id}"):
                return start

        if line.startswith("Excerpt"):
            if "appr." in line:
                search_string_start = "appr. {} ("
            else:
                search_string_start = "from {} ("
            if "(h:min:sec)" in line:
                append = ""
            else:
                append = "00:"
            start = append + str(search(search_string_start, line)[0])
            start_found = True

    return None


def get_end(sheet_id, table_id, entry_id):
    """Returns the video end time of an entry"""
    if sheet_id == "WB":
        return None

    end_found = False
    end = None

    for line in file:

        if end_found:
            if line.startswith(f"{sheet_id}-{table_id}"):
                return end
            if line.startswith(f"{sheet_id}"):
                end_found = False

        if line.startswith("Excerpt"):
            if "h:min" in line:
                append = ""
            else:
                append = "00:"
            end = str(append + search(" to {} (", line)[0])
            end_found = True

    return None


def get_codec(sheet_id, table_id, entry_id):
    """Returns the codec to be used for the entry"""
    if sheet_id == "WB":
        return None

    codec_column = 0
    for line in file:

        if line.startswith("Stimulus-ID"):
            i = 0
            for s in line.split(";"):
                if s == "Codec":
                    codec_column = i
                    break
                i += 1

        if line.startswith(f"{sheet_id}-{table_id}-{entry_id}") and codec_column != 0:
            return line.split(";")[codec_column]


def get_parameters(sheet_id, table_id, entry_id):
    """Returns a list of the netem parameteres for the entry: [t_init, rul, rdl, dul, ddl]"""
    for line in file:
        if line.startswith(f"{sheet_id}-{table_id}-{entry_id}"):
            return line.split(";")[2:7]


def get_entries(sheet_id_filter=None, table_id_filter=None):
    """Returns a list of all entries matching the filter as named tuples"""
    entries = []

    for sheet_id in get_sheet_ids():

        if sheet_id_filter is not None and sheet_id != sheet_id_filter:
            continue

        for table_id in get_table_ids(sheet_id):

            if table_id_filter is not None and table_id is not table_id_filter:
                continue

            for entry_id in get_entry_ids(sheet_id, table_id):
                entries.append(Entry(sheet_id,
                                     table_id,
                                     entry_id,
                                     get_link(sheet_id, table_id, entry_id),
                                     get_start(sheet_id, table_id, entry_id),
                                     get_end(sheet_id, table_id, entry_id),
                                     get_codec(sheet_id, table_id, entry_id),
                                     *get_parameters(sheet_id, table_id, entry_id)))
    return entries
