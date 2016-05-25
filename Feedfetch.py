#!/usr/bin/python3

import os
import time
import datetime
import threading

import torndb

import feedparser

def fixed_feedparser_parse(uri):
    try:
        return feedparser.parse(uri)
    except TypeError:
        if 'drv_libxml2' in feedparser.PREFERRED_XML_PARSERS:
            feedparser.PREFERRED_XML_PARSERS.remove('drv_libxml2')
            return feedparser.parse(uri)
        else:
            raise


class FeedfetchThread(threading.Thread):
    def __init__(self, db_conn):
        threading.Thread.__init__(self)  
        self.db_conn = db_conn
        return
    
    def do_this_uri(self, uri):
        d = fixed_feedparser_parse(uri)
        print('Processing: %s' %(d.feed.link))
        for item in d.entries:
            sql = """ SELECT news_link FROM site_news WHERE news_link=%s """
            if self.db_conn.execute_rowcount(sql, item.link):
                print(" Already done for %s" %(d.feed.link))
                return
            tm = datetime.datetime(item.updated_parsed[0],item.updated_parsed[1],item.updated_parsed[2],
                                   item.updated_parsed[3],item.updated_parsed[4],item.updated_parsed[5])
            sql = """ INSERT INTO site_news (news_title, news_link, news_pubtime, news_desc, news_sitefrom, news_score, news_touched, time) 
            VALUES (%s, %s, %s, %s, %s, 1, 0, NOW()) """
            self.db_conn.execute(sql, item.title, item.link, tm, item.description, d.feed.title)
        print("Done.")
            
        return
    
    def run(self):
        print("FeedfetchThread Start....")
        
        # 每隔300秒，检查一下数据库，看最近一小时是不是还有没有爬的站点
        while True:
            sql = """ SELECT feed_uri FROM site_info WHERE crawl_date < DATE_SUB(NOW(),INTERVAL 5 MINUTE) and valid = 1; """
            feed_uris = self.db_conn.query(sql)
            if feed_uris:
                for item in feed_uris:
                    self.do_this_uri(item['feed_uri'])
                    sql = """ UPDATE site_info SET crawl_date=NOW() WHERE feed_uri=%s and valid = 1; """
                    self.db_conn.execute(sql, item['feed_uri'])
                
            time.sleep(10)
            
        return


    