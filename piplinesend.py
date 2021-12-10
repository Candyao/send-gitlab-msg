#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor
import hug
executor = ThreadPoolExecutor(2)
from telegram import Bot
from telegram import ParseMode
import configparser
import json

conf=configparser.ConfigParser()
conf.read("config.ini",encoding="utf-8")


def get_bot():
    token=conf.get("COMMON","bot_token")
    bot = Bot(token=token)
    return bot

class CiCd:
    def __init__(self, data):
        self.data=data
        self.stages=data['object_attributes']['stages']

    def dic_stage(self):
        list_state={}
        for i in range(len(self.stages)):
            list_state[self.stages[i]]=[]
        return list_state

    def check_status(self):
        pipline_status=self.data['object_attributes']['status']
        if pipline_status=="failed":
            pipline_status="❌ "
        elif pipline_status=="success":
            pipline_status="✅ "
        else:
            return False
        return pipline_status

    def get_msg(self):
        self.pipline_satus=self.check_status()
        if self.pipline_satus:
            try:
                self.project_url=self.data['project']['web_url']
                self.project_name=self.data['project']['name']
                self.commit_title=self.data['commit']['title']
                self.commit_id=self.data['commit']['id']
                self.commit_url=self.data['commit']['url']
                self.username=self.data['user']['username']
                return True
            except Exception as e:
                print(e)
                return False
        else:
            return False

    def msg_common(self):
        msg = f'<b>Deploy Remind</b>\n' \
              f'Pipline Status : {self.pipline_satus}\n' \
              f'Project : <a href="{self.project_url}">[{self.project_name}]</a>\n'\
              f'Commit Title : {self.commit_title}\n'\
              f'Commit Id : {self.commit_id[0:7]}\n' \
              f'Commit URL :<a href="{self.commit_url}">[{self.commit_url.split("/")[-1]}]</a>'
        return msg

    def check_id(self):
        dic_stage = self.dic_stage()
        for var in self.data['builds']:
            if var['stage'] in dic_stage.keys():
                dic_stage[var['stage']].append(var['id'])
            else:
                pass
        for k in dic_stage.keys():
            dic_stage[k]=max(dic_stage[k])
        return dic_stage

    def msg_format(self):
        dic_stage=self.check_id()
        msg=self.msg_common()
        for var in self.data['builds']:
            if var['status']=="failed" and var['id']==dic_stage[var['stage']]:
                var['status']="❌ "
                if 'sonar' in var['name']:
                    msg=msg+"\n"+f'Job {var["name"]} : {var["status"]} <a href="{conf.get("COMMON", "sonar")+self.project_name}">[{self.project_name}]</a>'
                else:
                    msg=msg+"\n"+f'Job {var["name"]} : {var["status"]}'
        return msg

    def send_msg(self):
        bot = get_bot()
        msg=self.get_msg()
        if msg:
            msg=self.msg_format()
            try:
                if self.pipline_satus=="❌ ":
                    bot.send_message(chat_id=conf.get('COMMON', 'group_id'), text=msg, parse_mode=ParseMode.HTML)
                bot.send_message(chat_id=conf.get('USER',self.username), text=msg, parse_mode=ParseMode.HTML)
                return True
            except Exception as e:
                print(e)
                return False
        else:
            return False

@hug.post()
def cicdsend(body):
    print(body)
    T=type(body)
    if T==str:
        body=json.loads(body)
    t = CiCd(body)
    try:
        f=executor.submit(t.send_msg)
        if f.result():
            return {'code': 200, 'status': 'success'}
    except Exception:
        return {'code': -1, 'status': 'failed', 'message': '参数不正确！'}

if __name__ == '__main__':
    hug.API(__name__).http.serve(port=8870)  #python api 端口