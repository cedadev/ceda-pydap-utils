#!/usr/bin/env python
"""
Tests for page_utils functions.

"""

__author__ = "William Tucker"
__copyright__ = "Copyright (c) 2014, Science & Technology Facilities Council (STFC)"
__license__ = "BSD - see LICENSE file in top-level directory"

import os
import unittest

from ceda.pydap.utils import file_utils

class TestGetReadmeTitle(unittest.TestCase):
    
    test_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'file_utils_test')
    
    def setUp(self):
        os.makedirs(self.test_dir)
    
    def tearDown(self):
        os.rmdir(self.test_dir)
    
    def testFirstLine(self):
        FIRST_LINE = "First Line"
        
        readme_path = os.path.join(self.test_dir, file_utils.README_NAME)
        with open(readme_path, 'w') as readme_file:
            readme_file.write(FIRST_LINE + "\n" + "SecondLine")
        
        readme_title = file_utils.get_readme_title(self.test_dir)
        os.remove(readme_path)
        
        self.assertEqual(readme_title, FIRST_LINE,
            "Wrong README title")
    
    def testEmpty(self):
        readme_path = os.path.join(self.test_dir, file_utils.README_NAME)
        with open(readme_path, 'w') as readme_file:
            readme_file.write("")
        
        readme_title = file_utils.get_readme_title(self.test_dir)
        os.remove(readme_path)
        
        self.assertEqual(len(readme_title), 0,
            "Title should be an empty string")
    
    def testNotFound(self):
        readme_title = file_utils.get_readme_title(self.test_dir)
        
        self.assertEqual(len(readme_title), 0,
            "Title should be an empty string")

if __name__ == "__main__":
    unittest.main()