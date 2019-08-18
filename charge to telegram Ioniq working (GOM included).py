import logging
import requests
import pickle
import os
from enum import Enum

log = logging.getLogger(__name__)

# Telegram tokens - see https://www.mariansauter.de/2018/01/send-telegram-notifications-to-your-mobile-from-python-opensesame/
#
BOT_TOKEN = '8888888888888888xxxxxxxxxxxxx88888888888'
BOT_CHATID = '88888888888'



def checkChargeStatus():

    # load previous status
    #
    persistance = load()

    # check if we are driving or charging
    #
    charging = get_charging()
    if charging == 0 or charging == -1:
        if persistance['charging'] == True:
            bot_sendtext("Charging stopped. Last known State of charge "+format(persistance['SOC'],'.1f')+"% (BMS)")
            #bot_sendtext("Charging stopped. Last known State of charge "+format(persistance['SOC'],'.1f')+"% BMS - "+format(soc_display,'.1f')+ "% Display")
            persistance['charging'] = False
            save(persistance)
        return {"msg": "Not charging"} # Does nothing ?


    chargingPower = get_charging_power()
    soc = get_soc()
    soc_display = get_soc_display()
    temp = get_temp()
    air_temp = get_air_temp()

    # if batt temp is more or equal to 25 then set to 25
    #
    #if temp >= 25:
        #temp = 25

    # alert if just started to charge
    #
    if persistance['charging'] == False:
        bot_sendtext("Charging started at a rate of "+format(2*chargingPower,'.2f')+"kW. SOC BMS = "+format(soc,'.1f')+"%, SOC Display = "+format(soc_display,'.1f')+ "%, GOM "+format(0.01*soc_display*2800/(16.08813 + (air_temp*(-0.13873))),'.0f')+"km, batt. temp. = "+format(temp,'.0f')+" Degrees, air temp. = "+format(air_temp,'.0f')+" Degrees")


    # Alerts at 40, 50, 60, 70, 80, 90 and 94% SOC BMS
    #
    if (soc >= 40 and persistance['SOC'] < 40) or (soc >= 50 and persistance['SOC'] < 50) or (soc >= 60 and persistance['SOC'] < 60) or (soc >= 70 and persistance['SOC'] < 70) or (soc >= 80 and persistance['SOC'] < 80) or (soc >= 90 and persistance['SOC'] < 90) or (soc >= 94 and persistance['SOC'] < 94):
        bot_sendtext("Charging at a rate of "+format(2*chargingPower,'.2f')+"kW. SOC BMS = "+format(soc,'.1f')+"%, SOC Display = "+format(soc_display,'.1f')+ "%, GOM "+format(0.01*soc_display*2800/(16.08813 + (air_temp*(-0.13873))),'.0f')+"km, batt. temp. = "+format(temp,'.0f')+" Degrees, air temp. = "+format(air_temp,'.0f')+" Degrees")

    # store status for next time
    #
    persistance['charging'] = True
    persistance['SOC'] = soc
    save(persistance)

    #return {"msg": "Charging at "+format(chargingPower,'.2f')+"kW, SOC now "+format(soc,'.1f')+"% "+format(temp,'.1f')+" temp"}
    #return {"msg": "Charging at "+format(chargingPower,'.2f')+"kW, SOC (BMS) now "+format(soc,'.1f')+"% GOM now "+format(0.01*soc_display*2800/(16.08813 + (temp*(-0.13873))),'.0f')+"km and batt. temp. is "+format(temp,'.0f')+" Degrees Centigrade"}
    #return {"msg": "Charging at "+format(chargingPower,'.2f')+"kW, SOC (BMS) = "+format(soc,'.1f')+"% GOM = "+format(0.01*soc_display*2800/(16.08813 + (air_temp*(-0.13873))),'.0f')+" km,  batt. temp.="+format(temp,'.0f')+" Degrees, air temp. = "+format(air_temp,'.0f')+" Degrees"}
    return {"msg": "Charging at a rate of "+format(2*chargingPower,'.2f')+"kW. SOC BMS = "+format(soc,'.1f')+"%, SOC Display = "+format(soc_display,'.1f')+ "%, GOM "+format(0.01*soc_display*2800/(16.08813 + (air_temp*(-0.13873))),'.0f')+"km, batt. temp. = "+format(temp,'.0f')+" Degrees, air temp. = "+format(air_temp,'.0f')+" Degrees"}


# send message to telegram
#
def bot_sendtext(message):
    send_text = 'https://api.telegram.org/bot' + BOT_TOKEN + '/sendMessage?chat_id=' + BOT_CHATID + '&parse_mode=Markdown&text=' + message
    requests.get(send_text)

# load persistance
#
def load():
    try:
        persistance = pickle.load( open( 'charge_status.p', 'rb' ) )
    except:
        persistance = { 'charging': False, 'SOC': 0 }

    return persistance

