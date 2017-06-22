# The MIT License (MIT)
# Copyright (c) 2014-2017 University of Bristol
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.
"""
Main HyperStream class
"""

from . import ChannelManager, HyperStreamConfig, PlateManager, WorkflowManager
from . import Client, Workflow
from version import __version__
from utils import HyperStreamLogger, ToolContainer, PluginContainer, PluginWrapper

import logging


class HyperStream(object):
    """ HyperStream class

    This class can be instantiated simply with hyperstream = HyperStream() for
    default operation
    """
    def __init__(self, loglevel=logging.DEBUG, file_logger=True,
                 console_logger=True, mqtt_logger=None):
        """Initialise the HyperStream class.

        This starts the logger, loads the config files, connects to the main
        mongodb, and initialises the managers (channels, plates, workflows).

        :type console_logger: bool | dict | None
        :type file_logger: bool | dict | None
        :type mqtt_logger: dict | None
        :param loglevel: The default logging level
        :param file_logger: Whether to use a file logger. Either specify "True"
        in which case defaults are used, otherwise a dict optionally containing
        path, filename, loglevel
        :param console_logger: The console logger. Either specify "True" in
        which case defaults are used, otherwise a dict optionally containing
        loglevel
        :param mqtt_logger: Dict containing mqtt server, topic, and optionally
        loglevel
        """
<<<<<<< HEAD
        self.parameters = dict(
            loglevel=loglevel,
            file_logger=file_logger,
            console_logger=console_logger,
            mqtt_logger=mqtt_logger
        )

        self.logger = HyperStreamLogger(
            default_loglevel=loglevel, file_logger=file_logger, console_logger=console_logger, mqtt_logger=mqtt_logger)
=======
        self.logger = HyperStreamLogger(default_loglevel=loglevel,
                                        file_logger=file_logger,
                                        console_logger=console_logger,
                                        mqtt_logger=mqtt_logger)
>>>>>>> 90776b1fdf06bab5d8154e31ad468797c19e95dc
        self.config = HyperStreamConfig()
        self.client = Client(self.config.mongo)

        # Define some managers
        self.channel_manager = ChannelManager(self.config.plugins)
        self.plate_manager = PlateManager()
<<<<<<< HEAD
        self.workflow_manager = WorkflowManager(channel_manager=self.channel_manager, plate_manager=self.plate_manager)
        self.plugins = PluginContainer()
        self.populate_tools()
=======
        self.workflow_manager = WorkflowManager(
                channel_manager=self.channel_manager,
                plate_manager=self.plate_manager)
>>>>>>> 90776b1fdf06bab5d8154e31ad468797c19e95dc

    def __repr__(self):
        name = self.__class__.__name__
        # values = ", ".join("{}={}".format(k, repr(v)) for k, v in sorted(self.__dict__.items())
        #                    if k[0] != "_" and not k.endswith('manager'))
        values = ", ".join("{}={}".format(k, v) for k, v in self.parameters.items())
        return "{}({})".format(name, values)

    def __str__(self):
        return ("HyperStream version {version}, connected to "
                "mongodb://{host}:{port}/{db}").format(
                    version=__version__,
                    host=self.config.mongo['host'],
                    port=self.config.mongo['port'],
                    db=self.config.mongo['db']
        )

    def __del__(self):
        self._cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._cleanup()
        return self

    def _cleanup(self):
        """
        Clean-up operations
        """
        for handler in list(self.logger.root_logger.handlers):
            self.logger.root_logger.removeHandler(handler)
            handler.flush()
            handler.close()

    def create_workflow(self, workflow_id, name, owner, description,
                        online=False, monitor=False):
        """Create a new workflow.

        Simple wrapper for creating a workflow and adding it to the workflow
        manager.

        :param workflow_id: The workflow id
        :param name: The workflow name
        :param owner: The owner/creator of the workflow
        :param description: A human readable description
        :param online: Whether this workflow should be executed by the online
        engine
        :param monitor:
        :return: The workflow
        """
        w = Workflow(
            channels=self.channel_manager,
            plate_manager=self.plate_manager,
            workflow_id=workflow_id,
            name=name,
            owner=owner,
            description=description,
            online=online,
            monitor=monitor
        )

        self.workflow_manager.add_workflow(w)

        return w

    def populate_tools(self):
        for tool_channel in self.channel_manager.tool_channels:
            if tool_channel.channel_id == "tools":
                # These are the core tools
                setattr(self, tool_channel.channel_id, ToolContainer())
                tool_container = getattr(self, tool_channel.channel_id)
            else:
                # This is a plugin, so ends in "_tools"
                plugin_name = "_".join(tool_channel.channel_id.split("_")[:-1])
                setattr(self.plugins, plugin_name, PluginWrapper())
                plugin = getattr(self.plugins, plugin_name)
                tool_container = plugin.tools
            for tool_stream in tool_channel.streams:
                try:
                    setattr(tool_container, tool_stream.name,
                            self.channel_manager.get_tool_class(tool_stream.name))
                except (NameError, AttributeError, ImportError) as e:
                    logging.warn('Error loading tool {}: {}'.format(tool_stream.name, e))
