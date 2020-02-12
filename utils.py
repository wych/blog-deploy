import toml
import os
import subprocess
import re
import shutil
from urllib.parse import quote_plus

class ConfigInvalidValueError(Exception):
    pass

class RepoInitError(Exception):
    pass

class RepoOperationError(Exception):
    pass

class BlogBuildError(Exception):
    pass


class Config:
    
    root_path: str      = None
    listen_ip: str      = '0.0.0.0'
    listen_port: int    = 8080
    listen_url: str     = '/'
    secret_key: bytes   = None
    source: str         = None
    git_username: str   = None
    git_token: str      = None
    blog_app: str       = None # Hugo, Hexo or Jekyll
    repo_dir: str       = 'repo' # Where the repository saved
    deploy_dir: str     = 'deploy' # Generated static folder parent
    deplot_name: str    = 'www' # Generated static folder name
    
    @classmethod
    def parse(cls, toml_path):
        toml_conf = toml.load(toml_path)
        conf = cls()
        conf.root_path = os.path.dirname(os.path.abspath(toml_path))


        listen_conf         = toml_conf["listen"]
        conf.listen_ip      = listen_conf['ip'] if listen_conf.get('ip') else cls.listen_ip
        conf.listen_port    = listen_conf['port'] if listen_conf.get('port') else cls.listen_port
        conf.listen_url     = listen_conf['url'] if listen_conf.get('url') else cls.listen_url
        conf.secret_key     = bytes(listen_conf['secretKey'].encode('utf-8'))

        repo_conf           = toml_conf["repo"]
        conf.source         = repo_conf["source"]
        conf.git_username   = repo_conf.get("username")
        conf.git_token      = repo_conf.get("token")
        conf.blog_app       = cls.check_blog_app(repo_conf["blogApp"])
        conf.repo_dir       = os.path.join(conf.root_path, repo_conf["repoDir"] if repo_conf.get('repoDir') else cls.repo_dir)
        conf.deploy_dir     = os.path.join(conf.root_path, repo_conf["deployDir"] if repo_conf.get('deployDir') else cls.deploy_dir)
        conf.deploy_name    = repo_conf["deployName"] if repo_conf.get('deployName') else cls.deploy_name

        return conf

    @staticmethod
    def check_blog_app(blog_app: str) -> str:
        available = ["hugo", "jekyll", "hexo"]
        if blog_app in available:
            return blog_app
        raise ConfigInvalidValueError


class Repo:

    def __init__(self, conf: Config):
        self.source     = conf.source
        self.repo_dir   = conf.repo_dir
        self.username   = conf.git_username
        self.password   = conf.git_token

        if not self.__is_existed_repo():
            self.__repo_init()

    def __repo_init(self):
        if not os.path.exists(self.repo_dir):
            os.mkdir(self.repo_dir)
            self.__clone()
        elif os.path.isdir(self.repo_dir) and os.listdir(self.repo_dir) == []:
            self.__clone()
        else:
            raise RepoInitError("%s exists and not an empty directory!" % self.repo_dir)
        return

    def __is_existed_repo(self) -> bool:

        command = 'git remote -v'.split(' ')
        pattern_str = r'origin\s%s\s\(fetch\)' % self.__gen_url()
        try:
            ret = self.__run(command)
            if not re.search(pattern_str, ret):
                return False
            else:
                return True
        except:
            return False

    def __clone(self):
        quiet_option = '-q'
        recursive_option = '--recursive'
        command = 'git clone {} {} {} .'.format(quiet_option, recursive_option, self.__gen_url()).split(' ')
        self.__run(command)

    def update(self):
        quiet_option = '-q'
        command = 'git pull {}'.format(quiet_option).split(' ')
        self.__run(command)

    def __gen_url(self):
        if hasattr(self, 'url'):
            return self.__url
        if self.username is None:
            self.__url = self.source
            return self.__url
        else:
            url_ele_list = self.source.split('://')
            ret = []
            for i, e in enumerate(url_ele_list):
                if i == 1:
                    ret.extend(('://', self.username, ':', quote_plus(self.password), '@'))
                ret.append(e)
            self.__url = ''.join(ret)
            return self.__url

    def __run(self, command: list):
        ret = subprocess.run(command, capture_output=True, cwd=self.repo_dir, text=True)
        if ret.stderr != '':
            raise RepoOperationError
        return ret.stdout


class Builder:

    STATIC_FOLDER_MAP = {
        'hugo':     'public',
        'jekyll':   '_site',
        'hexo':     'public'
    }

    def __init__(self, conf: Config):
        self.repo_dir       = conf.repo_dir
        self.deploy_dir     = conf.deploy_dir
        self.deploy_name    = conf.deploy_name
        self.blog_app       = conf.blog_app

    def __static4hugo(self):
        quiet_option = '--quiet'
        command = 'hugo {}'.format(quiet_option).split(' ')
        self.__run(command)

    def __static4hexo(self):
        quiet_option = '--slient'
        command = 'hexo {} g'.format(quiet_option).split(' ')
        self.__run(command)

    def __static4jekyll(self):
        quiet_option = '-q'
        command = 'jekyll build {}'.format(quiet_option).split(' ')
        self.__run(command)
    
    def gen_static(self):
        if self.blog_app == 'hugo':
            self.__static4hugo()
        elif self.blog_app == 'hexo':
            self.__static4hexo()
        elif self.blog_app == 'jekyll':
            self.__static4jekyll()

    def deploy(self):
        source = os.path.join(self.repo_dir, self.STATIC_FOLDER_MAP[self.blog_app])
        target = os.path.join(self.deploy_dir, self.deploy_name)
        if os.path.exists(target):
            shutil.rmtree(target)
        shutil.copytree(source, target)

    def __run(self, command: str):
        ret = subprocess.run(command, capture_output=True, cwd=self.repo_dir, text=True)
        if ret.stderr != '':
            raise BlogBuildError
        return ret.stdout