# save persistance
#
def save(persistance):
    pickle.dump( persistance, open( "charge_status.p", "wb" ) )

# delete persistance
#
def delete():
    os.remove("charge_status.p")



# OBD Queries -----------------------------------------------------------------------------

# get Battery Temprature
#
def get_temp():
    args = ['temp']
    kwargs = {
        'mode': '21',
        'pid': '01',
        'header': '7E4',
        'baudrate': 500000,
        'formula': 'twos_comp(bytes_to_int(message.data[17:18]),8)',
        'protocol': '6',
        'verify': False,
        'force': True,
        }
    return __salt__['obd.query'](*args, **kwargs)['value']

# get Air Temperature, used to calcualte GOM range
#
def get_air_temp():
    args = ['air_temp']
    kwargs = {
        'mode': '21',
        'pid': '80',
        'header': '7E6',
        'baudrate': 500000,
        #'formula': '(twos_comp(bytes_to_int(message.data[15:16]), 8)-80)/2',
        'formula': '(bytes_to_int(message.data[14:15])-80)/2',
        'protocol': '6',
        'verify': False,
        'force': True,
        }
    return __salt__['obd.query'](*args, **kwargs)['value']

def get_charging_power():
        args = ['charging_power']
        kwargs = {
        'mode': '21',
        'pid': '01',
        'header': '7E4',
        'baudrate': 500000,
        #'formula': '(twos_comp(bytes_to_int(message.data[13:14])*256+bytes_to_int(message.data[14:15]),16)/10.0)*((bytes_to_int(message.data[15:16])+bytes_to_int(message.data[16:17]))/10.0)/1000.0',
        'formula': '(twos_comp(bytes_to_int(message.data[12:13])*256+bytes_to_int(message.data[13:14]),16)/10.0)*((bytes_to_int(message.data[14:15])+bytes_to_int(message.data[15:16]))/10.0)/100.0',
        'protocol': '6',
        'verify': False,
        'force': True,
        }
        return __salt__['obd.query'](*args, **kwargs)['value']*-1.0

# get BMS state of charge
#
def get_soc():
    args = ['soc']
    kwargs = {
        'mode': '21',
        'pid': '01',
        'header': '7E4',
        'baudrate': 500000,
        'formula': 'bytes_to_int(message.data[6:7])',
        'protocol': '6',
        'verify': False,
        'force': True,
        }
    return __salt__['obd.query'](*args, **kwargs)['value']/2.0

# get display state of charge
#
def get_soc_display():
    try:
        args = ['soc']
        kwargs = {
            'mode': '21',
            'pid': '05',
            'header': '7E4',
            'baudrate': 500000,
            'formula': 'bytes_to_int(message.data[33:34])',
            'protocol': '6',
            'verify': False,
            'force': True,
            }
        return __salt__['obd.query'](*args, **kwargs)['value']/2.0
    except:
        return -1

## LOCATION
#
def get_location():
    args = []
    kwargs = {}
    return __salt__['ec2x.gnss_nmea_gga'](*args, **kwargs)

# Retuns exception
def get_carState():
  #  try:
        args = ['driving']
        kwargs = {
        'mode': '21',
        'pid': '01',
        'header': '7E4',
        'baudrate': 500000,
        'formula': 'bytes_to_int(message.data[53:54])',  # Ignition
        'protocol': '6',
        'verify': False,
        'force': True,
        }
        return (int(__salt__['obd.query'](*args, **kwargs)['value'])&4)/4

def get_charging():
    try:
        args = ['driving']
        kwargs = {
        'mode': '21',
        'pid': '01',
        'header': '7E4',
        'baudrate': 500000,
        'formula': 'bytes_to_int(message.data[11:12])',
        'protocol': '6',
        'verify': False,
        'force': True,
        }
        return (int(__salt__['obd.query'](*args, **kwargs)['value'])&128)/128
    except:
        return -1

# Charging CCS
def get_charging_chademo():
#  try:
        args = ['CCS Plug']
        kwargs = {
        'mode': '21',
        'pid': '01',
        'header': '7E4',
        'baudrate': 500000,
        'formula': 'bytes_to_int(message.data[12:13])',
        'protocol': '6',
        'verify': False,
        'force': True,
        }
        return (int(__salt__['obd.query'](*args, **kwargs)['value'])&64)/64

# Charging 230V
def get_charging_normal():
#  try:
        args = ['J1772 Plug']
        kwargs = {
        'mode': '21',
        'pid': '01',
        'header': '7E4',
        'baudrate': 500000,
        'formula': 'bytes_to_int(message.data[12:13])',
        'protocol': '6',
        'verify': False,
        'force': True,
        }
        return (int(__salt__['obd.query'](*args, **kwargs)['value'])&32)/32
