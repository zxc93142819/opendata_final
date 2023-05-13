import copy
from transitions.extensions import GraphMachine
import os
import sys
import json
from flask import Flask, jsonify, request, abort, send_file
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
from utils import send_text_message
from geopy.geocoders import Nominatim
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pyimgur
import message_template
from urllib.parse import quote
import random
load_dotenv()

# TDX
app_id = 'f74096124-772963e1-9c77-4bc4'
app_key = '40db7be0-1789-437d-939b-63997dcbc8aa'

auth_url="https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
url = "https://tdx.transportdata.tw/api/basic/v2/Tourism/ScenicSpot/"
class Auth():

    def __init__(self, app_id, app_key):
        self.app_id = app_id
        self.app_key = app_key

    def get_auth_header(self):
        content_type = 'application/x-www-form-urlencoded'
        grant_type = 'client_credentials'

        return{
            'content-type' : content_type,
            'grant_type' : grant_type,
            'client_id' : self.app_id,
            'client_secret' : self.app_key
        }

class data():

    def __init__(self, app_id, app_key, auth_response):
        self.app_id = app_id
        self.app_key = app_key
        self.auth_response = auth_response

    def get_data_header(self):
        auth_JSON = json.loads(self.auth_response.text)
        access_token = auth_JSON.get('access_token')

        return{
            'authorization': 'Bearer '+ access_token
        }

channel_secret = os.environ.get("LINE_CHANNEL_SECRET")
channel_access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")


country_name = ["南投縣" , "嘉義市" , "嘉義縣" , "基隆市" , "宜蘭縣" , "屏東縣" , 
                "彰化縣" , "新北市" , "新竹市" , "新竹縣" , "桃園市" , "澎湖縣" , 
                "臺中市" , "臺北市" , "臺南市" , "臺東縣" , "花蓮縣" , "苗栗縣" , 
                "連江縣" , "金門縣" , "雲林縣" , "高雄市"]

english_name = ["NantouCounty" , "Chiayi" , "ChiayiCounty" , "Keelung" , "YilanCounty" , "PingtungCounty",
                "ChanghuaCounty" , "NewTaipei" , "Hsinchu" , "HsinchuCounty" , "Taoyuan" , "PenghuCounty" , 
                "Taichung" , "Taipei" , "Tainan" , "TaitungCounty" , "HualienCounty" , "MiaoliCounty" ,
                "LienchiangCounty" , "KinmenCounty" , "YunlinCounty" , "Kaohsiung"]

keyword = {}
search_imageurl = {}
search_website = {}
search_address = {}
search_detail = {}
search_name = {}
index = {}

favorite_imageurl = {}
favorite_detail = {}
favorite_website = {}
favorite_address = {}
favorite_name = {}
favorite_index = {}

def get_restaurant_now(user_id):
    id = 0
    key = keyword[user_id]
    key_index = country_name.index(key)
    global url
    temp_url = url
    temp_url = temp_url + english_name[key_index] + "?$top=50&$format=JSON"
    print(temp_url)
    try:
        d = data(app_id, app_key, auth_response)
        data_response = requests.get(temp_url, headers=d.get_data_header())
    except:
        a = Auth(app_id, app_key)
        auth_response = requests.post(auth_url, a.get_auth_header())
        d = data(app_id, app_key, auth_response)
        data_response = requests.get(temp_url, headers=d.get_data_header())
    search_data = json.loads(data_response.text)

    random_numbers = random.sample(range(0, 50), 10)
    spe_search_imageurl = []
    # 以後做map 查詢距離
    # spe_search_website = []
    spe_search_address = []
    spe_search_name = []
    spe_search_detail = []
    for i in random_numbers :
        # # 初始化Nominatim geocoder
        # geolocator = Nominatim(user_agent="my_app")

        # # 定義經緯度
        # latitude, longitude = data[i]["Position"]["PositionLat"] , data[i]["Position"]["PositionLon"]
        # # 透過geolocator.reverse()方法來將經緯度轉換為地址
        # location = geolocator.reverse(f"{latitude}, {longitude}")

        # 輸出轉換後的地址
        spe_search_name.append(search_data[i]["ScenicSpotName"])
        spe_search_address.append("https://www.google.com/maps/place?q=" + search_data[i]["ScenicSpotName"])
        spe_search_imageurl.append(search_data[i]["Picture"]["PictureUrl1"])
        # spe_search_detail.append(search_data[i]["DescriptionDetail"])
        spe_search_detail.append("介紹啦")
        id += 1
    search_imageurl.update( {user_id : spe_search_imageurl} )
    search_address.update({user_id : spe_search_address})
    search_name.update({user_id : spe_search_name})
    search_detail.update({user_id : spe_search_detail})
    index.update( {user_id : id} )

