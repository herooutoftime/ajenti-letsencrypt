import pwd
import grp
import os

from string import Template
from shutil import copyfile
from subprocess import call

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder
from ajenti.util import platform_select

class Settings (object):
   def __init__(self):
      self.basedir = "/etc/letsencrypt.sh/"
      self.wellknown = '/var/www/letsencrypt.sh/'
      self.domains = 'example.com sub.example.com'
      self.cronjob = False

@plugin
class LetsEncryptPlugin (SectionPlugin):
    pwd = os.path.join(os.path.dirname(os.path.realpath(__file__)), '')
    etc_available_dir = platform_select(
        debian='/etc/letsencrypt.sh/',
        centos='/etc/letsencrypt.sh/',
        mageia='/etc/letsencrypt.sh/',
        freebsd='/usr/local/etc/letsencrypt.sh/',
        arch='/etc/letsencrypt.sh/',
        osx='/opt/local/etc/letsencrypt.sh/',
    )
    nginx_config_dir = platform_select(
        debian='/etc/nginx/conf.d',
        centos='/etc/nginx/conf.d',
        mageia='/etc/nginx/conf.d',
        freebsd='/usr/local/etc/nginx/conf.d',
        arch='/etc/nginx/sites-available',
        osx='/opt/local/etc/nginx',
    )

    def init(self):
        self.title = 'LetsEncrypt'  # those are not class attributes and can be only set in or after init()
        self.icon = 'user-secret'
        self.category = 'Security'

        """
        UI Inflater searches for the named XML layout and inflates it into
        an UIElement object tree
        """
        self.append(self.ui.inflate('letsencrypt:main'))

	self.settings = Settings()

	self.binder = Binder(self.settings, self)
	self.binder.populate()

    # self.counter = 0
    # self.refresh()

    # def refresh(self):
    #     """
    #     Changing element properties automatically results
    #     in an UI updated being issued to client
    #     """
    #     self.find('counter-label').text = 'Counter: %i' % self.counter

    def write_domain_file(self):
    	filename = 'domains.txt'
        filepath = self.settings.basedir + filename
    	target = open(filepath, 'w')
    	target.write(self.settings.domains)
    	target.close()

    # def write_config_file(self):
    # 	filename = 'config'
    #     filepath = self.settings.basedir + filename
    # 	target = open(filename, 'w')
    # 	target.write(self.settings.domains)
    # 	target.close()

    def write_dir(self):
    	uid = pwd.getpwnam("www-data").pw_uid
    	gid = grp.getgrnam("www-data").gr_gid

    	if not os.path.exists(self.settings.basedir):
        	os.makedirs(self.settings.basedir)
    		os.chown(self.settings.basedir, uid, gid)
    	if not os.path.exists(self.settings.wellknown):
        	os.makedirs(self.settings.wellknown)
    		os.chown(self.settings.wellknown, uid, gid)

    def copy_config_to_etc(self):
        dir = self.pwd

        src_config = dir + 'libs/letsencrypt.sh/docs/examples/config'
        dst_config = self.settings.basedir + 'config'
        copyfile(src_config, dst_config)

    def create_custom_config(self):
        template = """
        BASEDIR=$basedir
        WELLKNOWN=$wellknown
        """
        dict = {
            'basedir': self.settings.basedir,
            'wellknown': self.settings.wellknown
        }

        filename = 'config'
        filepath = self.etc_available_dir + filename
        custom_config = open(filepath, 'w')
        src = Template( template )
        custom_config.write(src.safe_substitute(dict))

    def create_wellknown_location(self):
        template = """
        location $location {
            alias $alias;
        }
        """
        dict = {
            'location': '/.well-known/acme-challenge',
            'alias': self.settings.wellknown
        }
        filename = 'letsencrypt.conf'
        filepath = self.nginx_config_dir + '/' + filename
        letsencrypt_host = open(filepath, 'w')
        src = Template( template )
        letsencrypt_host.write(src.safe_substitute(dict))
        self.context.notify('info', filepath)


    def call_script(self):
        cmd = self.pwd + 'libs/letsencrypt.sh/letsencrypt.sh'
        self.context.notify('info', call([cmd, "-c"]))

    #def create_cron(self):

    #def remove cron(self):

    @on('apply', 'click')
    def on_button(self):
    	self.binder.update()
    	self.binder.populate()
        self.write_dir()
        self.write_domain_file()
        # self.copy_config_to_etc()
        self.create_custom_config()
        self.create_wellknown_location()
        self.call_script()

        self.context.notify('info', 'Saved')
