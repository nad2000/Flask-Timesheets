# Flexible Lightweight Time-Tracking Application

## Screen shots

### Timesheet Filling and Submission
![ScreenShot](/Screenshots/s1.png?raw=true "Filling-in Timesheets")

### Update Account
![ScreenShot](/Screenshots/user_profile.png?raw=true "Update Account")

## Admin and Approver Functions

### Manage Accounts
![ScreenShot](/Screenshots/s4.png?raw=true "Manage Accounts")
![ScreenShot](/Screenshots/s5.png?raw=true "Manage Accounts")

### Timesheet Approving
![ScreenShot](/Screenshots/s2.png?raw=true "Timesheet Approving")

### Reporting and Export to MS Excel
![ScreenShot](/Screenshots/s3.png?raw=true "Reporting and Export to MS Excel")

## Installation

```
# Create a virtualenv:
virtualenv -ppython3.6 venv
# Activate it:
. venv/bin/activate
# Install the app and development dependencies:
pip insall -e '.[dev]'
# Tell the Flask which module to use:
export FLASK_APP=time_sheets
# Init DB:
flask initdb
# Add some test data:
flask crtestdata
# Run the app:
flask run

# Try to login with 'admin0' (password: '12345')
```

