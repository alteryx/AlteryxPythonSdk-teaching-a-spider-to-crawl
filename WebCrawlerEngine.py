"""
AyxPlugin (required) has-a IncomingInterface (optional).
Although defining IncomingInterface is optional, the interface methods are
    needed if an upstream tool exists.
"""

import AlteryxPythonSDK as Sdk
import xml.etree.ElementTree as Et
import csv
import os, sys
npath = os.path.abspath(__file__)
sys.path.append(os.path.join(os.path.dirname(npath), "Patches"))
#import run_patch

import subprocess
def RunPatch():
    if os.path.exists(os.path.join(
        os.path.dirname(npath), "Patches", "PATCHED")):
        return # only need to patch once and for all
    proc = subprocess.Popen([os.path.join(
        os.path.dirname(npath), "Scripts", "python.exe")
                      , os.path.join(
                          os.path.dirname(npath), "Patches", "run_patch.py")]
                      , creationflags=subprocess.CREATE_NEW_CONSOLE)
    sout, serr = proc.communicate()
    file = open(os.path.join(
        os.path.dirname(npath), "Patches", "PATCHED"), "w")
    file.close()

def LaunchProcess():
    RunPatch()
    proc = subprocess.Popen([os.path.join(
        os.path.dirname(npath), "Scripts", "scrapy.exe")
                      , "runspider", "-s USER_AGENT=\"Mozilla/5.0 "
                      "(Windows NT 6.2; WOW64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36\""
                      , "-o %s" % os.path.join(
                          os.path.dirname(npath), "Scripts", "ourfirstscraper",
                          "reddit.csv")
                      , os.path.join(
                          os.path.dirname(npath), "Scripts", "ourfirstscraper",
                          "ourfirstscraper", "spiders", "redditbot.py")]
                      , creationflags=subprocess.CREATE_NEW_CONSOLE)
    sout, serr = proc.communicate()

