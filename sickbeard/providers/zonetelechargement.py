# coding=utf-8
# Author: djoole <bobby.djoole@gmail.com>
#
# URL: https://SickChill.github.io
#
# This file is part of SickChill.
#
# SickChill is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickChill is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickChill. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re
# import time
# import traceback
from sickbeard.common import USER_AGENT

import validators
from requests.compat import urljoin

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser
from sickchill.helper.common import convert_size, try_int
from sickchill.providers.ddl.DDLProvider import DDLProvider



class ZoneTelechargementProvider(DDLProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        DDLProvider.__init__(self, "ZoneTelechargement")

        self.cache = tvcache.TVCache(self, min_time=0)  # Only poll ZoneTelechargement every 10 minutes max

        self.urls = {'base_url': 'https://www.annuaire-telechargement.com/',
                     'search': 'https://www.annuaire-telechargement.com/index.php?do=search',
                     'rss': 'https://www.annuaire-telechargement.com/rss.xml'}

        self.url = self.urls['base_url']

        self.headers.update({'User-Agent': USER_AGENT})

        self.storageProviderAllow = {}


        self.titleVersion = {
            'vostfr': {
                'keywords': ["vostfr", "hdtv"],
                'suffix': 'VOSTFR.HDTV'
            },
            'vf': {
                'keywords': ["french", "hdtv"],
                'suffix': 'FRENCH.HDTV'
            },
            'vostfr-hd': {
                'keywords': ["720p","vostfr"],
                'suffix': 'VOSTFR.720P.HDTV.x264'
            },
            'vf-hd': {
                'keywords': ["french", "720p"],
                'suffix': 'FRENCH.720P.HDTV.x264'
            },
            'vostfr-1080p': {
                'keywords': ["vostfr", "hd1080p"],
                'suffix': 'VOSTFR.1080P.HDTV.x264'
            },
            'vf-1080p': {
                'keywords': ["french", "hd1080p"],
                'suffix': 'FRENCH.1080P.HDTV.x264'
            }
        }

    def getTitleVersion(self, x):
        return titleVersion.get(x, '')

    def canUseProvider(self, data):
        for key,value in self.storageProviderAllow.items():
            if key == data and value:
                return True
        return False


    def search(self, search_params, age=0, ep_obj=None):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        results = []

        for mode in search_params:
            # Don't support RSS
            if mode == 'RSS':
                continue

            items = []

            logger.log(u"Search Mode: {0}".format(mode), logger.DEBUG)

            for search_string in search_params[mode]:

                detectSeasonEpisode = re.search('(\d{1,2})[^\d]{1,2}(\d{1,2})(?:[^\d]{1,2}(\d{1,2}))?.*', search_string)
                seasonVersion = detectSeasonEpisode.group(1)
                episodeVersion = detectSeasonEpisode.group(2)

                search_string_for_url = search_string.replace(search_string.split(" ")[-1],"")

                logger.log(u"Search string: {0}".format
                           (search_string.decode("utf-8")), logger.DEBUG)

                logger.log(u"search_string_for_url: {0}".format
                           (search_string_for_url.decode("utf-8")), logger.DEBUG)

                search_urlS = [self.urls['search']]
                for search_url in search_urlS:

                    data = {}
                    data["do"] = "search"
                    data["subaction"] = "search"
                    data["story"] = search_string_for_url
                    data["catlist[]"] = "15,16,17,18,19,20,21"

                    dataSearch = self.get_url(search_url, post_data=data)
                    if not dataSearch:
                        continue

                    with BS4Parser(dataSearch, 'html5lib') as html:
                        serie_rows = html(class_=re.compile('cover_infos_title'))

                        for result_rows in serie_rows:
                            try:
                                links_page = result_rows.find_all('a')
                                logger.log(links_page[0].get('href'), logger.DEBUG)
                                
                                seasonNameDetect = links_page[0].get_text()
                                if not seasonNameDetect.find("Saison "+str(int(seasonVersion))) >= 0:
                                    continue

                                dataPage = self.get_url(links_page[0].get('href'), verify=False)
                                with BS4Parser(dataPage, 'html5lib') as htmlPage:
                                    url = links_page[0].get('href')
                                    title = ""
                                    for key, tv in self.titleVersion.items():
                                        if all(keyword in url for keyword in tv["keywords"]):
                                            title = search_string.replace(" ",".") +"."+ tv["suffix"]
                                            break;

                                    content_page = htmlPage(class_=re.compile('postinfo'))
                                    bTags = content_page[0].find_all('b')
                                    providerDDLName = ""
                                    for bTag in bTags:
                                        if self.canUseProvider(bTag.text):
                                            providerDDLName = bTag.text

                                        if  self.canUseProvider(providerDDLName) and \
                                            bTag.text.startswith("Episode "+str(int(episodeVersion))):
                                            providerDDLLink = bTag.find_all('a')[0]['href']
                                            logger.log(providerDDLName, logger.DEBUG)
                                            logger.log(title, logger.DEBUG)
                                            logger.log(providerDDLLink, logger.DEBUG)

                                            item = {'title': title, 'link': providerDDLLink}
                                            items.append(item)
                                            providerDDLName = ""

                            except Exception:
                                logger.log(u'Failed doing webui callback: {0}'.format(self.name), logger.ERROR)
            results += items

        return results

provider = ZoneTelechargementProvider()
