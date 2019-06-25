#!/usr/bin/env python3
from __future__ import print_function

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import os
import re
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
kaltura_host = "cdnapisec.kaltura.com"
kaltura_origin = 'https://cdnapisec.kaltura.com'

base_vault_url = "https://www.gdcvault.com"
gdc_url = 'https://www.gdcvault.com/free/gdc-19'

video_item_regexp = r"session_item.*href=\"(.*)\""
m3u8_file = "index_0_av.m3u8"

base_kaltura_url = "https://blaze-vh.akamaihd.net/i/kaltura/content/r71v1/entry/data/974/192/"
iframe_entryid_regexp = r"<iframe.*entry_id=(.*)&"
iframe_url_regexp = r"<iframe.*src=\"(.*)\".width"

playerconfig_regexp = r"window.kalturaIframePackageData = (.*);"

id_regexp = r"entryResult.*meta.*\"id\":\"(.*?)\",\""
entryid_regexp = r"playerConfig.*\"entryId\":\"(.*)\""
version_regexp = r"playerConfig.*\"version\":\"(.*)\""


def get_category_url(lbl):
    return gdc_url + '/?categories=' + lbl + "&media=v"


def text(msg):
    print("[gdc-downloader] " + msg)


def error(message):
    print("[gdc-downloader] Error: " + message)
    raise


def message(msg):
    print("[gdc-downloader] Message: " + msg)


def download_file(fragments, name, folder):
    local_filename = folder + '/' + name

    if not os.path.exists(folder):
        os.makedirs(folder)

    final_file_name = folder + "/" + name.split(".")[0] + ".mp4"

    if os.path.exists(final_file_name):
        message(final_file_name + " already exists")
        return

    index = 0
    concat_file = ""
    to_delete = []
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

    concat_file = folder + "/concat_list.txt"
    process = subprocess.run(
        ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_file, "-c", "copy", final_file_name])

    if process.returncode is not 0:
        return ""

    # Clean up after
    for file in to_delete:
        os.remove(file)

    os.remove(concat_file)

    return local_filename


def download_url(url, referer=None, origin=None, host=None):
    headers = {'User-Agent': user_agent}

    if origin is not None:
        headers['Origin'] = origin

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
    message("Downloading: " + link)

    # i.e. 'https://www.gdcvault.com/play/1026394/Accessible-Player-Experiences-A-New'
    page_url = base_vault_url + link
    html = download_url(page_url)

    if not re.search(iframe_url_regexp, html):
        message("File download failed, try again later.")
        return None

    iframe_url = re.search(iframe_url_regexp, html).group(1)
    try:
        iframe_content = download_url(iframe_url, origin=kaltura_origin, referer=page_url, host=kaltura_host)
    except:
        message("Failed to get the content page.")
        return None

    playerconfig = json.loads(re.search(playerconfig_regexp, iframe_content).group(1))
    entry_id = playerconfig['playerConfig']['entryId']
    flavorsId = playerconfig['entryResult']['contextData']['flavorAssets'][0]['id']

    maifest_url = "https://cdnapisec.kaltura.com/p/1670711/sp/167071100/playManifest/entryId/" + entry_id + "/flavorIds/"+ flavorsId +"/format/applehttp/protocol/https/a.m3u8?referrer=aHR0cHM6Ly9nZGN2YXVsdC5jb20=&clientTag=html5:v2.76&uiConfId=43558772&responseFormat=jsonp&callback="
    manifest = download_url(maifest_url)
    manifest_result = json.loads(manifest.replace('(', '').replace(')', ''))

    # i.e. https://blaze-vh.akamaihd.net/i/kaltura/content/r71v1/entry/data/974/192/0_rw01g00j_0_doglll3b_2.mp4/master.m3u8
    m3u8_url = manifest_result['flavors'][0]['url']

    # i.e. https://blaze-vh.akamaihd.net/i/kaltura/content/r71v1/entry/data/974/192/0_rw01g00j_0_doglll3b_2.mp4/
    base_video_url = m3u8_url.replace("master.m3u8", "")

    # i.e. https://blaze-vh.akamaihd.net/i/kaltura/content/r71v1/entry/data/974/192/0_rw01g00j_0_doglll3b_2.mp4/index_0_av.m3u8
    m3u8_index= download_url(m3u8_url.replace("master.m3u8", "index_0_av.m3u8"))

    return re.findall(base_video_url + '.*', m3u8_index)


def _main():
    for category in categories:

        message("Downloading videos from: " + categories[category])
        cat_url = get_category_url(category)
        video_links = get_video_list_urls(cat_url)
        for link in video_links:

            # i.e. 2019/Advocacy
            folder_name = '2019/' + categories[category]

            if not os.path.exists(folder_name):
                os.makedirs(folder_name)

            # i.e. AccessiblePlayerExperiencesANew_1026394.mp4
            file_name = link.split("/")[-1].replace('-', '') + '_' + link.split("/")[-2].split(".")[0] + ".mp4"

            if os.path.exists(folder_name + '/' + file_name):
                message(file_name + " already exists")
                continue

            fragments = get_video_fragments(link)
            if not fragments:
                continue

            if fragments:
                download_file(fragments, file_name + '.ts', folder_name)


if __name__ == "__main__":
    _main()
