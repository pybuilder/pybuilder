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

import unittest

from pybuilder.errors import PyBuilderException
from pybuilder.vcs import VCSRevision, count_travis
from test_utils import patch


class VCSRevisionTest(unittest.TestCase):
    def setUp(self):
        self.execute_command = patch("pybuilder.vcs.execute_command_and_capture_output").start()

    def tearDown(self):
        patch.stopall()

    def test_should_raise_when_git_revlist_fails(self):
        self.execute_command.return_value = 1, "any-stdout", "any-stderr"
        self.assertRaises(PyBuilderException, VCSRevision().get_git_revision_count)

    def test_should_raise_when_svnversion_fails(self):
        self.execute_command.return_value = 1, "any-stdout", "any-stderr"
        self.assertRaises(PyBuilderException, VCSRevision().get_svn_revision_count)

    def test_should_fail_when_svnversion_succeeds_but_unversioned_directory(self):
        self.execute_command.return_value = 0, "Unversioned directory", "any-stderr"
        self.assertRaises(PyBuilderException, VCSRevision().get_svn_revision_count)

    def test_should_fail_when_svnversion_succeeds_but_moved_path(self):
        self.execute_command.return_value = 0, "Uncommitted local addition, copy or move", "any-stderr"
        self.assertRaises(PyBuilderException, VCSRevision().get_svn_revision_count)

    def test_should_return_revision_when_svnversion_succeeds(self):
        self.execute_command.return_value = 0, "451", "any-stderr"
        self.assertEqual("451", VCSRevision().get_svn_revision_count())

    def test_should_return_revision_without_modified_when_svnversion_succeeds(self):
        self.execute_command.return_value = 0, "451M", "any-stderr"
        self.assertEqual("451", VCSRevision().get_svn_revision_count())

    def test_should_return_revision_without_switched_when_svnversion_succeeds(self):
        self.execute_command.return_value = 0, "451S", "any-stderr"
        self.assertEqual("451", VCSRevision().get_svn_revision_count())

    def test_should_return_revision_without_sparse_partial_when_svnversion_succeeds(self):
        self.execute_command.return_value = 0, "451P", "any-stderr"
        self.assertEqual("451", VCSRevision().get_svn_revision_count())

    def test_should_return_revision_without_mixed_when_svnversion_succeeds(self):
        self.execute_command.return_value = 0, "451:321", "any-stderr"
        self.assertEqual("451", VCSRevision().get_svn_revision_count())

    def test_should_return_revision_without_trailing_emptiness_when_svnversion_succeeds(self):
        self.execute_command.return_value = 0, "451  \n", "any-stderr"
        self.assertEqual("451", VCSRevision().get_svn_revision_count())

    def test_should_return_revision_when_git_revlist_succeeds(self):
        self.execute_command.return_value = 0, "1\n2\n3", "any-stderr"
        self.assertEqual("3", VCSRevision().get_git_revision_count())

    def test_should_detect_svn_when_status_succeeds(self):
        self.execute_command.return_value = 0, "", ""
        self.assertTrue(VCSRevision().is_a_svn_repo())

    def test_should_not_detect_svn_when_status_fails(self):
        self.execute_command.return_value = 1, "", ""
        self.assertFalse(VCSRevision().is_a_svn_repo())

    def test_should_not_detect_svn_when_status_succeeds_but_mentions_unversioned(self):
        self.execute_command.return_value = 0, "", "svn: warning: W155007: '/some/path' is not a working copy"
        self.assertFalse(VCSRevision().is_a_svn_repo())

    def test_should_detect_git_when_status_succeeds(self):
        self.execute_command.return_value = 0, "", ""
        self.assertTrue(VCSRevision().is_a_git_repo())

    def test_should_not_detect_git_when_status_fails(self):
        self.execute_command.return_value = 1, "", ""
        self.assertFalse(VCSRevision().is_a_git_repo())

    def test_should_return_revision_when_git_from_count_succeeds(self):
        self.execute_command.side_effect = [(0, "", ""),  # is git
                                            (0, "1\n2\n3", "any-stderr")]
        self.assertEqual("3", VCSRevision().count)

    def test_should_return_revision_when_svn_from_count_succeeds(self):
        self.execute_command.side_effect = [(1, "", ""),  # not git
                                            (0, "", ""),  # is svn
                                            (0, "451", "any-stderr")]
        self.assertEqual("451", VCSRevision().count)

    def test_should_raise_when_not_git_or_svn(self):
        self.execute_command.side_effect = [(1, "", ""),  # not git
                                            (1, "", "")]  # is svn
        self.assertRaises(PyBuilderException, getattr, VCSRevision(), "count")

    def test_should_raise_when_revparse_fails_in_get_git_hash(self):
        self.execute_command.side_effect = [(0, "", ""),  # is git
                                            (1, "", "")]
        self.assertRaises(PyBuilderException, VCSRevision().get_git_hash)

    def test_should_raise_when_not_git_in_get_git_hash(self):
        self.execute_command.return_value = 1, "", ""  # not git
        self.assertRaises(PyBuilderException, VCSRevision().get_git_hash)

    def test_should_return_revision_when_get_git_hash_succeeds(self):
        self.execute_command.side_effect = [(0, "", ""),  # is git
                                            (0, "451", "any-stderr")]
        self.assertEqual("451", VCSRevision().get_git_hash())

    def test_should_return_rev_and_travis_info_when_count_travis(self):
        environ_get = patch("pybuilder.vcs.os.environ.get").start()
        environ_get.return_value = "456"
        self.execute_command.side_effect = [(1, "", ""),  # not git
                                            (0, "", ""),  # is svn
                                            (0, "123", "any-stderr")]
        travis = count_travis()

        if "123" not in travis or "456" not in travis:
            self.assertEqual(False, True)
