import requests, robotparser, urlparse, re, os, string, sys, operator, numpy
from bs4 import BeautifulSoup
from HTMLParser import HTMLParser
from time import localtime, strftime
from stemmer import PorterStemmer
from collections import Counter
from math import log10
import hashlib

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
    	"""
    	This method declares the list stopwords, dictionaries all_words and
    	all_words_freq, as well as the PorterStemmer object.
    	"""
        self.stopwords = []
        self.p = PorterStemmer()
        self.all_words = {}
        self.all_words_freq = {}
        self.tfidf = {}
        self.vocabulary = []
        self.doc_term_matrix = [[0] * 23 for n in range(809)]
        self.docs = {}
        self.parser = robotparser.RobotFileParser()

        self.visited_urls = []
        self.external_urls = []
        self.image_urls = []
        self.excel_urls = []
        self.broken_urls = []
        self.duplicate_md5_map = {}

    def fetch(self, url):
        """
        This method will fetch the contents of the page.
        """
        r = requests.get(urlparse.urljoin(ROOT_URL, self.clean_url(url)))
        return r.text

    def external_link(self, url):
        """
        This method will check if the URL is an external link outside the root domain
        """
        if url:
            url = re.compile('https*://').sub('', url)
            if re.compile('.*lyle.smu.edu/~fmoore.*').match(url):
                return False
            elif re.compile('www.*').match(url):
                return True
            elif re.compile('java-source.*').match(url):
                return True
            elif re.compile('.*smu.edu.*').match(url):
                return True
            elif re.compile('.*.aspx').match(url):
                return True
            elif re.compile('mailto:').match(url):
                return True
            elif re.compile('.*.xlsx').match(url):
                return False
            elif requests.get(ROOT_URL + url).status_code == 200:
                return False
            elif self.image_link(url):
                return False
            else:
                return True
        else:
            return True

    def broken_link(self, url):
        """
        This method will check if the link is broken.
        """
        return False if requests.get(ROOT_URL + self.clean_url(url)).status_code == 200 else True

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
                self.doc_term_matrix[self.vocabulary.index(key)][self.docs[self.add_root_if_not_there(url)]] = \
                    self.all_words[key][0][1]
            else:
                self.all_words[key].append((url, doc_words[key]))
                self.all_words_freq[key][0] += 1
                self.all_words_freq[key][1] += doc_words[key]
                for tup in self.all_words[key]:
                    if tup[0] == str(url):
                        self.doc_term_matrix[self.vocabulary.index(key)][self.docs[self.add_root_if_not_there(url)]] = tup[1]

    def calculate_tfidf(self, word):
        """
        This method will calculate the TF-IDF for a given word.

        1 + log(number of times word appears in a document) * log(total documents/ how many documents the word appears in)
        """
        if word in self.all_words:
            for i in self.all_words[word]:
                return (1 + log10(i[1])) * log10(len(self.visited_urls)/self.all_words_freq[word][0])
        else:
            return 0

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
        for link in self.visited_urls:
            f.write("    " + link + '\n')
        f.write('\n')

        # External links
        f.write('External Links: (' + str(len(self.external_urls)) + ' total)\n')
        for link in self.external_urls:
            f.write("    " + link + '\n')
        f.write('\n')

        # Image links
        f.write('Image Links: (' + str(len(self.image_urls)) + ' total)\n')
        for link in self.image_urls:
            f.write("    " + link + '\n')
        f.write('\n')

        # Excel links
        f.write('Excel Links: (' + str(len(self.excel_urls)) + ' total)\n')
        for link in self.excel_urls:
            f.write("    " + link + '\n')
        f.write('\n')

        # Broken links
        f.write('Broken Links: (' + str(len(self.broken_urls)) + ' total)\n')
        for link in self.broken_urls:
            f.write("    " + link + '\n')
        f.write('\n')

        # Term Frequency
        f.write('Top 20 Most Common Words with Document Frequency:\n')
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
        self.parser.set_url(urlparse.urljoin(ROOT_URL, 'robots.txt'))
        self.parser.read()

    def check_duplicate_file(self, text):
        m = hashlib.md5()
        m.update(text)
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
        EX. http://lyle.smu.edu/~fmoore/schedule.htm => schedule.htm
        """

        url = re.compile(ROOT_URL).sub('', url)
        url = re.compile('http://lyle.smu.edu/~fmoore').sub('', url)
        # url = re.compile('index.*').sub('', url)
        # url = re.compile('.*.gif').sub('', url)
        return re.compile('\.\./').sub('', url)
    
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
    def excel_link(url):
        """
        This method will check if the link is an excel file.
        """
        return True if re.compile('.*.xlsx').match(url) else False

    @staticmethod
    def add_root_to_links(urls):
        """
        This method will add the root URL to all of the links for visual apperance
        """
        new_urls = [ROOT_URL + re.compile('http://lyle.smu.edu/~fmoore/').sub('', link) for link in urls]
        return new_urls

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
    def add_root_if_not_there(url):
        """
        This method will add the root url to a single link if it isnt there
        """
        url = re.compile('http://lyle.smu.edu/~fmoore/').sub('', url)
        return ROOT_URL + url

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
    def clean_external_links(external):
        """
        This method will remove the non links from the external links
        """
        urls = []
        for link in external:
            if link is None:
                return urls
            else:
                urls.append(link)
        return urls

    @staticmethod
    def normalize_vector(vector):
        """
        This method will normalize the vector to prep for calculate_cosine_similarity
        """
        if numpy.linalg.norm(vector) == 0.0:
            return [0.0 for i in vector]
        else:
            return [i / numpy.linalg.norm(vector) for i in vector]

    @staticmethod
    def calculate_cosine_similarity(doc, query):
        """
        This method will calculate the cosine similarity betwee two vectors of equal size
        """
        if len(doc) != len(query):
            return 0.0
        return numpy.dot(doc, query)

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
        print "############### Preston and Arturo's Web Crawler ################"
        print "#################################################################"
        print
        print "Please enter a query to search the lyle.smu.edu/~fmoore domain."
        print "Search will display top " + str(N) + " results or all results that query is found on."
        print "Type 'quit' to exit the search engine"

        while True:
            user_input = raw_input("> ")
            if user_input == "quit" or user_input == "Quit" or user_input == "QUIT":
                break
            query = self.p.stem_word(re.sub("[^\w]", " ",  user_input).split())
            query = [word.lower() for word in query]
            for word in query:
                if word in self.stopwords:
                    query.remove(word)
            query_vector = [self.calculate_tfidf(word) for word in query]
            docs = {}
            for doc_name, ID in self.docs.iteritems():
                vector = []
                for word in query:
                    if word in self.vocabulary:
                        if self.doc_term_matrix[self.vocabulary.index(word)][self.docs[self.add_root_if_not_there(doc_name)]] >= 1:
                            vector.append(1)
                        else:
                            vector.append(0)
                docs[doc_name] = self.normalize_vector(vector)
            rankings = {}
            for url, doc_vec in docs.iteritems():
                rankings[url] = self.calculate_cosine_similarity(doc_vec, query_vector)

            sorted_rankings = sorted(rankings.items(), key=operator.itemgetter(1), reverse=True)
            i = 0
            if sorted_rankings[0][1] == 0.0:
                print '%s not found in domain.\n' % user_input
                continue
            print '  Score:      Document:'
            while i < N:
                if sorted_rankings[i][1] == 0.0:
                    break
                print '   {0:4f}'.format(sorted_rankings[i][1]) + '    {}'.format(sorted_rankings[i][0])
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
        urlqueue = [ROOT_URL + 'index.html']

        # pages indexed
        pages_indexed = 0

        while urlqueue:
            # get last element in urlqueue
            url = urlqueue.pop(-1)

            print "    " + self.clean_url(url),

            if self.clean_url(url) in self.visited_urls:
                print "... visited"
                continue


            # check if we can fetch the page first
            if self.parser.can_fetch('*', urlparse.urljoin('/', url)):

                # remove the / at the beginning of the string
                url = re.compile('^/').sub('', url)

                # fetch the page
                page = self.fetch(url)

                # add page to visited links
                self.visited_urls.append(self.clean_url(url))

                # docs and page id
                self.docs[self.add_root_if_not_there(url)] = pages_indexed

                # Only parses html, htm, and txt extension files
                file_extension = self.get_file_extension(url)
                if file_extension in ['html', 'htm', 'txt']:
                    page_text = requests.get(ROOT_URL + self.clean_url(url))
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
                    print "        " + new_url,
                    if new_url in self.visited_urls:
                        print "... visited"
                    elif new_url not in urlqueue and new_url not in self.image_urls \
                            and new_url not in self.broken_urls and new_url not in self.external_urls:
                        if self.external_link(new_url):
                            print "... external"
                            self.external_urls.append(new_url)
                        elif self.image_link(new_url):
                            print "... image"
                            self.image_urls.append(new_url)
                        elif self.excel_link(new_url):
                            print "... excel"
                            self.excel_urls.append(new_url)
                        elif self.broken_link(new_url):
                            print "... broken"
                            self.broken_urls.append(new_url)
                        elif self.valid_link(new_url):
                            print "... new"
                            urlqueue.append(new_url)
                        else:
                            print "... skipped"
                    else:
                        print "... skipped"

            else:
                print "... restricted"




            # end if
        # end while

        # clean the links for visual appearance
        self.visited_urls = set(self.add_root_to_links(self.visited_urls))
        self.image_urls = self.add_root_to_links(self.image_urls)
        self.excel_urls = self.add_root_to_links(self.excel_urls)
        self.broken_urls = self.add_root_to_links(self.broken_urls)
        self.external_urls = self.clean_external_links(self.external_urls)

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

    # Start query engine
    # crawler.query_engine(5)
