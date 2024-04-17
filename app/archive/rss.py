import os
import time
import aiohttp
from cachelib import FileSystemCache
import feedparser
import requests

from post_processor import post_processor
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
import warnings

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

class Rss:
	def __init__(self):
		cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'feed_cache')
		if not os.path.exists(cache_dir):
			os.makedirs(cache_dir)
		self.feed_cache = FileSystemCache(cache_dir, default_timeout=60*15)

	async def load_feed(self, widget):
		start_time = time.time()

		cached_widget = self.feed_cache.get(widget['name'])
		
		# check if feed is in self.feeds and that the last updated time is less than 15 minutes ago	
		if cached_widget and 'last_updated' in cached_widget and (start_time - cached_widget['last_updated']) < 60 * 15:
			widget['articles'] = cached_widget['articles']
			#print(f"Loaded {widget['name']} from cache")
		else:
			headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'}
			async with aiohttp.ClientSession() as session:
				async with session.get(widget['url'], allow_redirects=True, headers=headers) as response:
					if(response.status != 200):
						print(f"Failed to load {widget['name']} from {widget['url']} with Status Code: {response.status} Response follows:")
						print(await response.text())
					else:
						#print(f"Loaded {widget['name']} with Status Code: {response.status}")
						article_limit = widget.get('article_limit', 10)
						parsed_feed = feedparser.parse(await response.text())
						
						widget['articles'] = [{
								'original_title': entry.get('title', 'No Title').strip(), 
								'link': entry.link, 
								'original_summary': entry.get('summary', None)
						} for entry in parsed_feed.entries[:article_limit]] if 'entries' in parsed_feed else []
						
						widget['last_updated'] = start_time
						self.feed_cache.set(widget['name'], widget)
						
			post_processor.process(widget)
			self.feed_cache.set(widget['name'], widget)
		
		return widget
	
	def find_feed_links(self, url):
		response = requests.get(url)
		
		if response.status_code == 200:
			soup = BeautifulSoup(response.content, 'html.parser')
			links = soup.find_all('link', type=["application/rss+xml", "application/atom+xml"])
			
			feed_links = []
			for link in links:
				feed_links.append(link.get('href'))
			
			return feed_links
		else:
			print(f"Failed to retrieve content from {url}")
			return None

rss = Rss()   