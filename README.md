# uArm Swift Pro Test

Trying out the uArm Swift Pro

## Installation

Download and install this repo
```
git clone https://github.com/andySigler/uarm-test.git
cd uarm-test
```

Setup a Python virtual environment, if you want.

Also, the `uArm-Python-SDK` recommends using Python >=3.5.x

Install the `uArm-Python-SDK`:
```
git submodule update --init --recursive
cd uArm-Python-SDK
python setup.py install
cd ..
```

## Run the Test

Make sure the uArm Swift Pro device is powered on and connected to your computer. Also, that no other software is connected to its serial port.

```
python test.py
```
