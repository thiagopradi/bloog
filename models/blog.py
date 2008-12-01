# The MIT License
# 
# Copyright (c) 2008 William T. Katz
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to 
# deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.

import logging

from google.appengine.api import memcache
from google.appengine.ext import db

import config
import models
from models import search


class Author(models.MemcachedModel):
    list_includes = ["nick"]
    user = db.UserProperty(required=True)
    name = db.TextProperty(required=True)
    article_count = db.IntegerProperty(required=True, default=0)

    @property
    def nick(self):
        return self.key().name()


class Article(search.SearchableModel):
    unsearchable_properties = ['legacy_id', 'article_type', 
                               'excerpt', 'html', 'format']
    json_does_not_include = ['assoc_dict', 'next_comment_id']

    author = db.ReferenceProperty(Author)
    # Useful for aliasing of old urls
    legacy_id = db.StringProperty()
    title = db.StringProperty(required=True)
    article_type = db.StringProperty(required=True, 
                                     choices=set(["article", "blog entry"]))
    # Body can be in any format supported by Bloog (e.g. textile)
    body = db.TextProperty(required=True)
    # If available, we use 'excerpt' to summarize instead of 
    # extracting the first 68 words of 'body'.
    excerpt = db.TextProperty()
    # The html property is generated from body
    html = db.TextProperty()
    published = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now_add=True)
    format = db.StringProperty(required=True, 
                               choices=set(["html", "textile", 
                                            "markdown", "text"]))
    # Picked dict for sidelinks, associated Amazon items, etc.
    assoc_dict = db.BlobProperty()
    # To prevent full query when just showing article headlines
    num_comments = db.IntegerProperty(default=0)
    # Id of next comment, for generating unique comment numbers.
    # We can't use num_comments because that could decrease if we delete some.
    next_comment_id = db.IntegerProperty(default=1)
    # Use keys instead of db.Category for consolidation of tag names
    tags = db.StringListProperty(default=[])
    allow_comments = db.BooleanProperty()
    # A list of languages for code embedded in article.
    # This lets us choose the proper javascript for pretty viewing.
    embedded_code = db.StringListProperty()

    def __init__(self, permalink=None, **kwargs):
        if permalink:
            super(Article, self).__init__(key_name='/'+permalink, **kwargs)
        else:
            super(Article, self).__init__(**kwargs)

    @property
    def comments(self):
        """Return comments lexicographically sorted on thread string"""
        return db.GqlQuery("SELECT * FROM Comment " +
                           "WHERE ancestor IS :1 " +
                           "ORDER BY __key__ ASC", self.key())

    def set_associated_data(self, data):
        """
        Serialize data that we'd like to store with this article.
        Examples include relevant (per article) links and associated 
        Amazon items.
        """
        import pickle
        self.assoc_dict = pickle.dumps(data)

    def get_associated_data(self):
        import pickle
        return pickle.loads(self.assoc_dict)

    @property
    def permalink(self):
        return self.key().name()[1:]

    def full_permalink(self):
        return config.BLOG['root_url'] + '/' + self.permalink
    
    def rfc3339_published(self):
        return self.published.strftime('%Y-%m-%dT%H:%M:%SZ')

    def rfc3339_updated(self):
        return self.updated.strftime('%Y-%m-%dT%H:%M:%SZ')

    def is_big(self):
        guess_chars = len(self.html) + self.num_comments * 80
        if guess_chars > 2000 or \
           self.embedded_code or \
           '<img' in self.html or \
           '<code>' in self.html or \
           '<pre>' in self.html:
            return True
        else:
            return False

    def to_atom_xml(self):
        """Returns a string suitable for inclusion in Atom XML feed
        
        Internal html property should already have XHTML entities
        converted into unicode.  However, ampersands are valid ASCII
        and will cause issues with XML, so reconvert ampersands to
        valid XML entities &amp;
        """
        import re
        return re.sub('&(?!amp;)', '&amp;', self.html)

class Comment(models.SerializableModel):
    """Stores comments and their position in comment threads.
    
    Comments have as their parent entity the comment to which they are a reply
    or the Article entity if they're a root-level comment.
    """
    name = db.StringProperty()
    email = db.EmailProperty()
    homepage = db.StringProperty()
    title = db.StringProperty()
    body = db.TextProperty(required=True)
    published = db.DateTimeProperty(auto_now_add=True)
    # Only guaranteed to be unique for the parent article.
    comment_id = db.IntegerProperty()

    def get_indentation(self):
        # Indentation is based on degree of nesting in "thread"
        return self.key()._ToPb().path().element_size()


class Tag(models.MemcachedModel):
    # Inserts these values into aggregate list returned by Tag.list()
    list_includes = ['counter.count', 'name']

    def delete(self):
        self.delete_counter()
        super(Tag, self).delete()

    def get_counter(self):
        counter = models.Counter('Tag' + self.name)
        return counter

    def set_counter(self, value):
        # Not implemented at this time
        pass

    def delete_counter(self):
        models.Counter('Tag' + self.name).delete()

    counter = property(get_counter, set_counter, delete_counter)

    def get_name(self):
        return self.key().name()
    name = property(get_name)


class Year(db.Model):
    """Empty model for keeping track of years in which there are blog posts."""
    
    MEMCACHE_KEY = "PS_Year_ALL"

    @classmethod
    def get_all_years(cls):
        years = memcache.get(cls.MEMCACHE_KEY)
        if years:
            return years.split(',')
        else:
            years = sorted(x.key().name()[1:] for x in cls.all())
            memcache.set(cls.MEMCACHE_KEY, ','.join(years))
            return years

    @classmethod
    def get_or_insert(cls, key_name, **kwargs):
        memcache.delete(cls.MEMCACHE_KEY)
        return super(Year, cls).get_or_insert(key_name, **kwargs)
