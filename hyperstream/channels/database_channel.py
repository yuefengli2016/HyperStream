"""
The MIT License (MIT)
Copyright (c) 2014-2017 University of Bristol

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.
"""
from base_channel import BaseChannel
from ..models import StreamInstanceModel, StreamDefinitionModel, StreamStatusModel
from ..stream import StreamId, StreamReference
from datetime import datetime
from ..time_interval import TimeIntervals
from ..modifiers import Identity
from ..utils import MIN_DATE, utcnow
import logging


class DatabaseChannel(BaseChannel):
    def __init__(self, channel_id):
        super(DatabaseChannel, self).__init__(channel_id=channel_id, can_calc=True, can_create=False)
        self.update_streams()
        self.update_state()

    def update_state(self):
        intervals = TimeIntervals([(MIN_DATE, utcnow())])
        for stream_id in self.streams.keys():
            self.state.calculated_intervals[stream_id] = intervals

    def update_streams(self):
        """
        Call this function to load streams in from the database
        """
        # TODO What about start/end/modifier??? are they needed
        for s in StreamDefinitionModel.objects():
            stream_id = StreamId(name=s.stream_id.name, meta_data=s.stream_id.meta_data)
            self.streams[stream_id] = StreamReference(
                channel_id=self.state.channel_id,
                stream_id=stream_id,
                time_interval=None,
                modifier=Identity(),
                get_results_func=self.get_results
            )

    def get_params(self, x, start, end):
        # TODO: This was copied from MemoryChannel
        if isinstance(x, (list, tuple)):
            res = []
            for x_i in x:
                res.append(self.get_params(x_i, start, end))
            if isinstance(x, list):
                return res
            else:
                return tuple(res)
        elif isinstance(x, dict):
            res = {}
            for x_i in x:
                res[x_i] = self.get_params(x[x_i], start, end)
            return res
        elif isinstance(x, StreamReference):
            return x(start=start, end=end)
        else:
            return x

    def get_results(self, stream_ref, args, kwargs):
        stream_id = stream_ref.stream_id
        abs_end, abs_start = self.get_absolute_start_end(kwargs, stream_ref)

        # TODO: this should be read from the stream_status collection
        done_calc_times = self.state.calculated_intervals[stream_id]
        need_to_calc_times = TimeIntervals([(abs_start, abs_end)]) - done_calc_times

        self.do_calculations(stream_id, abs_start, abs_end, need_to_calc_times)

        result = []
        for (timestamp, data) in self.streams[stream_ref.stream_id]:
            if abs_start < timestamp <= abs_end:
                result.append((timestamp, data))

        result.sort(key=lambda x: x[0])

        # make a generator out from result and then apply the modifier
        result = stream_ref.modifier(iter(result))  # (x for x in result))
        return result
    
    def do_calculations(self, stream_id, abs_start, abs_end, need_to_calc_times):
        if need_to_calc_times.is_empty:
            return
            
        stream_def = self.state.stream_id_to_definition_mapping[stream_id]
        writer = self.get_stream_writer(stream_id)
        tool = stream_def.tool
        
        for (start2, end2) in need_to_calc_times.value:
            args2 = self.get_params(stream_def.args, start2, end2)
            kwargs2 = self.get_params(stream_def.kwargs, start2, end2)

            # Here we're actually executing the tool
            tool(stream_def, start2, end2, writer, *args2, **kwargs2)

            # TODO: write to stream_status collection
            self.state.calculated_intervals[stream_id] += TimeIntervals([(start2, end2)])

        done_calc_times = self.state.calculated_intervals[stream_id]
        need_to_calc_times = TimeIntervals([(abs_start, abs_end)]) - done_calc_times
        logging.debug(done_calc_times)
        logging.debug(need_to_calc_times)

        if need_to_calc_times.is_not_empty:
            raise ValueError('Tool execution did not cover the specified interval.')

    def create_stream(self, stream_id, stream_def):
        # TODO: Functionality here
        raise NotImplementedError("Database streams currently need to be defined in the database")

    def get_stream_writer(self, stream_id):
        def writer(document_collection):
            # TODO: Should this be for (doc_datetime, doc) in ... and then in StreamInstanceModel datetime=doc_datetime
            # TODO: Does this check whether a stream_id/datetime pair already exists in the DB? (unique pairs?)
            for doc in document_collection:
                instance = StreamInstanceModel(
                    stream_id=stream_id,
                    stream_type="",
                    datetime=utcnow(),
                    metadata={},
                    version="",
                    value=doc
                )
                instance.save()
        return writer
