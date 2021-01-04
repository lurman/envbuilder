
# envbuilder
Environment builder  - All Tools/Scripts in One.
 1. Create from scratch multi git repository development environment
 2. A tool to work with Git in parallel mode
 3. Troubleshoot your environment
 4. Add your script to EnvBuilder by creating your own plugin in one simple step
<pre>
#  ______            ____        _ _     _             __ _  _   
# |  ____|          |  _ \      (_) |   | |           /_ | || |  
# | |__   _ ____   _| |_) |_   _ _| | __| | ___ _ __   | | || |_ 
# |  __| | '_ \ \ / /  _ <| | | | | |/ _` |/ _ \ '__|  | |__   _|
# | |____| | | \ V /| |_) | |_| | | | (_| |  __/ |     | |_ | |  
# |______|_| |_|\_/ |____/ \__,_|_|_|\__,_|\___|_|     |_(_)|_| 
# 
 Init: PluginsLoader 
 Loading plugin Clotho installation 
 Loading plugin Get MID Head dump 
 Loading plugin Run Clotho DB 
 Loading plugin Agent Simulator 
 Loading plugin Get MID Thread dump 
 The -r [release] option is not provided, using default [paris] from envbuilder.conf 

usage: envbuilder.py [-h] [-clone] [-pull] [-sw] [-t [TRACK]] [-r [RELEASE]]
                     [-copy] [-nr [NEW_RELEASE]] [-commits] [-sha]
                     [-days [SINCE_DAYS]] [-status] [-mvn] [-mid]
                     [-port [PORT]] [-zboot] [-glide] [-git [GIT_COMMAND]]
                     [-pull_request] [-p [PROJECT]] [-rm_dimentions]
                     [-mid_thread] [-mid_heap] [-acc_sim] [-run_clotho]
                     [-inst_clotho]

Build environment tool

optional arguments:
  -h, --help          show this help message and exit
  -clone              Clone defined repositories in the conf file to the specified release directory
  -pull               run git pull for all or specified repositories 
                       ./envbuilder.py -pull -r release
  -sw                 switch all repositories to relevant track 
                       /envbuilder.py -sw -t trackname|branch -r release
  -t [TRACK|BRANCH]          track to switch
  -r [RELEASE]        release name
  -copy               Copy local release to the new one. Useful for Intellij developers
  -nr [NEW_RELEASE]   new release name
  -commits            Show my release commits
  -sha                SHA key as part of commit message
  -days [SINCE_DAYS]  Commit since days ago
  -status             Status of the current local branches
  -mvn                Run maven install -DskipTests for the specified release
                       /envbuilder.py -mid -port number -r release
  -port [PORT]        Specify port number to change the default
  -glide              Configuring glide
  -git [GIT_COMMAND]  Run custom git command
  -pull_request       Commits, push and prepare pull request. 
                       /envbuilder.py -pull_request -r release -p project
  -p [PROJECT]        project name

If you are getting error due to missing pip use the following instructions to fix it.

1. curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
2. python ./get-pip.py
3. pip install requests
</pre>
