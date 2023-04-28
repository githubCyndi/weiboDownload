# -*- coding: utf-8 -*-
"""
@Time ： 2023/4/25 15:50
@Auth ： recordCyndi
@File ：recordCyndiWeiboContent.py
@IDE ：PyCharm
"""

import json
import os
import requests
import datetime
import pymongo
import pymysql


class Cyndi(object):

    def __init__(self, headers, username_id):
        self.headers = headers
        self.username_id = username_id
        self.username = self.get_username()
        self.folder = self.username + "_" + self.username_id
        self.directory_name_time = self.get_directory_name()
        # self.directory_name = self.username + '_' + self.directory_name_time
        self.directory_name = '王心凌_20230427140625'
        # self.directory_name = '王心凌_20230305194836'
        self.create_folder(folder_name=f"{self.folder}/{self.directory_name}")
        # 数据库部分
        self.MONGODB_CONNECTION_STRING = "mongodb://localhost:27017"
        self.MONGODB_DATABASE = '微博-Cyndi'
        self.MONGODB_CLIENT = self.username + '_' + self.username_id + '_' + self.directory_name_time
        self.mongo_client = pymongo.MongoClient(self.MONGODB_CONNECTION_STRING)
        self.mongo_db = self.mongo_client[f"{self.MONGODB_DATABASE}"]
        self.mongo_collection = self.mongo_db[f"{self.MONGODB_CLIENT}"]

    def get_username(self):
        url = 'https://weibo.com/ajax/profile/info?uid=' + self.username_id
        response = requests.get(url=url, headers=self.headers)
        response.encoding = 'utf-8'
        return response.json().get('data').get('user').get('screen_name')

    def insert_pymongo(self):
        data = self.get_all_json_simplify_data()
        for key, value in data.items():
            self.mongo_collection.insert_one(value)

    def summary_insert_pymongo(self, json_data):
        for key, value in json_data.items():
            self.mongo_collection.insert_one(value)

    @staticmethod
    def get_directory_name():
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    def get_weibo_json_data(self, since_id: str):
        ajax_api = "https://weibo.com/ajax/statuses/mymblog?uid="
        url = ajax_api + str(self.username_id) + "&page=1&feature=0&since_id=" + str(since_id)
        response = requests.get(url=url, headers=self.headers)
        response.encoding = 'utf-8'
        next_id = "" if response.json().get('data', "").get('since_id', "") == "" \
            else response.json().get('data', "").get('since_id', "")
        try:
            return response.json(), next_id
        except Exception as e:
            print(next_id, e)
            return response.json(), next_id

    def get_all_json_simplify_data(self):
        data_list_dict = dict()
        for file in list(os.listdir(f"{self.folder}/{self.directory_name}")):
            data_list = self.read_json_data(filename=f"{self.folder}/{self.directory_name}/{file}").get('data', "").get(
                'list', '')
            for data in data_list:
                data_list_dict = self.get_weibo_simplify_json(data=data, data_list_dict=data_list_dict)
        self.write_json_data(filename=f"{self.folder}/{self.directory_name}_simplify.json", json_data=data_list_dict)
        return data_list_dict

    @staticmethod
    def replace_content(content: str):
        replace_year = content.replace(f'{content[-4:]}', "").replace(" ", "").replace('+0800', '').replace(":", "")
        replace_weekday = replace_year.replace(f'{replace_year[:3]}', "")
        replace_month = replace_weekday.replace('Jan', '01').replace('Feb', '02').replace('Mar', '03') \
            .replace('Apr', '04').replace('May', '05').replace('Jun', '06') \
            .replace('Jul', '07').replace('Aug', '08').replace('Sep', '09') \
            .replace('Oct', '10').replace('Nov', '11').replace('Dec', '12')
        return content[-4:] + replace_month

    def get_weibo_simplify_json(self, data: dict, data_list_dict: str):

        data_dict = dict()

        data_dict['user_screen_name'] = data.get('user', "").get('screen_name', "")
        origin_created_ed = data.get('created_at', "")
        created_ed = self.replace_content(content=origin_created_ed)
        data_dict['created_at'] = origin_created_ed
        data_dict['created_at'] = created_ed
        data_dict['text_raw'] = data.get('text_raw', "")
        data_dict['region_name'] = data.get('region_name', "")

        # image information
        if data.get('pic_infos', "") is not None and data.get('pic_infos', "") != "":
            image_dict = dict()
            for item, origin_image_id in enumerate(data.get('pic_ids', "")):
                image_name = created_ed + '_' + '{:0>2d}'.format(item + 1)
                image_dict[f"{image_name}"] = data.get('pic_infos', "").get(f'{origin_image_id}', "") \
                    .get('largest', "").get('url', '')
            data_dict['origin_image'] = image_dict
        else:
            data_dict['origin_image'] = ""

        # repost image_information
        retweeted_status = data.get('retweeted_status', "")
        if retweeted_status is not None and retweeted_status != "":
            retweeted_status_user = data.get('retweeted_status', "").get('user', "")
            retweeted_status_user_screen_name = retweeted_status_user.get('screen_name', "")
            data_dict['retweeted_status_user_screen_name'] = "null" if retweeted_status_user is None \
                else retweeted_status_user_screen_name
            retweeted_status_origin_create_at = retweeted_status.get('created_at', "")
            retweeted_status_created_ed = self.replace_content(content=retweeted_status_origin_create_at)
            data_dict['retweeted_status_origin_create_at'] = retweeted_status_origin_create_at
            data_dict['retweeted_status_created_ed'] = retweeted_status_created_ed
            data_dict['retweeted_status_text_raw'] = retweeted_status.get('text_raw', "")
            retweeted_status_pic_infos = retweeted_status.get('pic_infos', "")
            # 微博转发照片
            if retweeted_status_pic_infos is not None and retweeted_status_pic_infos != "":
                retweeted_status_dict = dict()
                for item, retweeted_status_image_id in enumerate(retweeted_status.get('pic_ids', "")):
                    retweeted_status_image_name = retweeted_status_created_ed + '_' + '{:0>2d}'.format(item + 1)
                    retweeted_status_dict[f"{retweeted_status_image_name}"] = retweeted_status.get('pic_infos', "").get(
                        f'{retweeted_status_image_id}', "").get('largest', "").get('url', '')
                data_dict['retweeted_status_repost_image'] = retweeted_status_dict
                del retweeted_status_dict
            else:
                data_dict['retweeted_status_repost_image'] = ""
        else:
            data_dict['retweeted_status_user_screen_name'] = ""
            data_dict['retweeted_status_created_ed'] = ""
            data_dict['retweeted_status_text_raw'] = ""
            data_dict['retweeted_status_repost_image'] = ""

        # 微博视频链接
        if data.get('page_info', "") is not None and data.get('page_info', "") != "":
            if data.get('retweeted_status', "") is not None and data.get('retweeted_status', "") != "":
                data_dict['微博视频链接'] = ""
                data_dict['转发视频链接'] = data.get('page_info', "").get('short_url', "")
            else:
                data_dict['微博视频链接'] = data.get('page_info', "").get('short_url', "")
                data_dict['转发视频链接'] = ""
        else:
            data_dict['微博视频链接'] = ""
            data_dict['转发视频链接'] = ""

        # 微博标签
        title = data.get('title', "")
        if title is not None and title != "":
            data_dict['title'] = title.get('text', "")
        else:
            data_dict['title'] = ""

        data_list_dict[f'{created_ed}'] = data_dict
        return data_list_dict

    def download_origin_image(self):
        self.create_folder(folder_name=f"{self.folder}/原创微博照片")
        json_data = self.read_json_data(filename=f"{self.folder}/{self.directory_name}_simplify.json")
        for key, value in json_data.items():
            if value['user_screen_name'] == self.username and value['user_screen_name'] != "" and value['origin_image'] != "":
                print(key, value)
                for image_name, image_url in value['origin_image'].items():
                    full_image_name = f"{self.folder}/原创微博照片" + '/' + value['user_screen_name'] + '_' + image_name + \
                                 os.path.splitext(image_url)[1]
                    print(full_image_name, image_url)
                    # self.download_images(url=image_url, image_name=full_image_name)

    def download_repost_image(self):
        self.create_folder(folder_name=f"{self.folder}/转发微博照片")
        json_data = self.read_json_data(filename=f"{self.folder}/{self.directory_name}_simplify.json")
        for key, value in json_data.items():
            # if value['user_screen_name'] != self.username:
            #     print(key, value['user_screen_name'])
            if value['user_screen_name'] != self.username and value['user_screen_name'] != "" and \
                    value['origin_image'] != "":
                for image_name, image_url in value['origin_image'].items():
                    full_image_name = f"{self.folder}/原创微博照片" + '/' + value['user_screen_name'] + '_' + image_name + \
                                 os.path.splitext(image_url)[1]
                    print(full_image_name, image_url)
            # if '赞' not in value['微博标签'] and value['微博转发照片'] != "":
            # if '赞' not in value['微博标签'] and value['微博转发照片'] != "" and key >= '20230324222233':
            #     for image_number, image_url in value['微博转发照片'].items():
            #         image_path = f"{self.folder}/转发微博照片" + '/' + value['微博转发用户'] + '_' + image_number + \
            #                      os.path.splitext(image_url)[1]
            #         self.download_images(url=image_url, image_name=image_path)

    def download_attitude_origin_image(self):
        self.create_folder(folder_name=f"{self.folder}/点赞原创微博照片")
        json_data = self.read_json_data(filename=f"{self.folder}/{self.directory_name}_simplify.json")
        for key, value in json_data.items():
            if '赞' in value['微博标签'] and value['微博原创照片'] != "":
                print(key, value)

    def download_attitude_repost_image(self):
        self.create_folder(folder_name=f"{self.folder}/点赞转发微博照片")
        json_data = self.read_json_data(filename=f"{self.folder}/{self.directory_name}_simplify.json")
        for key, value in json_data.items():
            if '赞' in value['微博标签'] and value['微博转发照片'] != "":
                print(key, value)

    def download_images(self, url: str, image_name: str):
        with open(file=image_name, mode="wb") as file:
            try:
                file.write(requests.get(url=url, headers=self.headers).content)
            except Exception as e:
                print(f"download {url} {image_name}, Exception: {e}")

    def download_weibo_json_data(self):
        response_json, next_id = self.get_weibo_json_data(since_id='0')
        number = 1
        while True:
            number_str = '{:0>3d}'.format(number)
            filename = f"{self.folder}/{self.directory_name}/{self.directory_name}_{number_str}.json"
            number += 1
            if next_id == "":
                self.write_json_data(filename=filename, json_data=response_json)
                break
            else:
                self.write_json_data(filename=filename, json_data=response_json)
            response_json, next_id = self.get_weibo_json_data(since_id=next_id)

    @staticmethod
    def write_json_data(filename: str, json_data: dict):
        with open(file=filename, mode="w", encoding="utf-8") as file:
            file.write(json.dumps(json_data, indent=4, ensure_ascii=False, sort_keys=True))

    @staticmethod
    def read_json_data(filename: str):
        with open(file=filename, mode="r", encoding="utf-8") as file:
            return json.loads(file.read())

    @staticmethod
    def create_folder(folder_name):
        if not os.path.isdir(folder_name):
            os.makedirs(name=folder_name)

    def deal_simplify_json(self):
        files = [file for file in os.listdir(f"{self.folder}") if 'simplify.json' in file]
        print(files)
        summary_json_data = dict()
        for file in files:
            file_data = self.read_json_data(filename=f"{self.folder}/{file}")
            for key, value in file_data.items():
                if key not in summary_json_data:
                    summary_json_data[f"{key}"] = value
            print(len(summary_json_data))
        self.write_json_data(filename=f"{self.folder}/summary.json", json_data=summary_json_data)
        self.summary_insert_pymongo(json_data=summary_json_data)

    @staticmethod
    def connect_pymysql():
        connect = pymysql.connect(
            host='127.0.0.1',
            user='root',
            passwd='Cyndi0905',
            port=3306,
            db='Cyndi0905',
            charset='utf8'
        )
        return connect


