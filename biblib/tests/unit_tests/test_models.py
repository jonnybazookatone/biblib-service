"""
Tests the underlying models of the database
"""

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import app
import uuid
import unittest
from models import db, User, Library, Permissions, MutableList, GUID
from flask.ext.testing import TestCase
from tests.base import TestCaseDatabase

class TestGUIDType(TestCaseDatabase):
    """
    Class for testing the behaviour of the custom GUUID type created in the
    models of the database
    """
    def create_app(self):
        """
        Create the wsgi application

        :return: application instance
        """
        app_ = app.create_app(config_type='TEST')
        return app_

    def test_slug_to_uuid(self):
        """
        Test the conversion of a base64 URL encoded string to a UUID behaves as
        expected

        :return:
        """
        input_slug = '878JECDeTX6hoI77gq1Y2Q'
        expected_uuid = 'f3bf0910-20de-4d7e-a1a0-8efb82ad58d9'

        output_uuid = GUID.slug_to_uuid(input_slug)
        self.assertEqual(expected_uuid, output_uuid)

    def test_uuid_to_slug(self):
        """
        Test the conversion of UUID to a base64 URL encoded string behaves as
        expected

        :return: no return
        """
        input_uuid = uuid.UUID('f3bf0910-20de-4d7e-a1a0-8efb82ad58d9')
        expected_slug = '878JECDeTX6hoI77gq1Y2Q'

        output_slug = GUID.uuid_to_slug(input_uuid)
        self.assertEqual(expected_slug, output_slug)

class TestMutableType(TestCase):
    """
    Class for testing the behaviour of the custom MutableType types created in
    the models of the database
    """
    def create_app(self):
        """
        Create the wsgi application

        :return: application instance
        """
        app_ = app.create_app(config_type='TEST')
        return app_

    def test_append_of_mutable_list(self):
        """
        Checks that the append method of the mutable list behaves as expected

        :return: no return
        """
        expected_list = [1]
        mutable_list = MutableList()
        mutable_list.append(expected_list[0])
        self.assertEqual(expected_list, mutable_list)

    def test_extend_of_mutable_list(self):
        """
        Checks that the extend method of the mutable list behaves as expected

        :return: no return
        """
        expected_list = [1]
        mutable_list = MutableList()
        mutable_list.extend(expected_list)
        self.assertEqual(expected_list, mutable_list)

    def test_remove_of_mutable_list(self):
        """
        Checks that the remove method of the mutable list behaves as expected

        :return: no return
        """
        expected_list = [1]
        mutable_list = MutableList()
        mutable_list.append(expected_list[0])
        mutable_list.remove(expected_list[0])

        self.assertEqual([], mutable_list)

    def test_shorten_of_mutable_list(self):
        """
        Checks that the remove method of the mutable list behaves as expected

        :return: no return
        """
        expected_list = [1]
        mutable_list = MutableList()
        mutable_list.extend(expected_list)
        mutable_list.shorten(expected_list)

        self.assertEqual([], mutable_list)

    def test_upsert_of_mutable_list(self):
        """
        Checks that the custom upsert command works as expected

        :return: no return
        """

        input_list_1 = [1, 2, 3]
        input_list_2 = [2, 2, 3, 4, 4]
        expected_output = [1, 2, 3, 4]

        mutable_list = MutableList()
        mutable_list.extend(input_list_1)
        mutable_list.upsert(input_list_2)

        self.assertEqual(mutable_list, expected_output)

    def test_coerce(self):
        """
        Checks the coerce for SQLAlchemy works correctly

        :return: no return
        """

        mutable_list = MutableList()

        with self.assertRaises(ValueError):
            mutable_list.coerce('key', 2)

        new_type = mutable_list.coerce('key', [2])
        self.assertIsInstance(new_type, MutableList)

        same_list = mutable_list.coerce('key', mutable_list)
        self.assertEqual(same_list, mutable_list)

if __name__ == '__main__':
    unittest.main(verbosity=2)