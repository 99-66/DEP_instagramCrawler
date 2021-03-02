import json
from datetime import datetime
from operator import itemgetter

from pymongo import MongoClient
from redis import Redis

import config


class RedisConnector:
    connectionString = config.REDIS

    def __init__(self, encoding='utf-8', db=None):
        self.client = self._default(db)
        self.encoding = encoding
        self.error_table = self._error_table()

    @classmethod
    def _error_table(cls):
        return cls.connectionString['ERROR_TABLE']

    @classmethod
    def _default(cls, db):
        if db:
            redis_db = db
        else:
            redis_db = cls.connectionString['DB']

        return Redis(host=cls.connectionString['HOST'],
                     port=cls.connectionString['PORT'],
                     password=cls.connectionString['PASSWORD'],
                     db=redis_db,
                     decode_responses=True)

    def conn(self):
        return self.client

    def saved_error(self, username: str, error: str = None) -> None:
        """
        인스타그램 유저 크롤링 시에 에러가 발생하는 경우, 유저 이름과 에러 내용을 Redis에 저장한다
        :param username: instagram username
        :param error: error message
        :return: None
        """
        error_data = {
            'username': username,
            'date': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            'error': error
        }
        self.client.lpush(self.error_table, json.dumps(error_data))

    def error_usernames(self) -> dict:
        """
        인스타그램 크롤링에 실패한 유저 정보를 한개씩 반환한다
        :return:
        """
        error_user_counts = self.client.llen(self.error_table)
        for _ in range(error_user_counts):
            yield self.client.rpop(self.error_table)


class MongoDBConnector:
    mongodb = config.MONGODB

    def __init__(self, client=None):
        if client:
            self.client = client
        else:
            self.client = MongoClient(self._default())
        self.collection = self._collection()

    def conn(self):
        return self.client

    @classmethod
    def _collection(cls):
        return cls.mongodb['COLLECTION']

    @classmethod
    def _default(cls):
        conn = f'mongodb://{cls.mongodb["USER"]}:{cls.mongodb["PASSWORD"]}@{cls.mongodb["HOST"]}:{cls.mongodb["PORT"]}/'
        if cls.mongodb['SSL'] and cls.mongodb['SSL'] is True:
            conn = f'{conn}?ssl=true'
            if cls.mongodb['SSL_CA_CERTS']:
                conn = f'{conn}&ssl_ca_certs={cls.mongodb["SSL_CA_CERTS"]}'

        else:
            conn = f'{conn}?ssl=false'

        if cls.mongodb['REPLICA_SET']:
            conn = f'{conn}&replicaSet={cls.mongodb["REPLICA_SET"]}'

        return conn

    def over_500_followers(self):
        fixed_pages_list = self.client[self.collection]['']
        keyword_user_stats = self.client[self.collection]['']
        ret = []
        # 팔로워 수가 500이상인 유저의 수만 가져온다
        for i in fixed_pages_list.find({'followersCount': {'$gte': 500}}).sort([('followersCount', -1)]):
            ret.append({'username': i['_id'], 'followersCount': i['followersCount']})

        for i in keyword_user_stats.find({'followersCount': {'$gte': 500}}).sort([('followersCount', -1)]):
            ret.append({'username': i['_id'], 'followersCount': i['followersCount']})

        # 두 개의 collection 에서 가져온 유저의 수를 다시 팔로워 순으로 정렬한다
        ret.sort(key=itemgetter('followersCount'), reverse=True)
        return [i['username']for i in ret]
