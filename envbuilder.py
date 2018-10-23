#!/usr/bin/python

import subprocess
from snc_config import SncConfig
import argparse
from color_print import ColorPrint
import os
from multiprocessing import Pool
import copy_reg
import types
from itertools import repeat
import time
import xml.etree.ElementTree as ET
from property_file import Properties



def _reduce_method(m):
    if m.im_self is None:
        return getattr, (m.im_class, m.im_func.func_name)
    else:
        return getattr, (m.im_self, m.im_func.func_name)
copy_reg.pickle(types.MethodType, _reduce_method)


class EnvironmentBuilder(object):
    """
    This class is main class of SNC Env builder
    """
    def __init__(self, release_name):
        self.release = release_name
        self.config = SncConfig()
        self.base_dir = self.config.getstring('git_repo','base_dir');
        self.path_to_workspace = self.base_dir + os.sep + release_name
        self.eclipse = self.config.getstring('envbuilder','eclipse');
        self.abort_on_error = self.config.getboolean('envbuilder', 'abort_on_error')
        self.parallel_run = self.config.getboolean('envbuilder', 'parallel_run')
        self.print_cmd_output = self.config.getboolean('envbuilder', 'print_cmd_output')
        self.instance_port = self.config.getint('mid', 'instance_port')
        self.instance_host = self.config.getstring('mid', 'instance_host')
        self.instance_user = self.config.getstring('mid', 'instance_user')
        self.instance_password = self.config.getstring('mid', 'instance_password')
        self.repo_status = {}

    def clone_env(self, user, password):
        now = time.time()
        if not os.path.exists(self.path_to_workspace):
            os.makedirs(self.path_to_workspace)
        list_of_repos = self.config.getlist('git_repo','repo');
        if self.parallel_run and password:
            pool = Pool(len(list_of_repos))
            pool.map(self._clone_env, zip(list_of_repos,repeat(user),repeat(password)))
        else:
            for repo in list_of_repos:
                self._clone_env([repo, user, password])
        later = time.time()
        difference = int(later - now)
        ColorPrint.blue_highlight("Clone operation for release [{0}] took [{1}] seconds".format(self.release,difference))

    def _clone_env(self, args):
        password = None
        if len(args) == 3:
            repo, user, password = args
        else:
            repo, user = args
        if not os.path.exists(self.path_to_workspace + os.sep + repo):
            if password is not None:
                clone_cmd ='cd {0};git clone https://{1}:\'{2}\'@code.devsnc.com/dev/{3}'.format(self.path_to_workspace,user,password,repo)
            else:
                clone_cmd ='cd {0};git clone https://{1}@code.devsnc.com/dev/{2}'.format(self.path_to_workspace,user,repo)
            self.handle_command(clone_cmd)

    def switch_track(self, track_name):
        now = time.time()
        list_of_repos = self.config.getlist('git_repo','repo');
        if(self.parallel_run):
            pool = Pool(len(list_of_repos))
            pool.map(self._switch_repo, zip(list_of_repos,repeat(track_name)))
        else:
            for repo in list_of_repos:
                self._switch_repo([repo, track_name])
        later = time.time()
        difference = int(later - now)
        ColorPrint.blue_highlight("Switch operation for release [{0}] took [{1}] seconds".format(self.release,difference))

    def _switch_repo(self, args):
        repo, track_name = args
        ColorPrint.blue_highlight("Trying to switch the repository [{0}] to [{1}]".format(repo, track_name))
        if os.path.exists(self.path_to_workspace + os.sep + repo):
            p_status, out, err = self.handle_command('cd {0};git rev-parse --abbrev-ref HEAD'.format(self.path_to_workspace + os.sep + repo))
            if out == track_name:
                ColorPrint.warn("The current repository [{0}] already switched to [{1}], skipping".format(repo, track_name))
            else:
                self.handle_command('cd {0};git fetch && git checkout {1}'.format(self.path_to_workspace + os.sep + repo, track_name))

    def import_projects(self):
        project_per_repo = self.config.getsection('projects')
        for repo_name, projects in project_per_repo:
            ColorPrint.blue_highlight("Importing {0} repository projects".format(repo_name))
            for project_name in projects.split(','):
                project_path = self.path_to_workspace + os.sep + repo_name + os.sep + project_name
                if os.path.exists(project_path):
                    java_env = 'source ~/.bash_profile'
                    cmd = java_env + ';{2} -nosplash -data "{0}"  -application org.eclipse.cdt.managedbuilder.core.headlessbuild  -import {1}'.format(self.path_to_workspace,project_path,self.eclipse)
                    self.handle_command(cmd)

    def mvn_build(self):
        project_per_repo = self.config.getsection('projects')
        for repo_name, projects in project_per_repo:
            ColorPrint.blue_highlight("Starting mvn install for repository {0}".format(repo_name))
            for project_name in projects.split(','):
                project_path = self.path_to_workspace + os.sep + repo_name + os.sep + project_name
                java_env = 'source ~/.bash_profile'
                cmd = java_env + ';cd {0};mvn clean install -DskipTests'.format(project_path)
                self.handle_command(cmd)

    def open_ide(self):
        java_env = 'source ~/.bash_profile'
        cmd = java_env + ';{0} -nosplash -data "{1}"'.format(self.eclipse,self.path_to_workspace)
        self.handle_command(cmd)

    def run_git_pull(self):
        now = time.time()
        list_of_repos = self.config.getlist('git_repo','repo');
        if(self.parallel_run):
            pool = Pool(len(list_of_repos))
            pool.map(self._git_pull, list_of_repos)
        else:
            for repo in list_of_repos:
                self._git_pull(repo)
        later = time.time()
        difference = int(later - now)
        ColorPrint.blue_highlight("Pull operation for release [{0}] took [{1}] seconds".format(self.release,difference))

    def _git_pull(self, repo):
        ColorPrint.blue_highlight("Pulling the repository [{0}]".format(repo))
        repo_path = self.path_to_workspace + os.sep + repo
        if os.path.exists(repo_path):
            if self._is_branch_up_to_date(repo_path):
                if repo in self.repo_status and self.repo_status[repo]:
                    ColorPrint.blue_highlight('Your repository [{0}] is up-to-date, skipping [git pull]'.format(repo))
                else:
                    self.handle_command('cd {0};git pull'.format(repo_path))
            else:
                self.run_git_stash(repo_path)
                if self._is_ready_to_pull(repo_path):
                    if repo in self.repo_status and self.repo_status[repo]:
                        ColorPrint.blue_highlight('Your repository [{0}] is up-to-date, skipping [git pull]'.format(repo))
                    else:
                        self.handle_command('cd {0};git pull'.format(repo_path))
                self.run_git_unstash(repo_path)
        else:
            ColorPrint.warn( "The repository path [{0}] is not available".format(repo))

    def run_git_stash(self, repo_path):
        if os.path.exists(repo_path):
            ColorPrint.blue_highlight( "Stashing the repository [{0}]".format(repo_path))
            self.handle_command('cd {0};git stash'.format(repo_path))
        else:
            ColorPrint.warn( "The repository path [{0}] is not available".format(repo_path))

    def run_git_unstash(self, repo_path):
        if os.path.exists(repo_path):
            ColorPrint.blue_highlight("Unstashing the repository [{0}]".format(repo_path))
            self.handle_command('cd {0};git stash pop'.format(repo_path))
        else:
            ColorPrint.warn("The repository path [{0}] is not available".format(repo_path))

    def _is_ready_to_pull(self, repo_path):
        ColorPrint.blue_highlight("Checking repository status [{0}]".format(repo_path))
        p_status, cmd_out, err = self.handle_command('cd {0};git status -uno'.format(repo_path),True, True)
        ColorPrint.info(cmd_out)
        repo = os.path.basename(os.path.normpath(repo_path))
        if 'Your branch is up-to-date' in str(cmd_out):
            self.repo_status[repo] = True
        else:
            self.repo_status[repo] = False

        if 'nothing to commit' in str(cmd_out):
            return True
        else:
            return False

    def _is_branch_up_to_date(self, repo_path):
        ColorPrint.blue_highlight("Checking repository status [{0}]".format(repo_path))
        self.handle_command('cd {0};git remote update'.format(repo_path))
        if self._is_ready_to_pull(repo_path):
            return True
        else:
            repo = os.path.basename(os.path.normpath(repo_path))
            if repo in self.repo_status and self.repo_status[repo]:
                return True
            else:
                return False

    @staticmethod
    def print_list_avalable_versions():
        base_dir = SncConfig().getstring('git_repo','base_dir');
        ColorPrint.blue_highlight("***** Avalable versions ****:")
        for dir in os.listdir(base_dir):
            if os.path.isdir(base_dir + os.sep + dir) and not dir.startswith('.'):
                if EnvironmentBuilder.is_release_direcrory(dir):
                    ColorPrint.info('[' + dir + ']')

    def create_mid_config(self, port='0'):
        current_port = int(port)
        if not (current_port > 0 and current_port < 65536):
            current_port = self.instance_port;
        path_to_work_config = self.path_to_workspace + os.sep + 'mid/mid/work/config.xml'
        path_to_orig_config = self.path_to_workspace + os.sep + 'mid/mid/config.xml'
        path_to_key_store = self.path_to_workspace + os.sep + 'mid/mid/keystore/agent_keystore.jks'
        if not os.path.exists(path_to_work_config):
            ColorPrint.blue_highlight("Configuring the local mid server with instance port [{0}]".format(current_port))
            tree = ET.parse(path_to_orig_config)
            root = tree.getroot()
            for parameter in root.findall('parameter'):
                parameter_name = parameter.get('name')
                if parameter_name == 'url':
                    parameter.set('value', '{0}:{1}/'.format(self.instance_host, current_port))
                if parameter_name == 'mid.instance.username':
                    parameter.set('value', self.instance_user)
                if parameter_name == 'mid.instance.password':
                    parameter.set('value', self.instance_password)
                if parameter_name == 'name':
                    parameter.set('value', 'eclipse01')
            tree.write(path_to_work_config)
            if os.path.exists(path_to_key_store):
                ColorPrint.info("Found keystore file, deleting it to prevent crash on mid start [{0}]".format(path_to_key_store))
                os.remove(path_to_key_store)
            ColorPrint.blue_highlight("Mid server is ready to start")
        else:
            ColorPrint.err("Configuration file for mid server already exist in [{0}] directory".format(path_to_work_config))

    def hard_zboot(self, release):
        self.instance_db_name_prefix = self.config.getstring('glide', 'instance_db_name_prefix')
        db_name = '{0}_{1}'.format(self.instance_db_name_prefix, release);
        ColorPrint.blue_highlight("Zboot db name [{0}]".format(db_name))
        self.delete_mysql_db(db_name)
        self.create_mysql_db(db_name)


    @staticmethod
    def is_release_direcrory(release_dir):
        base_dir = SncConfig().getstring('git_repo','base_dir');
        full_path = base_dir + os.sep + release_dir
        list_of_dirs =  os.listdir(full_path)
        list_of_repos = SncConfig().getlist('git_repo','repo');
        return not set(list_of_repos).isdisjoint(list_of_dirs)


    def create_mysql_db(self, db_name):
        ColorPrint.blue_highlight("Creating mysql db [{0}]".format(db_name))
        cmd = 'mysql -uroot -e "create database {0}" '.format(db_name)
        self.handle_command(cmd)

    def delete_mysql_db(self, db_name):
        ColorPrint.blue_highlight("Deleting mysql db [{0}]".format(db_name))
        cmd = 'mysql -uroot -e "drop database {0}" '.format(db_name)
        self.handle_command(cmd)

    def configure_instance(self):
        glide_db_properties = self.path_to_workspace + \
                              os.sep + 'glide-launcher/glide-home-dist/conf/overrides.d/glide.db.properties'
        glide_properties = self.path_to_workspace + \
                           os.sep + 'glide-launcher/glide-home-dist/conf/overrides.d/glide.properties'


        if os.path.isfile(glide_db_properties):
            print glide_db_properties
            p = Properties(glide_db_properties)
            print p.get_all_properies()

        if os.path.isfile(glide_properties):
            print glide_properties
            p = Properties(glide_properties)
            print p.get_all_properies()



    def handle_command(self, cmd, check_rc=True, get_output=False):
        """
         Executes command
        :param cmd: command string to be executed
        :return: rc, stdout, stderr
        """

        ColorPrint.info("Running command: {0}, Please Wait".format(cmd))
        stdout_flag = None
        if get_output:
            stdout_flag = subprocess.PIPE
        p = subprocess.Popen(cmd,
                              stdout=stdout_flag,
                              stderr=subprocess.STDOUT,
                              shell=True)


        (out, err) = p.communicate()
        p_status = p.wait()

        if check_rc:
            if p_status != 0:
                ColorPrint.err("[handle_command] failed executing: {0}".format(cmd))
                ColorPrint.err(str(err))
            else:
                ColorPrint.info("[handle_command] succeeded executing: {0}".format(cmd))

        if self.abort_on_error and p_status != 0:
            ColorPrint.err("EnvironmentBuilder: Execution aborted due to error[s]")
            exit(1)

        return p_status, out, err


