import serial
import time
from sys import exit

###################################################################################################
####                                           Config                                          ####
###################################################################################################

# The serial ports that the two radios are attached to
PORT_A = '/dev/ttyUSB0'
PORT_A_BAUD = 9600
PORT_B = '/dev/ttyUSB1'
PORT_B_BAUD = 9600

# Set to True if you would like each radio's destination address to be the other's serial number
SET_DESTINATIONS = True

# Include any other parameters you would like to set on both radios in this dictionary
COMMON_CONFIG = {
    'CH': '12',
    'MM': '1'
}

###################################################################################################

RADIO_OK = [b'O', b'K']

def readResponse(serialPort):
    response = []
    while len(response) == 0 or response[-1] != b'\r':
        response.append(serialPort.read())
    return response[:-1]

def runCommand(command, serialPort, delay = 1):
    if type(command) is str:
        command = command.encode()
    serialPort.write(command)
    time.sleep(delay)
    return readResponse(serialPort)

def setValue(serialPort, field, value):
    if type(value) is list:
        value = b''.join(value)
    command = b'AT' + field.encode() + b' ' + value + b'\r'
    fieldSet = runCommand(command, serialPort) == RADIO_OK
    fieldConfirmed = b''.join(runCommand(b'AT' + field.encode() + b'\r', serialPort)) == value
    return fieldSet and fieldConfirmed

def checkReady(serialPort, name):
    radioReady = runCommand('+++', serialPort)
    if radioReady != RADIO_OK:
        print('Radio {} did not respond OK! ({})'.format(name, radioReady))
        return False
    print('Radio {} ready!'.format(name))
    return True

def getSerialNumber(serialPort, name):
    print('Getting serial number from {}'.format(name))
    serialHigh = runCommand('ATSH\r', serialPort)
    serialLow = runCommand('ATSL\r', serialPort)
    serialString = ''.join([b.decode('ascii') for b in serialHigh + serialLow])
    print('Serial Number {}: {}'.format(name, serialString))
    return serialHigh, serialLow

def setDestinationAddress(serialPort, destinationHigh, destinationLow, name):
    print('Setting destination address on {}'.format(name))
    highSet = setValue(serialPort, 'DH', destinationHigh)
    lowSet = setValue(serialPort, 'DL', destinationLow)
    if not highSet or not lowSet:
        print('Failed to set address on {}'.format(name))
        return False
    print('Address set on {}'.format(name))
    return True

def writeAndExit(serialPort, name):
    print('Saving configuration on {}'.format(name))
    saveResponse = runCommand(b'ATWR\r', serialPort)
    if saveResponse == RADIO_OK:
        print('Written to {}'.format(name))
    else:
        print('Got {} when trying to save to {}'.format(saveResponse, name))
    exitResponse = runCommand(b'ATCN\r', serialPort)
    if exitResponse == RADIO_OK:
        print('Exited command mode on {}'.format(name))
    else:
        print('Got {} when trying to save to {}'.format(exitResponse, name))

with serial.Serial(PORT_A, PORT_A_BAUD) as serialPortA, serial.Serial(PORT_B, PORT_B_BAUD) as serialPortB:
    if not checkReady(serialPortA, 'A') or not checkReady(serialPortB, 'B'):
        exit()

    if SET_DESTINATIONS:
        print('\nSetting destination addresses')
        radioASerialHigh, radioASerialLow = getSerialNumber(serialPortA, 'A')
        radioBSerialHigh, radioBSerialLow = getSerialNumber(serialPortB, 'B')

        if not setDestinationAddress(serialPortA, radioBSerialHigh, radioBSerialLow, 'A'):
            exit()
        if not setDestinationAddress(serialPortB, radioASerialHigh, radioASerialLow, 'B'):
            exit()
        print('Done setting destination addresses')

    for field, value in COMMON_CONFIG.items():
        print('\nSetting {} to {}'.format(field, value))
        encoded = value.encode()
        if not setValue(serialPortA, field, encoded):
            print('Failed to set value on A')
            exit()
        print('Set value for A')
        if not setValue(serialPortB, field, encoded):
            print('Failed to set value on B')
            exit()
        print('Set value for B')

    print()
    writeAndExit(serialPortA, 'A')
    writeAndExit(serialPortB, 'B')

    print('\nDone')
