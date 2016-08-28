import pwd
import grp
import os
import subprocess
import json

from string import Template
from shutil import copyfile

from ajenti.api import *
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui import on
from ajenti.ui.binder import Binder
from ajenti.util import platform_select

from pprint import pprint

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
      self.cronfile = 'letsencrypt'
      self.results = ''
      self.domainfile = 'domains.txt'
      self.nginx_config = '00_letsencrypt.conf'

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

    has_domains = False

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
        filepath = self.settings.basedir + self.settings.domainfile
        domains = ''
        if os.path.isfile(filepath):
            domains = os.linesep.join(self.read_domain_file())
        cron = self.check_cron()
        self.find('domains').value = str(domains)
        self.find('cronjob').value = cron

    def write_domain_file(self):
        filepath = self.settings.basedir + self.settings.domainfile
        if not self.find('domains').value:
            self.context.notify('info', 'No domains specified')
            self.has_domains = False
            return

        file = open(filepath, 'w')
        if file.write(self.find('domains').value) is None:
            self.has_domains = True
        else:
            self.context.notify('error', 'Domain file write error')
    	file.close()

    def read_domain_file(self):
        filepath = self.settings.basedir + self.settings.domainfile
    	if not open(filepath):
            self.context.notify('error', 'Domain file could not be read')

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
        if file.write(src.safe_substitute(dict)) is not None:
            self.context.notify('info', 'Letsencrypt error')
        file.close()

    def create_wellknown_location(self):
        if not self.check_nginx_custom_dir():
            return False

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
        filepath = self.nginx_config_dir + '/' + self.settings.nginx_config
        file = open(filepath, 'w')
        src = Template( template )
        if file.write(src.safe_substitute(dict)) is not None:
            self.context.notify('info', 'WELLKNOWN config write error')
        file.close()

    def create_cron(self):
        file = open(self.crontab_dir + '/' + self.settings.cronfile, 'w')
        template = "0 0 1 * * " + self.pwd + 'libs/letsencrypt.sh/letsencrypt.sh -c'
        if not file.write(template):
            self.context.notify('info', 'Cron job error')
        file.close()

    def remove_cron(self):
        if os.path.isfile(self.crontab_dir + '/' + self.settings.cronfile):
            if os.remove(self.crontab_dir + '/' + self.settings.cronfile):
                return True
            else:
                self.context.notify('info', 'Cron remove error')
                return False

    def check_cron(self):
        if os.path.isfile(self.crontab_dir + '/' + self.settings.cronfile):
            return True
        return False

    def check_nginx_custom_dir(self):
        if not os.path.isdir(self.nginx_config_dir):
            if os.makedirs(self.nginx_config_dir):
                return True
            else:
                self.context.notify('error', 'NGINX custom dir write error')
                return False

    def request_certificates(self):
        params = [self.pwd + 'libs/letsencrypt.sh/letsencrypt.sh', '-c']
        if self.find('renewal').value:
            params.append('--force')

        p = subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()

        if out:
            self.context.notify('info', 'OUT: ' + out)
        if err:
            self.context.notify('info', 'ERR: ' + err)

    def save(self):
        self.binder.update()
    	self.binder.populate()
        self.write_dir()
        self.write_domain_file()

        if not self.has_domains:
            return

        self.create_custom_config()
        self.create_wellknown_location()

        if self.settings.cronjob:
            self.create_cron()
        else:
            self.remove_cron()

    @on('save', 'click')
    def save_button(self):
        self.save()

    @on('request', 'click')
    def request_button(self):
        self.save()
        self.request_certificates()
