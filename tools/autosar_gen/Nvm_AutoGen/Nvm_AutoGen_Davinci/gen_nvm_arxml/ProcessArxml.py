#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import pandas
from xml.dom.minidom import parse
from xml.dom import minidom
import random
import string


## brief 
#  @param xml_path NVM_SWC_1.arxml
#  @param data_xml_path DataTypes.arxml
#  @param excel_data XXXX_PlatformPara.xlsx
def ProcessArxml(xml_path, data_xml_path, excel_data):
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

    ## brief write_two_sub_node
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    #  @param name
    #  @param attr
    #  @param value
    #  @param text
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

    ## brief write_INIT_VALUE_node
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    #  @param lenth
    def write_INIT_VALUE_node(dom,father_node,lenth):
        if ((lenth > 4) or (3 == lenth)):
            root = dom.createElement("ARRAY-VALUE-SPECIFICATION")
            father_node.appendChild(root)

            ELEMENTS_node = dom.createElement("ELEMENTS")

            for i in range(lenth):
                NUM_node = dom.createElement("NUMERICAL-VALUE-SPECIFICATION")
                val_node = dom.createElement("VALUE")
                name = dom.createTextNode("0")
                val_node.appendChild(name)
                NUM_node.appendChild(val_node)
                ELEMENTS_node.appendChild(NUM_node)

            root.appendChild(ELEMENTS_node)
        else:
            NUM_node = dom.createElement("NUMERICAL-VALUE-SPECIFICATION")
            val_node = dom.createElement("VALUE")
            name = dom.createTextNode("0")
            val_node.appendChild(name)
            NUM_node.appendChild(val_node)
            father_node.appendChild(NUM_node)
        return

    ## brief write_sub_node_from_ADMIN_DATA
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    #  @param excel_name
    def write_sub_node_from_ADMIN_DATA(dom, father_node, excel_name):
        SDGS_node = dom.createElement("SDGS")
        SDG_node = dom.createElement("SDG")
        SDG_node.setAttribute("GID", "DV_SDG")

        name = ['SD']
        attr = ['GID']
        value = ['AutoServiceNeedNameHdlg']
        text = ['1']
        write_two_sub_node(dom, SDG_node, name, attr, value, text)

        SDGS_node.appendChild(SDG_node)
        father_node.appendChild(SDGS_node)

        return

    ## brief write_read_node
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    def write_read_node(dom, father_node):
        VARIANTS_node = dom.createElement("SW-DATA-DEF-PROPS-VARIANTS")
        CONDITIONAL_node = dom.createElement("SW-DATA-DEF-PROPS-CONDITIONAL")
        ACCESS_node = dom.createElement("SW-CALIBRATION-ACCESS")
        name = dom.createTextNode("READ-WRITE")
        ACCESS_node.appendChild(name)
        CONDITIONAL_node.appendChild(ACCESS_node)
        VARIANTS_node.appendChild(CONDITIONAL_node)
        father_node.appendChild(VARIANTS_node)
        return

    ## brief write_sub_node_from_RAM_BLOCK
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    #  @param excel_name
    #  @param lenth - data type lenth
    def write_sub_node_from_RAM_BLOCK(dom, father_node, excel_name, lenth):
        name = ['SHORT-NAME','TYPE-TREF']
        attr = ['','DEST']
        value = ['','IMPLEMENTATION-DATA-TYPE']
        if (lenth == 1): #选择长度
            text = [(excel_name.replace("Pdm_","PDM_")+ '_Ram'), '/AUTOSAR_Platform/ImplementationDataTypes/uint8']
        elif (lenth == 2):
            text = [(excel_name.replace("Pdm_","PDM_")+ '_Ram'), '/AUTOSAR_Platform/ImplementationDataTypes/uint16']
        elif (lenth == 4):
            text = [(excel_name.replace("Pdm_","PDM_")+ '_Ram'), '/AUTOSAR_Platform/ImplementationDataTypes/uint32']
        else:
            text = [(excel_name.replace("Pdm_","PDM_")+ '_Ram'), '/DataTypes/'+excel_name.replace("Pdm_","PDM_") + '_size']
        write_two_sub_node(dom, father_node, name, attr, value, text)

        root = dom.createElement("INIT-VALUE")
        write_INIT_VALUE_node(dom, root,lenth)
        father_node.appendChild(root)
        return

    def write_sub_node_from_ROM_BLOCK(dom, father_node, excel_name, lenth):
        name = ['SHORT-NAME']
        attr = ['']
        value = ['']
        text = [(excel_name.replace("Pdm_","PDM_")+ '_Rom')]
        write_two_sub_node(dom, father_node, name, attr, value, text)

        root = dom.createElement("SW-DATA-DEF-PROPS")
        write_read_node(dom,root)
        father_node.appendChild(root)

        name = ['TYPE-TREF']
        attr = ['DEST']
        value = ['IMPLEMENTATION-DATA-TYPE']
        if lenth == 1: #选择长度
            text = ['/AUTOSAR_Platform/ImplementationDataTypes/uint8']
        elif lenth == 2:
            text = ['/AUTOSAR_Platform/ImplementationDataTypes/uint16']
        elif lenth == 4:
            text = ['/AUTOSAR_Platform/ImplementationDataTypes/uint32']
        else:
            text = ['/DataTypes/'+excel_name.replace("Pdm_","PDM_")]
        write_two_sub_node(dom, father_node, name, attr, value, text)

        root = dom.createElement("INIT-VALUE")
        write_INIT_VALUE_node(dom, root,lenth)
        father_node.appendChild(root)
        return

    ## brief write_sub_node_from_NV_BLOCK_NEEDS
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    #  @param excel_name
    #  @param lenth - data type lenth
    def write_sub_node_from_NV_BLOCK_NEEDS(dom, father_node, excel_name, lenth):

        root = dom.createElement("SHORT-NAME")
        name = dom.createTextNode("NVNeed_NVBlockDescriptor")
        root.appendChild(name)
        father_node.appendChild(root)

        root = dom.createElement("ADMIN-DATA")
        #if lenth > 4:
        write_sub_node_from_ADMIN_DATA(dom,root,excel_name)
        father_node.appendChild(root)

        root = dom.createElement("N-DATA-SETS")
        name = dom.createTextNode("0")
        root.appendChild(name)
        father_node.appendChild(root)

        root = dom.createElement("RAM-BLOCK-STATUS-CONTROL")
        name = dom.createTextNode("API")
        root.appendChild(name)
        father_node.appendChild(root)

        root = dom.createElement("RELIABILITY")
        name = dom.createTextNode("NO-PROTECTION")
        root.appendChild(name)
        father_node.appendChild(root)

        root = dom.createElement("RESTORE-AT-START")
        name = dom.createTextNode("false")
        root.appendChild(name)
        father_node.appendChild(root)

        root = dom.createElement("STORE-AT-SHUTDOWN")
        name = dom.createTextNode("false")
        root.appendChild(name)
        father_node.appendChild(root)

        return

    ## brief 获取UUID随机值
    def GetUUID():
        UUID1 = ''.join(random.sample(string.ascii_uppercase + string.digits, 8))
        UUID2 = ''.join(random.sample(string.ascii_uppercase + string.digits, 4))
        UUID3 = ''.join(random.sample(string.ascii_uppercase + string.digits, 4))
        UUID4 = ''.join(random.sample(string.ascii_uppercase + string.digits, 4))
        UUID5 = ''.join(random.sample(string.ascii_uppercase + string.digits, 12))
        UUID0 = UUID1 + "-" + UUID2 + "-" + UUID3 + "-" + UUID4 + "-" + UUID5
        return UUID0

    def write_sub_node_from_CLIENT_SERVER_PORTS(dom, father_node,excel_name):

        # ROLE-BASED-PORT-ASSIGNMENT
        root = dom.createElement("ROLE-BASED-PORT-ASSIGNMENT")
        name = ['ROLE']
        attr = ['']
        value = ['']
        text = ['NvSWC_NvMService_AC2']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)


        root = dom.createElement("ROLE-BASED-PORT-ASSIGNMENT")
        name = ['PORT-PROTOTYPE-REF', 'ROLE']
        attr = ['DEST', '']
        value = ['P-PORT-PROTOTYPE', '']
        text = ['/ComponentTypes/NvM_SWC/NvMService_' + excel_name, 'NvSWC_NvMService_AC2']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)
        return

    ## brief write_sub_node_from_root
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    #  @param excel_name
    #  @param lenth - data type lenth
    def write_sub_node_from_root(dom, father_node, excel_name, lenth):
        # short name
        root = dom.createElement("SHORT-NAME")
        name = dom.createTextNode(excel_name.replace("Pdm_","PDM_"))
        root.appendChild(name)
        father_node.appendChild(root)

        # CLIENT-SERVER-PORTS
        # root = dom.createElement("CLIENT-SERVER-PORTS")
        # write_sub_node_from_CLIENT_SERVER_PORTS(dom, root, excel_name)
        # father_node.appendChild(root)

        # NV-BLOCK-NEEDS
        root = dom.createElement("NV-BLOCK-NEEDS")
        root.setAttribute("UUID", GetUUID())
        write_sub_node_from_NV_BLOCK_NEEDS(dom, root, excel_name, lenth)
        father_node.appendChild(root)

        # RAM-BLOCK
        root = dom.createElement("RAM-BLOCK")
        root.setAttribute("UUID", GetUUID())
        write_sub_node_from_RAM_BLOCK(dom, root, excel_name, lenth)
        father_node.appendChild(root)

        # # ROM-BLOCK
        # root = dom.createElement("ROM-BLOCK")
        # root.setAttribute("UUID", GetUUID())
        # write_sub_node_from_ROM_BLOCK(dom, root, excel_name, lenth)
        # father_node.appendChild(root)

        # SUPPORT-DIRTY-FLAG
        # root = dom.createElement("SUPPORT-DIRTY-FLAG")
        # name = dom.createTextNode('true')
        # root.appendChild(name)
        # father_node.appendChild(root)
        return

    ## brief write_PDM_block_root_node_in_arxml
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    #  @param name
    #  @param lenth - data type lenth
    def write_PDM_block_root_node_in_arxml(dom, father_node, name, lenth):
        root = dom.createElement("NV-BLOCK-DESCRIPTOR")
        root.setAttribute("UUID", GetUUID())
        write_sub_node_from_root(dom, root, name, lenth)
        father_node.appendChild(root)

        return
        
    ## brief modify_DATA_TYPE_lenth_node_in_arxml
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    #  @param lenth - data type lenth
    def modify_DATA_TYPE_lenth_node_in_arxml(dom, father_node, lenth):
        for node in father_node.childNodes:
            if node.nodeType == 1 and node.nodeName == "SUB-ELEMENTS":
                for node1 in node.childNodes:
                    if node1.nodeType == 1 and node1.nodeName == "IMPLEMENTATION-DATA-TYPE-ELEMENT":
                        for node2 in node1.childNodes:
                            if node2.nodeType == 1 and node2.nodeName == "ARRAY-SIZE":
                                node2.firstChild.nodeValue = lenth

        return

    ## brief write_SW_DATA_DEF_PROPS_node
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    def write_SW_DATA_DEF_PROPS_node(dom, father_node):
        root = dom.createElement("SW-DATA-DEF-PROPS-VARIANTS")
        CONDITIONAL_node = dom.createElement("SW-DATA-DEF-PROPS-CONDITIONAL")
        sw_node = dom.createElement("SW-CALIBRATION-ACCESS")
        name = dom.createTextNode("READ-WRITE")
        sw_node.appendChild(name)
        CONDITIONAL_node.appendChild(sw_node)
        root.appendChild(CONDITIONAL_node)
        father_node.appendChild(root)
        return

    ## brief write_SW_DATA_DEF_PROPS_VARIANTS_node
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    #  @param lenth
    def write_SW_DATA_DEF_PROPS_VARIANTS_node(dom, father_node, lenth):
        root = dom.createElement("SW-DATA-DEF-PROPS-VARIANTS")
        sw_node = dom.createElement("SW-DATA-DEF-PROPS-CONDITIONAL")

        name = ['SW-CALIBRATION-ACCESS', 'IMPLEMENTATION-DATA-TYPE-REF']
        attr = ['', 'DEST']
        value = ['', 'IMPLEMENTATION-DATA-TYPE']
        text = ['READ-ONLY', '/AUTOSAR_Platform/ImplementationDataTypes/uint8']
        write_two_sub_node(dom, sw_node, name, attr, value, text)

        root.appendChild(sw_node)
        father_node.appendChild(root)
        return

    ## brief write_SUB_ELEMENTS_node
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    #  @param lenth
    def write_SUB_ELEMENTS_node(dom, father_node, lenth):
        root = dom.createElement("IMPLEMENTATION-DATA-TYPE-ELEMENT")
        root.setAttribute("UUID", GetUUID())
        name = ['SHORT-NAME', 'CATEGORY','ARRAY-SIZE']
        attr = ['', '', '']
        value = ['', '', '']
        text = ['Element', 'TYPE_REFERENCE',str(lenth)]
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        sw_node = dom.createElement("SW-DATA-DEF-PROPS")
        write_SW_DATA_DEF_PROPS_VARIANTS_node(dom, sw_node, lenth)
        root.appendChild(sw_node)

        return

    ## brief write_DATA_TYPE_root_node_in_arxml
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    #  @param excel_name
    #  @param lenth
    def write_DATA_TYPE_root_node_in_arxml(dom, father_node, excel_name, lenth):
        root = dom.createElement("IMPLEMENTATION-DATA-TYPE")
        root.setAttribute("UUID", GetUUID())
        write_DATA_TYPE_node_in_arxml(dom, root, excel_name, lenth)
        father_node.appendChild(root)
        return

    ## brief write_DATA_TYPE_node_in_arxml
    #  @param dom dom = parse(xml_path)
    #  @param father_node
    #  @param excel_name
    #  @param lenth
    def write_DATA_TYPE_node_in_arxml(dom, father_node, excel_name, lenth):
        name = ['SHORT-NAME', 'CATEGORY']
        attr = ['', '']
        value = ['', '']
        text = [('PDM' + excel_name.lstrip('Pdm') + '_size'), 'ARRAY']
        write_two_sub_node(dom, father_node, name, attr, value, text)

        # SW-DATA-DEF-PROPS node
        root = dom.createElement("SW-DATA-DEF-PROPS")
        write_SW_DATA_DEF_PROPS_node(dom,root)
        father_node.appendChild(root)

        # SUB-ELEMENTS node
        root = dom.createElement("SUB-ELEMENTS")
        write_SUB_ELEMENTS_node(dom,root,lenth)
        father_node.appendChild(root)

        root = dom.createElement("TYPE-EMITTER")
        name = dom.createTextNode("RTE")
        root.appendChild(name)
        father_node.appendChild(root)
        return

    ## brief Get_All_Sub_Node
    #  @param rootNode
    #  @param event_max_num
    #  @param tag_name
    #  @param sub_tag_name
    def Get_All_Sub_Node(rootNode,event_max_num, tag_name, sub_tag_name):
        PDM_NUM = 0
        PDM_node_list = []
        PDM_name_list = []

        # if rootNode
        for node in rootNode.childNodes:
            if node.nodeType == 1 and node.nodeName == 'NV-BLOCK-DESCRIPTORS':
                for node1 in node.childNodes:
                    if node1.nodeType == 1 and node1.nodeName == tag_name:
                        for node2 in node1.childNodes:
                            if node2.nodeType == 1 and node2.nodeName == sub_tag_name:
                                name = node2.firstChild.nodeValue
                                if 'PDM_' in name:
                                    PDM_node_list.append(node1)
                                    PDM_name_list.append(name)
                                    PDM_NUM = PDM_NUM +1


        return PDM_node_list, PDM_name_list, PDM_NUM

    ## brief Get_All_TYPE_Sub_Node
    #  @param rootNode
    #  @param tag_name
    #  @param sub_tag_name
    def Get_All_TYPE_Sub_Node(rootNode, tag_name, sub_tag_name):
        TYPE_NUM = 0
        TYPE_node_list = []
        TYPE_name_list = []
        TYPE_lenth_list = []
        for node in rootNode.childNodes:
            if node.nodeType == 1 and node.nodeName == tag_name:
                flag = 0
                for node1 in node.childNodes:
                    if node1.nodeType == 1 and node1.nodeName == sub_tag_name:
                        name = node1.firstChild.nodeValue
                        if 'PDM_' in name:
                            TYPE_node_list.append(node)
                            TYPE_name_list.append(name)
                            TYPE_NUM = TYPE_NUM +1
                            flag = 1

                    if (flag == 1):
                        if node1.nodeType == 1 and node1.nodeName == "SUB-ELEMENTS":
                            for node2 in node1.childNodes:
                                if  node2.nodeType == 1 and node2.nodeName == "IMPLEMENTATION-DATA-TYPE-ELEMENT":
                                    for node3 in node2.childNodes:
                                        if node3.nodeType == 1 and node3.nodeName == "ARRAY-SIZE":
                                            lenth = node3.firstChild.nodeValue
                                            TYPE_lenth_list.append(lenth)



        return TYPE_node_list, TYPE_name_list, TYPE_lenth_list, TYPE_NUM

    ## brief 寻找我们自己需要添加的根节点
    #  @param rootNode 
    def find_root_write_node(rootNode):
        found_PDM_DEM_ADMIN = False
        for node1 in rootNode.childNodes:
            if node1.nodeType == 1 and node1.nodeName == "AR-PACKAGES":
                for node2 in node1.childNodes:
                    if node2.nodeType == 1 and node2.nodeName == "AR-PACKAGE":
                        for node3 in node2.childNodes:
                            if node3.nodeType == 1 and node3.nodeName == "ELEMENTS":
                                for node4 in node3.childNodes:
                                    if node4.nodeType == 1 and node4.nodeName == "NV-BLOCK-SW-COMPONENT-TYPE":
                                        for node5 in node4.childNodes:
                                            if node5.nodeType == 1 and node5.nodeName == "INTERNAL-BEHAVIORS":
                                                return node4
        return 0

    ## brief 寻找我们自己需要添加的根节点
    #  @param rootNode   
    def find_root_write_type_node(rootNode):
        found_PDM_DEM_ADMIN = False
        for node1 in rootNode.childNodes:
            if node1.nodeType == 1 and node1.nodeName == "AR-PACKAGES":
                for node2 in node1.childNodes:
                    if node2.nodeType == 1 and node2.nodeName == "AR-PACKAGE":
                        for node3 in node2.childNodes:
                            if node3.nodeType == 1 and node3.nodeName == "SHORT-NAME" and node3.firstChild.data == "DataTypes":
                                return node2

        return 0

    ####main process here
    minidom.Element.writexml = fixed_writexml
    try:
        dom = parse(xml_path)
    except IOError:
        print("Error open " + xml_path)
        return
        
    try:
        dom_data_type = parse(data_xml_path)
    except IOError:
        print("Error open " + data_xml_path)
        return

    # 获取根目录
    root_node = dom.documentElement
    root_type_node = dom_data_type.documentElement
    
    # 寻找要加入的根节点
    my_root_node = find_root_write_node(root_node)  #PDMParameter
    type_root_node = find_root_write_type_node(root_type_node)  #PDM data type Parameter

    flag = False
    node_list = type_root_node.childNodes
    for i in node_list:
        if 'ELEMENTS' in i.nodeName:
            print(i.nodeName)
            flag = True
            inserted_father_node = i
            pass

    if flag is False:
        inserted_father_node = dom_data_type.createElement("ELEMENTS")
        type_root_node.appendChild(inserted_father_node)


    #获得所有节点，以方便接下来的插入节点
    PDM_node_list, PDM_name_list, PDM_NUM= Get_All_Sub_Node(my_root_node, excel_data.num, 'NV-BLOCK-DESCRIPTOR', 'SHORT-NAME')

    TYPE_node_list, TYPE_name_list, TYPE_lenth_list, TYPE_NUM = Get_All_TYPE_Sub_Node(inserted_father_node, 'IMPLEMENTATION-DATA-TYPE', 'SHORT-NAME')

    #检查读取ARXML情况
    if len(PDM_name_list) == 0:
        print('Get PDM name faile from ARXML')
        # return

    if len(TYPE_name_list) == 0:
        print('Get PDM DATA TYPE faile from ARXML')
        # return

    #检查config中是否有多余的block
    for i in range (PDM_NUM):
        if PDM_name_list[i].replace("PDM_","Pdm_") not in excel_data.Pdm_Name:
            print(PDM_name_list[i] + '-------- not in excel please check config')

    for i in range(len(excel_data.Pdm_Name)):
        check_flag = 0
        if ((excel_data.lenth[i] > 4) or (3 == excel_data.lenth[i])):
            for j in range(TYPE_NUM):
                if((TYPE_name_list[j].replace("PDM_","") ) == (excel_data.Pdm_Name[i].replace("Pdm_","") + '_size')):
                    if (int(TYPE_lenth_list[j]) != excel_data.lenth[i]):
                        print(excel_data.Pdm_Name[i] + " data type incorrect ")
                        print("\t"+"excel "+excel_data.Pdm_Name[i] +" lenth " +str(excel_data.lenth[i]))
                        print("\t"+"arxml " + TYPE_name_list[j] + " lenth " + str(TYPE_lenth_list[j]))
                        modify_DATA_TYPE_lenth_node_in_arxml(dom_data_type,
                                                TYPE_node_list[j],
                                                excel_data.lenth[i])
                        for k in range(PDM_NUM):
                            if (PDM_name_list[k] == excel_data.Pdm_Name[i]):
                                PDM_node_list[k].parentNode.removeChild(PDM_node_list[k])
                                #y_root_node.removeChild(PDM_node_list[k])
                    check_flag = 1
            if(check_flag == 0):
                write_DATA_TYPE_root_node_in_arxml(dom_data_type,
                                              inserted_father_node,
                                              excel_data.Pdm_Name[i].replace("PDM_",""),
                                              excel_data.lenth[i])
                print(excel_data.Pdm_Name[i] + " ------create data TYPE")

    PDM_node_list, PDM_name_list, PDM_NUM = Get_All_Sub_Node(my_root_node, excel_data.num, 'NV-BLOCK-DESCRIPTOR', 'SHORT-NAME')

    nvm_swc_flag = False
    nvm_swc_node_list = my_root_node.childNodes
    for i in nvm_swc_node_list:
        if 'NV-BLOCK-DESCRIPTORS' in i.nodeName:
            print(i.nodeName)
            nvm_swc_flag = True
            nvm_swc_inserted_father_node = i
            pass

    if nvm_swc_flag is False:
        nvm_swc_inserted_father_node = dom.createElement("NV-BLOCK-DESCRIPTORS")
        my_root_node.appendChild(nvm_swc_inserted_father_node)

    for i in range(excel_data.num):
        # if ((excel_data.Pdm_Name[i].replace("Pdm_","PDM_") not in PDM_name_list) or (int(TYPE_lenth_list[j]) != excel_data.lenth[i])):
        if (excel_data.Pdm_Name[i].replace("Pdm_", "PDM_") not in PDM_name_list):
            print(excel_data.Pdm_Name[i] + ' ****************   not in list or lenth changed')
            write_PDM_block_root_node_in_arxml(dom,
                                     nvm_swc_inserted_father_node,
                                     excel_data.Pdm_Name[i],
                                     excel_data.lenth[i])
        else:
            #for j in range(PDM_NUM):
             #   if (PDM_name_list[j] == excel_data.Pdm_Name[i]):
              #      print("\t"+PDM_name_list[j]+"\t"+excel_data.Pdm_Name[i])
            print(excel_data.Pdm_Name[i] + '-------------- already in list')




    # 每一个结点对象（包括dom对象本身）都有输出XML内容的方法，如：toxml()--字符串, toprettyxml()--美化树形格式。
    try:
        with open(xml_path, 'w', encoding='UTF-8') as fh:
            # 4.writexml()第一个参数是目标文件对象，第二个参数是根节点的缩进格式，第三个参数是其他子节点的缩进格式，
            # 第四个参数制定了换行格式，第五个参数制定了xml内容的编码。
            dom.writexml(fh, indent='', addindent='  ', newl='\n', encoding='UTF-8')
            print('写入 ' + xml_path + ' OK!')
    except Exception as err:
        print('错误信息：{0}'.format(err))

    try:
        with open(data_xml_path, 'w', encoding='UTF-8') as fh:
            # 4.writexml()第一个参数是目标文件对象，第二个参数是根节点的缩进格式，第三个参数是其他子节点的缩进格式，
            # 第四个参数制定了换行格式，第五个参数制定了xml内容的编码。
            dom_data_type.writexml(fh, indent='', addindent='  ', newl='\n', encoding='UTF-8')
            print('写入 ' + data_xml_path + ' OK!')
    except Exception as err:
        print('错误信息：{0}'.format(err))
    return





















