#!/bin/bash
nohup python auth.py > auth.log 2>&1 &
#!/bin/bash
nohup python auth_upload.py > auth.log 2>&1 &