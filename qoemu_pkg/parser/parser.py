"""Module for parsing .csv stimuli-parameter files"""

# TODO: Refactor to reduce redundant code when detecting url, start, end

from collections import namedtuple
import os
from parse import *
import logging as log

CSV_FILENAME = '../../stimuli-params/full.csv'

Entry = namedtuple("Entry", "type_id table_id entry_id link start end codec t_init rul rdl dul ddl")

file = []
file_loaded = False


def load_parameter_file(file_path=CSV_FILENAME, is_relative_path=True):
    """
       Loads the specified file globally. If no file is specified it will load CSV_FILENAME.

       Reads the contents of the given file and saves it in the global variable "file" as a list of strings
       containing the lines of the file.

       Parameters
       ----------
       file_path : str, optional
            File path of the file to be loaded, default is the constant CSV_FILENAME
       is_relative_path : bool, optional
            True if the path is relative, default is True

       """
    global file
    global file_loaded
    try:
        if is_relative_path:
            file_dir = os.path.dirname(os.path.realpath('__file__'))
            file_path = os.path.join(file_dir, file_path)
            file = open(file_path).read().split("\n")
        else:
            file = open(file_path).read().split("\n")
        file_loaded = True
    except FileNotFoundError:
        log.error(f"Parameter file \"{file_path}\" not found")


def get_type_ids():
    """
        Returns a list of all type id's within the loaded file

        The provided parameter file identifies each set of parameters with an ID in the following form
        "VS-B-4"
        The first part of this id corresponds to the type of capture (Video Streaming/Web Browsing) and is
        therefore called type_id in this module.


        Returns
        -------
        *str
            A list of all type id's in the file

        """
    if not file_loaded:
        log.error("No file loaded")
        return

    type_ids = []

    next_line_has_id = False

    for line in file:

        if next_line_has_id:
            next_line_has_id = False
            type_id = line.split(";")[0].split("-")[0]
            if type_id not in type_ids:
                type_ids.append(type_id)

        if line.startswith("Stimulus-ID"):
            next_line_has_id = True

    return type_ids


def get_table_ids(type_id):
    """
            Returns a list of all table id's belonging to the specified type

            The provided paramter file identifies each set of parameters with an ID in the following form
            "VS-B-4"
            The second part of this id corresponds to a table of entries and is
            therefore called table_id in this module.

            Parameters
            ----------
            type_id : str
                The type id of which the table id's should be returned.

            Returns
            -------
            *str
                Returns a list of all table id's belonging to the specified type

            """

    if not file_loaded:
        log.error("No file loaded")
        return

    table_ids = []

    next_line_has_id = False

    for line in file:

        if next_line_has_id:
            next_line_has_id = False
            if line.split(";")[0].split("-")[0] == type_id:
                id = line.split(";")[0].split("-")[1]
                if id not in table_ids:
                    table_ids.append(line.split(";")[0].split("-")[1])

        if line.startswith("Stimulus-ID"):
            next_line_has_id = True

    return table_ids


def get_entry_ids(type_id, table_id):
    """
    Returns a list of the entry id's belonging to the specified type

    The provided paramter file identifies each set of parameters with an ID in the following form
    "VS-B-4"
    The third part of this id corresponds to an entry of parameters and is
    therefore called entry_id in this module.

    Parameters
    ----------
    type_id : str
        The type id of which the entry id's should be returned.
    table_id : str
        The table id of which the entry id's should be returned.

    Returns
    -------
    *str
         Returns a list of all entry id's belonging to the type and table

    """

    if not file_loaded:
        log.error("No file loaded")
        return

    entry_ids = []

    for line in file:
        if line.startswith(f"{type_id}-{table_id}"):
            search_string = f"{type_id}-{table_id}-" + "{}"
            id = search(search_string, line)[0]
            if id not in entry_ids:
                entry_ids.append(id)

    return entry_ids


def get_link(type_id, table_id, entry_id):
    """
        Returns the link belonging to the specified entry


        Parameters
        ----------
        type_id : str
            The type id of the entry
        table_id : str
            The table id of the entry
        entry_id : str
            The entry id of the entry

        Returns
        -------
        str
            The link belonging to the specified entry

        """
    if not file_loaded:
        log.error("No file loaded")
        return

    if type_id == "VS":

        link = None
        link_found = False

        for line in file:

            if link_found:
                if line.startswith(f"{type_id}-{table_id}"):
                    return link

            if line.startswith("Stimulus-ID"):
                # new table - previously detected link is invalid
                link = None
                link_found = False

            if line.startswith("Resolution"):
                link = line.split(";")[1]
                link_found = True

        return ""

    if type_id == "WB":
        table_found = False
        for line in file:

            if line.startswith(f"{type_id}-{table_id}"):
                table_found = True

            if table_found:
                if "https:" in line:
                    result = search("https:{})", line)
                    if result is None:
                        result = search("https:{};", line)
                    return "https:" + result[0]
        return


