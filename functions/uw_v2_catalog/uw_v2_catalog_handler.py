# -*- coding: utf-8 -*-

#
# Class for converting the catalog into a format compatible with the v2 api.
#

import time
from datetime import datetime
import pytz
import json
import tempfile
import os
from tools.file_utils import write_file
from d43_aws_tools import S3Handler
from tools.dict_utils import read_dict
from tools.url_utils import download_file, get_url

def datestring_to_timestamp(datestring):
    # TRICKY: force all datestamps to PST to normalize unit tests across servers.
    tz = pytz.timezone("US/Pacific")
    return str(int(time.mktime(tz.localize(datetime.strptime(datestring[:10], "%Y-%m-%d")).timetuple())))

class UwV2CatalogHandler:

    cdn_root_path = 'v2/uw'

    def __init__(self, event, s3_handler=None, url_handler=None, download_handler=None):
        """
        Initializes the converter with the catalog from which to generate the v2 catalog
        :param event:
        :param s3_handler: This is passed in so it can be mocked for unit testing
        :param url_handler: This is passed in so it can be mocked for unit testing
        :param download_handler: This is passed in so it can be mocked for unit testing
        """
        env_vars = read_dict(event, 'stage-variables', 'payload')
        self.catalog_url = read_dict(env_vars, 'catalog_url', 'Environment Vars')
        self.cdn_bucket = read_dict(env_vars, 'cdn_bucket', 'Environment Vars')
        self.cdn_url = read_dict(env_vars, 'cdn_url', 'Environment Vars')
        self.cdn_url = self.cdn_url.rstrip('/')
        if not s3_handler:
            self.cdn_handler = S3Handler(self.cdn_bucket)
        else:
            self.cdn_handler = s3_handler
        self.temp_dir = tempfile.mkdtemp('', 'uwv2', None)
        if not url_handler:
            self.get_url = get_url
        else:
            self.get_url = url_handler
        if not download_handler:
            self.download_file = download_file
        else:
            self.download_file = download_handler

    def convert_catalog(self):
        """
        Generates the v2 catalog
        :return: the v2 form of the catalog
        """
        uploads = []
        v2_catalog = {
            'obs': {},
            'bible': {}
        }

        res_map = {
            'ulb': 'bible',
            'udb': 'bible',
            'obs': 'obs'
        }

        title_map = {
            'bible': 'Bible',
            'obs': 'Open Bible Stories'
        }

        last_modified = 0

        # retrive the latest catalog
        catalog_content = self.get_url(self.catalog_url, True)
        if not catalog_content:
            print("ERROR: {0} does not exist".format(self.catalog_url))
            return False
        try:
            self.latest_catalog = json.loads(catalog_content)
        except Exception as e:
            print("ERROR: Failed to load the catalog json: {0}".format(e))
            return False

        # walk catalog
        for lang in self.latest_catalog['languages']:
            lang_slug = lang['identifier']
            for res in lang['resources']:
                res_id = res['identifier']
                print(res_id)
                key = res_map[res_id] if res_id in res_map else None

                if not key:
                    continue

                mod = datestring_to_timestamp(res['modified'])

                if int(mod) > last_modified:
                    last_modified = int(mod)

                toc = []
                for proj in res['projects']:
                    if 'formats' in proj and proj['formats']:
                        format = proj['formats'][0]
                        # TRICKY: obs must be converted to json
                        if res_id == 'obs':
                            # TODO: generate obs json source
                            # TRICKY: the obs json will have already been generated by the ts api
                            format = {
                                'url': '{}/en/udb/v4/obs.json'.format(self.cdn_url),
                                'signature': '{}/en/udb/v4/obs.json.sig'.format(self.cdn_url)
                            }
                        toc.append({
                            'desc': '',
                            'media': {
                                'audio': {},
                                'video': {}
                            },
                            'mod': mod,
                            'slug': proj['identifier'],
                            'src': format['url'],
                            'src_sig': format['signature'],
                            'title': proj['title'],
                        })
                    else:
                        print('WARNING: skipping lang:{} proj:{} because no formats were found'.format(lang_slug, proj['identifier']))

                source = res['source'][0]
                comment = ''
                if 'comment' in res:
                    comment = res['comment']
                res_v2 = {
                    'slug': res_id,
                    'name': res['title'],
                    'mod': mod,
                    'status': {
                        'checking_entity': '; '.join(res['checking']['checking_entity']),
                        'checking_level': res['checking']['checking_level'],
                        'comments': comment,
                        'contributors': '; '.join(res['contributor']),
                        'publish_date': res['issued'],
                        'source_text': source['identifier'] + '-' + source['language'],
                        'source_text_version': source['version'],
                        'version': res['version']
                    },
                    'toc': toc
                }

                if not lang_slug in v2_catalog[key]:
                    v2_catalog[key][lang_slug] = {
                        'lc': lang_slug,
                        'mod': mod,
                        'vers': []
                    }
                v2_catalog[key][lang_slug]['vers'].append(res_v2)

        # condense catalog
        catalog = {
            'cat': [],
            'mod': last_modified
        }
        for cat_slug in v2_catalog:
            langs = []
            for lang_slug in v2_catalog[cat_slug]:
                langs.append(v2_catalog[cat_slug][lang_slug])

            catalog['cat'].append({
                'slug': cat_slug,
                'title': title_map[cat_slug],
                'langs': langs
            })


        uploads.append(self._prep_data_upload('catalog.json', catalog))

        # upload files
        for upload in uploads:
            self.cdn_handler.upload_file(upload['path'], '{}/{}'.format(UwV2CatalogHandler.cdn_root_path, upload['key']))

    def _prep_data_upload(self, key, data):
        """
        Prepares some data for upload to s3
        :param key:
        :param data:
        :return:
        """
        temp_file = os.path.join(self.temp_dir, key)
        write_file(temp_file, json.dumps(data, sort_keys=True))
        return {
            'key': key,
            'path': temp_file
        }