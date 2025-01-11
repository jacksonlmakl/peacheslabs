#!/bin/bash
nohup python auth.py > auth.log 2>&1 &
nohup python auth_upload.py > auth.log 2>&1 &
nohup python auth_app.py > app.log 2>&1 &