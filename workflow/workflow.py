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
"""
Workflow and WorkflowManager definitions.
"""

import itertools
import logging
from collections import deque

from factor import Factor, MultiOutputFactor
from node import Node
from ..stream import StreamId
from ..tool import Tool, MultiOutputTool, AggregateTool
from ..utils import Printable, TypedFrozenKeyDict, IncompatiblePlatesError, FactorDefinitionError, NodeDefinitionError


class Workflow(Printable):
    """
    Workflow.
    This defines the graph of operations through "nodes" and "factors".
    """
    def __init__(self, channels, plates, workflow_id, name, description, owner):
        """
        Initialise the workflow

        :param channels: The channels used by this workflow
        :param plates: All of the plates used by this workflow
        :param workflow_id: The workflow id
        :param name: The name of the workflow
        :param description: A human readable description
        :param owner: The owner/author of the workflow
        """
        self.channels = channels
        self.plates = plates
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.owner = owner
        self.nodes = {}
        self.execution_order = []
        self.factor_collections = TypedFrozenKeyDict(str)

        logging.info("New workflow created with id {}".format(workflow_id))
    
    def execute(self, time_interval):
        """
        Here we execute the factors over the streams in the workflow

        :return: None
        """
        # TODO: Currently expects the factors to be declared sequentially
        # for factor_collection in self.factor_collections.values()[::-1]:
        #     for factor in factor_collection:
        for tool in self.execution_order:
            for factor in self.factor_collections[tool.name]:
                logging.debug("Executing factor {}".format(factor))
                factor.execute(time_interval)
            
    def create_node(self, stream_name, channel, plate_ids):
        """
        Create a node in the graph. Note: assumes that the streams already exist

        :param stream_name: The name of the stream
        :param channel: The channel where this stream lives
        :param plate_ids: The plate ids. The stream meta-data will be auto-generated from these
        :return: The streams associated with this node
        """
        streams = {}

        plate_values = self.get_overlapping_plate_values(plate_ids)

        if plate_ids:
            if not plate_values:
                raise NodeDefinitionError("No overlapping plate values found")
            for pv in plate_values:
                # Construct stream id
                stream_id = StreamId(name=stream_name, meta_data=pv)

                # Now try to locate the stream and add it (raises StreamNotFoundError if not found)
                streams[pv] = channel.get_or_create_stream(stream_id=stream_id)

        else:
            streams[None] = channel.get_or_create_stream(stream_id=StreamId(name=stream_name))

        if not streams:
            raise NodeDefinitionError("No streams created for node with id {}".format(stream_name))

        node = Node(stream_name, streams, plate_ids, plate_values)
        self.nodes[stream_name] = node
        logging.info("Added node with id {}".format(stream_name))

        return node

    def get_overlapping_plate_values(self, plate_ids):
        """
        Need to find where in the tree the two plates intersect, e.g.

        We are given as input plates D, E, whose positions in the tree are:

        root -> A -> B -> C -> D
        root -> A -> B -> E

        The results should then be the cartesian product between C, D, E looped over A and B

        If there's a shared plate in the hierarchy, we need to join on this shared plate, e.g.:

        [self.plates[p].values for p in plate_ids][0] =
          [(('house', '1'), ('location', 'hallway'), ('wearable', 'A')),
           (('house', '1'), ('location', 'kitchen'), ('wearable', 'A'))]
        [self.plates[p].values for p in plate_ids][1] =
          [(('house', '1'), ('scripted', '15')),
           (('house', '1'), ('scripted', '13'))]

        Result should be one stream for each of:
          [(('house', '1'), ('location', 'hallway'), ('wearable', 'A'), ('scripted', '15)),
           (('house', '1'), ('location', 'hallway'), ('wearable', 'A'), ('scripted', '13)),
           (('house', '1'), ('location', 'kitchen'), ('wearable', 'A'), ('scripted', '15)),
           (('house', '1'), ('location', 'kitchen'), ('wearable', 'A'), ('scripted', '13))]

        :param plate_ids:
        :return: The plate values
        :type plate_ids: list[str] | list[unicode]
        """
        if not plate_ids:
            return None

        if len(plate_ids) == 1:
            return self.plates[plate_ids[0]].values

        if len(plate_ids) > 2:
            raise NotImplementedError

        # get the actual plate objects
        plates = [self.plates[p] for p in plate_ids]

        # Get all of the ancestors zipped together, padded with None
        ancestors = deque(itertools.izip_longest(*(p.ancestor_plates for p in plates)))

        last_values = []
        while len(ancestors) > 0:
            current = ancestors.popleft()
            if current[0] == current[1]:
                # Plates are identical, take all values valid for matching parents
                if last_values:
                    raise NotImplementedError
                else:
                    last_values.extend(current[0].values)

            elif current[0] is not None and current[1] is not None \
                    and current[0].meta_data_id == current[1].meta_data_id:
                # Not identical, but same meta data id. Take all overlapping values valid for matching parents
                if last_values:
                    raise NotImplementedError
                else:
                    raise NotImplementedError
            else:
                # Different plates, take cartesian product of values with matching parents.
                # Note that one of them may be none
                if last_values:
                    tmp = []
                    for v in last_values:
                        # Get the valid ones based on v
                        valid = [filter(lambda x: all(xx in v for xx in x[:-1]), c.values)
                                 for c in current if c is not None]

                        # Strip out v from the valid ones
                        stripped = [map(lambda y: tuple(itertools.chain(*(yy for yy in y if yy not in v))), val)
                                    for val in valid]

                        # Get the cartesian product. Note that this still works if one of the current is None
                        prod = list(itertools.product(*stripped))

                        # Now update the last values be the product with v put back in
                        new_values = [v + p for p in prod]
                        if new_values:
                            tmp.append(new_values)

                    last_values = list(itertools.chain(*tmp))
                    if not last_values:
                        raise Exception
                else:
                    raise NotImplementedError

        if not last_values:
            raise ValueError("Plate value computation failed - possibly there were no shared plate values")

        return last_values

    def create_factor(self, tool, sources, sink, alignment_node=None):
        """
        Creates a factor. Instantiates a single tool for all of the plates, and connects the source and sink nodes with
        that tool.

        Note that the tool parameters these are currently fixed over a plate. For parameters that vary over a plate,
        an extra input stream should be used

        :param alignment_node:
        :param tool: The tool to use. This is either an instantiated Tool object or a dict with "name" and "parameters"
        :param sources: The source nodes
        :param sink: The sink node
        :return: The factor object
        :type tool: Tool | dict
        :type sources: list[Node] | tuple[Node] | None
        :type sink: Node
        :type alignment_node: Node | None
        :rtype: Factor
        """
        if isinstance(tool, dict):
            tool = self.channels.get_tool(**tool)

        if not isinstance(tool, Tool):
            raise ValueError("Expected Tool, got {}".format(type(tool)))

        if sink.plate_ids:
            if isinstance(tool, AggregateTool):
                if not sources or len(sources) != 1:
                    raise FactorDefinitionError("Aggregate tools require a single source node")

                if not sources[0].plate_ids:
                    raise FactorDefinitionError("Aggregate tool source must live on a plate")

                if len(sources[0].plate_ids) != 1:
                    # Make sure that there are exactly two plates that don't match: one from each side
                    difference = (tuple(set(sources[0].plate_ids) - set(sink.plate_ids)),
                                  tuple(set(sink.plate_ids) - set(sources[0].plate_ids)))
                    if map(len, difference) == [1, 1]:
                        if not self.plates[difference[0][0]].is_sub_plate(self.plates[difference[1][0]]):
                            raise IncompatiblePlatesError("Sink plate is not a simplification of source plate")
                    else:
                        raise IncompatiblePlatesError("Aggregate tool can only have a single plate that differs")

                else:
                    # Check if the parent plate is valid instead
                    source_plate = self.plates[sources[0].plate_ids[0]]
                    sink_plate = self.plates[sink.plate_ids[0]]

                    error = self.check_plate_compatibility(tool, source_plate, sink_plate)
                    if error is not None:
                        raise IncompatiblePlatesError(error)
            else:
                if sources:
                    # Check that the plates are compatible
                    source_plates = itertools.chain(*(source.plate_ids for source in sources))
                    for p in sink.plate_ids:
                        if p not in set(source_plates):
                            raise IncompatiblePlatesError("{} not in source plates".format(p))
                    for p in source_plates:
                        if p not in set(sink.plate_ids):
                            raise IncompatiblePlatesError("{} not in sink plates".format(p))
            plates = [self.plates[plate_id] for plate_id in sink.plate_ids]
        else:
            plates = None

        factor = Factor(tool=tool, source_nodes=sources,
                        sink_node=sink, alignment_node=alignment_node,
                        plates=plates)

        if tool.name not in self.factor_collections:
            self.factor_collections[tool.name] = []

        self.factor_collections[tool.name].append(factor)
        self.execution_order.append(tool)

        return factor

    def create_multi_output_factor(self, tool, source, sink):
        """
        Creates a multi-output factor.
        This takes a single node, applies a MultiOutputTool to create multiple nodes on a new plate
        Instantiates a single tool for all of the input plate values,
        and connects the source and sink nodes with that tool.

        Note that the tool parameters these are currently fixed over a plate. For parameters that vary over a plate,
        an extra input stream should be used

        :param tool: The tool to use. This is either an instantiated Tool object or a dict with "name" and "parameters"
        :param source: The source node
        :param sink: The sink node
        :return: The factor object
        :type tool: MultiOutputTool | dict
        :type source: Node
        :type sink: Node
        :rtype: Factor
        """
        if isinstance(tool, dict):
            tool = self.channels.get_tool(name=tool["name"], parameters=["parameters"])

        if not isinstance(tool, MultiOutputTool):
            raise ValueError("Expected MultiOutputTool, got {}".format(type(tool)))

        # Check that the input_plate are compatible - note this is the opposite way round to a normal factor
        input_plates = [self.plates[plate_id] for plate_id in source.plate_ids]
        output_plates = [self.plates[plate_id] for plate_id in sink.plate_ids]

        if len(input_plates) > 1:
            raise NotImplementedError

        if len(output_plates) == 0:
            raise ValueError("No output plate found")

        if len(output_plates) == 1:
            if not self.check_multi_output_plate_compatibility(input_plates, output_plates[0]):
                raise IncompatiblePlatesError("Parent plate does not match input plate")

            factor = MultiOutputFactor(tool=tool, source_node=source, sink_node=sink,
                                       input_plate=input_plates[0], output_plates=output_plates[0])
        else:
            # The output plates should be the same as the input plates, except for one
            # additional plate. Since we're currently only supporting one input plate,
            # we can safely assume that there is a single matching plate.
            # Finally, note that the output plate must either have no parents
            # (i.e. it is at the root of the tree), or the parent plate is somewhere
            # in the input plate's ancestry
            if len(output_plates) > 2:
                raise NotImplementedError
            if len(input_plates) != 1:
                raise IncompatiblePlatesError("Require an input plate to match all but one of the output plates")
            if output_plates[0] == input_plates[0]:
                # Found a match, so the output plate should be the other plate
                output_plate = output_plates[1]
            else:
                if output_plates[1].plate_id != input_plates[0].plate_id:
                    raise IncompatiblePlatesError("Require an input plate to match all but one of the output plates")
                output_plate = output_plates[0]
                # Swap them round so the new plate is the last plate - this is required by the factor
                output_plates[1], output_plates[0] = output_plates[0], output_plates[1]

            # We need to walk up the input plate's parent tree
            match = False
            parent = input_plates[0].parent
            while parent is not None:
                if parent.plate_id == output_plate.parent.plate_id:
                    match = True
                    break
                parent = parent.parent
            if not match:
                raise IncompatiblePlatesError("Require an input plate to match all but one of the output plates")

            factor = MultiOutputFactor(
                tool=tool, source_node=source, sink_node=sink,
                input_plate=input_plates[0], output_plates=output_plates)

        if tool.name not in self.factor_collections:
            self.factor_collections[tool.name] = []

        self.factor_collections[tool.name].append(factor)
        self.execution_order.append(tool)

        return factor

    @staticmethod
    def check_plate_compatibility(tool, source_plate, sink_plate):
        """
        Checks whether the source and sink plate are compatible given the tool

        :param tool: The tool
        :param source_plate: The source plate
        :param sink_plate: The sink plate
        :return: Either an error, or None
        :type tool: Tool
        :type source_plate: Plate
        :type sink_plate: Plate
        :rtype: None | str
        """
        if sink_plate == source_plate.parent:
            return None

        # could be that they have the same meta data, but the sink plate is a simplification of the source
        # plate (e.g. when using IndexOf tool)
        if sink_plate.meta_data_id == source_plate.meta_data_id:
            if sink_plate.is_sub_plate(source_plate):
                return None
            return "Sink plate {} is not a simplification of source plate {}".format(
                sink_plate.plate_id, source_plate.plate_id)

        # Also check to see if the meta data differs by only one value
        meta_data_diff = set(source_plate.ancestor_meta_data_ids) - set(sink_plate.ancestor_meta_data_ids)
        if len(meta_data_diff) == 1:
            # Is the diff value the same as the aggregation meta id passed to the aggregate tool
            if tool.aggregation_meta_data not in meta_data_diff:
                return "Aggregate tool meta data ({}) " \
                       "does not match the diff between source and sink plates ({})".format(
                        tool.aggregation_meta_data, list(meta_data_diff)[0])
        else:
            return "{} not in source's parent plates".format(sink_plate.plate_id)

    @staticmethod
    def check_multi_output_plate_compatibility(source_plates, sink_plate):
        if len(source_plates) == 0:
            if sink_plate.parent is not None:
                return False
        else:
            if sink_plate.parent is None:
                return False
            else:
                if sink_plate.parent.plate_id != source_plates[0].plate_id:
                    return False
        return True