class AyxPlugin:
    """
    Implements the plugin interface methods, to be utilized by the Alteryx
        engine to communicate with this plugin.
    Prefixed with "pi", the Alteryx engine will expect the below five interface
        methods to be defined.
    """

    def __init__(self, n_tool_id: int, alteryx_engine: object,
            output_anchor_mgr: object):
        """
        Constructor is called whenever the Alteryx engine wants to instantiate
            an instance of this plugin.
        :param n_tool_id: The assigned unique identification for a tool
            instance.
        :param alteryx_engine: Provides an interface into the Alteryx engine.
        :param output_anchor_mgr: A helper that wraps the outgoing connections
            for a plugin.
        """

        # Default properties
        self.n_tool_id = n_tool_id
        self.alteryx_engine = alteryx_engine
        self.output_anchor_mgr = output_anchor_mgr

        # Custom properties
        self.file_path = ''
        self.is_initialized = True
        self.output_anchor = None

    def pi_init(self, str_xml: str):
        """
        Handles extracting user-entered file name, and input data verification.
        Called when the Alteryx engine is ready to provide the tool
            configuration from the GUI.
        :param str_xml: The raw XML from the GUI.
        """

        # Getting the user-entered file name string from the GUI, and the 
        #   output anchor from the XML file.
        self.file_path = os.path.join(
            os.path.dirname(npath), "Scripts", "ourfirstscraper", "reddit.csv")
        self.output_anchor = self.output_anchor_mgr.get_output_anchor('Output')
        self.is_initialized = True

    def pi_add_incoming_connection(self, str_type: str, str_name: str
            ) -> object:
        """
        The IncomingInterface objects are instantiated here, one object per
            incoming connection, however since this tool does not accept an
            incoming connection, instantiation is not needed and "ii" methods
            won't be called.
        Called when the Alteryx engine is attempting to add an incoming data
            connection.
        :param str_type: The name of the input connection anchor, defined in
            the Config.xml file.
        :param str_name: The name of the wire, defined by the workflow author.
        :return: self.
        """

        return self

    def pi_add_outgoing_connection(self, str_name: str) -> bool:
        """
        Called when the Alteryx engine is attempting to add an outgoing data
            connection.
        :param str_name: The name of the output connection anchor, defined in
            the Config.xml file.
        :return: True signifies that the connection is accepted.
        """

        return True

    def crawl_spider(self):
        # delete any previous results, otherwise it appends to any existing
        #   results
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        LaunchProcess()

    def pi_push_all_records(self, n_record_limit: int) -> bool:
        """
        Handles pushing records out to downstream tool(s).
        Called when a tool has no incoming data connection.
        :param n_record_limit: Set it to <0 for no limit, 0 for no records, and
            >0 to specify the number of records.
        :return: False if there are issues with the input data or if the
            workflow isn't being ran, otherwise True.
        """

        if not self.is_initialized:
            return False

        if (self.alteryx_engine.get_init_var(self.n_tool_id, 'UpdateOnly')
            == 'True'):
            return False
        # crawl the spider
        self.crawl_spider()

        # Reading in the target file.
        file_reader, total_records = self.get_data(self.file_path, 
                                                    n_record_limit)
        # Building out the outgoing record layout.
        record_info_out = self.build_record_info_out(file_reader)
        # Lets the downstream tools know of the outgoing record metadata.
        self.output_anchor.init(record_info_out)
        # Creating a new record_creator for the new data.
        record_creator = record_info_out.construct_record_creator()

        for record in enumerate(file_reader):
            record_index = record[0]
            record_data = record[1]
            for field in enumerate(record_data):
                field_index = field[0]
                field_data = field[1]
                record_field = record_info_out[field_index]
                record_field.set_from_string(record_creator, field_data)
            # Asking for a record to push downstream
            out_record = record_creator.finalize_record()
            # False: completed connections will automatically close.
            self.output_anchor.push_record(out_record, False)
            # Not the best way to let the downstream tool know of this tool's
            #   progress, normally one would use a timer.
            if record_index % max(round(total_records * .30, 0), 1.0) == 0:
                self.output_anchor.update_progress(record_index
                                                    / float(total_records))
            # Resets the variable length data to 0 bytes (default) to prevent
            #   unexpected results.
            record_creator.reset()

        self.alteryx_engine.output_message(self.n_tool_id,
                                            Sdk.EngineMessageType.info,
                                            str(total_records)
                                            + ' records were read from '
                                            + self.file_path)
        self.output_anchor.close()  # Close outgoing connections.
        return True

    def pi_close(self, b_has_errors: bool):
        """
        Called after all records have been processed.
        :param b_has_errors: Set to true to not do the final processing.
        """

        # Checks whether connections were properly closed.
        self.output_anchor.assert_close()

    @staticmethod
    def is_csv(file_path: str):
        """
        A non-interface helper for pi_init() that is responsible for
            determining whether file is csv or not.
        :param file_path: The file path entered by the user.
        :return: False if the string literal entered for the file extension is
            not csv, otherwise True.
        """

        file_extension = os.path.splitext(file_path)[1]
        if file_extension.lower() == '.csv':
            return True
        return False

    @staticmethod
    def get_data(file_path: str, n_record_limit: int):
        """
        A non-interface helper for pi_push_all_records() that prepares the csv
            file reader.
        :param file_path: The file path entered by the user.
        :return: The name for csv file reader and the number of rows coming in.
        """

        file_object = open(file_path, 'r', encoding='utf-8')
        file_reader = csv.reader(file_object)
        # Disregard field names
        total_records = min(sum(1 for record in file_object) - 1,
                            n_record_limit)
        file_object.seek(0)
        return file_reader, total_records

    def build_record_info_out(self, file_reader: iter):
        """
        A non-interface helper for pi_push_all_records() responsible for
            creating the outgoing record layout.
        :param file_reader: The name for csv file reader.
        :return: The outgoing record layout, otherwise nothing.
        """

        # A fresh record info object for outgoing records.
        record_info_out = Sdk.RecordInfo(self.alteryx_engine)
        try:  # Add metadata info that is passed to tools downstream.
            for field in next(file_reader):
                record_info_out.add_field(field, Sdk.FieldType.v_wstring, 254,
                                            0, 'File: ' + self.file_path, '')
        except UnicodeError:
            self.display_error_msg('Must be a UTF-8 file')
        return record_info_out

    def display_error_msg(self, msg_string: str):
        """
        A non-interface method, that is responsible for displaying the relevant
            error message in Designer.
        :param msg_string: The custom error message.
        """

        self.is_initialized = False
        self.alteryx_engine.output_message(self.n_tool_id,
                                            Sdk.EngineMessageType.error,
                                            self.xmsg(msg_string))

    def xmsg(self, msg_string: str):
        """
        A non-interface, non-operational placeholder for the eventual
            localization of predefined user-facing strings.
        :param msg_string: The user-facing string.
        :return: msg_string
        """

        return msg_string


class IncomingInterface:
    """
    This optional class is returned by pi_add_incoming_connection, and it
        implements the incoming interface methods, to be utilized by the
        Alteryx engine to communicate with a plugin when processing an
        incoming connection.
    Prefixed with "ii", the Alteryx engine will expect the below four
        interface methods to be defined.
    """

    def __init__(self, parent: object):
        """
        Constructor for IncomingInterface.
        :param parent: AyxPlugin
        """

        pass

    def ii_init(self, record_info_in: object) -> bool:
        """
        Called to report changes of the incoming connection's record metadata
            to the Alteryx engine.
        :param record_info_in: A RecordInfo object for the incoming
            connection's fields.
        """

        pass

    def ii_push_record(self, in_record: object) -> bool:
        """
        Called when an input record is being sent to the plugin.
        :param in_record: The data for the incoming record.
        """

        pass

    def ii_update_progress(self, d_percent: float):
        """
        Called by the upstream tool to report what percentage of records have
            been pushed.
        :param d_percent: Value between 0.0 and 1.0.
        """

        pass

    def ii_close(self):
        """
        Called when the incoming connection has finished passing all of its
            records.
        """

        pass
