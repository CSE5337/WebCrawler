## CSE 5337 Web Crawler Project
A web crawler and indexer using python.

## Used Software
This project has been developed on a mid-2010 Macbook Pro running OS X El Capitan


## Installation
You can clone this repository to gain access to the code of the project.

```
git clone https://github.com/CSE5337/WebCrawler.git
```

## Execution
```
~/WebCrawler/$ python crawler.py $PAGES_TO_CRAWL
```

## Query engine
When executed, the web crawler will also execute a query engine to search for words in the domain http://lyle.smu.edu/~fmoore/. The output is as follows:
```
#################################################################
################ Preston and Arturo's Web Crawler ###############
#################################################################

Please enter a query to search the lyle.smu.edu/~fmoore domain.
Search will display top 5 results or all results that query is found on.
Type 'quit' to exit the search engine
> moore smu
  Score:      Document:
   2.346721    http://lyle.smu.edu/~fmoore/
   1.079181    http://lyle.smu.edu/~fmoore/schedule.htm
```

## Dependencies

### Python 2.7

### Python packages: numpy, HTMLParser, requests, BeautifulSoup, PorterStemmer
