# The MIT License
# 
# Copyright (c) 2008 Nick Johnson
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
from google.appengine.api import datastore
from google.appengine.ext import webapp
from utils import authorized

class UpgradeHandler(webapp.RequestHandler):
    ARTICLE_PROPERTIES = ['legacy_id', 'title', 'article_type', 'body',
                          'excerpt', 'html', 'published', 'updated', 'format',
                          'assoc_dict', 'num_comments', 'tags',
                          'allow_comments', 'embedded_code']
    COMMENT_PROPERTIES = ['name', 'email', 'homepage', 'title', 'body',
                          'published']

    def ArticleUpdateTx(self, old_article, old_comments):
        article = datastore.Entity('Article', name='/'+old_article['permalink'])
        for prop in self.ARTICLE_PROPERTIES:
            if prop in old_article:
                article[prop] = old_article[prop]
        article['next_comment_id'] = len(old_comments) + 1
        datastore.Put(article)
        
        comments = {}
        i = 1
        for old_comment in old_comments:
            parent_thread = old_comment['thread'].rpartition('.')[0]
            parent = comments.get(parent_thread, article)
            comment = datastore.Entity('Comment', parent=parent.key())
            for prop in self.COMMENT_PROPERTIES:
                if prop in old_comment:
                    comment[prop] = old_comment[prop]
            comment['comment_id'] = i
            i += 1
            datastore.Put(comment)
            comments[old_comment['thread']] = comment
        
        return True
        
    @authorized.role("admin")
    def get(self):
        next = self.request.get('next', None)
        q = datastore.Query('Article')
        if next:
            q['__key__ >='] = datastore.Key(next)
        q.Order('__key__')
        articles = q.Get(2)
        logging.info(len(articles))
        if not articles or 'permalink' not in articles[0]:
            self.response.out.write("Done!")
            return
        article = articles[0]
        q = datastore.Query('Comment')
        q['article ='] = article.key()
        q.Order('thread')
        comments = q.Get(1000)
        if datastore.RunInTransaction(self.ArticleUpdateTx, article, comments):
            datastore.Delete([article] + comments)
            logging.info("Updated article %s" % (article['title'],))
            self.response.out.write("Updated article %s" % (article['title'],))
            if len(articles) > 1:
                self.redirect("/admin/upgrade?next=%s" % (articles[1].key()))
            else:
                self.response.out.write("Done!")
                return
        else:
            logging.info("Failed to update article %s. Trying again." % (article['title'],))
            self.response.out.write("Failed to update article %s. Trying again." % (article['title'],))
            self.redirect("/admin/upgrade?next=%s" % (article.key()))
