#  Copyright 2008-2011 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from robot.common import Statistics
from robot.errors import DataError
from robot.output import LOGGER
from robot.result.builders import ResultFromXML as RFX
from robot.result.serializer import RebotXMLWriter
from robot import utils

from robot.reporting.xunitwriter import XUnitWriter
from robot.reporting.builders import LogBuilder, ReportBuilder, XUnitBuilder, OutputBuilder
from robot.reporting.outputparser import OutputParser


class ResultWriter(object):

    def __init__(self, settings):
        self.settings = settings
        self._xml_result = None
        self._execution_result = None
        self._data_model = None
        self._data_sources = []

    @property
    def data_model(self):
        if self._data_model is None:
            parser = OutputParser(self.settings['Log'], self.settings['SplitLog'])
            self._data_model = parser.parse(self._data_sources[0])
        return self._data_model

    @property
    def result_from_xml(self):
        if self._xml_result is None:
            self._execution_result = RFX(*self._data_sources)
            opts = self._create_opts()
            self._execution_result.configure(status_rc=not self.settings['NoStatusRC'], **opts)
            self._xml_result = ResultFromXML(self._execution_result, self.settings)
        return self._xml_result

    def _create_opts(self):
        opts = {}
        for opt_name, settings_name in [
            ('name', 'Name'), ('doc', 'Doc'), ('metadata', 'Metadata'),
            ('set_tags', 'SetTag'), ('include_tags', 'Include'),
            ('exclude_tags', 'Exclude'), ('include_suites', 'SuiteNames'),
            ('include_tests', 'TestNames'), ('remove_keywords', 'RemoveKeywords'),
            ('log_level', 'LogLevel'), ('critical', 'Critical'),
            ('noncritical', 'NonCritical'), ('starttime', 'StartTime'),
            ('endtime', 'EndTime')
            ]:
            opts[opt_name] = self.settings[settings_name]

        opts['metadata'] = dict(opts['metadata'])
        return opts


    def write_robot_results(self, data_source):
        self._data_sources = [data_source]
        LogBuilder(self).build()
        ReportBuilder(self).build()
        XUnitBuilder(self).build()

    def write_rebot_results(self, *data_sources):
        self._data_sources = data_sources
        builder = OutputBuilder(self)
        self.write_robot_results(builder.build())
        builder.finalize()
        return self._execution_result


class ResultFromXML(object):

    def __init__(self, execution_result, settings=None):
        self.result = execution_result
        self.suite = execution_result.suite
        self.exec_errors = execution_result.errors
        if settings:
            params = (settings['SuiteStatLevel'], settings['TagStatInclude'],
                      settings['TagStatExclude'], settings['TagStatCombine'],
                      settings['TagDoc'], settings['TagStatLink'])
        else:
            params = ()
        self.statistics = Statistics(self.suite, *params)
        self._generator = 'Robot'

    def serialize_output(self, path, log=True):
        if path == 'NONE':
            return
        serializer = RebotXMLWriter(path)
        self.result.visit(serializer)
        if log:
            LOGGER.output_file('Output', path)

    def serialize_xunit(self, path):
        if path == 'NONE':
            return
        serializer = XUnitWriter(path)
        try:
            self.suite.visit(serializer)
        except:
            raise DataError("Writing XUnit result file '%s' failed: %s" %
                            (path, utils.get_error_message()))
        finally:
            serializer.close()
        LOGGER.output_file('XUnit', path)

