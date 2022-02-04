# -*- coding: utf-8 -*-
"""
Enter relative path to Sphinx HTML file and process to get rid of excess.

@author: Mason Hicks
"""

import codecs
import sys, os

file = sys.argv[0]
dirname = os.path.dirname(file)

file_location = input()

if file_location[-4:] != "html":
    sys.exit(1)

file = codecs.open(file_location, "r", "utf-8")
unprocessed = file.read()

startindex = unprocessed.find('<section')
endindex = unprocessed.rfind('</section>')

processed = unprocessed[startindex:endindex]

print(processed)