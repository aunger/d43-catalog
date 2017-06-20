import os
import codecs
import json
import shutil
from tools.file_utils import load_json_object
from unittest import TestCase
from tools.mocks import MockS3Handler, MockDynamodbHandler

from functions.ts_v2_catalog.ts_v2_catalog_handler import TsV2CatalogHandler

class TestTsV2Catalog(TestCase):

    resources_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources')

    def setUp(self):
        self.latest_catalog = load_json_object(os.path.join(TestTsV2Catalog.resources_dir, "v3_catalog.json"))
        self.assertIsNotNone(self.latest_catalog)

    @staticmethod
    def mock_get_url(urls, url, catch_exception):
        """

        :param dict urls: valid urls with their associated files
        :param string url: url to get
        :param bool catch_exception:
        :return:
        """
        if url in urls:
            try:
                return TestTsV2Catalog.read_file(urls[url])
            except Exception as e:
                if not catch_exception:
                    raise e
        else:
            raise Exception('404: {}'.format(url))

    @staticmethod
    def mock_download_file(urls, url, path):
        """

        :param dict urls: valid urls with their associated files
        :param string url: url to get
        :param string path:
        :return:
        """
        if url in urls:
            shutil.copyfile(urls[url], path)
        else:
            raise Exception('404: {}'.format(url))

    @staticmethod
    def readMockApi(path):
        """
        Rest a file from the mock api
        :param path: 
        :return: 
        """
        if(path.startswith('/')): path = path[1:]
        file_path = os.path.join(TestTsV2Catalog.resources_dir, 'ts_api', path.split('?')[0])
        if os.path.exists(file_path):
            return TestTsV2Catalog.read_file(file_path)
        else:
            raise Exception('Mock API path does not exist: {}'.format(file_path))

    @staticmethod
    def read_file(file_name, encoding='utf-8-sig'):
        with codecs.open(file_name, 'r', encoding=encoding) as f:
            return f.read()

    @staticmethod
    def ordered(obj):
        """
        Orders the values in an object
        :param obj: 
        :return: 
        """
        if isinstance(obj, dict):
            return sorted((k, TestTsV2Catalog.ordered(v)) for k, v in obj.items())
        if isinstance(obj, list):
            return sorted(TestTsV2Catalog.ordered(x) for x in obj)
        else:
            return obj

    def make_event(self):
        return {
            'stage-variables': {
                'cdn_bucket': '',
                'cdn_url': 'https://api.unfoldingword.org/ts/txt/2',
                'catalog_url': 'https://api.door43.org/v3/catalog.json'
            }
        }

    def assertObjectEqual(self, obj1, obj2):
        """
        Checks if two objects are equal after recursively sorting them
        :param obj1: 
        :param obj2: 
        :return: 
        """
        self.assertEqual(TestTsV2Catalog.ordered(obj1), TestTsV2Catalog.ordered(obj2))

    def assertS3EqualsApiJSON(self, mockS3, key):
        """
        Checks if a generated s3 file matches a file in the mock api
        :param mockS3: 
        :param key: 
        :return: 
        """
        self.assertIn(key, mockS3._uploads)
        s3_obj = json.loads(TestTsV2Catalog.read_file(mockS3._uploads[key]))

        expected_obj = json.loads(TestTsV2Catalog.readMockApi(key))
        self.assertObjectEqual(s3_obj, expected_obj)

    def test_convert_catalog(self):
        mockS3 = MockS3Handler('ts_bucket')
        urls = {
            'https://test-cdn.door43.org/en/ulb/v7/ulb.zip': os.path.join(TestTsV2Catalog.resources_dir, "en_ulb.zip"),
            'https://test-cdn.door43.org/en/udb/v7/udb.zip': os.path.join(TestTsV2Catalog.resources_dir, "en_ulb.zip"),
            'https://api.door43.org/v3/catalog.json': os.path.join(TestTsV2Catalog.resources_dir, "v3_catalog.json"),
            'https://test-cdn.door43.org/en/obs/v4/obs.zip': os.path.join(TestTsV2Catalog.resources_dir, "en_obs.zip"),
            'https://test-cdn.door43.org/en/tw/v5/tw.zip': os.path.join(TestTsV2Catalog.resources_dir, 'en_tw.zip')
        }
        mockDb = MockDynamodbHandler()
        mockDb._load_db(os.path.join(TestTsV2Catalog.resources_dir, 'db.json'))
        mock_get_url = lambda url, catch_exception: TestTsV2Catalog.mock_get_url(urls, url, catch_exception)
        mock_download = lambda url, dest: TestTsV2Catalog.mock_download_file(urls, url, dest)
        converter = TsV2CatalogHandler(self.make_event(), mockS3, mockDb, mock_get_url, mock_download)
        converter.convert_catalog()

        self.assertS3EqualsApiJSON(mockS3, 'v2/ts/catalog.json')
        self.assertS3EqualsApiJSON(mockS3, 'v2/ts/obs/languages.json')
        self.assertS3EqualsApiJSON(mockS3, 'v2/ts/obs/en/resources.json')
        self.assertS3EqualsApiJSON(mockS3, 'v2/ts/obs/en/obs/source.json')
        # self.assertS3EqualsApiJSON(mockS3, 'v2/ts/obs/en/notes.json')
        # self.assertS3EqualsApiJSON(mockS3, 'v2/ts/obs/en/questions.json')
        # self.assertS3EqualsApiJSON(mockS3, 'v2/ts/obs/en/tw_cat.json')

        self.assertS3EqualsApiJSON(mockS3, 'v2/ts/1ch/languages.json')
        self.assertS3EqualsApiJSON(mockS3, 'v2/ts/1ch/en/resources.json')
        self.assertS3EqualsApiJSON(mockS3, 'v2/ts/1ch/en/ulb/source.json')
        # self.assertS3EqualsApiJSON(mockS3, 'v2/ts/1ch/en/notes.json')
        # self.assertS3EqualsApiJSON(mockS3, 'v2/ts/1ch/en/questions.json')
        # self.assertS3EqualsApiJSON(mockS3, 'v2/ts/1ch/en/tw_cat.json')

        self.assertS3EqualsApiJSON(mockS3, 'v2/ts/bible/en/words.json')