class TocMachine(GraphMachine):
    def __init__(self, **machine_configs):
        self.machine = GraphMachine(model=self, **machine_configs)

    def is_going_to_menu(self, event):
        text = event.message.text
        return text == "主選單"

    def is_going_to_show_fsm_pic(self, event):
        text = event.message.text
        return text.lower() == "fsm"
    
    def is_going_to_stock_input_key(self , event):
        user_id = event.source.user_id
        key = event.message.text
        if(key not in country_name) :
            return True
        else :
            return False

    def is_going_to_search_restaurant(self, event):
        user_id = event.source.user_id
        key = event.message.text
        if(key in country_name) :
            global keyword
            keyword.update( { user_id : key } )
            return True
        else :
            return False
        
    def is_going_to_show_detail(self , event) :
        key = event.message.text
        return key == "了解景點介紹"

    def on_enter_input_key(self, event):
        send_text_message(event.reply_token, '請輸入你現在想去哪裡(請輸入正確的縣市名稱，且"台"請寫"臺"，例如臺北市、澎湖縣等等)')

    def on_enter_stock_input_key(self, event):
        send_text_message(event.reply_token, '輸入錯誤，請輸入你現在想去哪裡(請輸入正確的縣市名稱，且"台"請寫"臺"，例如臺北市、澎湖縣等等)')

    # back------------------------------------------------------
    def is_going_to_back_input_key(self , event):
        text = event.message.text
        return text == "返回重新輸入查詢縣市"

    def is_going_to_show_search_result(self , event):
        text = event.message.text
        return text == "返回查詢結果"

    def is_going_to_back_show_favorite(self , event):
        text = event.message.text
        return text == "返回我的最愛清單"
    # ---------------------------------------------------------

    def is_going_to_input_key(self , event):
        text = event.message.text
        return text == "查詢景點資訊"

    def is_going_to_introduction(self, event):
        text = event.message.text
        return text == "功能介紹與使用說明"

    def on_enter_menu(self, event):
        reply_token = event.reply_token
        message = message_template.main_menu
        message_to_reply = FlexSendMessage("開啟主選單", message)
        line_bot_api = LineBotApi( channel_access_token )
        line_bot_api.reply_message(reply_token, message_to_reply)
    
    def on_enter_show_fsm_pic(self, event):
        reply_token = event.reply_token
        message = message_template.show_pic
        message_to_reply = FlexSendMessage("查看fsm結構圖", message)
        line_bot_api = LineBotApi( channel_access_token )
        line_bot_api.reply_message(reply_token, message_to_reply)

    def on_enter_show_search_result(self , event):
        reply_token = event.reply_token
        user_id = event.source.user_id

        id = index[user_id]
        img_array = search_imageurl[user_id]
        name_array = search_name[user_id]
        # website_array = search_website[user_id]
        detail_array = search_detail[user_id]
        address_array = search_address[user_id]

        if id != 0 :
            message = message_template.site_list
            message["contents"].clear()
            first_message = copy.deepcopy(message_template.site_first_item)
            msg = "共查到" + str(id) + "處符合的景點(最多10處)"
            first_message["body"]["contents"][0]["text"] = msg
            message["contents"].append(first_message)
            for i in range (id):
                new_message = copy.deepcopy(message_template.site_item)
                new_message["hero"]["url"] = img_array[i]
                new_message["body"]["contents"][0]["text"] = name_array[i]
                new_message["body"]["contents"][1]['action']["uri"] = address_array[i]
                new_message["body"]["contents"][2]['action']["data"] = str(i)
                # record data
                new_message["footer"]["contents"][0]['action']["data"] = "加入最愛," + img_array[i] + "," + name_array[i] + "," + address_array[i] + "," + detail_array[i]
                message["contents"].append(new_message)
            message_to_reply = FlexSendMessage("查詢景點資訊", message)
            line_bot_api = LineBotApi( channel_access_token )
            line_bot_api.reply_message(reply_token, message_to_reply)
        else :
            message_to_reply = FlexSendMessage("查詢景點資訊", message_template.no_result)
            line_bot_api = LineBotApi( channel_access_token )
            line_bot_api.reply_message(reply_token, message_to_reply)

    def on_enter_search_restaurant(self, event):
        reply_token = event.reply_token
        user_id = event.source.user_id
        get_restaurant_now(user_id)

        id = index[user_id]
        img_array = search_imageurl[user_id]
        name_array = search_name[user_id]
        # website_array = search_website[user_id]
        detail_array = search_detail[user_id]
        address_array = search_address[user_id]

        if id != 0 :
            message = message_template.site_list
            message["contents"].clear()
            first_message = copy.deepcopy(message_template.site_first_item)
            msg = "共查到" + str(id) + "處符合的景點(最多10處)"
            first_message["body"]["contents"][0]["text"] = msg
            message["contents"].append(first_message)
            for i in range (id):
                new_message = copy.deepcopy(message_template.site_item)
                new_message["hero"]["url"] = img_array[i]
                new_message["body"]["contents"][0]["text"] = name_array[i]
                new_message["body"]["contents"][1]['action']["uri"] = address_array[i]
                new_message["body"]["contents"][2]['action']["data"] = str(i)
                # record data
                new_message["footer"]["contents"][0]['action']["data"] = "加入最愛," + img_array[i] + "," + name_array[i] + "," + address_array[i] + "," + detail_array[i]
                message["contents"].append(new_message)

            print(reply_token)
            message_to_reply = FlexSendMessage("查詢景點資訊", message)
            line_bot_api = LineBotApi( channel_access_token )
            line_bot_api.reply_message(reply_token, message_to_reply)
            print("幹")
        else :
            message_to_reply = FlexSendMessage("查詢景點資訊", message_template.no_result)
            line_bot_api = LineBotApi( channel_access_token )
            line_bot_api.reply_message(reply_token, message_to_reply)

    # 加入最愛-----------------------------------------------------------------------
    def is_going_to_add_favorite(self , event):
        text = event.postback.data
        add_or_delete = text.split(',')[0]
        return add_or_delete == '加入最愛'

    def on_enter_add_favorite(self, event):
        user_id = event.source.user_id
        reply_token = event.reply_token
        image = event.postback.data.split(',')[1]
        name = event.postback.data.split(',')[2]
        address = event.postback.data.split(',')[3]
        detail = event.postback.data.split(',')[4]
        global search_detail
        global search_address
        global search_name
        global search_imageurl

        has_data = False
        global favorite_index
        index = 0
        msg = ""

        name_array = []
        img_array = []
        address_array = []
        detail_array = []
        # web_array = []
        if favorite_index.__contains__(user_id):
            index = favorite_index[user_id]
            name_array = favorite_name[user_id]
            img_array = favorite_imageurl[user_id]
            address_array = favorite_address[user_id]
            detail_array = favorite_detail[user_id]
            # web_array = favorite_website[user_id]

        for tmp_name in name_array :
            if tmp_name == name :
                msg = '已在我的最愛!'
                has_data = True
                break
        if has_data == False :
            if index < 10:
                img_array.append(image)
                name_array.append(name)
                address_array.append(address)
                detail_array.append(detail)
                # web_array.append(website)
                index += 1
                msg = '成功加入我的最愛'
            else:
                msg = '我的最愛已滿(最多10個)'
    
        favorite_imageurl.update( {user_id : img_array} )
        # favorite_website.update({user_id : web_array})
        favorite_address.update({user_id : address_array})
        favorite_name.update({user_id : name_array})
        favorite_detail.update({user_id : detail_array})
        favorite_index.update( {user_id : index} )

        message = message_template.add_reply
        message["body"]["contents"][0]["text"] = msg
        message_to_reply = FlexSendMessage("加入最愛", message)
        line_bot_api = LineBotApi( channel_access_token )
        line_bot_api.reply_message(reply_token, message_to_reply)
    # ----------------------------------------------------------------------------------------------------
    
    # 查詢最愛-----------------------------------------------------------------------
    def is_going_to_show_favorite(self , event):
        text = event.message.text
        return text == "查看我的最愛"

    def on_enter_show_favorite(self, event):
        user_id = event.source.user_id
        reply_token = event.reply_token
        global favorite_index

        index = 0
        name_array = []
        img_array = []
        address_array = []
        detail_array = []
        # web_array = []
        if favorite_index.__contains__(user_id):
            index = favorite_index[user_id]
            name_array = favorite_name[user_id]
            img_array = favorite_imageurl[user_id]
            address_array = favorite_address[user_id]
            detail_array = favorite_detail[user_id]
            # web_array = favorite_website[user_id]

        if index != 0 :
            message = message_template.site_list
            message["contents"].clear()
            first_message = copy.deepcopy(message_template.site_first_favorite)
            msg = "共查到" + str(index) + "處您儲存的最愛景點(最多10處)"
            first_message["body"]["contents"][0]["text"] = msg
            message["contents"].append(first_message)
            for i in range (index):
                new_message = copy.deepcopy(message_template.favorite_item)
                new_message["hero"]["url"] = img_array[i]
                new_message["body"]["contents"][0]["text"] = name_array[i]
                new_message["body"]["contents"][1]["contents"][0]["contents"][1]["text"] = address_array[i]
                new_message["body"]["contents"][1]["contents"][1]["contents"][1]["text"] = detail_array[i]
                # record data
                new_message["footer"]["contents"][0]['action']["data"] = "從我的最愛移除," + name_array[i]
                message["contents"].append(new_message)
            message_to_reply = FlexSendMessage("查詢我的最愛", message)
            line_bot_api = LineBotApi( channel_access_token )
            line_bot_api.reply_message(reply_token, message_to_reply)
        else :
            message_to_reply = FlexSendMessage("查詢我的最愛", message_template.no_favorite)
            line_bot_api = LineBotApi( channel_access_token )
            line_bot_api.reply_message(reply_token, message_to_reply)
    # ----------------------------------------------------------------------------------------------------

    # 刪除最愛-----------------------------------------------------------------------
    def is_going_to_delete_favorite(self , event):
        text = event.postback.data
        add_or_delete = text.split(',')[0]
        return add_or_delete == '從我的最愛移除'

    def on_enter_delete_favorite(self, event):
        user_id = event.source.user_id
        reply_token = event.reply_token
        name = event.postback.data.split(',')[1]

        has_data = False
        global favorite_index
        msg = ""

        index = 0
        name_array = []
        img_array = []
        address_array = []
        detail_array = []
        item_index = -1
        # web_array = []
        if favorite_index.__contains__(user_id):
            index = favorite_index[user_id]
            name_array = favorite_name[user_id]
            img_array = favorite_imageurl[user_id]
            address_array = favorite_address[user_id]
            detail_array = favorite_detail[user_id]
            # web_array = favorite_website[user_id]

        for tmp_name in name_array :
            if tmp_name == name :
                item_index = name_array.index(name)
                has_data = True
                break
        if has_data == True :
            if index > 0:
                img_array.pop(item_index)
                name_array.pop(item_index)
                address_array.pop(item_index)
                detail_array.pop(item_index)
                # web_array.pop(item_index)
                index -= 1
                msg = '成功從我的最愛中移除'
            else :
                msg = "我的最愛中無資料哦~"
        else :
            msg = "我的最愛中無此資料哦~"

        favorite_imageurl.update( {user_id : img_array} )
        # favorite_website.update({user_id : web_array})
        favorite_address.update({user_id : address_array})
        favorite_name.update({user_id : name_array})
        favorite_detail.update({user_id : detail_array})
        favorite_index.update( {user_id : index} )

        message = message_template.delete_reply
        message["body"]["contents"][0]["text"] = msg
        message_to_reply = FlexSendMessage("加入最愛", message)
        line_bot_api = LineBotApi( channel_access_token )
        line_bot_api.reply_message(reply_token, message_to_reply)
    # ----------------------------------------------------------------------------------------------------
    
    def on_enter_introduction(self, event):
        reply_token = event.reply_token
        message = message_template.introduction_message
        message_to_reply = FlexSendMessage("功能介紹與使用說明", message)
        line_bot_api = LineBotApi( channel_access_token )
        line_bot_api.reply_message(reply_token, message_to_reply)

