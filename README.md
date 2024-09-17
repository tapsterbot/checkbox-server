# Checkbox Server
Server software to run on Tapster Checkbox hardware


**Note:** Most of the set-up can be done by an automated script:
https://valetnet.dev/config-os/
    
## Install Checkbox Server 
    cd ~/Projects/checkbox
    source env/bin/activate    
    git clone https://github.com/tapsterbot/checkbox-server.git
    cd checkbox-server
    pip install -r requirements.txt

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
