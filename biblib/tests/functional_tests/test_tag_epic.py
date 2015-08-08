# encoding: utf-8
"""
Functional test

Tag Epic

Storyboard is defined within the comments of the program itself
"""

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import json
import unittest
from flask import url_for
from tests.stubdata.stub_data import UserShop, LibraryShop, fake_biblist
from tests.base import TestCaseDatabase, MockEmailService, \
    MockSolrBigqueryService, MockEndPoint

class TestTagEpic(TestCaseDatabase):
    """
    Base class used to test the Job Epic
    """

    def test_tag_epic(self):
        """
        Carries out the epic '' where a user wants to tag some of their
        bibcodes so that when they return to the list, they remember why they
        put that bibcode there.

        1. Chris makes a library
        2. Chris adds two documents to the library
        3. Chris tags one document
        4. Chris decides to remove the tag
        5. He checks that the tag is no longer there
        """

        # Stub data
        user_chris = UserShop()
        stub_library = LibraryShop(public=True)

        # Christopher adds two documents to his library
        number_of_documents = 2
        user_view_post_data = stub_library.user_view_post_data
        user_view_post_data['bibcode'] = \
            fake_biblist(nb_codes=number_of_documents)
        tag_bibcode = user_view_post_data['bibcode'][0]
        tag_content = 'delete me'

        url = url_for('userview')
        response = self.client.post(
            url,
            data=json.dumps(user_view_post_data),
            headers=user_chris.headers
        )
        self.assertEqual(response.status_code, 200)
        library_id = response.json['id']

        # Chris decides to add a tag to the bibcode saying that this needs to
        # be deleted once the paper is released
        document_view_post_data = stub_library.document_view_post_data(
            'tag',
            tag_content,
            tag_bibcode
        )
        url = url_for('documentview', library=library_id)
        response = self.client.post(
            url,
            data=json.dumps(document_view_post_data),
            headers=user_chris.headers
        )
        self.assertEqual(response.json['tags_added'], 1)
        self.assertEqual(response.json['tags_removed'], 0)
        self.assertEqual(response.status_code, 200, response)

        # Chris checks they were added correctly
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(number_of_bibcodes=2) as BQ, \
                MockEndPoint([user_chris]) as EP:
            response = self.client.get(
                url,
                headers=user_chris.headers
            )
        self.assertIn('tags', response.json['documents'])
        self.assertEqual(tag_content,
                         response.json['documents'][tag_bibcode]['tags'][0])

        # The paper is released and so chris needs to delete the tag.
        document_view_post_data['action'] = 'detag'
        url = url_for('documentview', library=library_id)
        response = self.client.post(
            url,
            data=stub_library.document_view_data_json,
            headers=user_chris.headers
        )
        self.assertEqual(response.json['tags_removed'], 1)
        self.assertEqual(response.json['tags_added'], 0)
        self.assertEqual(response.status_code, 200, response)

        # Chris checks they were removed correctly
        # Chris checks they were added correctly
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(number_of_bibcodes=2) as BQ, \
                MockEndPoint([user_chris]) as EP:
            response = self.client.get(
                url,
                headers=user_chris.headers
            )
        self.assertIn('tags', response.json['documents'])
        self.assertEqual(
            0,
            len(response.json['documents'][tag_bibcode]['tags'][0])
        )

if __name__ == '__main__':
    unittest.main(verbosity=2)