if __name__ == '__main__':
    #Font Name: Big
    #http://patorjk.com/software/taag
    ColorPrint.blue_highlight("""
#    ______            ____        _ _     _                              __   ___
#   |  ____|          |  _ \      (_| |   | |                            /_ | |__ \\
#   | |__   _ ____   _| |_) |_   _ _| | __| | ___ _ __  __   _____ _ __   | |    ) |
#   |  __| | '_ \ \ / |  _ <| | | | | |/ _` |/ _ | '__| \ \ / / _ | '__|  | |   / /
#   | |____| | | \ V /| |_) | |_| | | | (_| |  __| |     \ V |  __| |     | |_ / /_
#   |______|_| |_|\_/ |____/ \__,_|_|_|\__,_|\___|_|      \_/ \___|_|     |_(_|____|
#                                                                                   """);

    parser = argparse.ArgumentParser(prog='envbuilder',
                                     description='ServiceNow build environment tool',
                                     epilog='./envbuilder.py -u some.user -p password -t trackname -r release')
    parser.add_argument('-u', help='git user name', nargs='?', dest="username")
    parser.add_argument('-p', help='git password',nargs='?', dest="password")
    parser.add_argument('-pull', help='run git pull for all or specified repositories \n ./envbuilder.py -pull -r release',action="store_true")
    parser.add_argument('-sw', help='switch all repositories to relevant track \n /envbuilder.py -sw -t trackname -r release', action="store_true")
    parser.add_argument('-t', help='track to switch', nargs='?',dest="track")
    parser.add_argument('-r', help='release name', nargs='?', dest="release")

    parser.add_argument('-status', help='Status of the current local branches', action="store_true")
    parser.add_argument('-mvn', help='Run maven install -DskipTests for the specified release', action="store_true")
    parser.add_argument('-mid', help='Add config file for local mid server with default configuration\n /envbuilder.py -mid -port number -r release',action="store_true")
    parser.add_argument('-port', help='Specify port number to change the default', nargs='?', dest="port")
    parser.add_argument('-zboot', help='Delete all tables of the db for specific release', action="store_true")
    parser.add_argument('-glide', help='Configuring glide', action="store_true")
    args = parser.parse_args()

    print str(args)

    if args.status:
        EnvironmentBuilder.print_list_avalable_versions()
        exit(0)

    if args.mvn and args.release:
        builder = EnvironmentBuilder(args.release)
        builder.mvn_build()
        exit(0)

    if args.mid and args.release:
        builder = EnvironmentBuilder(args.release)
        if args.port:
            builder.create_mid_config(args.port)
        else:
            builder.create_mid_config()
        exit(0)

    if args.sw and args.release and args.track:
        builder = EnvironmentBuilder(args.release)
        EnvironmentBuilder.print_list_avalable_versions()
        builder.switch_track(args.track)
        exit(0)

    if args.pull and args.release:
        builder = EnvironmentBuilder(args.release)
        EnvironmentBuilder.print_list_avalable_versions()
        builder.run_git_pull();
        exit(0)

    if args.zboot and args.release:
        builder = EnvironmentBuilder(args.release)
        builder.hard_zboot(args.release)
        exit(0)

    if args.glide and args.release:
        print "lior"
        builder = EnvironmentBuilder(args.release)
        builder.configure_instance()
        exit(0)

    if args.username and args.release and args.track:
        builder = EnvironmentBuilder(args.release)
        EnvironmentBuilder.print_list_avalable_versions()
        builder.clone_env(args.username,args.password)
        builder.switch_track(args.track)
        builder.import_projects()
        builder.mvn_build()
        builder.open_ide()
    else:
        parser.print_help()

