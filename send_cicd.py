#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor
import hug
executor = ThreadPoolExecutor(2)
from telegram import Bot
from telegram import ParseMode
import configparser
import json
import send_sonar
import sqlite3

conf=configparser.ConfigParser()
conf.read("config.ini",encoding="utf-8")


def get_bot():
    token=conf.get("COMMON","bot_token")
    bot = Bot(token=token)
    return bot

class CiCd:
    def __init__(self, data):
        self.data=data

    def get_msg(self):
        try:
            self.deployable_url=self.data['deployable_url']
            self.project_name=self.data['project']['name']
            self.commit_title=self.data['commit_title']
            self.environment=self.data['environment']
            self.status=self.data['status']
            self.commit_id=self.data['short_sha']
            self.commit_url=self.data['commit_url']
            self.username=self.data['user']['username']
        except Exception as e:
            print(e)

    def msg_format(self):
        msg = f'<b>Deploy Remind</b>\n' \
              f'Deploy Status : {self.status}\n' \
              f'Project : <a href="{self.deployable_url}">[{self.project_name}]</a>\n'\
              f'Commit Title : {self.commit_title}\n'\
              f'Cluster : {self.environment}\n' \
              f'Commit Id : {self.commit_id}\n' \
              f'Commit Url :<a href="{self.commit_url}">[{self.commit_url.split("/")[-1]}]</a>'
        f = executor.submit(select_data(self.project_name))
        var=f.result()
        if var:
            if var!=0:
                qualityGate_status="❌"
            else:
                qualityGate_status = "✅"
            msg=msg+'\n'+f'qualityGate Status: {qualityGate_status}'
        else:
            msg=msg+'\n'+f'qualityGate Status: NO VALUE'
        return msg

    def send_msg(self):
        bot = get_bot()
        self.get_msg()
        try:
            if self.status == "success":
                self.status ="✅ "
                msg = self.msg_format()
            else:
                self.status ="❌ "
                msg=self.msg_format()
                bot.send_message(chat_id=conf.get('COMMON', 'group_id'), text=msg, parse_mode=ParseMode.HTML)
            bot.send_message(chat_id=conf.get('USER',self.username), text=msg, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(e)

def select_data(project):
    try:
        conn = sqlite3.connect('sonar.db')
        c = conn.cursor()
        r=c.execute(f"select qualityGate where project_name=\"{project}\" order by id desc limit 1")
        for var in r:
            if len(var)==0:
                conn.close()
                return False
            else:
                conn.close()
                return var
    except Exception as e:
        print(e)
        return False


@hug.post()
def sonarsend(body):
    T=type(body)
    if T==str:
        body=json.loads(body)
    t = send_sonar.Sonar(body)
    try:
        t.get_msg()
        f=executor.submit(t.insert_data)
        if f.result():
            return {'code': 200, 'status': 'success'}
    except Exception as e:
        print(e)
        return {'code': -1, 'status': 'failed', 'message': '参数不正确！'}

@hug.post()
def cicdsend(body):
    T=type(body)
    if T==str:
        body=json.loads(body)
    t = CiCd(body)
    try:
        executor.submit(t.send_msg)
        return {'code': 200, 'status': 'success'}
    except Exception:
        return {'code': -1, 'status': 'failed', 'message': '参数不正确！'}

if __name__ == '__main__':
    hug.API(__name__).http.serve(port=8880)  #python api 端口