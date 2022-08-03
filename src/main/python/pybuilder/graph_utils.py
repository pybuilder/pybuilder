#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2020 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
"""
A module containing utilities for operations on a directed graph
"""


class Graph(object):
    """
        A graph using an edge dictionary as an internal representation.
    """

    def __init__(self, edges):
        self.edges = edges

    def assert_no_cycles_present(self, include_trivial_cycles=True):
        cycles = []
        components = tarjan_scc(self.edges)
        for component in components:
            if len(component) > 1:
                cycles.append(component)
                # every nontrivial strongly connected component
                # contains at least one directed cycle, so len()>1 is a showstopper

        if cycles:
            return cycles

        if include_trivial_cycles:
            return self.assert_no_trivial_cycles_present()

    def assert_no_trivial_cycles_present(self):
        trivial_cycles = []
        for source, destination in self.edges.items():
            if source in destination:
                trivial_cycles.append((source, source))

        if trivial_cycles:
            return trivial_cycles


def tarjan_scc(graph):
    """
    Tarjan's partitioning algorithm for finding strongly connected components in a graph.
    """

    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    result = []

    def strongconnect(node):
        index[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)

        try:
            successors = graph[node]
        except Exception:
            successors = []
        for successor in successors:
            if successor not in lowlinks:
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif successor in stack:
                lowlinks[node] = min(lowlinks[node], index[successor])

        if lowlinks[node] == index[node]:
            connected_component = []

            while True:
                successor = stack.pop()
                connected_component.append(successor)
                if successor == node:
                    break
            component = tuple(connected_component)
            result.append(component)

    for node in graph:
        if node not in lowlinks:
            strongconnect(node)

    return result
