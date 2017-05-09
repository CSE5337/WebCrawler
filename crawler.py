import requests, robotparser, urlparse, re, os, string, sys, operator, numpy
from bs4 import BeautifulSoup
from HTMLParser import HTMLParser
from time import localtime, strftime
from stemmer import PorterStemmer
from collections import Counter
from math import log10
import hashlib
from urlparse import urljoin


ROOT_URL = 'http://lyle.smu.edu/~fmoore/'


class MLStripper(HTMLParser):
    """
    This class removes the HTML tags from raw HTML text.
    http://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
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
        self.doc_term_matrix = [[0] * 30 for n in range(2000)]
        self.docs = []
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
                self.doc_term_matrix[self.vocabulary.index(key)][self.docs.index(url)] = self.all_words[key][0][1]
            else:
                self.all_words[key].append((url, doc_words[key]))
                self.all_words_freq[key][0] += 1
                self.all_words_freq[key][1] += doc_words[key]
                for tup in self.all_words[key]:
                    # check if right URL
                    if tup[0] == str(url):
                        self.doc_term_matrix[self.vocabulary.index(key)][self.docs.index(url)] = tup[1]

    def doc_query_tfidf(self, words):
        """
        tfidf:
        1 + log(number of times word appears in a document) * log(total documents/ how many documents the word appears in)
        """

        # term on row, document on column
        tfidf_matrix = []
        total_docs = len(self.docs)
        for word in words:
            row = []
            for url in self.docs:
                tfidf = 0
                for all_word in self.all_words[word]:
                    if url == all_word[0]:
                        try:
                            tfidf = (1 + log10(all_word[1])) * log10(total_docs / self.all_words_freq[word][0])
                            break
                        except ZeroDivisionError:
                            pass
                row.append(tfidf)
            tfidf_matrix.append(row)

        return tfidf_matrix
    def query_tfidf(self, words):
        """
        tfidf:
        1 + log(number of times word appears in the query) * log(total documents/ how many documents the word appears in)
        """

        tfidf_matrix = []
        total_docs = len(self.docs)
        term_frequency = Counter(words)
        terms_in_docs = len(term_frequency)

        for word in words:
            tfidf = 0
            try:
                tfidf = (1 + log10(float(term_frequency[word])/float(terms_in_docs))) * log10(float(total_docs) / float(self.all_words_freq[word][0]))
            except ZeroDivisionError, e:
                test = 2
            tfidf_matrix.append(tfidf)

        return tfidf_matrix

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
        for url in self.docs:
            f.write('{0:100}'.format(url))
        f.write('\n')
        for i in range(0, len(self.vocabulary)):
            f.write('{0:30}'.format(self.vocabulary[i]))
            for j in range(0, 30):
                f.write('{}'.format(self.appears(self.doc_term_matrix[i][j])).ljust(100))
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
    def normalize_vector(vector):
        """
        This method will normalize the vector to prep for calculate_cosine_similarity
        """
        if numpy.linalg.norm(vector) == 0.0:
            return [0.0 for i in vector]
        else:
            return [i / numpy.linalg.norm(vector) for i in vector]

    def calculate_cosine_similarity(self, user_input):

        query_words = self.prepare_text(user_input)
        doc_query_tfidf = numpy.array(self.doc_query_tfidf(query_words))
        query_tfidf = numpy.array(self.query_tfidf(query_words))

        cos_sims = []
        for index, url in enumerate(self.docs):
            dot_product = numpy.dot(doc_query_tfidf[:, index], query_tfidf)

            doc_norm = numpy.linalg.norm(doc_query_tfidf[:, index])
            query_norm = numpy.linalg.norm(query_tfidf)

            cos_sim = dot_product / (doc_norm * query_norm)
            cos_sim = 0 if numpy.isnan(cos_sim) else cos_sim

            visited_item = (item for item in self.visited_items if item["link"] == url).next()

            cos_sims.append({
                "cos_sim": cos_sim,
                "visited_item": visited_item
            })


        sorted_rankings = sorted(cos_sims, key=lambda k: k['cos_sim'], reverse=True)

        return sorted_rankings

    @staticmethod
    def get_file_extension(url):
        return os.path.splitext(url)[1][1:]

    def query_engine(self, N):
        """
        This method will be the main query handler.
        self.all_words format (var info below): [('spring'), [('url', 3), ('other_page', 4)] ]
                                                  word         tuples(url, frequency)
        """
        print "#################################################################"
        print "#################################################################"
        print "############### Preston and Arturo's Web Crawler ################"
        print "#################################################################"
        print "#################################################################"
        print
        print "Please enter a query to search the lyle.smu.edu/~fmoore domain."
        print "Search will display top " + str(N) + " results or all results that query is found on."
        print "Type 'quit' to exit the search engine"

        while True:
            user_input = raw_input("> ")
            if user_input == "quit" or user_input == "Quit" or user_input == "QUIT":
                break

            rankings = self.calculate_cosine_similarity(user_input)

            i = 0
            if rankings[0][1] == 0.0:
                print '%s not found in domain.\n' % user_input
                continue
            print '  Score:      Document:'
            while i < N:
                if rankings[i][1] == 0.0:
                    break
                print '   {0:4f}'.format(rankings[i][1]) + '    {}'.format(rankings[i][0])
                i += 1
            print
        return

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

        current_page_index = 0

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


                # Only parses html, htm, and txt extension files
                file_extension = self.get_file_extension(url)
                if file_extension in ['html', 'htm', 'txt']:
                    page_text = requests.get(url)
                    page_text = page_text.text

                    # Check if duplicate file
                    if self.check_duplicate_file(page_text):
                        print "... duplicate"
                        continue

                    self.docs.append(url)
                    clean_text = self.prepare_text(page_text)
                    doc_words = Counter(clean_text)
                    self.index(url, doc_words)
                    print "... indexed"
                    # increment the pages indexed
                    current_page_index += 1

                    if int(current_page_index) >= int(pages_to_index):
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

    test = 2
    # Start query engine
    crawler.query_engine(5)
