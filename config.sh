#!/bin/bash

# 1. 创建主目录结构
mkdir -p ./back/tcms
mkdir -p ./back/apps
mkdir -p ./back/static
mkdir -p ./back/media
mkdir -p ./back/templates

# 2. 创建必要的配置文件目录
mkdir -p ./back/tcms/settings

# 3. 创建apps下的应用目录（根据您现有的应用）
mkdir -p ./back/apps/users
mkdir -p ./back/apps/projects
mkdir -p ./back/apps/testcases
mkdir -p ./back/apps/executions
mkdir -p ./back/apps/reports
mkdir -p ./back/apps/crowd_testing

# 4. 创建必要的__init__.py文件
touch ./back/tcms/__init__.py
touch ./back/tcms/settings/__init__.py
touch ./back/apps/__init__.py
touch ./back/apps/users/__init__.py
touch ./back/apps/projects/__init__.py
touch ./back/apps/testcases/__init__.py
touch ./back/apps/executions/__init__.py
touch ./back/apps/reports/__init__.py
touch ./back/apps/crowd_testing/__init__.py