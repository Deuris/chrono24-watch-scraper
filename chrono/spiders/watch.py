import scrapy
import os
from urllib.parse import urlparse
from urllib.request import urlretrieve
from chrono.items import WatchItem

class WatchSpider(scrapy.Spider):
    name = "watch_detail_scraper"
    allowed_domains = ["chrono24.com"]
    base_url = "https://www.chrono24.com"
    start_urls = ["https://www.chrono24.com/alangesoehne/index.htm"]

    custom_settings = {
        'FEEDS': {
            'output.json': {
                'format': 'json',
                'overwrite': True,
            },
        },
    }

    custom_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.9999.99 Safari/537.36'
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, headers=self.custom_headers, callback=self.parse)

    def parse(self, response):
        watch_page_link = response.css('.article-item-container > a::attr(href)').getall()

        for link in watch_page_link:
            yield scrapy.Request(self.base_url+link, headers=self.custom_headers, callback=self.parse_watch_detail)

        next_page = response.css(".paging-next::attr(href)").get()

        if next_page is not None:
            yield scrapy.Request(next_page, headers=self.custom_headers, callback=self.parse)

    def parse_watch_detail(self, response):
        watch_item = WatchItem()

        watch_id = response.css(".wt-share-offer::attr(data-watch-id)").get()
        title = response.css("h1.h3::text").get().strip()
        currency = response.css(".js-price-shipping-country::text").get().strip()

        watch_data = {}
        section_name = None

        # Find and iterate through all rows in the table
        rows = response.xpath('(//table)[1]//tr')
        for row in rows:
            if row.xpath('td[@colspan]'):
                # This row contains a section title
                section_name = row.xpath('td/h3/text()').get()
                watch_data[section_name] = {}
            elif section_name:
                # Extract key-value pairs within the current section
                key = row.xpath('td[1]/strong/text()').get()
                value = row.xpath('td[2]/text()').get()
                if key and value:
                    watch_data[section_name][key] = value.strip()

        # Image extraction and download
        image_url = response.css('.image-container img::attr(src)').get()
        if image_url:
            image_name = os.path.basename(urlparse(image_url).path)
            image_path = os.path.join('images', image_name)

            # Ensure images directory exists
            os.makedirs('images', exist_ok=True)

            # Download the image
            urlretrieve(image_url, image_path)

            watch_item["imageName"] = image_name

        watch_item["watch_id"] = watch_id
        watch_item["watch_title"] = title
        watch_item["watch_price"] = currency
        watch_item["watch_details"] = watch_data

        yield watch_item