#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import pandas
from xml.dom.minidom import parse
from xml.dom import minidom
import random
import string



def ProcessArxml(xml_path, excel_data):
    def fixed_writexml(self, writer, indent="", addindent="", newl=""):
        # indent = current indentation
        # addindent = indentation to add to higher levels
        # newl = newline string
        writer.write(indent + "<" + self.tagName)

        attrs = self._get_attributes()
        a_names = attrs.keys()
        # a_names.sort()
        sorted(a_names)

        for a_name in a_names:
            writer.write(" %s=\"" % a_name)
            minidom._write_data(writer, attrs[a_name].value)
            writer.write("\"")
        if self.childNodes:
            if len(self.childNodes) == 1 and self.childNodes[0].nodeType == minidom.Node.TEXT_NODE:
                writer.write(">")
                self.childNodes[0].writexml(writer, "", "", "")
                writer.write("</%s>%s" % (self.tagName, newl))
                return
            writer.write(">%s" % (newl))
            for node in self.childNodes:
                if node.nodeType is not minidom.Node.TEXT_NODE:
                    node.writexml(writer, indent + addindent, addindent, newl)
            writer.write("%s</%s>%s" % (indent, self.tagName, newl))
        else:
            writer.write("/>%s" % (newl))

    minidom.Element.writexml = fixed_writexml

    # 获取UUID随机值
    def GetUUID():
        UUID1 = ''.join(random.sample(string.ascii_uppercase + string.digits, 8))
        UUID2 = ''.join(random.sample(string.ascii_uppercase + string.digits, 4))
        UUID3 = ''.join(random.sample(string.ascii_uppercase + string.digits, 4))
        UUID4 = ''.join(random.sample(string.ascii_uppercase + string.digits, 4))
        UUID5 = ''.join(random.sample(string.ascii_uppercase + string.digits, 12))
        UUID0 = UUID1 + "-" + UUID2 + "-" + UUID3 + "-" + UUID4 + "-" + UUID5
        return UUID0

    def transform_uds_dtc(id):
        '''
        bit15-bit14
            00 P   powertrain
            01 C   chassis
            10 B   body
            11 U   network
        bit13-bit12
            00 0    ISO/SAE standard
            01 1    manufactor
            10 2    ISO/SAE standard
            11 3   reserved
        '''
        if id[0:2] == 'U0':
            id_new = 'C'
        elif id[0:2] == 'U1':
            id_new = 'D'
        elif id[0:2] == 'U2':
            id_new = 'E'
        elif id[0:2] == 'U3':
            id_new = 'F'
        elif id[0:2] == 'P0':
            id_new = '0'
        elif id[0:2] == 'P1':
            id_new = '1'
        elif id[0:2] == 'P2':
            id_new = '2'
        elif id[0:2] == 'P3':
            id_new = '3'
        elif id[0:2] == 'C0':
            id_new = '4'
        elif id[0:2] == 'C1':
            id_new = '5'
        elif id[0:2] == 'C2':
            id_new = '6'
        elif id[0:2] == 'C3':
            id_new = '7'
        elif id[0:2] == 'B0':
            id_new = '8'
        elif id[0:2] == 'B1':
            id_new = '9'
        elif id[0:2] == 'B2':
            id_new = 'A'
        elif id[0:2] == 'B3':
            id_new = 'B'

        return id_new+id[2:]


    def Get_All_Sub_Node(rootNode,event_max_num, tag_name, sub_tag_name):
        DemDTC_name_list = []
        DemDTC_id_list = []
        for node in rootNode.childNodes:
            if node.nodeType == 1 and node.nodeName == tag_name:
                for node1 in node.childNodes:
                    if node1.nodeType == 1 and node1.nodeName == sub_tag_name:
                        name = node1.firstChild.nodeValue
                        if 'DemDTC_CAN_' in name:
                            id = transform_uds_dtc(name.split('DemDTC_CAN_')[1].split('_', 1)[0])
                            DemDTC_id_list.append(id)
                            #name = 'DemDTC_CAN_'+name.split('DemDTC_CAN_')[1].split('_', 1)[1]
                            DemDTC_name_list.append(name)
                        elif 'DemDTC_' in name:
                            id = transform_uds_dtc(name.split('DemDTC_')[1].split('_', 1)[0])
                            DemDTC_id_list.append(id)
                            #name = 'DemDTC_'+name.split('DemDTC_')[1].split('_', 1)[1]
                            DemDTC_name_list.append(name)

        return DemDTC_name_list, DemDTC_id_list

    def write_two_sub_node(dom, father_node, name, attr, value, text):
        for i in range(len(name)):
            node = dom.createElement(name[i])
            if attr[i] != '':
                node.setAttribute(attr[i], value[i])
            if text[i] != '':
                name_text = dom.createTextNode(text[i])
                node.appendChild(name_text)
            father_node.appendChild(node)
        return

    def write_PARAMETER_VALUES_subnode(dom, father_node, num):

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-BOOLEAN-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemDTCClass/DemImmediateNvStorage', 'false']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-INTEGER-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemDTCClass/DemUdsDTC', str(num)]
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        return

    def write_dem_dtc_in_arxml(dom, father_node, dtc_name, dtc_number):
        name_str = dtc_name
        root = dom.createElement("ECUC-CONTAINER-VALUE")
        root.setAttribute("UUID", GetUUID())
        ref_Child_node = find_DTC_ref_Child_node(father_node)
        father_node.insertBefore(root, ref_Child_node)

        ###short name
        short_name_node = dom.createElement("SHORT-NAME")
        name_text = dom.createTextNode(name_str)
        short_name_node.appendChild(name_text)
        root.appendChild(short_name_node)

        ###DEFINITION-REF
        DEFINITION_REF_node = dom.createElement("DEFINITION-REF")
        DEFINITION_REF_node.setAttribute("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
        name_text = dom.createTextNode('/MICROSAR/Dem/DemConfigSet/DemDTCClass')
        DEFINITION_REF_node.appendChild(name_text)
        root.appendChild(DEFINITION_REF_node)

        ###PARAMETER-VALUES
        PARAMETER_VALUES_node = dom.createElement("PARAMETER-VALUES")
        write_PARAMETER_VALUES_subnode(dom, PARAMETER_VALUES_node, dtc_number)
        root.appendChild(PARAMETER_VALUES_node)

        return

    # 寻找我们自己需要添加的根节点
    def find_root_write_node(rootNode):
        found_DemConfigSet = False
        for node1 in rootNode.childNodes:
            if node1.nodeType == 1 and node1.nodeName == "AR-PACKAGES":
                for node2 in node1.childNodes:
                    if node2.nodeType == 1 and node2.nodeName == "AR-PACKAGE":
                        for node3 in node2.childNodes:
                            if node3.nodeType == 1 and node3.nodeName == "ELEMENTS":
                                for node4 in node3.childNodes:
                                    if node4.nodeType == 1 and node4.nodeName == "ECUC-MODULE-CONFIGURATION-VALUES":
                                        for node5 in node4.childNodes:
                                            if node5.nodeType == 1 and node5.nodeName == "CONTAINERS":
                                                for node6 in node5.childNodes:
                                                    if node6.nodeType == 1 and node6.nodeName == "ECUC-CONTAINER-VALUE":
                                                        for node7 in node6.childNodes:
                                                            if node7.nodeType == 1 and node7.tagName == "SHORT-NAME" and node7.firstChild.nodeValue == "DemConfigSet":
                                                                found_DemConfigSet = True
                                                            if node7.nodeType == 1 and node7.nodeName == "SUB-CONTAINERS" and found_DemConfigSet:
                                                                return node7
        return 0

    # 寻找添加DTC的参考节点
    def find_DTC_ref_Child_node(demNode):
        for node1 in demNode.childNodes:
            if node1.nodeType == 1 and node1.nodeName == "ECUC-CONTAINER-VALUE":
                for node2 in node1.childNodes:
                    if node2.nodeType == 1 and node2.tagName == "SHORT-NAME" and node2.firstChild.nodeValue == "DemEventParameter":
                        return node1
        return 0

    ####main process here
    try:
        dom = parse(xml_path)
    except IOError:
        print("Error open " + xml_path)
        return

    # 获取根目录
    root_node = dom.documentElement

    # 寻找要加入的根节点
    my_root_node = find_root_write_node(root_node)  #DemEventParameter

    DemDTC_name_list, DemDTC_id_list = Get_All_Sub_Node(my_root_node, excel_data.num, 'ECUC-CONTAINER-VALUE', 'SHORT-NAME')

    for i in range(excel_data.num):
        if excel_data.DTC_Hex_Number[i + excel_data.start_offset] in DemDTC_id_list:
            print(excel_data.DTC_Hex_Number[i + excel_data.start_offset] + '-------------- already in list')
        else:
            write_dem_dtc_in_arxml(dom, my_root_node, excel_data.DTC_Name[i + excel_data.start_offset],
                                   excel_data.DTC_Dec_Number[i + excel_data.start_offset])
            print(excel_data.DTC_Hex_Number[i + excel_data.start_offset] + '-------------- add in list')
            ##break

    # 每一个结点对象（包括dom对象本身）都有输出XML内容的方法，如：toxml()--字符串, toprettyxml()--美化树形格式。
    try:
        with open(xml_path, 'w', encoding='UTF-8') as fh:
            # 4.writexml()第一个参数是目标文件对象，第二个参数是根节点的缩进格式，第三个参数是其他子节点的缩进格式，
            # 第四个参数制定了换行格式，第五个参数制定了xml内容的编码。
            dom.writexml(fh, indent='', addindent='  ', newl='\n', encoding='UTF-8', standalone=False)
            print('在 ' + xml_path + ' 中写入DTC OK!')
    except Exception as err:
        print('错误信息：{0}'.format(err))

    return





















