import os
import requests
import json
from typing import List
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from IPython.display import Markdown, display, update_display
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')

driver=webdriver.Chrome(service=Service(ChromeDriverManager().install()))

if api_key and api_key.startswith('sk-proj-') and len(api_key) > 10:
    print("API key looks good so far")
else:
    print("There might be a problem with your API key? Please visit the troubleshooting notebook!")

MODEL = 'gpt-4o-mini'
openai = OpenAI()

link_system_prompt = "You are provided with a list of links found on a webpage. \
You are able to decide which of the links would be most relevant to include in a brochure about the company, \
such as links to an About page, or a Company page, or Careers/Jobs pages.\n"
link_system_prompt += "You should respond in JSON as in this example:"
link_system_prompt += """
{
    "links": [
        {"type": "about page", "url": "https://full.url/goes/here/about"},
        {"type": "careers page": "url": "https://another.full.url/careers"}
    ]
}
"""

def get_links_user_prompt(links, url):
    user_prompt = f"Here is the list of links on the website of {url} - "
    user_prompt += "please decide which of these are relevant web links for a brochure about the company, respond with the full https URL in JSON format. \
Do not include Terms of Service, Privacy, email links.\n"
    user_prompt += "Links (some might be relative links):\n"
    user_prompt += "\n".join(links)
    return user_prompt

def selenium_scrape_data(url):
    val = url
    wait = WebDriverWait(driver,30)
    driver.get(val)

    get_url = driver.current_url
    page_source = driver.page_source
    soup = BeautifulSoup(page_source,features="html.parser")
    for irrelevant in soup.body(["script", "style", "img", "input"]):
        irrelevant.decompose()
        text = soup.body.get_text(separator="\n", strip=True)
    text = soup.body.get_text(separator="\n", strip=True)
    links = [link.get('href') for link in soup.find_all('a')]
    links = [link for link in links if link]
    content = f"Webpage Title:\n{driver.title}\nWebpage Contents:\n{text}\n\n"
    return {'links': links, 'content': content}

def get_links(url):
    links = selenium_scrape_data(url).get('links')
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": link_system_prompt},
            {"role": "user", "content": get_links_user_prompt(links, url)}
      ],
        response_format={"type": "json_object"}
    )
    result = response.choices[0].message.content
    return json.loads(result)

# result = get_links("https://huggingface.co")

def get_all_details(url):
    result = 'Landing Page: \n'
    result += selenium_scrape_data(url).get('content')
    links = get_links(url)
    print(f'Found links {links}')
    for link in links['links']:

        result += f"\n\n {link['type']}\n"
        result += selenium_scrape_data(link['url']).get('content')
    return result

system_prompt = ("You are an assistant that analyses the content of several relevant pages from a company's website"
                 "and create a short funny and jokey brochure about the company for the prospective customers, investors and recruits. Respond in Markdown."
                 "Include details of the company culture, customers, career/jobs if you have the information.")


def get_brochure_user_prompt(company_name, url):
    user_prompt = f'You are looking at a company called {company_name}\n'
    user_prompt += f'Here are the contents of it"s landing page and other relevant pages; use this information to build a short brochure of the company in the markdown\n'
    user_prompt += get_all_details(url)
    user_prompt += user_prompt[:20000]
    return user_prompt

def create_brochure(company_name, url):
    response = openai.chat.completions.create(model=MODEL,
                                              messages=[
                                                  {
                                                      'role': 'system', 'content': system_prompt
                                                  },
                                                  {
                                                      'role': 'user', 'content': get_brochure_user_prompt(company_name, url)
                                                  }
                                              ])
    result = response.choices[0].message.content
    print(result)
    display(Markdown(result))

create_brochure("HuggingFace", "https://huggingface.co")
