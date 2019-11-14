from __future__ import print_function
from urllib2 import Request, HTTPError, URLError

import requests
import os
import re
import sys
from urlparse import urlparse
from tqdm import tqdm
from urllib import urlopen

categories = {
    'Ad': 'Advocacy',
    'Ai': 'AI',
    'Au': 'Audio',
    'Bm': 'Business & Marketing',
    'Cm': 'Community Management',
    'De': 'Design',
    'Es': 'eSports',
    'Ed': 'Game Career - Education',
    'Gn': 'Game Narrative',
    'In': 'Indipendent Games',
    'Lq': 'Localization - QA',
    'Mo': 'Monetization',
    'Or': 'Other',
    'Pr': 'Production',
    'Pg': 'Programming',
    'Sg': 'Serious Games',
    'Ta': 'Smartphone - Table Games',
    'On': 'Social - Online Games',
    'Vr': 'Virtual - Augmented Reality',
    'Va': 'Visual Arts'}

base_vault_url = "http://www.gdcvault.com"
gdc_url = 'http://www.gdcvault.com/free/gdc-17'
ds_url = 'http://s3-2u.digitallyspeaking.com/'
xml_url = 'http://evt.dispeak.com/ubm/gdc/sf17/xml/'

# possible values 500,1300
quality = '500'

video_item_regexp = r"session_item.*href=\"(.*)\""
video_player_regexp = r"<iframe.*player.html.xml=(.*).xml"
pdf_regexp = r"<iframe.*player.html.xml=(.*).xml"


def get_category_url(lbl):
    return gdc_url + '/?categories=' + lbl


def text(msg):
    print("[gdc-downloader] " + msg)


def error(message):
    print("[gdc-downloader] Error: " + message)
    sys.exit(1)


def message(msg):
    print("[gdc-downloader] Message: " + msg)


def download_file(url, name, folder):
    local_filename = folder + '/' + name
    r = requests.get(url, stream=True)

    file_size = int(r.headers['Content-Length'])

    if not os.path.exists(folder):
        os.makedirs(folder)

    if os.path.exists(local_filename):
        message(local_filename + " already exists, skipping")
        return

    with open(local_filename, 'wb') as f:
        for data in tqdm(r.iter_content(chunk_size=1024), desc=local_filename, leave=True, total=(file_size / 1024),
                         unit='KB'):
            if data:
                f.write(data)

    return local_filename


def download_url(url):
    try:
        response = urlopen(url)
    except HTTPError as e:
        error("http error: " + "\"" + str(e) + "\"")
    except URLError as e:
        error("url error (make sure you're online): " + "\"" + str(e) + "\"")

    return response.read()


def get_video_list_urls(catUrl):
    html = download_url(catUrl)
    found = re.findall(video_item_regexp, html)
    return found


def get_video_url(link):
    html = download_url(base_vault_url + link)
    found = re.search(video_player_regexp, html)

    if not found:
        return None

    video_xml = found.group(1)
    xml = download_url(xml_url + video_xml + '.xml')

    found = re.search('(asset.*' + video_xml + '.*' + quality + '\.mp4)', xml)

    if found is not None:
        return ds_url + found.group(0)
    else:
        return None


def _main():
    for category in categories:
        cat_url = get_category_url(category)
        video_links = get_video_list_urls(cat_url)

        for link in video_links:
            video_url = get_video_url(link)
            file_name = link.split("/")[-1].replace('-', '') + '_' + link.split("/")[-2]
            if video_url is not None:
                download_file(video_url, file_name + '.mp4', '2017/' + categories[category])


if __name__ == "__main__":
    _main()
