#!/usr/bin/env python3
from __future__ import print_function

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import os
import re
import sys
import subprocess
from pathlib import Path

import requests
from tqdm import tqdm

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

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
kaltura_host = 'cdnapisec.kaltura.com'

base_vault_url = "https://www.gdcvault.com"
gdc_url = 'https://www.gdcvault.com/free/gdc-18'

video_item_regexp = r"session_item.*href=\"(.*)\""
m3u8_file = "index_0_av.m3u8"

base_kaltura_url = "https://blaze-vh.akamaihd.net/i/kaltura/content/r71v1/entry/data/926/706/"
iframe_entryid_regexp = r"<iframe.*entry_id=(.*)&"
iframe_url_regexp = r"<iframe.*src=\"(.*)\".width"

playerconfig_regexp = r"window.kalturaIframePackageData = (.*);"

id_regexp = r"entryResult.*meta.*\"id\":\"(.*?)\",\""
entryid_regexp = r"playerConfig.*\"entryId\":\"(.*)\""
version_regexp = r"playerConfig.*\"version\":\"(.*)\""

def get_category_url(lbl):
    return gdc_url + '/?categories=' + lbl


def text(msg):
    print("[gdc-downloader] " + msg)


def error(message):
    print("[gdc-downloader] Error: " + message)
    sys.exit(1)


def message(msg):
    print("[gdc-downloader] Message: " + msg)


def download_file(fragments, name, folder):
    local_filename = folder + '/' + name

    if not os.path.exists(folder):
        os.makedirs(folder)

    final_file_name = folder + "/" + name.split(".")[0] + ".mp4"

    if os.path.exists(final_file_name):
        message(final_file_name + " already exists")

    index = 0
    concat_file = ""
    to_delete  = []
    for fragment in fragments:
        r = requests.get(fragment, stream=True)

        file_size = int(r.headers['Content-Length'])

        fragment_file = folder + '/' + str(index) + "_" + name

        if os.path.exists(fragment_file):
            message(fragment_file + " already exists, skipping")
            index += 1
            continue

        with open(fragment_file, 'wb+') as f:
            for data in tqdm(r.iter_content(chunk_size=1024), desc=fragment_file, leave=True, total=(file_size / 1024),
                             unit='KB'):
                if data:
                    f.write(data)

        fragment_abs_path = str(Path().absolute()) + "/" + fragment_file
        to_delete.append(fragment_file)
        concat_file += "file '" + fragment_abs_path + "'\n"
        index += 1

    with open(str(Path().absolute()) + "/" + folder + "/concat_list.txt", 'w+') as f:
        f.write(concat_file)

    process = subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', folder + "/concat_list.txt", "-c", "copy", final_file_name])

    if process.returncode is not 0:
        return ""

    # Clean up after
    for file in to_delete:
        os.remove(file)

    return local_filename


def download_url(url, referer=None, host=None):
    headers = {'User-Agent': user_agent}

    if host is not None:
        headers['Host'] = host

    if referer is not None:
        headers['Referer'] = referer

    req = Request(
        url,
        data=None,
        headers=headers
    )
    try:
        response = urlopen(req)
    except HTTPError as e:
        error("http error: " + "\"" + str(e) + "\"")
    except URLError as e:
        error("url error (make sure you're online): " + "\"" + str(e) + "\"")

    return response.read().decode('utf-8')


def get_video_list_urls(cat_url):
    html = download_url(cat_url)
    found = re.findall(video_item_regexp, html)
    return found


def get_video_fragments(link):
    page_url = base_vault_url + link
    html = download_url(page_url)

    iframe_url = re.search(iframe_url_regexp, html).group(1)
    iframe_content = download_url(iframe_url, host=kaltura_host, referer=page_url)

    playerconfig = json.loads(re.search(playerconfig_regexp, iframe_content).group(1))
    entry_id = playerconfig['playerConfig']['entryId']
    id = playerconfig['entryResult']['contextData']['flavorAssets'][0]['id']
    version = playerconfig['entryResult']['contextData']['flavorAssets'][0]['version']

    base_video_url = base_kaltura_url + entry_id + '_' + id + '_' + version + ".mp4/"
    m3u8_index = download_url(base_video_url + m3u8_file)
    return re.findall(base_video_url + '.*', m3u8_index)


def _main():
    for category in categories:
        cat_url = get_category_url(category)
        video_links = get_video_list_urls(cat_url)
        for link in video_links:
            fragments = get_video_fragments(link)
            file_name = link.split("/")[-1].replace('-', '') + '_' + link.split("/")[-2]
            if fragments:
                download_file(fragments, file_name + '.ts', '2018/' + categories[category])

    # for category in categories:
    #     cat_url = get_category_url(category)
    #     video_links = get_video_list_urls(cat_url)
    #
    #     for link in video_links:
    #         fragments = get_video_fragments(link)
    #         file_name = link.split("/")[-1].replace('-', '') + '_' + link.split("/")[-2]
    #         if fragments:
    #             download_file(fragments, file_name + '.mp4', '2018/' + categories[category])


if __name__ == "__main__":
    _main()
