#!/usr/bin/env python

import subprocess
from snc_config import SncConfig
from datetime import datetime, timedelta
import argparse
from argparse import RawTextHelpFormatter
from color_print import ColorPrint
from plugins import PluginsLoader
import os
from multiprocessing import Pool
import copy_reg
import types
from itertools import repeat
import time
from functools import partial
from notification_manager import NotificationManager


ENVB_PATH = 'ENVB_PATH'


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
        self.git_url = self.config.getstring('git_repo', 'git_url')
        self.base_dir = self.config.getstring('git_repo', 'base_dir');
        self.path_to_workspace = self.base_dir + os.sep + release_name
        self.abort_on_error = self.config.getboolean('envbuilder', 'abort_on_error')
        self.parallel_run = self.config.getboolean('envbuilder', 'parallel_run')
        self.print_cmd_output = self.config.getboolean('envbuilder', 'print_cmd_output')
        self.print_cmd = self.config.getboolean('envbuilder', 'print_cmd')
        self.repo_status = {}
        self.notif_mgr = NotificationManager(None, None, None)
        if os.path.exists("errors.txt"):
            os.remove("errors.txt")

    def run_commands_in_current_release(self, commands):
        final_status = True
        final_error = ''
        final_output = ''
        for command in commands:
            p_status, output, error = self.run_command_and_collect_errors("cd {0};{1}".format(self.path_to_workspace, str(command)))
            if p_status != 0:
                final_status = False
                final_error = final_error + ' ' + str(error)
                final_output = final_output + ' ' + str(output)
                break
        return final_status, final_output, final_error

    def run_command_in_background(self, command):
        b_command = "cd {0};{1} &".format(self.path_to_workspace, command)
        os.system(b_command)

    def run_command_and_collect_errors(self, command):
        p_status, output, error = EnvironmentBuilder.handle_command(command, True, True, self.print_cmd_output, self.print_cmd)
        if p_status != 0:
            current_error = "Failed command: [{0}] Error: [{1}], Output: [{2}]".format(command, error, output)
            filename = 'errors.txt'
            if os.path.exists(filename):
                append_write = 'a' # append if already exists
            else:
                append_write = 'w' # make a new file if not
            error_file = open(filename,append_write)
            error_file.write(current_error + '\n')
            error_file.close()

        return p_status, output, error

    def clone_env(self):
        now = time.time()
        if not os.path.exists(self.path_to_workspace):
            os.makedirs(self.path_to_workspace)
        list_of_repos = self.config.getlist('git_repo', 'repo');
        if self.parallel_run:
            pool = Pool(len(list_of_repos))
            pool.map(self._clone_env, list_of_repos)
        else:
            for repo in list_of_repos:
                self._clone_env(repo)
        later = time.time()
        difference = int(later - now)
        log_message = "Clone operation for release [{0}] took [{1}] seconds".format(self.release,difference)
        ColorPrint.blue_highlight(log_message)
        self.notif_mgr.send_notification(True, 'clone_env', log_message)

    def _clone_env(self, repo):
        if not os.path.exists(self.path_to_workspace + os.sep + repo):
            clone_cmd ='cd {0};git clone https://{1}/{2}'.format(self.path_to_workspace, self.git_url, repo)
            self.run_command_and_collect_errors(clone_cmd)


    def copy_local_env(self, new_release_name):
        path_to_new_release = self.base_dir + os.sep + new_release_name
        copy_cmdb = 'cp -rp ' + self.path_to_workspace + ' ' + path_to_new_release
        ColorPrint.blue_highlight("Copying environment [{0}] to [{1}] ".format(self.release, new_release_name))
        if os.path.exists(self.path_to_workspace):
            self.run_command_and_collect_errors(copy_cmdb)
        else:
            ColorPrint.err("Can't copy due to invalid path: [{0}] ".format(self.path_to_workspace))

    def show_my_commits(self, show_sha, since_days):
        list_of_repos = self.config.getlist('git_repo','repo');
        for repo in list_of_repos:
            current_repo_path = self.path_to_workspace + os.sep + repo;
            if os.path.exists(current_repo_path):

                if since_days is None:
                    commit_since_days = self.config.getint('git_repo','commit_since_days');
                else:
                    commit_since_days = int(since_days)
                since_date = datetime.now() - timedelta(days=commit_since_days)
                show_commit = ''
                if not show_sha:
                    show_commit = '\|commit ';
                cmd_commits = 'cd ' + current_repo_path + ';git log --author="$(git config user.name)" --since "{0} {1} {2}"|grep -v "Author:\|Date:{3}"'.\
                        format(since_date.strftime("%B"), since_date.day, since_date.year, show_commit)
                commits_output = EnvironmentBuilder.handle_command(cmd_commits, False, True, self.print_cmd_output, self.print_cmd)
                p_status, output, err = commits_output;
                if p_status == 0 and not (output.rstrip('\n').isspace()):
                    output = os.linesep.join(['\t' + s.strip() for s in output.splitlines() if s])
                    ColorPrint.blue_highlight("Commits for repository [{0}]".format(repo.upper()))
                    ColorPrint.info(output)

                unpushed_commits = self.get_unpushed_commits(current_repo_path)
                if unpushed_commits and not unpushed_commits.rstrip('\n').isspace():
                    ColorPrint.err("\tUnpushed commits!!!")
                    ColorPrint.warn(unpushed_commits)

    def get_branch_name(self, repository_path):
        cmd_get_branch = 'cd {0};git rev-parse --abbrev-ref HEAD'.format(repository_path)
        result = self.run_command_and_collect_errors(cmd_get_branch)
        p_status, branch_name, err = result;
        branch_name = branch_name.rstrip('\n')
        if p_status == 0:
            return branch_name
        return None

    def get_unpushed_commits(self, repository_path):
        current_branch = self.get_branch_name(repository_path)
        cmd_commits = 'cd {0};git log origin/{1}..{2}|grep -v "Author:\|Date:"'.format(repository_path, current_branch, current_branch)
        commits_output = EnvironmentBuilder.handle_command(cmd_commits, False, True, False)
        p_status, output, err = commits_output;
        if p_status == 0 and not (output.rstrip('\n').isspace()):
            output = os.linesep.join(['\t' + s.strip() for s in output.splitlines() if s])
            return output
        return None

    def switch_track(self, track_name):

        if not os.path.exists(self.path_to_workspace):
            ColorPrint.err("Invalid release name: [{0}]".format(self.release))
            exit(1)
        now = time.time()
        list_of_repos = self.config.getlist('git_repo','repo');
        if self.parallel_run:
            pool = Pool(len(list_of_repos))
            pool.map(self._switch_repo, zip(list_of_repos, repeat(track_name)))
        else:
            for repo in list_of_repos:
                self._switch_repo([repo, track_name])
        later = time.time()
        difference = int(later - now)
        log_message = "Switch operation for release [{0}] took [{1}] seconds".format(self.release, difference)
        ColorPrint.blue_highlight(log_message)
        self.notif_mgr.send_notification(True, "Switch branch", log_message)

    def _switch_repo(self, args):
        repo, track_name = args
        ColorPrint.blue_highlight("Trying to switch the repository [{0}] to [{1}]".format(repo, track_name))
        if os.path.exists(self.path_to_workspace + os.sep + repo):
            p_status, out, err = self.run_command_and_collect_errors('cd {0};git rev-parse --abbrev-ref HEAD'.format(self.path_to_workspace + os.sep + repo))
            if out == track_name:
                ColorPrint.warn("The current repository [{0}] already switched to [{1}], skipping".format(repo, track_name))
            else:
                self.run_command_and_collect_errors('cd {0};git checkout {1}'.format(self.path_to_workspace + os.sep + repo, track_name))

    def mvn_build(self):
        if not os.path.exists(self.path_to_workspace):
            ColorPrint.err("Invalid release name: [{0}]".format(self.release))
            exit(1)
        project_per_repo = self.config.getsection('projects')
        for repo_name, projects in project_per_repo:
            ColorPrint.blue_highlight("Starting mvn install for repository {0}".format(repo_name))
            for project_name in projects.split(','):
                project_path = self.path_to_workspace + os.sep + repo_name + os.sep + project_name
                java_env = 'source ~/.bash_profile'
                cmd = java_env + ';cd {0};mvn clean install -DskipTests'.format(project_path)
                self.run_command_and_collect_errors(cmd)
        log_message = "Maven build operation for release completed".format(self.release)
        ColorPrint.blue_highlight(log_message)
        self.notif_mgr.send_notification(True, 'Maven Build', log_message)

    def mvn_clean(self):
        if not os.path.exists(self.path_to_workspace):
            ColorPrint.err("Invalid release name: [{0}]".format(self.release))
            exit(1)
        project_per_repo = self.config.getsection('projects')
        for repo_name, projects in project_per_repo:
            ColorPrint.blue_highlight("Starting mvn clean for repository {0}".format(repo_name))
            for project_name in projects.split(','):
                project_path = self.path_to_workspace + os.sep + repo_name + os.sep + project_name
                java_env = 'source ~/.bash_profile'
                cmd = java_env + ';cd {0};mvn clean'.format(project_path)
                self.run_command_and_collect_errors(cmd)
        log_message = "Maven clean operation for release completed".format(self.release)
        ColorPrint.blue_highlight(log_message)
        self.notif_mgr.send_notification(True, 'Maven Clean', log_message)

    def run_git_pull(self):
        if not os.path.exists(self.path_to_workspace):
            ColorPrint.err("Invalid release name: [{0}]".format(self.release))
            exit(1)
        now = time.time()
        list_of_repos = self.config.getlist('git_repo', 'repo');
        if self.parallel_run:
            pool = Pool(len(list_of_repos))
            pool.map(self._git_pull, list_of_repos)
        else:
            for repo in list_of_repos:
                self._git_pull(repo)
        later = time.time()
        difference = int(later - now)
        log_message = "Pull operation for release [{0}] took [{1}] seconds".format(self.release, difference)
        ColorPrint.blue_highlight(log_message)
        self.notif_mgr.send_notification(True, 'git pull', log_message)

    def run_git_custom(self,git_command):
        if not os.path.exists(self.path_to_workspace):
            ColorPrint.err("Invalid release name: [{0}]".format(self.release))
            exit(1)
        now = time.time()
        list_of_repos = self.config.getlist('git_repo', 'repo');
        func = partial(self._git_custom, git_command)
        if self.parallel_run:
            pool = Pool(len(list_of_repos))
            pool.map(func, list_of_repos)
        else:
            for repo in list_of_repos:
                self._git_custom(git_command, repo)
        later = time.time()
        difference = int(later - now)
        log_message = "Git custom operation for release [{0}] took [{1}] seconds".format(self.release, difference)
        ColorPrint.blue_highlight(log_message)
        self.notif_mgr.send_notification(True, git_command, log_message)

    def _git_pull(self, repo):
        ColorPrint.blue_highlight("Pulling the repository [{0}]".format(repo))
        repo_path = self.path_to_workspace + os.sep + repo
        is_git_pull_ran = False
        if os.path.exists(repo_path):
            current_branch = self.get_branch_name(repo_path)
            if self._is_branch_up_to_date(repo_path):
                if repo in self.repo_status and self.repo_status[repo]:
                    ColorPrint.blue_highlight('Your repository [{0}] is up-to-date, skipping [git pull]'.format(repo))
                else:
                    p_status, output, error = self.run_command_and_collect_errors('cd {0};git pull origin {1}'.format(repo_path, current_branch))
                    is_git_pull_ran = True
            else:
                self.run_git_stash(repo_path)
                if self._is_ready_to_pull(repo_path):
                    if repo in self.repo_status and self.repo_status[repo]:
                        ColorPrint.blue_highlight('Your repository [{0}] is up-to-date, skipping [git pull]'.format(repo))
                    else:
                        p_status, output, error = self.run_command_and_collect_errors('cd {0};git pull origin {1}'.format(repo_path, current_branch))
                        is_git_pull_ran = True
                self.run_git_unstash(repo_path)
        else:
            ColorPrint.warn( "The repository path [{0}] is not available".format(repo))

        if is_git_pull_ran and p_status == 0:
            if 'up to date' in output or 'Successfully rebased and updated' or 'Fast-forward' in output:
                ColorPrint.blue_highlight("Pull for repository {0} finished successfully".format(repo))
            else:
                current_error = "Your repository {0} is broken, try to run 'git gc --prune=now' and 'git remote prune origin' to fix it".format(repo)
                ColorPrint.err(current_error)
                filename = 'errors.txt'
                if os.path.exists(filename):
                    append_write = 'a'  # append if already exists
                else:
                    append_write = 'w'  # make a new file if not
                error_file = open(filename, append_write)
                error_file.write(current_error + '\n')
                error_file.close()

    def _git_custom(self, git_command, repo):
        ColorPrint.blue_highlight("Running custom git command on repository [{0}]".format(repo))
        repo_path = self.path_to_workspace + os.sep + repo
        if os.path.exists(repo_path):
            self.run_command_and_collect_errors('cd {0};git {1}'.format(repo_path, git_command ))
        else:
            ColorPrint.warn( "The repository path [{0}] is not available".format(repo))

    def run_git_stash(self, repo_path):
        if os.path.exists(repo_path):
            ColorPrint.blue_highlight( "Stashing the repository [{0}]".format(repo_path))
            self.run_command_and_collect_errors('cd {0};git stash'.format(repo_path))
        else:
            ColorPrint.warn( "The repository path [{0}] is not available".format(repo_path))

    def run_git_unstash(self, repo_path):
        if os.path.exists(repo_path):
            ColorPrint.blue_highlight("Unstashing the repository [{0}]".format(repo_path))
            self.run_command_and_collect_errors('cd {0};git stash pop'.format(repo_path))
        else:
            ColorPrint.warn("The repository path [{0}] is not available".format(repo_path))

    def _is_ready_to_pull(self, repo_path):
        ColorPrint.blue_highlight("Checking repository status [{0}]".format(repo_path))
        p_status, cmd_out, err = self.run_command_and_collect_errors('cd {0};git status -uno'.format(repo_path))
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
        self.run_command_and_collect_errors('cd {0};git remote update'.format(repo_path))
        if self._is_ready_to_pull(repo_path):
            return True
        else:
            repo = os.path.basename(os.path.normpath(repo_path))
            if repo in self.repo_status and self.repo_status[repo]:
                return True
            else:
                return False

    @staticmethod
    def print_list_avalable_versions(current_release):
        base_dir = SncConfig().getstring('git_repo', 'base_dir');

        if current_release is not None:
            ColorPrint.blue_highlight('================' + current_release.upper() + '================')
            EnvironmentBuilder.print_release_branch_per_repository(current_release)
            exit(0)
        for dir in os.listdir(base_dir):
            if os.path.isdir(base_dir + os.sep + dir) and not dir.startswith('.'):
                if EnvironmentBuilder.is_release_direcrory(dir):
                    ColorPrint.blue_highlight('================' + dir.upper() + '================')
                    EnvironmentBuilder.print_release_branch_per_repository(dir)

    @staticmethod
    def print_release_branch_per_repository(current_release):
        """git remote prune origin"""

        base_dir = SncConfig().getstring('git_repo','base_dir');
        list_of_repos = SncConfig().getlist('git_repo', 'repo');
        list_of_messages = {}
        brunches_d = {}
        for repository in list_of_repos:
            path_to_repository = base_dir + os.sep + current_release + os.sep + repository
            if os.path.exists(path_to_repository + os.sep + '.git'):
                cmd_get_branch = 'cd {0};git rev-parse --abbrev-ref HEAD'.format(path_to_repository)
                status, current_brunch, error = EnvironmentBuilder.handle_command(cmd_get_branch, True, True, False)
                current_brunch = current_brunch.rstrip();
                current_message = "Release: [{0}] Repository: [{1}], Branch: [{2}]".rstrip().format(current_release, repository, current_brunch)
                list_of_messages[current_message] = current_brunch
                if current_brunch in brunches_d:
                    brunches_d[current_brunch] += 1
                else:
                    brunches_d[current_brunch] = 0
        if brunches_d.values():
            max_brunch = max(brunches_d.values())
            for message, branch in list_of_messages.iteritems():
                if brunches_d[branch] < max_brunch:
                    ColorPrint.err(message)
                else:
                    ColorPrint.info(message)

    @staticmethod
    def is_release_direcrory(release_dir):
        base_dir = SncConfig().getstring('git_repo','base_dir');
        full_path = base_dir + os.sep + release_dir
        list_of_dirs = os.listdir(full_path)
        list_of_repos = SncConfig().getlist('git_repo','repo');
        return not set(list_of_repos).isdisjoint(list_of_dirs)

    def print_execution_error_summary(self):
        if not os.path.exists("errors.txt"):
            exit(0)
        with open('errors.txt', 'r') as error_file:
            all_errors=error_file.read()

        if all_errors:
            ColorPrint.blue_highlight("Fix the following errors and run again")
            ColorPrint.err('\n' + all_errors)
        else:
            ColorPrint.blue_highlight("Execution complited without errors")

    @staticmethod
    def handle_command(cmd, check_rc=True, get_output=True, print_output=False, print_cmd=False, background=False):
        """
         Executes command
        :param cmd: command string to be executed
        :return: rc, stdout, stderr
        """

        stdout_flag = None
        if get_output:
            stdout_flag = subprocess.PIPE
        if print_cmd:
            ColorPrint.info("[handle_command] running {0}".format(cmd))
        p = subprocess.Popen(cmd,
                              stdout=stdout_flag,
                              stderr=subprocess.STDOUT,
                              shell=True)

        out, err = p.communicate()
        p_status = p.wait()
        if check_rc:
            if p_status != 0:
                ColorPrint.err("[handle_command] failed executing: {0}".format(cmd))
                ColorPrint.err(str(err) + ' ' + str(out))
            else:
                if print_output:
                    ColorPrint.info("[handle_command] Command output: {0} ".format(str(out)))

        abort_on_error = SncConfig().getboolean('envbuilder', 'abort_on_error')
        if abort_on_error and p_status != 0:
            ColorPrint.err("EnvironmentBuilder: Execution aborted due to error[s]")
            exit(1)

        return p_status, out, err


