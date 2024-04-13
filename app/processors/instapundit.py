import re
import os
import json
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate, PromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.output_parsers import ResponseSchema, StructuredOutputParser

class Instapundit:
	def __init__(self):
		self.ollama_url = os.getenv('OLLAMA_URL')
		if self.ollama_url:
			parser = StructuredOutputParser.from_response_schemas(
				[ResponseSchema(name="title", description="title of the article")]
			)

			prompt = PromptTemplate(
				template="""
					title: {title},
					summary: {summary},
					{format_instructions}
				""",
				input_variables=["title", "summary"],
				partial_variables={"format_instructions": parser.get_format_instructions()},
			)

			# format chat prompt
			system_prompt = SystemMessage(content=("""
				You are an expert news article title editor.
				Use the provided title and summary to write a concise and accurate title that is concise, informative and avoids sounding like clickbait. 
				Do not include links or urls in the title.
				Title should be as short as possible, aim to be less that 70 characters long.
				Title should have an absolute minimum of punctuation and use at most one all capitalized word at the start of the title.
				"""))
			user_prompt = HumanMessagePromptTemplate(prompt=prompt)

			chat_prompt = ChatPromptTemplate.from_messages([system_prompt, user_prompt])
			model = Ollama(base_url=self.ollama_url, model="dolphin-mistral", keep_alive=5, temperature=0.0)
			self.chain = chat_prompt | model | parser
			

	def process(self, widget):
		for article in widget['articles'][:]:
			if article['title'] and ('#CommissionEarned' in article['title'] or re.search('Open Thread', article['title'], re.IGNORECASE)):
				widget['articles'].remove(article)
				next
			if not self.ollama_url:
				article['title'] = article['title'].strip().strip('""')
			else:
				data = [{"title": article['original_title'], "summary": article['original_summary']} for article in widget['articles']]
				rows = self.chain.batch(data, max_concurrency=len(data)//2)
		
				for article, row in zip(widget['articles'], rows):
					article['title'] = row['title']
				
		return widget
