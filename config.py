import os
import logging

APP_ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

# If we're debugging, turn the cache off, etc.
# Set to true if we want to have our webapp print stack traces, etc
DEBUG = os.environ['SERVER_SOFTWARE'].startswith('Dev')
logging.info("Starting application in DEBUG mode: %s", DEBUG)

# Don't change default_blog or default_page to prevent conflicts when merging #  Bloog source code updates.
# Do change blog or page dictionaries at the bottom of this config module.

BLOG = {
    "bloog_version": "0.8",
    "html_type": "text/html",
    "charset": "utf-8",
    "title": "dotcomstolemybrain.com",
    # List authors here, in the form of email: (real name, nick). email address
    # must match the one the user will sign in with, and nick will be the
    # identifier used in URLs. It must not start with a number or underscore.
    # Note that any change to an entry here will cause them to be treated as a
    # new author entirely. Deleting an author who should no longer have access
    # is fine, though.
    "authors": {
        "lex@notdot.net": ("Your Name", "lex"),
    },
    # This must be the email address of a registered administrator for the 
    # application due to mail api restrictions. Must match an email in the
    # authors array above.
    "email": "lex@notdot.net",
    "description": "But we'll give it back if you're nice.",
    "root_url": "http://www.dotcomstolemybrain.com",
    "master_atom_url": "/feeds/atom.xml",
    # By default, visitors can comment on article for this many days.
    # This can be overridden by setting article.allow_comments
    "days_can_comment": 60,
    # You can override this default for each page through a handler's call to 
    #  view.ViewPage(cache_time=...)
    "cache_time": 0 if DEBUG else 3600,

    # Use the default YUI-based theme.
    # If another string is used besides 'default', calls to static files and
    #  use of template files in /views will go to directory by that name.
    "theme": ["vectorlover", "default"],
    
    # Display gravatars alongside user comments?
    "use_gravatars": True,
    
    # Do you want to be emailed when new comments are posted?
    "send_comment_notification": True,

    # If you want to use legacy ID mapping for your former blog platform,
    # define it here and insert the necessary mapping code in the
    # legacy_id_mapping() function in ArticleHandler (blog.py).
    # Currently only "Drupal" is supported.
    "legacy_blog_software": None,
    #"legacy_blog_software": "Drupal",
    #"legacy_blog_software": "Serendipity",
    
    # If you want imported legacy entries _not_ mapped in the file above to
    # redirect to their new permanent URL rather than responding on their
    # old URL, set this flag to True.
    "legacy_entry_redirect": False,
    
    # If you want to use a Google Custom Search Engine instead of the built-in
    # search facility, set the setting below to True. To improve the
    # completeness and timeliness of the search, make sure you've submitted your
    # sitemap to Google (/sitemap.xml).
    "use_google_cse": True,
    
    # If you want to 'claim' your blog as your OpenID identity, put your OpenID
    # server and URL here.
    "openid_server": "",
    "openid_delegate": "",
}

PAGE = {
    "title": BLOG["title"],
    "articles_per_page": 5,
    "navlinks": [
        { "title": "Articles", "description": "Bits of Info", 
          "url": "/articles"},
        { "title": "Contact", "description": "Send me a note", 
          "url": "/contact"},
    ],
    "featuredMyPages": {
    },
    "featuredOthersPages": {
    },
}
