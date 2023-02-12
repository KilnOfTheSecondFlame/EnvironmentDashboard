# Environment Dashboard
Small project hosting the code for RaspberryPi EnvironmentDashboard and BME680 Sensor 

Very amateurish, sorry for that!

## Update Default Python
```terminal
# update-alternatives --install /usr/bin/python python /usr/bin/python2.7 1
update-alternatives: using /usr/bin/python2.7 to provide /usr/bin/python (python) in auto mode
# update-alternatives --install /usr/bin/python python /usr/bin/python3.2 2
update-alternatives: using /usr/bin/python3.2 to provide /usr/bin/python (python) in auto mode
```

## Satisfy requirements
```terminal
sudo pip install -r requirements.txt
```

## BME680
Activate I2C in Raspberrry Pi and reboot
```terminal
curl https://get.pimoroni.com/bme680 | bash
```

## Desktop File
```text
[Desktop Entry]
Version=1.0
Type=Link
Encoding=UTF-8
Name=EnvironmentDashboard
URL=http://localhost:8055
Icon=text-html
```

## gunicorn
```terminal
sudo apt install gunicorn3
gunicorn3 app:server -b :8050
```

## Service Installation
Place the service in ```/etc/systemd/system/```
```terminal
sudo apt install gunicorn3
```
