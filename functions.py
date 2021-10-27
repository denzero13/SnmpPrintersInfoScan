from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.hlapi import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
import plotly.graph_objects as go
from multiprocessing import Pool
import ipaddress
import json
import datetime
import csv
import socket
from getmac import getmac

from Classes import PrinterModel, DataPreparationForVisual
from config import tmp, log, devices


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

    with open(devices, "w") as json_file:
        with Pool(number_of_ip) as processing:
            data = processing.map(device_snmp_filter, ip_diapason)
        device = list()
        for obj in data:
            status = obj["snmp"]
            device.append(obj)
        json.dump(device, json_file, ensure_ascii=False)


def device_snmp_filter(ip_address):
    """
    Accepts the address and filters all devices if there is a protocol SNMP
    """
    ip = str(ip_address)
    ip_dict = dict()
    get_data = snmp_cmd_get(ip)
    mac = getmac.get_mac_address(ip=ip, network_request=True)

    if "No SNMP" in str(get_data):
        ip_dict["ip_host"] = ip
        ip_dict["snmp"] = "No SNMP"
        ip_dict["mac-address"] = mac

        try:
            ip_dict["hostname"] = str(socket.gethostbyaddr(ip))[0]
        except socket.herror:
            ip_dict["hostname"] = None

    elif "SNMPv2-MIB::sysDescr.0" in str(get_data):
        ip_dict["ip_host"] = ip
        ip_dict["snmp"] = get_data
        ip_dict["mac-address"] = mac

        try:
            ip_dict["hostname"] = str(socket.gethostbyaddr(ip))[0]
        except socket.herror:
            ip_dict["hostname"] = None

    return ip_dict


def multi_scan_run(devices):
    """
    Start OID scan with multiprocess
    """
    with Pool(30) as processing:
        data = processing.map(oid_scan, devices)


def oid_scan(device):
    """
    :param device:
    :return:
    """
    bool_status = device["snmp"]
    if bool_status:
        oid_list = PrinterModel(device).printer_model()
        ip_device = device["ip_host"]
        toner_type = snmp_cmd_gen(oid=oid_list["TonerType"], ip_address=ip_device)
        toner_type_color = snmp_cmd_gen(oid=str(oid_list["TonerType"])[:-1]+str(2), ip_address=ip_device)
        with open(tmp, "a") as tmp_file, open(log, "a") as log_file:
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


def start_get_printer_info(time):
    """
    Start get information about printers status
    """
    fieldnames = list(PrinterModel("").KYOCERA.keys())
    fieldnames.append("time")
    fieldnames = ",".join(fieldnames)
    file = open(tmp, "w")
    print(fieldnames)
    file.write(fieldnames)
    file.close()
    with open(devices, "r", encoding='utf-8') as json_file:
        print("Start printers toner level", time)
        json_file = json.load(json_file)
        multi_scan_run(devices=json_file)
        print("CSV", time)
        DataPreparationForVisual()


def data_visual_stack_bar(data, color):
    color_map = {"black": "0,0,0,",
                 "cyan": "60, 163, 206,",
                 "yellow": "255,245,57",
                 "magenta": "246, 78, 139,"}

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=data["Full Name"],
        x=data["Level"],
        name='Level',
        orientation='h',
        marker=dict(
                color=f'rgba({color_map.get(color)} 0.8)',
                line=dict(color=f'rgba({color_map.get(color)} 1.0)', width=3)
                )
        ))
    fig.add_trace(go.Bar(
        y=data["Full Name"],
        x=data["Used"],
        name='Used',
        orientation='h',
        marker=dict(
            color='rgba(68, 81, 90, 0.4)',
            line=dict(color='rgba(58, 71, 80, 1.0)', width=3)
            )
        ))

    if color != "black":
        fig.update_layout(barmode='stack', height=400, width=760,
                          plot_bgcolor="#111111",
                          paper_bgcolor="#111111",
                          font=dict(family="Courier New, monospace", size=13, color=color))
    else:
        fig.update_layout(barmode='stack', height=1200, width=1150,
                          plot_bgcolor="#a4a4a4",
                          paper_bgcolor="#a4a4a4",
                          font=dict(family="Courier New, monospace", size=18, color=color))

    return fig