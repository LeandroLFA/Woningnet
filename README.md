# Woningnet

This repository contains a simple scraper for [amsterdam.mijndak.nl](https://amsterdam.mijndak.nl).

## Running the scraper

Install the requirements and run the script:

```bash
pip install -r requirements.txt
python scrape_mijndak.py
```

The script fetches the homepage and prints the page title along with a short HTML snippet. This page is mostly
rendered with JavaScript, so for deeper scraping you may need a headless browser such as Selenium.
Always review the website's terms of service and robots.txt before scraping.
