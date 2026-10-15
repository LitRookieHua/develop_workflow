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

    # 从根节点开始检索是否存在满足条件的节点
    def is_node_exist(rootNode, tagName, tagValue):
        nodes = rootNode.getElementsByTagName(tagName)
        if len(nodes) == 0:
            print("no nodes found")
            return 0
        else:
            if tagValue == "null":
                return nodes[0]
            else:
                for node in nodes:
                    if node.firstChild.nodeValue == tagValue:
                        return node
            #print("no childNodeName " + tagValue + " found")
            return 0

    def found_ref_event_num_value(node1):
        for node2 in node1.childNodes:
            if node2.nodeType == 1 and node2.nodeName == "PARAMETER-VALUES":
                for node3 in node2.childNodes:
                    if node3.nodeType == 1 and node3.nodeName == "ECUC-NUMERICAL-PARAM-VALUE":
                        found_tag = False
                        for node4 in node3.childNodes:
                            if node4.nodeType == 1 and node4.nodeName == "DEFINITION-REF" and node4.firstChild.nodeValue == '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventId':
                                found_tag = True
                            if found_tag and node4.nodeType == 1 and node4.nodeName == "VALUE":
                                return node4.firstChild.nodeValue
        return '0'
    def modify_ref_event_num_value(node1,value):
        for node2 in node1.childNodes:
            if node2.nodeType == 1 and node2.nodeName == "PARAMETER-VALUES":
                for node3 in node2.childNodes:
                    if node3.nodeType == 1 and node3.nodeName == "ECUC-NUMERICAL-PARAM-VALUE":
                        found_tag = False
                        for node4 in node3.childNodes:
                            if node4.nodeType == 1 and node4.nodeName == "DEFINITION-REF" and node4.firstChild.nodeValue == '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventId':
                                found_tag = True
                            if found_tag and node4.nodeType == 1 and node4.nodeName == "VALUE":
                                node4.firstChild.nodeValue = value

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
        demEvent_node_list = []
        demEvent_name_list = []
        DemDTC_name_list = []
        DemDTC_id_list = []
        demEvent_value_ref_event_num = 0
        for node in rootNode.childNodes:
            if node.nodeType == 1 and node.nodeName == tag_name:
                for node1 in node.childNodes:
                    if node1.nodeType == 1 and node1.nodeName == sub_tag_name:
                        name = node1.firstChild.nodeValue
                        if 'DemEvent' in name:
                            demEvent_node_list.append(node1)
                            #cnt_str = name.split('DemEvent_')[1].split('_', 1)[0]
                            #name = 'DemEvent_'+name.split('DemEvent_')[1].split('_', 1)[1]
                            if name == 'DemEventParameter':
                                demEvent_value_ref_event_num = int(found_ref_event_num_value(node))
                                modify_ref_event_num_value(node,event_max_num + 1)
                            demEvent_name_list.append(name)
                        elif 'DemDTC_CAN_' in name:
                            id = transform_uds_dtc(name.split('DemDTC_CAN_')[1].split('_', 1)[0])
                            DemDTC_id_list.append(id)
                            #name = 'DemDTC_CAN_'+name.split('DemDTC_CAN_')[1].split('_', 1)[1]
                            DemDTC_name_list.append(name)
                        elif 'DemDTC_' in name:
                            id = transform_uds_dtc(name.split('DemDTC_')[1].split('_', 1)[0])
                            DemDTC_id_list.append(id)
                            #name = 'DemDTC_'+name.split('DemDTC_')[1].split('_', 1)[1]
                            DemDTC_name_list.append(name)

        return demEvent_node_list, demEvent_name_list, demEvent_value_ref_event_num, DemDTC_name_list, DemDTC_id_list

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

    def write_SubContainer_SubCOntainer_PARAMETER_VALUES_subnode(dom, father_node, Debounce_Pass, Debounce_Failed):
        root = dom.createElement("ECUC-TEXTUAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-ENUMERATION-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceCounterBased/DemDebounceBehavior',
                'DEM_DEBOUNCE_FREEZE']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-INTEGER-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceCounterBased/DemDebounceCounterDecrementStepSize',
            '1']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-INTEGER-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceCounterBased/DemDebounceCounterFailedThreshold',
            Debounce_Failed]
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-INTEGER-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceCounterBased/DemDebounceCounterIncrementStepSize',
            '1']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-BOOLEAN-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceCounterBased/DemDebounceCounterJumpDown',
            'true']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-INTEGER-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceCounterBased/DemDebounceCounterJumpDownValue',
            '0']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-BOOLEAN-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceCounterBased/DemDebounceCounterJumpUp',
            'true']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-INTEGER-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceCounterBased/DemDebounceCounterJumpUpValue',
            '0']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-INTEGER-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceCounterBased/DemDebounceCounterPassedThreshold',
            Debounce_Pass]
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-BOOLEAN-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceCounterBased/DemDebounceCounterStorage',
            'false']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-BOOLEAN-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceCounterBased/DemDebounceContinuous',
            'false']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)
        return

    def write_SubContainer_SubCOntainer_PARAMETER_VALUES_subnode_with_timebase(dom, father_node, time_Passed, time_Failed):
        root = dom.createElement("ECUC-TEXTUAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-ENUMERATION-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceTimeBase/DemDebounceBehavior',
                'DEM_DEBOUNCE_FREEZE']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-FLOAT-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceTimeBase/DemDebounceTimeFailedThreshold',
            str(int(time_Failed) / 1000) ]
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-FLOAT-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceTimeBase/DemDebounceTimePassedThreshold',
            str(int(time_Passed) / 1000)]
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-BOOLEAN-PARAM-DEF', '']
        text = [
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceTimeBase/DemDebounceContinuous',
            'false']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)
        return

    def write_SubContainer_SubCOntainer_SUB_CONTAINERS_subnode(dom, father_node, Debounce_Pass, Debounce_Failed):
        root = dom.createElement("ECUC-CONTAINER-VALUE")
        root.setAttribute("UUID", GetUUID())
        father_node.appendChild(root)

        ###short name
        short_name_node = dom.createElement("SHORT-NAME")
        name_text = dom.createTextNode('DemDebounceCounterBased')
        short_name_node.appendChild(name_text)
        root.appendChild(short_name_node)

        ###DEFINITION-REF
        DEFINITION_REF_node = dom.createElement("DEFINITION-REF")
        DEFINITION_REF_node.setAttribute("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
        name_text = dom.createTextNode(
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceCounterBased')
        DEFINITION_REF_node.appendChild(name_text)
        root.appendChild(DEFINITION_REF_node)

        ###PARAMETER-VALUES
        PARAMETER_VALUES_node = dom.createElement("PARAMETER-VALUES")
        write_SubContainer_SubCOntainer_PARAMETER_VALUES_subnode(dom, PARAMETER_VALUES_node, Debounce_Pass, Debounce_Failed)
        root.appendChild(PARAMETER_VALUES_node)
        return

    def write_SubContainer_SubCOntainer_SUB_CONTAINERS_subnode_with_timebase(dom, father_node, Debounce_Pass, Debounce_Failed):
        root = dom.createElement("ECUC-CONTAINER-VALUE")
        root.setAttribute("UUID", GetUUID())
        father_node.appendChild(root)

        ###short name
        short_name_node = dom.createElement("SHORT-NAME")
        name_text = dom.createTextNode('DemDebounceTimeBase')
        short_name_node.appendChild(name_text)
        root.appendChild(short_name_node)

        ###DEFINITION-REF
        DEFINITION_REF_node = dom.createElement("DEFINITION-REF")
        DEFINITION_REF_node.setAttribute("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
        name_text = dom.createTextNode(
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass/DemDebounceTimeBase')
        DEFINITION_REF_node.appendChild(name_text)
        root.appendChild(DEFINITION_REF_node)

        ###PARAMETER-VALUES
        PARAMETER_VALUES_node = dom.createElement("PARAMETER-VALUES")
        write_SubContainer_SubCOntainer_PARAMETER_VALUES_subnode_with_timebase(dom, PARAMETER_VALUES_node, Debounce_Pass, Debounce_Failed)
        root.appendChild(PARAMETER_VALUES_node)
        return


    def write_SubContainer_SUB_CONTAINERS_subnode(dom, father_node,Debounce_Algorithm, Debounce_Pass, Debounce_Failed):
        root = dom.createElement("ECUC-CONTAINER-VALUE")
        root.setAttribute("UUID", GetUUID())
        father_node.appendChild(root)

        ###short name
        short_name_node = dom.createElement("SHORT-NAME")
        name_text = dom.createTextNode('DemDebounceAlgorithmClass')
        short_name_node.appendChild(name_text)
        root.appendChild(short_name_node)

        ###DEFINITION-REF
        DEFINITION_REF_node = dom.createElement("DEFINITION-REF")
        DEFINITION_REF_node.setAttribute("DEST", "ECUC-CHOICE-CONTAINER-DEF")
        name_text = dom.createTextNode(
            '/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemDebounceAlgorithmClass')
        DEFINITION_REF_node.appendChild(name_text)
        root.appendChild(DEFINITION_REF_node)

        ###SUB-CONTAINERS
        SUB_CONTAINERS_node = dom.createElement("SUB-CONTAINERS")
        if Debounce_Algorithm == "CounterBase":
            write_SubContainer_SubCOntainer_SUB_CONTAINERS_subnode(dom, SUB_CONTAINERS_node,'-' + Debounce_Pass, Debounce_Failed)
        elif Debounce_Algorithm == "TimeBase":
            write_SubContainer_SubCOntainer_SUB_CONTAINERS_subnode_with_timebase(dom, SUB_CONTAINERS_node, Debounce_Pass,Debounce_Failed)
        root.appendChild(SUB_CONTAINERS_node)
        return

    def write_SubContainer_REFERENCE_VALUES_subnode(dom, father_node ,EnableCondition):
        root = dom.createElement("ECUC-REFERENCE-VALUE")
        name = ['DEFINITION-REF', 'VALUE-REF']
        attr = ['DEST', 'DEST']
        value = ['ECUC-REFERENCE-DEF', 'ECUC-CONTAINER-VALUE']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemOperationCycleRef',
                '/ActiveEcuC/Dem/DemGeneral/PowerCycle']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-REFERENCE-VALUE")
        name = ['DEFINITION-REF', 'VALUE-REF']
        attr = ['DEST', 'DEST']
        value = ['ECUC-CHOICE-REFERENCE-DEF', 'ECUC-CONTAINER-VALUE']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemAgingCycleRef',
                '/ActiveEcuC/Dem/DemGeneral/IgnitionCycle']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        if EnableCondition != "N.A" :
            root = dom.createElement("ECUC-REFERENCE-VALUE")
            name = ['DEFINITION-REF', 'VALUE-REF']
            attr = ['DEST', 'DEST']
            value = ['ECUC-REFERENCE-DEF', 'ECUC-CONTAINER-VALUE']
            text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemEnableConditionGroupRef',
                    '/ActiveEcuC/Dem/DemGeneral/' + str(EnableCondition)]
            write_two_sub_node(dom, root, name, attr, value, text)
            father_node.appendChild(root)
        return

    def write_SubContainer_PARAMETER_VALUES_subnode(dom, father_node, priority, aging):
        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-BOOLEAN-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemAgingAllowed', 'true']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-BOOLEAN-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemConsiderPtoStatus', 'false']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-TEXTUAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-ENUMERATION-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemEventDestination', 'DEM_DTC_ORIGIN_PRIMARY_MEMORY']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-INTEGER-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemEventPriority', str(priority)]
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-BOOLEAN-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemFFPrestorageSupported', 'false']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-INTEGER-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass/DemAgingCycleCounterThreshold', str(aging)]
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)
        return

    def write_SUB_CONTAINERS_subnode(dom, father_node, priority, aging, EnableCondition, Debounce_Algorithm, Debounce_Pass, Debounce_Failed):
        root = dom.createElement("ECUC-CONTAINER-VALUE")
        root.setAttribute("UUID", GetUUID())
        father_node.appendChild(root)

        ###short name
        short_name_node = dom.createElement("SHORT-NAME")
        name_text = dom.createTextNode('DemEventClass')
        short_name_node.appendChild(name_text)
        root.appendChild(short_name_node)

        ###DEFINITION-REF
        DEFINITION_REF_node = dom.createElement("DEFINITION-REF")
        DEFINITION_REF_node.setAttribute("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
        name_text = dom.createTextNode('/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventClass')
        DEFINITION_REF_node.appendChild(name_text)
        root.appendChild(DEFINITION_REF_node)

        ###PARAMETER-VALUES
        PARAMETER_VALUES_node = dom.createElement("PARAMETER-VALUES")
        write_SubContainer_PARAMETER_VALUES_subnode(dom, PARAMETER_VALUES_node, priority, aging)
        root.appendChild(PARAMETER_VALUES_node)


        ###REFERENCE-VALUES
        REFERENCE_VALUES_node = dom.createElement("REFERENCE-VALUES")
        write_SubContainer_REFERENCE_VALUES_subnode(dom, REFERENCE_VALUES_node, EnableCondition)
        root.appendChild(REFERENCE_VALUES_node)

        ###SUB-CONTAINERS
        SUB_CONTAINERS_node = dom.createElement("SUB-CONTAINERS")
        write_SubContainer_SUB_CONTAINERS_subnode(dom, SUB_CONTAINERS_node,Debounce_Algorithm, Debounce_Pass, Debounce_Failed)
        root.appendChild(SUB_CONTAINERS_node)
        return

    def write_REFERENCE_VALUES_subnode(dom, father_node, dtc_name):
        root = dom.createElement("ECUC-REFERENCE-VALUE")
        name = ['DEFINITION-REF', 'VALUE-REF']
        attr = ['DEST', 'DEST']
        value = ['ECUC-REFERENCE-DEF', 'ECUC-CONTAINER-VALUE']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemExtendedDataClassRef',
                '/ActiveEcuC/Dem/DemGeneral/DemExtendedDataClass_ID01']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-REFERENCE-VALUE")
        name = ['DEFINITION-REF', 'VALUE-REF']
        attr = ['DEST', 'DEST']
        value = ['ECUC-REFERENCE-DEF', 'ECUC-CONTAINER-VALUE']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemFreezeFrameClassRef',
                '/ActiveEcuC/Dem/DemGeneral/DemFreezeFrameClass_ID01']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        if dtc_name != 'NonDtc':
            root = dom.createElement("ECUC-REFERENCE-VALUE")
            name = ['DEFINITION-REF', 'VALUE-REF']
            attr = ['DEST', 'DEST']
            value = ['ECUC-REFERENCE-DEF', 'ECUC-CONTAINER-VALUE']
            text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemDTCClassRef',
                    '/ActiveEcuC/Dem/DemConfigSet/'+dtc_name]
            write_two_sub_node(dom, root, name, attr, value, text)
            father_node.appendChild(root)
        return

    def write_PARAMETER_VALUES_subnode(dom, father_node, num):
        root = dom.createElement("ECUC-TEXTUAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-ENUMERATION-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventTimeSeries', 'DEM_TIMESERIES_SNAPSHOT_NONE']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-BOOLEAN-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventAvailable', 'true']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-INTEGER-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventId', str(num)]
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-TEXTUAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-ENUMERATION-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventKind', 'DEM_EVENT_KIND_SWC']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-BOOLEAN-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventAvailableInVariant', 'true']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-BOOLEAN-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventLatchTestFailed', 'false']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-INTEGER-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemMaxNumberFreezeFrameRecords', '2']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        root = dom.createElement("ECUC-NUMERICAL-PARAM-VALUE")
        name = ['DEFINITION-REF', 'VALUE']
        attr = ['DEST', '']
        value = ['ECUC-INTEGER-PARAM-DEF', '']
        text = ['/MICROSAR/Dem/DemConfigSet/DemEventParameter/DemEventCreateInfoPort', 'true']
        write_two_sub_node(dom, root, name, attr, value, text)
        father_node.appendChild(root)

        return

    def write_dem_event_in_arxml(dom, father_node, name, num, ref_event_num, dtc_name, priority, aging, EnableCondition, Debounce_Algorithm, Debounce_Pass, Debounce_Failed):
        #name_str = 'DemEvent_' + '{:0>3d}'.format(num)+'_'+name.split('DemEvent_')[1]
        name_str = 'DemEvent_' + name.split('DemEvent_')[1]
        root = dom.createElement("ECUC-CONTAINER-VALUE")
        root.setAttribute("UUID", GetUUID())
        father_node.appendChild(root)

        ###short name
        short_name_node = dom.createElement("SHORT-NAME")
        name_text = dom.createTextNode(name_str)
        short_name_node.appendChild(name_text)
        root.appendChild(short_name_node)

        ###DEFINITION-REF
        DEFINITION_REF_node = dom.createElement("DEFINITION-REF")
        DEFINITION_REF_node.setAttribute("DEST", "ECUC-PARAM-CONF-CONTAINER-DEF")
        name_text = dom.createTextNode('/MICROSAR/Dem/DemConfigSet/DemEventParameter')
        DEFINITION_REF_node.appendChild(name_text)
        root.appendChild(DEFINITION_REF_node)

        ###PARAMETER-VALUES
        PARAMETER_VALUES_node = dom.createElement("PARAMETER-VALUES")
        write_PARAMETER_VALUES_subnode(dom, PARAMETER_VALUES_node, ref_event_num)
        root.appendChild(PARAMETER_VALUES_node)

        ###REFERENCE-VALUES
        REFERENCE_VALUES_node = dom.createElement("REFERENCE-VALUES")
        write_REFERENCE_VALUES_subnode(dom, REFERENCE_VALUES_node, dtc_name)
        root.appendChild(REFERENCE_VALUES_node)

        ###SUB-CONTAINERS
        SUB_CONTAINERS_node = dom.createElement("SUB-CONTAINERS")
        write_SUB_CONTAINERS_subnode(dom, SUB_CONTAINERS_node, priority, aging, EnableCondition, Debounce_Algorithm, Debounce_Pass, Debounce_Failed)
        root.appendChild(SUB_CONTAINERS_node)
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

    demEvent_node_list, demEvent_name_list, demEvent_value_ref_event_num, DemDTC_name_list, DemDTC_id_list = Get_All_Sub_Node(my_root_node,excel_data.num, 'ECUC-CONTAINER-VALUE', 'SHORT-NAME')
    insert_cnt = demEvent_value_ref_event_num ####start number
    if len(demEvent_name_list) != 1 :
        print('Just keep the DemEventParameter in the template file. Please clear the old DEM event first')
        return

    for i in range(excel_data.num):
        if excel_data.Event_Name[i+excel_data.start_offset] in demEvent_name_list:
            print(excel_data.Event_Name[i + excel_data.start_offset] + '-------------- already in list')
        else:
            ##print(excel_data.Event_Name[i + excel_data.start_offset] + ' ****************not in list')
            if excel_data.DTC[ i +excel_data.start_offset] == "N.A":
                index = -1
            else:
                excel_DTC_str = str(excel_data.DTC[i + excel_data.start_offset])
                if "DemDTC_CAN_" in excel_DTC_str:
                    dtc_hex = transform_uds_dtc(excel_DTC_str.split('DemDTC_CAN_')[1].split('_', 1)[0])
                elif "DemDTC_" in excel_DTC_str:
                    dtc_hex = transform_uds_dtc(excel_DTC_str.split('DemDTC_')[1].split('_', 1)[0])
                index = DemDTC_id_list.index(dtc_hex)

            write_dem_event_in_arxml(dom,
                                     my_root_node,
                                     excel_data.Event_Name[i+excel_data.start_offset],
                                     insert_cnt,
                                     demEvent_value_ref_event_num,
                                     'NonDtc' if index == -1 else DemDTC_name_list[index],
                                     excel_data.Priority[i+excel_data.start_offset],
                                     excel_data.Aging[i+excel_data.start_offset],
                                     excel_data.EnableCondition[i + excel_data.start_offset],
                                     excel_data.Debounce_Algorithm[i + excel_data.start_offset],
                                     str(excel_data.Debounce_Pass[i + excel_data.start_offset]),
                                     str(excel_data.Debounce_Failed[i+excel_data.start_offset]))
            insert_cnt = insert_cnt + 1
            demEvent_value_ref_event_num = demEvent_value_ref_event_num + 1
            ##break

    # 每一个结点对象（包括dom对象本身）都有输出XML内容的方法，如：toxml()--字符串, toprettyxml()--美化树形格式。
    try:
        with open(xml_path, 'w', encoding='UTF-8') as fh:
            # 4.writexml()第一个参数是目标文件对象，第二个参数是根节点的缩进格式，第三个参数是其他子节点的缩进格式，
            # 第四个参数制定了换行格式，第五个参数制定了xml内容的编码。
            dom.writexml(fh, indent='', addindent='  ', newl='\n', encoding='UTF-8', standalone=False)
            print('在 ' + xml_path + ' 中写入events OK!')
    except Exception as err:
        print('错误信息：{0}'.format(err))

    return





















