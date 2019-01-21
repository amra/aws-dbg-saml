Key Generator for AWS CLI Access

Language: Python 2.7

Description:

* Script generates assumedRole.pkl storing AWS credentials. It's used for comparing timestamps and generating AWS credentials file.

* Credentials file is stored in User profile ~/.aws directory.

* If Credentials are going to expire in <5 minutes, user needs to provide UID/Token/Password again

# User configuration
You can configure a default user. You need to create a file `~/.aws/user` containing just the username.

Example of `~/.aws/user` for username `ab123`

```
ab123
```

# Environmant names
It is difficult sometimes to differentiate enviroments from each other while running this script. User can preconfigure his enviromet description so the script will append additional text to each line.

## Example
Original login dialog
```
Username: gi997
MFA token: 877303
Password: 
Please choose the role you would like to assume:
[0]: 147789435585 - role/EnergyDevelopment
[1]: 723232346150 - role/EnergyDevelopment
[2]: 322652345670 - role/PowerUser
[3]: 367821342543 - role/SharedComponentDevelopment
Selection: 
...
```

New login dialog
```
Username: gi997
MFA token: 877303
Password: 
Please choose the role you would like to assume:
[0]: 147789435585 - role/EnergyDevelopment - acceptance
[1]: 723232346150 - role/EnergyDevelopment - sandbox
[2]: 322652345670 - role/PowerUser - production
[3]: 367821342543 - role/SharedComponentDevelopment - simulation
Selection: 
...
```


## Configuration
Create a json file `~/.aws/env.json` with content in key:value form `environment number : name`

Example configuration
```
{
    "723232346150": "sandbox",
    "147789435585": "acceptance",
    "367821342543": "simulation",
    "322652345670": "production"
}
```
