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
from google.appengine.api import datastore_errors
from google.appengine.api import users
from google.appengine.ext import webapp
from utils import authorized
from utils.external import simplejson
import config
import view

class UpgradeHandler(webapp.RequestHandler):
    ARTICLE_PROPERTIES = ['legacy_id', 'title', 'article_type', 'body',
                          'excerpt', 'html', 'published', 'updated', 'format',
                          'assoc_dict', 'num_comments', 'tags',
                          'allow_comments', 'embedded_code',
                          '__searchable_text_index']
    COMMENT_PROPERTIES = ['name', 'email', 'homepage', 'title', 'body',
                          'published']

    def upgrade1(self, article):
        def ArticleUpdateTx(old_article, old_comments):
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

        if 'permalink' not in article:
            return -1
        q = datastore.Query('Comment')
        q['article ='] = article.key()
        q.Order('thread')
        comments = q.Get(1000)
        if datastore.RunInTransaction(ArticleUpdateTx, article, comments):
            datastore.Delete([article] + comments)
            logging.info('Updated article "%s"' % (article['title'],))
            return 1
        else:
            logging.info('Failed to update article "%s". Trying again.' % (article['title'],))
            return 0
    
    def upgrade2(self, article):
        if 'author' in article:
            return 1
        email = config.BLOG['email']
        name, nick = config.BLOG['authors'][email]
        try:
            author = datastore.Get(datastore.Key.from_path("Author", nick))
        except datastore_errors.EntityNotFoundError:
            author = datastore.Entity('Author', name=nick)
            author['user'] = users.User(email)
            author['name'] = name
            author['article_count'] = 0
        author['article_count'] += 1
        article['author'] = author.key()
        datastore.Put([article, author])
        return 1
    
    upgrade_phases = {
        1: upgrade1,
        2: upgrade2,
    }
    
    @authorized.role("admin")
    def get(self):
        upgrade_phase = int(self.request.get('phase', 0))
        if not upgrade_phase:
            page = view.ViewPage()
            page.render(self, {})
            return

        next = self.request.get('next', None)
        upgrade_func = self.upgrade_phases[upgrade_phase]
        
        q = datastore.Query('Article')
        if next:
            q['__key__ >'] = datastore.Key(next)
        q.Order('__key__')
        articles = q.Get(1)
        if articles:
            article = articles[0]
            logging.info("Running upgrade phase %d on article '%s'"
                         % (upgrade_phase, article['title']))
            result = upgrade_func(self, article)
            if result == -1:
                upgrade_phase +=1
                next = ''
            elif result == 1:
                next = str(article.key())
        if upgrade_phase not in self.upgrade_phases or not article:
            self.response.out.write("")
        else:
            response = {
                "title": article['title'] if next else '',
                "next": next,
                "phase": upgrade_phase,
            }
            self.response.out.write(simplejson.dumps(response))
