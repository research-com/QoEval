"""Module for parsing .csv stimuli-parameter files"""

# TODO: Refactor to reduce redundant code when detecting url, start, end, parameter names / named tuple

from collections import namedtuple
import os
from typing import List

import logging as log
from importlib_resources import files
from parse import search
from parse import log as parselog

Entry = namedtuple("Entry", "type_id table_id entry_id link start end codec t_init rul rdl dul ddl")
_PARAMETER_NAMES = ['t_init', 'rul', 'rdl', 'dul', 'ddl', 'stimulus', 'codec', 'dynamic', 'genbufn', 'genbuft']

file = []
file_loaded = False


def load_parameter_file(file_path):
    """
       Loads the specified file globally. If no file is specified it will load CSV_FILENAME.

       Reads the contents of the given file and saves it in the global variable "file" as a list of strings
       containing the lines of the file.

       Parameters
       ----------
       file_path : str, optional
            File path of the file to be loaded, default is the constant CSV_FILENAME

       """
    global file
    global file_loaded

    parselog.setLevel('WARNING')

    try:
        if os.path.isabs(file_path):
            file = open(file_path).read().split("\n")
        else:
            file_path = os.path.join("../", file_path)
            file = files('qoemu_pkg').joinpath(file_path).read_text().split("\n")
        file_loaded = True
        if not _is_correct_parameter_file():
            log.warning(f"Parameter file \"{file_path}\" is not fully parsable - some use-cases might not have valid "
                        f"parameter values. Please check the format of the csv file.")
    except FileNotFoundError:
        log.error(f"Parameter file \"{file_path}\" not found")
        raise FileNotFoundError


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


def get_table_ids(type_id):
    """
    Returns a list of the table id's belonging to the specified type

    The provided paramter file identifies each set of parameters with an ID in the following form
    "VS-B-4"
    The second part of this id corresponds to a table of parameters and is
    therefore called table_id in this module.

    Parameters
    ----------
    type_id : str
        The type id of which the entry id's should be returned.

    Returns
    -------
    *str
         Returns a list of all table id's belonging to the type

    """

    if not file_loaded:
        log.error("No file loaded")
        return

    table_ids = []

    for line in file:
        if line.startswith(f"{type_id}-"):
            search_string = f"{type_id}-" + "{}"
            id = search(search_string, line)[0]
            if id not in table_ids:
                table_ids.append(id)

    return table_ids


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

    if type_id == "VS" or type_id == "VSB":

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
    if type_id == "AL":
        table_found = False
        for line in file:

            if line.startswith(f"{type_id}-{table_id}"):
                table_found = True

            if table_found:
                if "app://" in line:
                    result = search("app://{})", line)
                    if result is None:
                        result = search("app://{};", line)
                    return result[0]
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
            return line.split(";")[codec_column].translate(str.maketrans('', '', '"'))


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
                The list of parameters: [t_init, rul, rdl, dul, ddl, stimulus, codec, dynamic, genbufn, genbuft]

            """
    if not file_loaded:
        log.error("No file loaded")
        return

    for line in file:
        if line.startswith(f"{type_id}-{table_id}-{entry_id}"):
            splitted_line = line.split(";")
            float_parameter_values_str = splitted_line[2:7]
            float_parameter_values = [float(i) for i in float_parameter_values_str]
            # evaluate string parameters
            str_parameter_values = splitted_line[7:10]
            # evaluate parameters for artificial buffer generation (VSB stimuli), if present
            if len(splitted_line) > 12:
                gen_parameter_values_str = splitted_line[10:12]
                gen_parameter_values_str = [_replace_empty_with_default(i, "0") for i in gen_parameter_values_str]
                gen_parameter_values = [float(i) for i in gen_parameter_values_str]
            else:
                gen_parameter_values = [0.0, 0.0]
            it_name = iter(_PARAMETER_NAMES)
            it_value = iter(float_parameter_values + str_parameter_values + gen_parameter_values)
            return dict(zip(it_name, it_value))


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


def export_entries(type_id: str, table_id: str, output_path: str, compact: bool = False):
    """
            Exports a parameter table as individual .csv file (e.g. for documentation purposes)

            :param str type_id :
                The type id of the requested entries
            :param str table_id :
                The table id of the requested entries
            :param str output_path :
                The path to the output file
            :param compact:
                If set to True, a compact format is used (for reports only)
            """
    if not file_loaded:
        log.error("No file loaded")
        return

    output_file = open(output_path, "w")

    nr_ids_to_be_written = len(get_entry_ids(type_id, table_id))

    is_header_written = False

    if compact:
        columns_to_be_removed = [1,7,12,13,14]
    else:
        columns_to_be_removed = []

    is_in_relevant_section = False

    for line in file:
        if line.startswith(f"Stimulus-ID"):
            if compact:
                header_line = line.replace("Stimulus-ID", "ID")
                header_line = _remove_columns(header_line, columns_to_be_removed)
            else:
                header_line = line

        if line.startswith(f"{type_id}-{table_id}-"):
            is_in_relevant_section = True
            if not is_header_written:
                output_file.write(header_line+"\n")
                is_header_written = True
            if compact:
                line = _remove_columns(line, columns_to_be_removed)
            nr_ids_to_be_written = nr_ids_to_be_written - 1

        if is_in_relevant_section and (not compact or line.startswith(f"{type_id}-{table_id}-")):
            output_file.write(line + "\n")

        if nr_ids_to_be_written < 1:
            break

    output_file.close()
    log.info(f"Exported {type_id}-{table_id} to {output_path}.")


def _is_correct_parameter_file() -> bool:
    status_ok = True
    all_type_ids = get_type_ids()
    for type_id in all_type_ids:
        all_table_ids = get_table_ids(type_id)
        for table_id in all_table_ids:
            all_entry_ids = get_entry_ids(type_id, table_id)
            for entry_id in all_entry_ids:
                try:
                    get_parameters(type_id, table_id, entry_id)
                    get_codec(type_id, table_id, entry_id)
                    get_link(type_id, table_id, entry_id)
                    get_start(type_id, table_id, entry_id)
                    get_end(type_id, table_id, entry_id)
                except ValueError as ve:
                    log.error(f"Error while parsing {type_id}-{table_id}-{entry_id} - {ve}")
                    status_ok = False

    return status_ok


def _remove_columns(csv_line: str, columns: List[int]) -> str:
    splitted_line = csv_line.split(";")
    columns.sort(reverse=True)
    for column in columns:
        if column < len(splitted_line):
            del splitted_line[column]
    return ";".join(splitted_line)

def _replace_empty_with_default(value: str, default_value: str):
    if not value or len(value) == 0:
        return default_value
    else:
        return value