# 王心凌
USERNAME_ID = '1504965390'

COOKIE = """XSRF-TOKEN=IQb8K0nrlyfhkai01R0jTvL8; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9Wh_DjrvXOKyHIXlaDUe3f3j5JpX5KMhUgL.Fo-cS0M71K-N1h.2dJLoIEBLxKnL12-LB.eLxK.L1KeLB-qLxK-L1KMLBoeLxKqL1hnL1h5t; ALF=1685167429; SSOLoginState=1682575430; SCF=AjJULSaQQUvosuxxxcaYrL-SyW4ZI5A-gP8Pswg777FMsJBKg1tA6RWIzc5yJwEnLqG1GS8z9-H7OhTArwl3aqw.; SUB=_2A25JTmAWDeRhGeNI7FUR-SvLwzWIHXVqOtberDV8PUNbmtANLXLMkW9NSCXSXYUMfbmeeMbIA7IKdb-ChlWuNdbh; WBPSESS=-sDiyXGOExEGZ0l52dl4iSSE9VAIj3C2g4BSKiKO7E1YrCsyknTihx4fEVzcmE2WbhbgxPqg9gvSHCAWwszVJDelO9mjBpSIkIMYhxKU2EeRpY-xNwMSZeN1kH84-s0J-6NsmsE6akYLcbqBK5QlAw=="""
# COOKIE = """XSRF-TOKEN=YJbOOq8UTJuySjLVPPuE2K-g; SUB=_2A25JQ_zNDeRhGeNI7FUR-SvLwzWIHXVqOWkFrDV8PUNbmtANLWPakW9NSCXSXZPEklZJck51_8Cj_Z_qIalJJZVk; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9Wh_DjrvXOKyHIXlaDUe3f3j5JpX5KzhUgL.Fo-cS0M71K-N1h.2dJLoIEBLxKnL12-LB.eLxK.L1KeLB-qLxK-L1KMLBoeLxKqL1hnL1h5t; ALF=1713946653; SSOLoginState=1682410653; WBPSESS=-sDiyXGOExEGZ0l52dl4iSSE9VAIj3C2g4BSKiKO7E1YrCsyknTihx4fEVzcmE2WbhbgxPqg9gvSHCAWwszVJAcvnlewR3kYOhIJbBRE4OchnjaFzpznDWYB_y9TF8FQ6RCt2Gu-rtHn7fy98Le6HA=="""

HEADERS = {
    "authority": "weibo.com",
    "method": "GET",
    "path": "/ajax/profile/info?uid=" + USERNAME_ID + '&page=1&feature=0',
    "scheme": "https",
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "zh-CN,zh;q=0.9",
    "client-version": "v2.36.23",
    "cookie": COOKIE,
    "referer": "https://weibo.com/u/" + USERNAME_ID + '?tabtype=feed',
    "sec-ch-ua": '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "server-version": "v2022.11.18.1",
    "traceparent": "00-24fd75d3c60548c0bf2d9ecb5e31cf1e-3327ff46bc66421c-00",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/109.0.0.0 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
    "x-xsrf-token": "UQ5KoTFGg4UcPLLaCR-YbOjK",
}

cyndi = Cyndi(headers=HEADERS, username_id=USERNAME_ID)
# 加上一个筛选时间
# cyndi.download_weibo_json_data()
# 处理微博数据
# result = cyndi.get_all_json_simplify_data()
# 多个 simplify 文件的处理
# cyndi.deal_simplify_json()
# cyndi.insert_pymongo()
# cyndi.download_origin_image()
cyndi.download_repost_image()
# cyndi.download_attitude_origin_image()
# cyndi.download_attitude_repost_image()
