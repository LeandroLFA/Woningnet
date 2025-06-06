import requests
from bs4 import BeautifulSoup

BASE_URL = "https://amsterdam.mijndak.nl"


def get_page(url=BASE_URL):
    """Fetch HTML from the site."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text


def parse_title(html):
    """Extract page title from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.title.string if soup.title else ""


def main():
    html = get_page()
    title = parse_title(html)
    snippet = html[:100].replace("\n", " ")
    print(f"Page title: {title}")
    print(f"Snippet: {snippet}")


if __name__ == "__main__":
    main()
