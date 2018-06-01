# -*- coding: utf-8 -*-
import scrapy


class RedditbotSpider(scrapy.Spider):
    name = 'redditbot'
    allowed_domains = ['www.reddit.com/r/gameofthrones/']
    start_urls = ['https://www.reddit.com/r/gameofthrones/']
    handle_httpstatus_list = range(0, 500)

    def parse(self, response):
        print("parsing")
        if response.status not in [200]:
            item = {}
            item['url'] = response.url
            item['meta'] = response.meta
            item['status'] = response.status
 
            yield item
 
        else:
            titles = response.css('.title.may-blank::text').extract()
            votes = response.css('.score.unvoted::text').extract()
            times = response.css('time::attr(title)').extract()
            comments = response.css('.comments::text').extract()
       
            data = zip(titles,votes,times,comments)
            if len(titles) < 1:
                item = {}
                item['url'] = response.url
                item['meta'] = response.meta
                item['status'] = response.status
    
                yield item
            
            else:
                #Give the extracted content row wise
                for item in data:
                    #create a dictionary to store the scraped info
                    scraped_info = {
                        'title' : item[0],
                        'vote' : item[1],
                        'created_at' : item[2],
                        'comments' : item[3],
                    }

                    #yield or give the scraped info to scrapy
                    yield scraped_info