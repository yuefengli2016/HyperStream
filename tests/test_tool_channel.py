# The MIT License (MIT) # Copyright (c) 2014-2017 University of Bristol
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#  OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#  OR OTHER DEALINGS IN THE SOFTWARE.

import unittest

from hyperstream import HyperStream, Stream, StreamId, TimeInterval
from hyperstream.utils import MIN_DATE, utcnow
from helpers import *


class TestToolChannel(unittest.TestCase):
    def test_tool_channel(self):

        hs = HyperStream(file_logger=False, console_logger=False, mqtt_logger=None)
        T = hs.channel_manager.tools

        # Load in the objects and print them
        clock_stream = T[clock]
        assert(isinstance(clock_stream, Stream))
        # assert(clock_stream.modifier == Last() + IData())

        agg = T[aggregate].window((MIN_DATE, utcnow())).items()
        assert(len(agg) > 0)
        # noinspection PyTypeChecker
        assert(agg[0].timestamp == datetime(2016, 10, 26, 0, 0, tzinfo=UTC))
        assert(isinstance(agg[0].value, type))

    def test_tool_channel_new_api(self):

        hs = HyperStream(file_logger=False, console_logger=False, mqtt_logger=None)
        M = hs.channel_manager.memory

        # new way of loading tools
        clock_new = hs.tools.clock()

        # old way of loading tools
        clock_old = hs.channel_manager.tools[clock].window((MIN_DATE, utcnow())).last().value()

        # TODO: NOTE THAT IF WE DO IT THE OLD WAY FIRST, THEN THE NEW WAY FAILS WITH:
        # TypeError: super(type, obj): obj must be an instance or subtype of type
        # which possibly relates to: https://stackoverflow.com/questions/9722343/python-super-behavior-not-dependable

        ticker_old = M.get_or_create_stream(StreamId("ticker_old"))
        ticker_new = M.get_or_create_stream(StreamId("ticker_new"))

        now = utcnow()
        before = (now - timedelta(seconds=30)).replace(tzinfo=UTC)
        ti = TimeInterval(before, now)

        clock_old.execute(sources=[], sink=ticker_old, interval=ti)
        clock_new.execute(sources=[], sink=ticker_new, interval=ti)

        assert(all(map(lambda (old, new): old.value == new.value, zip(ticker_old.window(), ticker_new.window()))))
