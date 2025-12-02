import scrapy


class NewsItem(scrapy.Item):
    title = scrapy.Field()
    image_path = scrapy.Field()
    source = scrapy.Field()
    link = scrapy.Field()
    date = scrapy.Field()
    country = scrapy.Field()
    language = scrapy.Field()
