#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
This tool reads a USFM file (generated by csvtousfm3.py)
and injects tW links to the matching Greek or Hebrew words.

Assumptions:
1. The tW RC contains a list of occurrences for each word.
2. This list of occurrences is stored in the config.yaml file
3. The word content contains a number 2 heading "Word Data" section under which is the strong numbers
"""

import argparse
import os
import sys
import re

from resource_container import factory, ResourceContainer
from libraries.tools.file_utils import write_file, read_file

def indexLocationWords(words_rc):
    """
    Generates an index of word occurrences where words may be looked up by
    textual occurrence.
    :param words_rc:
    :type words_rc: ResourceContainer.RC
    :return:
    """
    index = {}
    config = words_rc.config()
    for word in config:
        word_obj = config[word]
        if 'occurrences' in word_obj:
            for location in word_obj['occurrences']:
                parts = location.split('/')
                length = len(parts)
                verse = '{}'.format(int(parts[length-1]))
                chapter = '{}'.format(int(parts[length-2]))
                book = parts[length - 3]
                location = '{}/{}/{}'.format(book, chapter, verse)
                if location in index:
                    # append to index
                    index[location].append(word)
                else:
                    # create index
                    index[location] = [word]
    return index

def getStrongNumbers(word, words_rc):
    """
    Retrieves the strong numbers for a word
    :param word: the word to index
    :param words_rc:
    :type words_rc: ResourceContainer.RC
    :return:
    """

    # TRICKY: the config.yaml does not provide sufficient information to
    # locate the word, however we only have 3 options.
    # There should not be any duplicate within these folders.
    numbers = []
    data = words_rc.read_chunk('kt', word)
    if not data:
        data = words_rc.read_chunk('names', word)
    if not data:
        data = words_rc.read_chunk('other', word)
    if not data:
        raise Exception('Failed to look up word {}'.format(word))

    header = re.findall('^#+\s*Word\s+Data\s*\:?.*', data, re.MULTILINE|re.IGNORECASE)
    if(len(header)):
        word_data = data.split(header[0])[1]
        numbers = re.findall('[HG]\d+', word_data, re.MULTILINE | re.IGNORECASE)
    else:
        raise Exception('Missing Word Data section in word {}'.format(word))

    return numbers


def getLocationWords(location, occurrences_index):
    """
    Retrieves the words found at the passage location
    :param location:
    :param occurrences_index:
    :return:
    """
    if location in occurrences_index:
        return occurrences_index[location]
    else:
        return []

def indexLocationStrongs(location, occurrences_index, words_rc):
    """
    Generates an index of word strongs found in the given lcoation
    :param location:
    :param occurrences_index:
    :param words_rc:
    :return:
    """
    words = getLocationWords(location, occurrences_index)
    index = {}
    for word in words:
        index[word] = getStrongNumbers(word, words_rc)
    return index

def mapWord(strongs, words_rc, word_index):
    """
    Attepts to lookup a tW word by a strongs number.
    :param strongs:
    :param words_rc:
    :type words_rc: ResourceContainer.RC
    :param word_index:
    :return:
    """
    pass


def mapWords(usfm, words_rc):
    """
    Injects tW links into the usfm
    :param usfm_dir:
    :param words_rc_dir: tW resource container
    :return:
    """
    if sys.version_info >= (3,0,0):
        raise Exception('Only python 2.7 is supported')
    rc = factory.load(words_rc)

    return []

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                   formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-u', '--usfm', dest='usfm', required=True, help='Directory containing USFM files to read')
    parser.add_argument('-w', '--words', dest='words', required=True, help='tW resource container to read. The project should contain a config.yaml with word occurrences indicated')
    parser.add_argument('-o', '--output', dest='output', required=True, help='Directory where to save the updated USFM')

    args = parser.parse_args(sys.argv[1:])
    if os.path.isfile(args.output):
        raise Exception('Output must be a directory')

    rc = factory.load(args.words)
    # TODO: fix this.
    usfm_books = mapWords(args.usfm, rc)

    for book in usfm_books:
        file_path = os.path.join(args.output, '{}-{}.usfm'.format(book['sort'], book['id']))
        write_file(file_path, book['usfm'])