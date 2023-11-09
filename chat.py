import json
import sqlite3
import string
import random
import requests
from datetime import datetime


class Chat:
    certify_url = 'http://148.113.16.225:3001/certify'

    def __init__(self):
        self.storage = Storage()
        self.persona = '''
            You're Stephan, an application manager at the Near Protocol Grant program. You should validate 
            the grant proposal and answer "funded" if the proposal is good enough or "declined" if not. 
            The proposal should be innovative, decentralized, and valuable to the NEAR ecosystem. Ask 
            additional questions regarding the proposal one by one. Newer answer with the single word 
            before asking 2 questions and ensuring that the proposal follows the grant program criteria.
            For any message that does not describe the proposal, reply with "Please, focus on your proposal" 
            ask one more question, and decline the proposal.
            When replying to the user you should act as the above given persona
        '''

    def message(self, txhash, user, message):
        completion = self.build_completion(user)
        completion.append({"role": "user", "content": message})

        data = {
            'address': user,
            'request': json.dumps({
                "model": "gpt-3.5-turbo",
                "messages": completion,
            })
        }
        print(f"Request data: {data}")

        response = requests.post(self.certify_url, json=data, headers={'Content-Type': 'application/json'})
        response_object = json.loads(response.text)
        response_data = json.loads(response_object["data"])

        response_object["data"] = response_data
        print(f"Response object: {response_object}")

        assistant_message = response_data['response']['choices'][0]['message']['content']
        self.storage.save_message(txhash, user, message, assistant_message)

        return response_object

    def build_completion(self, user):
        completion = [
            {"role": "system", "content": self.persona},
        ]

        archive = self.storage.fetch_messages(user)
        for row in archive:
            completion.append({"role": "user", "content": row[3]})
            completion.append({"role": "assistant", "content": row[4]})

        return completion

    def get_archive(self, user):
        return self.storage.fetch_messages(user)


class Storage:
    def __init__(self):
        self.con = sqlite3.connect("quex.db")
        self.check_table()

    def save_message(self, txhash, user, user_message, assistant_message):
        sql = "INSERT INTO messages (txhash, created_at, user, user_message, assistant_message) VALUES (?, ?, ?, ?, ?)"
        row = (txhash, datetime.now(), user, user_message, assistant_message)
        print(f"Query: {sql}, Row: {row}")

        c = self.con.cursor()
        c.execute(sql, row)
        self.con.commit()

    def fetch_messages(self, user):
        c = self.con.cursor()
        c.execute(f"SELECT * FROM messages WHERE user = '%s'" % user)
        return c.fetchall()

    def check_table(self):
        c = self.con.cursor()

        c.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='messages' ''')
        if c.fetchone()[0] == 1:
            print('Table exists.')
        else:
            print('Table does not exist.')
            c.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    txhash TEXT NULL,
                    created_at TEXT NULL,
                    user TEXT NULL,
                    user_message TEXT NULL,
                    assistant_message TEXT NULL
                ) 
            ''')
            self.con.commit()