def get_start(type_id, table_id, entry_id):
    """
            Returns the video start time of the specified entry


            Parameters
            ----------
            type_id : str
                The type id of the entry
            table_id : str
                The table id of the entry
            entry_id : str
                The entry id of the entry

            Returns
            -------
            str
                The video start time belonging to the specified entry

            """
    if not file_loaded:
        log.error("No file loaded")
        return

    start_found = False
    start = None

    for line in file:

        if start_found:
            if line.startswith(f"{type_id}-{table_id}"):
                return start

        if line.startswith("Stimulus-ID"):
            # new table - previously detected start is invalid
            start = None
            start_found = False

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


def get_end(type_id, table_id, entry_id):
    """
            Returns the video end time of the specified entry


            Parameters
            ----------
            type_id : str
                The type id of the entry
            table_id : str
                The table id of the entry
            entry_id : str
                The entry id of the entry

            Returns
            -------
            str
                The video end time belonging to the specified entry

            """
    if not file_loaded:
        log.error("No file loaded")
        return

    end_found = False
    end = None

    for line in file:

        if end_found:
            if line.startswith(f"{type_id}-{table_id}"):
                return end
            if line.startswith(f"{type_id}"):
                end_found = False

        if line.startswith("Stimulus-ID"):
            # new table - previously detected end is invalid
            start = None
            start_found = False

        if line.startswith("Excerpt"):
            if "h:min" in line:
                append = ""
            else:
                append = "00:"
            end = str(append + search(" to {} (", line)[0])
            end_found = True

    return None


def get_codec(type_id, table_id, entry_id):
    """
            Returns the codec of the specified entry


            Parameters
            ----------
            type_id : str
                The type id of the entry
            table_id : str
                The table id of the entry
            entry_id : str
                The entry id of the entry

            Returns
            -------
            str
                The codec belonging to the specified entry

            """
    if not file_loaded:
        log.error("No file loaded")
        return

    if type_id == "WB":
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

        if line.startswith(f"{type_id}-{table_id}-{entry_id}") and codec_column != 0:
            return line.split(";")[codec_column]


def get_parameters(type_id, table_id, entry_id):
    """
            Returns the list of netem parameters of the specified entry


            Parameters
            ----------
            type_id : str
                The type id of the entry
            table_id : str
                The table id of the entry
            entry_id : str
                The entry id of the entry

            Returns
            -------
            *str
                The list of parameters: [t_init, rul, rdl, dul, ddl]

            """
    if not file_loaded:
        log.error("No file loaded")
        return

    parameter_names = ['t_init', 'rul', 'rdl', 'dul', 'ddl', 'stimulus', 'codec', 'dynamic']

    for line in file:
        if line.startswith(f"{type_id}-{table_id}-{entry_id}"):
            float_parameter_values_str = line.split(";")[2:7]
            float_parameter_values = [float(i) for i in float_parameter_values_str]
            # evaluate string parameters
            str_parameter_values = line.split(";")[7:10]
            it_name = iter(parameter_names)
            it_value = iter(float_parameter_values + str_parameter_values)
            return dict(zip(it_name,it_value))


def get_entries(type_id_filter=None, table_id_filter=None):
    """
            Returns a list of named tuples, each tuple representing one entry matching the filter specified.

            The named tuples returned are defined as following:
             ("Entry", "type_id table_id entry_id link start end codec t_init rul rdl dul ddl")

            Parameters
            ----------
            type_id_filter : str, optional
                The type id of the requested entries
            table_id_filter : str, optional
                The table id of the requested entries

            Returns
            -------
            *Entry
                A list of named tuples, which represent one entry each, in the following form:
                namedtuple("Entry", "type_id table_id entry_id link start end codec t_init rul rdl dul ddl")

            """
    if not file_loaded:
        log.error("No file loaded")
        return []

    entries = []

    for type_id in get_type_ids():

        if type_id_filter is not None and type_id != type_id_filter:
            continue

        for table_id in get_table_ids(type_id):

            if table_id_filter is not None and table_id is not table_id_filter:
                continue

            for entry_id in get_entry_ids(type_id, table_id):
                entries.append(Entry(type_id,
                                     table_id,
                                     entry_id,
                                     get_link(type_id, table_id, entry_id),
                                     get_start(type_id, table_id, entry_id),
                                     get_end(type_id, table_id, entry_id),
                                     get_codec(type_id, table_id, entry_id),
                                     *get_parameters(type_id, table_id, entry_id)))
    return entries