if __name__ == '__main__':
    #Font Name: Big
    #http://patorjk.com/software/taag

    ColorPrint.blue_highlight("""
#  ______            ____        _ _     _             __ _  _   
# |  ____|          |  _ \      (_) |   | |           /_ | || |  
# | |__   _ ____   _| |_) |_   _ _| | __| | ___ _ __   | | || |_ 
# |  __| | '_ \ \ / /  _ <| | | | | |/ _` |/ _ \ '__|  | |__   _|
# | |____| | | \ V /| |_) | |_| | | | (_| |  __/ |     | |_ | |  
# |______|_| |_|\_/ |____/ \__,_|_|_|\__,_|\___|_|     |_(_)|_| 
#""");

    parser = argparse.ArgumentParser(prog='envbuilder.py',
                                     description='Build environment tool',
                                     formatter_class=RawTextHelpFormatter)
    parser.add_argument('-clone', help='Clone defined repositories in the conf file to the specifed release directory', action="store_true")
    parser.add_argument('-pull', help='run git pull for all or specified repositories \n ./envbuilder.py -pull -r release',action="store_true")
    parser.add_argument('-sw', help='switch all repositories to relevant track \n /envbuilder.py -sw -t trackname -r release', action="store_true")
    parser.add_argument('-t', help='track to switch', nargs='?',dest="track")
    parser.add_argument('-r', help='release name', nargs='?', dest="release")
    parser.add_argument('-copy', help='Copy local release to the new one. Useful for Intellij developers', action="store_true")
    parser.add_argument('-nr', help='new release name', nargs='?', dest="new_release")

    parser.add_argument('-commits', help='Show my release commits', action="store_true")
    parser.add_argument('-sha', help='SHA key as part of commit message', action="store_true")
    parser.add_argument('-days', help='Commit since days ago', nargs='?',dest="since_days")
    parser.add_argument('-status', help='Status of the current local branches', action="store_true")
    parser.add_argument('-mvn', help='Run maven install -DskipTests for the specified release', action="store_true")
    parser.add_argument('-mvn_clean', help='Run maven clean for the specified release', action="store_true")
    parser.add_argument('-git', help='Run custom git command', nargs='?',dest="git_command")

    config = SncConfig()
    default_release = config.getstring('envbuilder', 'release')

    pl = PluginsLoader(os.environ[ENVB_PATH] + os.sep + "plugins")
    plugins = pl.load_plugins()
    for flag in plugins:
        plugin = plugins[flag]
        if plugin['active'] is True:
            parser.add_argument('-{0}'.format(plugin['flag']),
                                help='{0}'.format(plugin['description']), action="store_true")

    args = parser.parse_args()

    # print str(args)
    if not args.release:
        ColorPrint.info("The -r [release] option is not provided, using default [{0}] from envbuilder.conf".format(default_release))
        if not default_release:
            ColorPrint.err('\n' + "The [release] parameter is not defined under [enbuilder] section in enbuilder.conf")
        args.release = default_release

    if args.status and args.release:
        EnvironmentBuilder.print_list_avalable_versions(args.release)
        exit(0)

    if args.status:
        EnvironmentBuilder.print_list_avalable_versions(None)
        exit(0)

    if args.mvn and args.release:
        builder = EnvironmentBuilder(args.release)
        builder.mvn_build()
        builder.print_execution_error_summary()
        exit(0)

    if args.mvn_clean and args.release:
        builder = EnvironmentBuilder(args.release)
        builder.mvn_clean()
        builder.print_execution_error_summary()
        exit(0)

    if args.commits and args.release:
        builder = EnvironmentBuilder(args.release)
        builder.show_my_commits(args.sha, args.since_days)
        exit(0)

    if args.copy and args.release and args.new_release:
        builder = EnvironmentBuilder(args.release)
        builder.copy_local_env(args.new_release)
        builder.print_execution_error_summary()
        exit(0)

    if args.sw and args.release and args.track:
        builder = EnvironmentBuilder(args.release)
        builder.switch_track(args.track)
        builder.print_execution_error_summary()
        exit(0)

    if args.pull and args.release:
        builder = EnvironmentBuilder(args.release)
        builder.run_git_pull()
        builder.print_execution_error_summary()
        exit(0)

    if args.git_command and args.release:
        builder = EnvironmentBuilder(args.release)
        builder.run_git_custom(args.git_command)
        builder.print_execution_error_summary()
        exit(0)

    if args.clone and args.release:
        builder = EnvironmentBuilder(args.release)
        builder.clone_env()
        if args.track:
            builder.switch_track(args.track)

        builder.print_execution_error_summary()
        exit(0)

    for option in plugins:
        try:
            current_arg = getattr(args, option)
            if current_arg is True:
                plugin = plugins[option]
                builder = EnvironmentBuilder(args.release)
                commands_to_run = plugin['commands']

                if plugin['type'] == 'group':
                    plugins_to_run = plugin['plugins']
                    for run_plugin_flag in plugins_to_run:
                        run_plugin = plugins[run_plugin_flag]
                        commands_to_run.extend(run_plugin['commands'])
                is_background = False
                if plugin['background'] is True:
                    is_background = True
                    last_command = commands_to_run.pop()
                final_status, final_output, final_error = builder.run_commands_in_current_release(commands_to_run)
                if is_background:
                    builder.run_command_in_background(last_command)
                if final_output is None:
                    final_output = ''

                if final_error is None:
                    final_error = ''

                if plugin['notify'] is True:
                    notifier = NotificationManager(None, None, None)
                    if final_status is True:
                        command_status = 'completed successfully'
                        final_result = final_output
                    else:
                        command_status = 'execution failed'
                        final_result = final_output + final_error
                    notif_msg = "Command: [{0}] Status: {1} Result: {2}".format(plugin['description'],
                                                                                command_status, final_result)
                    notifier.send_notification(final_status,plugin['name'], notif_msg)
                exit(0)
        except AttributeError:
            continue

    else:
        parser.print_help()

