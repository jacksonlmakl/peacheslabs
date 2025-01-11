#!/bin/bash
nohup python auth.py > auth.log 2>&1 &
nohup sqlite_web core.db > db.log 2>&1 &