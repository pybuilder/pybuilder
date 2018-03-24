#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2015 PyBuilder Team
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

from unittest import TestCase
from pybuilder.graph_utils import Graph


class GraphUtilsTests(TestCase):

    def test_should_find_trivial_cycle_in_graph_when_there_is_one(self):
        graph_with_trivial_cycle = Graph({"a": "a"})
        self.assertIsNotNone(graph_with_trivial_cycle.assert_no_trivial_cycles_present())

    def test_should_find_trivial_cycle_in_graph_when_there_are_two(self):
        graph_with_trivial_cycles = Graph({"a": "a", "b": "b"})
        self.assertIsNotNone(graph_with_trivial_cycles.assert_no_trivial_cycles_present())

    def test_should_find_trivial_cycle_in_graph_when_searching_for_cycles(self):
        graph_with_trivial_cycle = Graph({"a": "a"})
        self.assertIsNotNone(graph_with_trivial_cycle.assert_no_cycles_present())

    def test_should_not_find_trivial_cycles_in_graph_when_there_are_none(self):
        graph_without_trivial_cycle = Graph({"a": "b", "b": "c", "d": "e"})
        graph_without_trivial_cycle.assert_no_trivial_cycles_present()

    def test_should_not_find_cycles_in_graph_when_there_are_none(self):
        graph_without_cycle = Graph({"a": "b", "b": "c", "d": "e"})
        graph_without_cycle.assert_no_cycles_present()

    def test_should_find_simple_nontrivial_cycle_in_graph_when_there_is_one(self):
        graph_with_simple_cycle = Graph({"a": "b", "b": "a"})
        self.assertIsNotNone(graph_with_simple_cycle.assert_no_cycles_present())

    def test_should_find_long_nontrivial_cycle_in_graph_when_there_is_one(self):
        graph_with_long_cycle = Graph({"a": "b", "b": "c", "c": "d", "d": "b"})
        self.assertIsNotNone(graph_with_long_cycle.assert_no_cycles_present())

    def test_should_find_long_nontrivial_cycle_in_graph_when_there_are_two(self):
        graph_with_long_cycle = Graph({"a": "b", "b": "c", "c": "a", "d": "e", "e": "f", "f": "d"})
        self.assertIsNotNone(graph_with_long_cycle.assert_no_cycles_present())
