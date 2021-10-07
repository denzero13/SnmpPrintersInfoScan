from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.hlapi import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
from multiprocessing import Pool
import ipaddress
import json
import datetime
import csv
from Classes import PrinterModel, DataForVisual


def snmp_cmd_gen(oid, ip_address, community="public", port=161):
    """
    The function takes the printer IDs and returns the value using the oid
    """
    get_printer_data = cmdgen.CommandGenerator()
    errorIndication, errorStatus, errorIndex, varBinds = get_printer_data.getCmd(
        cmdgen.CommunityData(community, mpModel=0),
        cmdgen.UdpTransportTarget((ip_address, port)),
        oid)

    if errorIndication is None:
        return varBinds[0][1]


def snmp_cmd_get(ip_address, community="public", port=161):
    """
    The function takes the address and checks
    it for the SNMP v1 v2 protocol whit standard settings
    """
    iterator = getCmd(SnmpEngine(),
                      CommunityData(community, mpModel=0),
                      UdpTransportTarget((ip_address, port)),
                      ContextData(),
                      ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysDescr', 0)))

    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

    if errorIndication:  # SNMP engine errors
        return errorIndication
    else:
        if errorStatus:  # SNMP agent errors
            status = str('%s at %s' % (errorStatus.prettyPrint(), varBinds[int(errorIndex) - 1] if errorIndex else '?'))
            return status
        else:
            for varBind in varBinds:  # SNMP response contents
                var = str(' = '.join([x.prettyPrint() for x in varBind]))
                return var


def ip_scan_diapason(ip_diapason="172.16.0.0/22"):
    """
    The function scans the specified range of addresses and create
    json with the list of devices in which the SNMP protocol is enabled
    """
    ip_diapason = ipaddress.IPv4Network(ip_diapason)
    number_of_ip = ip_diapason.prefixlen

    with open("devices.json", "w") as json_file:
        with Pool(number_of_ip) as processing:
            data = processing.map(device_snmp_filter, ip_diapason)
        devices = list()
        for obj in data:
            status = obj["snmp"]
            if status != "No SNMP":
                devices.append(obj)
        json.dump(devices, json_file, ensure_ascii=False)


def device_snmp_filter(ip_address):
    """
    Accepts the address and filters all devices if there is a protocol SNMP
    """
    ip_dict = dict()
    get_data = snmp_cmd_get(str(ip_address))

    if "No SNMP" in str(get_data):
        ip_dict["ip_host"] = str(ip_address)
        ip_dict["snmp"] = "No SNMP"
        return ip_dict

    elif "SNMPv2-MIB::sysDescr.0" in str(get_data):
        ip_dict["ip_host"] = str(ip_address)
        ip_dict["snmp"] = get_data
        return ip_dict


def csv_creator(devices):
    """
    Start OID scan with multiprocess
    """
    with Pool(30) as processing:
        data = processing.map(oid_multi_scan, devices)


def oid_multi_scan(device):
    """
    :param device:
    :return:
    """
    oid_list = PrinterModel(device).printer_model()
    if oid_list:
        ip_device = device["ip_host"]
        toner_type = snmp_cmd_gen(oid=oid_list["TonerType"], ip_address=ip_device)
        toner_type_color = snmp_cmd_gen(oid=str(oid_list["TonerType"])[:-1]+str(2), ip_address=ip_device)
        with open("tmp.csv", "a") as tmp_file, open("log.csv", "a") as log_file:
            fieldnames = list(oid_list.keys())
            fieldnames.append("time")
            tmp_writer = csv.DictWriter(tmp_file, fieldnames=fieldnames)
            log_writer = csv.DictWriter(log_file, fieldnames=fieldnames)
            print("Value: ", device, "\n", str(toner_type), str(toner_type_color))
            if "OctetString" in str(type(toner_type_color)) and str(toner_type_color) in ["cyan", "magenta", "yellow"]:
                for n in range(1, 5):
                    oid_list["TonerModel"] = str(oid_list["TonerModel"])[:-1]+str(n)
                    oid_list["TonerType"] = str(oid_list["TonerType"])[:-1] + str(n)
                    oid_list["TonerLevel"] = str(oid_list["TonerLevel"])[:-1] + str(n)
                    oid_list["CartridgeMaxCapacity"] = str(oid_list["CartridgeMaxCapacity"])[:-1] + str(n)
                    tmp_writer.writerow(indicators_oid(ip_device, oid_list))
                    log_writer.writerow(indicators_oid(ip_device, oid_list))
            elif "NoneType" in str(type(toner_type)) and str(toner_type) == "None":
                pass

            else:
                tmp_writer.writerow(indicators_oid(ip_device, oid_list))
                log_writer.writerow(indicators_oid(ip_device, oid_list))


def indicators_oid(ip_address, oid_list):
    """
    Get information in OID SNMP system with loop
    """
    printer_info = {}
    for oid_key in oid_list.keys():
        oid = oid_list[oid_key]
        printer_info[oid_key] = snmp_cmd_gen(oid=oid, ip_address=ip_address)

    printer_info["time"] = datetime.datetime.today().strftime("%d%m%Y%H%M%S")
    return printer_info


def start_get_printer_info(t):
    """
    Start get information about printers status
    """
    f = open("tmp.csv", "w")
    f.write("location,model,InventoryNumber,TonerModel,TonerType,TonerLevel,"
            "CartridgeMaxCapacity,PrintsBlack,PrintsColor,ip_host,time")
    f.close()
    with open("devices.json", "r", encoding='utf-8') as devices:
        print("Start printers toner level", t)
        devices = json.load(devices)
        csv_creator(devices)

        print("CSV", t)
        DataForVisual()