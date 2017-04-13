import requests, robotparser, re, os, string, sys
from bs4 import BeautifulSoup
from HTMLParser import HTMLParser
from time import localtime, strftime
from stemmer import PorterStemmer
from collections import Counter
import hashlib
from urlparse import urljoin

ROOT_URL = 'http://lyle.smu.edu/~fmoore/'


class MLStripper(HTMLParser):
    """
    This class removes the HTML tags from raw HTML text.
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


class Crawler:
    def __init__(self):
        self.stopwords = []
        self.p = PorterStemmer()
        self.all_words = {}
        self.all_words_freq = {}
        self.vocabulary = []
        self.doc_term_matrix = [[0] * 23 for n in range(809)]
        self.docs = {}
        self.parser = robotparser.RobotFileParser()

        self.visited_urls = []
        self.visited_items = []
        self.external_urls = []
        self.image_urls = []
        self.broken_urls = []
        self.duplicate_md5_map = {}

    def fetch(self, url):
        """
        This method will fetch the contents of the page.
        """
        r = requests.get(url)
        return r.text

    def external_link(self, url):
        """
        This method will check if the URL is an external link outside the root domain
        """
        return not ROOT_URL in url

    def broken_link(self, url):
        """
        This method will check if the link is broken.
        """
        return False if requests.get(url).status_code == 200 else True

    def load_stop_words(self, file_name):
        """
        This method stores the list of stopwords from a file to the class
        variable list self.stopwords.
        """
        self.stopwords = [line.rstrip(' \n').lower() for line in open(file_name)]

    def prepare_text(self, text):
        """
        This method prepares the raw HTML text for it to be indexed by lowering
        the letters, removing the HTML tags, removing the punctuation, removing
        the extra white space, changing the list to ASCII from unicode, removing
        the stop words, and stemming each word.
        """
        text = self.strip_tags(text.lower())
        text = self.remove_punctuation(text)
        text = self.remove_extra_whitespace(text)
        text = [word.encode('UTF8') for word in text.split()]
        text = [word for word in text if word not in self.stopwords]
        text = self.p.stem_word(text)
        return text

    def index(self, url, doc_words):
        """
        This method indexes all the words in a document and keeps track of
        the frequency of a word in overall documents and overall occurrences.
        """
        for key in doc_words:
            if key not in self.all_words:
                self.all_words[key] = [(url, doc_words[key])]
                self.all_words_freq[key] = [1, doc_words[key]]
                self.vocabulary.append(key)
                self.doc_term_matrix[self.vocabulary.index(key)][self.docs[url]] = \
                    self.all_words[key][0][1]
            else:
                self.all_words[key].append((url, doc_words[key]))
                self.all_words_freq[key][0] += 1
                self.all_words_freq[key][1] += doc_words[key]
                for tup in self.all_words[key]:
                    if tup[0] == str(url):
                        self.doc_term_matrix[self.vocabulary.index(key)][self.docs[url]] = tup[1]

    def write_output(self):
        """
        This method will write the output of the crawler and the 20 most common words to output.txt
        """
        dictionary = sorted(self.all_words_freq.items(), key=lambda e: e[1][1], reverse=True)[:20]

        f = open('output.txt', 'w')
        f.write('Output of Preston and Arturo\'s web crawler.\n\n')
        f.write('Current Time: ' + '\n')
        f.write(strftime("    " + "%Y-%m-%d %H:%M:%S", localtime()))
        f.write('\n\n')

        # Visited links
        f.write('Visited Links: (' + str(len(self.visited_urls)) + ' total)\n')
        for item in self.visited_items:
            f.write("    " + self.clean_url(item['link']) + ' (' + item['title'] + ')\n')
        f.write('\n')

        # External links
        f.write('External Links: (' + str(len(self.external_urls)) + ' total)\n')
        for link in self.external_urls:
            f.write("    " + self.clean_url(link) + '\n')
        f.write('\n')

        # Image links
        f.write('Image Links: (' + str(len(self.image_urls)) + ' total)\n')
        for link in self.image_urls:
            f.write("    " + self.clean_url(link) + '\n')
        f.write('\n')

        # Broken links
        f.write('Broken Links: (' + str(len(self.broken_urls)) + ' total)\n')
        for link in self.broken_urls:
            f.write("    " + self.clean_url(link) + '\n')
        f.write('\n')

        # Term Frequency
        f.write('Top 20 Most Common Stemmed Words with Document Frequency:\n')
        for i in dictionary:
            f.write('    The term ' + i[0] + ' occurs ' + str(i[1][1]) + ' times in ' + str(i[1][0]) + ' documents.\n')

        f.close()
        f = open('term_document_frequency_matrix.txt', 'w')
        f.write('Term/Document Frequency Matrix for Preston and Arturo\'s web crawler.\n')
        f.write('Current Time: ')
        f.write(strftime("%Y-%m-%d %H:%M:%S", localtime()))
        f.write('\n\n               ')  # 15 spaces
        for key, val in self.docs.iteritems():
            f.write('{0:60}'.format(key))
        f.write('\n')
        for i in range(0,len(self.vocabulary)):
            f.write('{0:15}'.format(self.vocabulary[i]))
            for j in range(0,23):
                f.write('{}'.format(self.appears(self.doc_term_matrix[i][j])).ljust(60))
            f.write('\n')
        f.close()

    def parse_robots(self):
        self.parser.set_url(urljoin(ROOT_URL, 'robots.txt'))
        self.parser.read()

    def check_duplicate_file(self, text):
        m = hashlib.md5()
        m.update(text.encode('utf-8'))
        md5_value = m.hexdigest()
        is_duplicate = md5_value in self.duplicate_md5_map

        if not is_duplicate:
            self.duplicate_md5_map[md5_value] = True

        return is_duplicate

    @staticmethod
    def strip_tags(html):
        """
        This class removes the HTML tags from raw HTML text.
        http://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
        """
        s = MLStripper()
        s.feed(html)
        return s.get_data()

    @staticmethod
    def clean_url(url):
        """
        This method removes the base url
        """

        return url.replace(ROOT_URL, '')
    
    @staticmethod
    def extract_urls(text):
        """
        This method will take the contents of a page and extract all of the URLs on it
        """
        urls = []
        soup = BeautifulSoup(text, 'html.parser')
        for atag in soup.find_all('a'):
            href = atag.get('href')
            if href:
                urls.append(href.replace("\"", ""))
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                urls.append(src.replace("\"", ""))
        return urls

    @staticmethod
    def extract_title(text):
        """
        This method will take the contents of a page and extract the title from it
        """
        soup = BeautifulSoup(text, 'html.parser')
        try:
            return soup.title.string
        except Exception as e:
            return "No page title"

    @staticmethod
    def image_link(url):
        """
        This method will check if the link is a JPEG
        """
        r_image = re.compile(r".*\.(jpg|png|gif)$")
        return r_image.match(url)

    @staticmethod
    def valid_link(url):
        """
        This method will check if the link is a JPEG
        """
        r_image = re.compile(r".*\.(html|htm|txt)$")
        return r_image.match(url)

    @staticmethod
    def add_root_to_link(url):
        """
        This method will add the root URL
        """
        return ROOT_URL + re.compile('http://lyle.smu.edu/~fmoore/').sub('', url)

    @staticmethod
    def remove_extra_whitespace(text):
        """
        This method removes more than one white space between words.
        """
        p = re.compile(r'\s+')
        return p.sub(' ', text)

    @staticmethod
    def remove_punctuation(text):
        """
        This method uses regex to remove the punctuation in text.
        http://stackoverflow.com/questions/265960/best-way-to-strip-punctuation-from-a-string-in-python
        """
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)

    @staticmethod
    def appears(i):
        """
        This method will return 1 if the frequency (i) is greater than 1. It is
        used for writing the term/document frequency matrix
        """
        if i >= 1:
            return 1
        else:
            return 0

    @staticmethod
    def get_file_extension(url):
        return os.path.splitext(url)[1][1:]

    def crawl(self, pages_to_index):
        """
        This is the main worker method. It will parse the urls, add the words to
        the index, get the next links, and continue looping through the queue until
        the number of pages to index is met.
        """

        print "Crawling..."

        self.parse_robots()

        # Add ROOT_URL url to queue
        url_queue = [ROOT_URL + 'index.html']

        # pages indexed
        pages_indexed = 0

        while url_queue:
            # get last element in url_queue
            url = url_queue.pop(-1)

            print "    " + self.clean_url(url),

            if url in self.visited_urls:
                print "... already visited"
                continue

            # check if we can fetch the page first
            if self.parser.can_fetch('*', self.clean_url(url)) and self.parser.can_fetch('*', '/' + self.clean_url(url)):

                # fetch the page
                page = self.fetch(url)

                # fetch the page title
                title = self.extract_title(page)

                # add page to visited links
                self.visited_urls.append(url)

                # add page to visited items
                self.visited_items.append({
                    "link": url,
                    "title": title
                })

                # docs and page id
                self.docs[url] = pages_indexed

                # Only parses html, htm, and txt extension files
                file_extension = self.get_file_extension(url)
                if file_extension in ['html', 'htm', 'txt']:
                    page_text = requests.get(url)
                    page_text = page_text.text

                    # Check if duplicate file
                    if self.check_duplicate_file(page_text):
                        print "... duplicate"
                        continue

                    clean_text = self.prepare_text(page_text)
                    doc_words = Counter(clean_text)
                    self.index(url, doc_words)
                    print "... indexed"
                    # increment the pages indexed
                    pages_indexed += 1
                    if int(pages_indexed) >= int(pages_to_index):
                        break
                else:
                    print "... skipped"

                # get urls from page
                new_urls = self.extract_urls(page)

                for new_url in new_urls:
                    # check if we have already visited it or are going to
                    joined_url = urljoin(url, new_url)

                    print "        " + self.clean_url(joined_url),
                    if joined_url in self.visited_urls:
                        print "... visited"
                    elif new_url not in url_queue and new_url not in self.image_urls \
                            and new_url not in self.broken_urls and new_url not in self.external_urls:
                        if self.external_link(joined_url):
                            print "... external"
                            self.external_urls.append(joined_url)
                        elif self.image_link(joined_url):
                            print "... image"
                            self.image_urls.append(joined_url)
                        elif self.broken_link(joined_url):
                            print "... broken"
                            self.broken_urls.append(joined_url)
                        elif self.valid_link(joined_url):
                            print "... new"
                            url_queue.append(joined_url)
                        else:
                            print "... skipped"
                    else:
                        print "... skipped"

            else:
                print "... restricted"

            # end if
        # end while

        # write to output file
        self.write_output()

        print "Crawling finished"

    # end crawl method
# end crawler class

# Main method
if __name__ == "__main__":
    crawler = Crawler()

    # Load in stopwords
    crawler.load_stop_words('stopwords.txt')

    # Crawl N amount of pages or 1000 pages
    if len(sys.argv) == 2:
        crawler.crawl(sys.argv[1])
    else:
        crawler.crawl(1000)