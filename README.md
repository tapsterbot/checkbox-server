# Checkbox Server
Server software to run on Tapster Checkbox hardware


## Raspberry Pi Imager 
  ✅ Set hostname to checkbox.local

  ✅ Enable SSH
    
    🔘 Use password authentication

  ✅ Set username and password

    Username: tapster
    Password: xxxxxxx

  ✅ Configure wireless LAN

    SSID: xxxxx
    Password: xxxxx
    Wireless LAN country: US

  ✅ Set locale settings

    Time zone: America/Chicago
    Keyboard layout: us


## Initial Set Up
    sudo apt update
    sudo apt upgrade -y
    sudo apt install -y vim git python3-pip
    sudo apt install --upgrade python3-setuptools
    sudo apt install -y python3.11-venv


## Update raspi-config
    sudo raspi-config

    Select 8 Update    

## Change raspi-config settings
    # VNC
    # https://help.realvnc.com/hc/en-us/articles/14110635000221-Raspberry-Pi-5-Bookworm-and-RealVNC-Connect
    
    sudo raspi-config
    
    # Enable X11
    Select 6 Advanced Options -> A6 Wayland -> W1 X11
    
    # Enable VNC
    Select 3 Interface Options -> I2 VNC

## Install libcamera libraries

    # https://forums.raspberrypi.com/viewtopic.php?p=2148281&sid=b3617e05ef4d7cb5e371c17d13bf2e7d#p2148281
    sudo apt install libcamera-v4l2
    sudo apt install libcamera-tools

## Python environment set-up
    cd
    mkdir Projects
    cd Projects
    mkdir checkbox
    cd checkbox
    python -m venv env --system-site-packages
    source env/bin/activate

## Install OpenCV
    pip3 install opencv-contrib-python
    
## Checkout zero-hid
    cd ~/Projects
    git clone https://github.com/tapsterbot/zero-hid.git
    cd zero-hid
    git checkout dev

## Install usb_gadget
    cd usb_gadget
    chmod +x installer.bash && sudo ./installer.bash

    (Will prompt for another reboot, select Y)

## Renable the virtual env
    cd ~/Projects/checkbox
    source env/bin/activate

## Install zero-hid python library
    cd ~/Projects
    pip3 install ./zero-hid/


## Edit config.txt
    sudo vim /boot/config.txt 

### Add following to end of file /boot/config.txt 
    dtoverlay=tc358743
    dtoverlay=tc358743-audio

## Edit cmdline.txt
    sudo vim /boot/cmdline.txt 

### Add following to end of first line (Do NOT add any carriage returns)
    cma=96M

## Reboot. 
    (Again sorry)

## Check for video0 device    
If all is well you should see a video device at /dev/video0

"v4l2-ctl --list-devices" will tell you that it is provided by Unicam.

    $ v4l2-ctl --list-devices
    unicam (platform:fe801000.csi):
    	/dev/video0
    	/dev/media3
    
## Install Checkbox Server 
    cd ~/Projects/checkbox
    git clone https://github.com/tapsterbot/checkbox-server.git

## Run video setup
    cd ~/Projects/checkbox/checkbox-server/video-driver
    chmod u+x set-up-video.sh
    ./set-up-video.sh

## Optional: Install uStreamer pre-reqs
    sudo apt install libevent-dev libbsd-dev libjpeg62-turbo-dev

## Optional: Install uStreamer
    cd ~/Projects
    git clone --depth=1 https://github.com/tapsterbot/ustreamer.git
    cd ustreamer/
    make

## Optional: Run uStreamer
Note: You have to run the `set-up-video.sh` listed above after every reboot of the system and every time you (re)plug in a phone.
   
    ./ustreamer --device=/dev/video0 --host=0.0.0.0

    ### or
    
    ./ustreamer --device=/dev/video0 --host=0.0.0.0 --resolution=1920x1080 --format=UYVY

## Optional: Open a browser and view the stream
    http://checkboxmini:8080/

    If that works, then let's startup the Checkbox Server (finally!)

    Now stop the uStreamer app...

## Run Checkbox Server
Note: You have to run the `set-up-video.sh` listed above after every reboot of the system and **every** time you (re)plug in a phone.
    
    cd ~/Projects/checkbox/
    source env/bin/activate
    cd ~/Projects/checkbox/checkbox-server/video-driver/
    ./set-up-video.sh
    cd ..
    python server.py
