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
      self.basedir = platform_select(
          debian='/etc/letsencrypt.sh/',
          centos='/etc/letsencrypt.sh/',
          mageia='/etc/letsencrypt.sh/',
          freebsd='/usr/local/etc/letsencrypt.sh/',
          arch='/etc/letsencrypt.sh/',
          osx='/opt/local/etc/letsencrypt.sh/',
      )
      self.wellknown = '/var/www/letsencrypt.sh/'
      self.domains = 'example.com sub.example.com'
      self.cronjob = False
      self.results = ''

@plugin
class LetsEncryptPlugin (SectionPlugin):

    pwd = os.path.join(os.path.dirname(os.path.realpath(__file__)), '')

    nginx_config_dir = platform_select(
        debian='/etc/nginx.custom.d',
        centos='/etc/nginx.custom.d',
        mageia='/etc/nginx.custom.d',
        freebsd='/usr/local/etc/nginx.custom.d',
        arch='/etc/nginx/sites-available',
        osx='/opt/local/etc/nginx',
    )
    crontab_dir = platform_select(
        debian='/etc/cron.d',
        centos='/etc/cron.d',
        mageia='/etc/cron.d',
        freebsd='/usr/local/etc/cron.d',
        arch='/etc/cron.d',
        osx='/opt/local/etc/cron.d',
    )

    def init(self):
        self.title = 'LetsEncrypt'  # those are not class attributes and can be only set in or after init()
        self.icon = 'lock'
        self.category = 'Security'

        """
        UI Inflater searches for the named XML layout and inflates it into
        an UIElement object tree
        """
        self.append(self.ui.inflate('letsencrypt:main'))

        self.settings = Settings()

        self.binder = Binder(self.settings, self)
    	self.binder.populate()

    def on_page_load(self):
        domains = os.linesep.join(self.read_domain_file())
        cron = self.check_cron()
        self.find('domains').value = str(domains)
        self.find('cronjob').value = cron

    def write_domain_file(self):
    	filename = 'domains.txt'
        filepath = self.settings.basedir + filename
    	file = open(filepath, 'w')
    	file.write(self.find('domains').value)
    	file.close()

    def read_domain_file(self):
        filename = 'domains.txt'
        filepath = self.settings.basedir + filename
    	file = open(filepath)
    	with file as f:
            lines = f.readlines()
        return lines

    def write_dir(self):
    	uid = pwd.getpwnam("www-data").pw_uid
    	gid = grp.getgrnam("www-data").gr_gid

    	if not os.path.exists(self.settings.basedir):
        	os.makedirs(self.settings.basedir)
    		os.chown(self.settings.basedir, uid, gid)
    	if not os.path.exists(self.settings.wellknown):
        	os.makedirs(self.settings.wellknown)
    		os.chown(self.settings.wellknown, uid, gid)

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
        filepath = self.settings.basedir + filename
        file = open(filepath, 'w')
        src = Template( template )
        file.write(src.safe_substitute(dict))
        file.close()

    def create_wellknown_location(self):
        template = """
server {
    server_name $domains;
    listen *:80;
    location $location {
        alias $alias;
    }
}
        """
        dict = {
            'location': '/.well-known/acme-challenge',
            'alias': self.settings.wellknown,
            'domains': " ".join(self.read_domain_file())
        }
        filename = '00_letsencrypt.conf'
        filepath = self.nginx_config_dir + '/' + filename
        file = open(filepath, 'w')
        src = Template( template )
        file.write(src.safe_substitute(dict))
        file.close()

    def call_script(self):
        cmd = self.pwd + 'libs/letsencrypt.sh/letsencrypt.sh'
        call([cmd, "-c"])
        self.context.notify('info', 'Certificates requested')

    def create_cron(self):
        filename = 'letsencrypt'
        file = open(self.crontab_dir + '/' + filename, 'w')
        template = "0 0 1 * * " + self.pwd + 'libs/letsencrypt.sh/letsencrypt.sh -c'
        file.write(template)
        file.close()

    #def remove cron(self):


    def check_cron(self):
        filename = 'letsencrypt'
        if os.path.isfile(self.crontab_dir + '/' + filename):
            return True
        return False

    @on('apply', 'click')
    def on_button(self):
    	self.binder.update()
    	self.binder.populate()
        self.write_dir()
        self.write_domain_file()
        # self.copy_config_to_etc()
        self.create_custom_config()
        self.create_wellknown_location()

        if self.settings.cronjob:
            self.create_cron()

        self.call_script()
