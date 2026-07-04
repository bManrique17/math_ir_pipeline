#!/usr/bin/env python
# -*- coding:utf-8 -*-

import html
import os
from copy import copy
import subprocess
import sys
from lib.math_lib.math_extractor import MathExtractor
from lib.math_lib import latex_mml
from bs4 import BeautifulSoup
from lxml import etree
import xml.etree.ElementTree as ET
import csv
from os.path import dirname, join
csv.field_size_limit(sys.maxsize)
sys.setrecursionlimit(10000)


SUBPROCESS_TIMEOUT = 10000
Port = 3354
LATEXMLC = [
    'latexmlc',
    '--preload=amsmath',
    '--preload=amsfonts',
    '--preload={}'.format(join(dirname(latex_mml.__file__), "mws.sty.ltxml")),
    '--pmml',
    '--cmml',
    '--profile=fragment',
    # '--whatsin=fragment',
    # '--whatsout=fragment',
    # '--format=html5',
    # '--port='+str(Port),
    '-',
]

XML_NAMESPACES = {
    'xhtml': 'http://www.w3.org/1999/xhtml',
    'mathml': 'http://www.w3.org/1998/Math/MathML',
    'ntcir-math': 'http://ntcir-math.nii.ac.jp/',
}
ETREE_TOSTRING_PARAMETERS = {
    'xml_declaration': True,
    'encoding': 'UTF-8',
    'with_tail': False,
}


def start_latexml_server():
    """
    Starting the latexml server on port 3990
    :return:
    """
    os.system('latexmls --port=' + str(Port))


def tree_to_unicode(tree):
    return etree.tostring(tree, **ETREE_TOSTRING_PARAMETERS).decode(ETREE_TOSTRING_PARAMETERS['encoding'])


def unicode_to_tree(text):
    xml_parser = etree.XMLParser(huge_tree=True)
    return etree.XML(text.encode(ETREE_TOSTRING_PARAMETERS['encoding']), xml_parser)


def remove_noise(xx):
    tree = etree.XML(str(xx))
    for el in tree.xpath("//*"):
        for attr in el.attrib:
            if attr.startswith("id") or attr.startswith("xref"):
                el.attrib.pop(attr)
    return ET.tostring(tree, encoding='unicode', method='xml')


def latexml(latex_input):
    xml_input = execute(LATEXMLC, latex_input)
    xml_output = resolve_share_elements(xml_input)
    return xml_output


def resolve_share_elements(xml_tokens):
    xml_document = BeautifulSoup(xml_tokens, 'lxml')
    for math_element in xml_document.find_all('math'):
        for share_element in math_element.find_all('share'):
            if 'href' not in share_element:
                share_element.decompose()
                continue
            assert share_element['href'].startswith('#')
            shared_element = math_element.find(id=share_element['href'][1:])
            if shared_element:
                share_element.replace_with(copy(shared_element))
            else:
                share_element.decompose()
    return str(xml_document)


def execute(command, unicode_input):
    str_input = unicode_input.encode('utf-8')
    process = subprocess.Popen(
        command,
        shell=False,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        str_output = process.communicate(
            str_input,
            timeout=SUBPROCESS_TIMEOUT,
        )[0]
    except subprocess.TimeoutExpired as e:
        process.kill()
        raise e
    unicode_output = str_output.decode('utf-8')
    return unicode_output


def check_dollar_sign(latex_list):
    for i in range(len(latex_list)):
        latex = latex_list[i]
        if not latex.startswith("$"):
            latex_list[i] = "$" + latex + "$"
    return latex_list


def get_mathmls(latex_list):
    latex_list = check_dollar_sign(latex_list)
    latex_paragraphs = '\n\n'.join(
        'Formula #{}:\n\\[{}\\]'.format(formula_number, latex)
        for formula_number, latex
        in enumerate(latex_list)
    )
    cmml_list = []
    pmml_list = []
    try:
        xml_output = latexml(latex_paragraphs)
        # print(xml_output)
        try:
            xml_document = unicode_to_tree(xml_output)
            for formula_number, _ in enumerate(latex_list):
                math_elements = xml_document.xpath(
                    '//xhtml:div[@class = "ltx_para" and xhtml:p[@class = "ltx_p" and normalize-space(text()) = "Formula #{}:"]]//mathml:math'.format(
                        formula_number),
                    namespaces=XML_NAMESPACES
                )
                if len(math_elements) >= 1:
                    math_element = math_elements[0]
                    math_tokens = tree_to_unicode(math_element)
                    try:
                        cmml_math_tokens = MathExtractor.isolate_cmml(math_tokens)
                        cmml_math_tokens = remove_noise(cmml_math_tokens)
                        cmml_math_element = unicode_to_tree(cmml_math_tokens)
                        pmml_math_tokens = MathExtractor.isolate_pmml(math_tokens)
                        pmml_math_tokens = remove_noise(pmml_math_tokens)
                        pmml_math_element = unicode_to_tree(pmml_math_tokens)
                        etree.strip_tags(cmml_math_element, '{{{}}}semantics'.format(XML_NAMESPACES['mathml']))
                        cmml_math_tokens = tree_to_unicode(cmml_math_element)
                        cmml_failure = None
                        pmml_math_tokens = tree_to_unicode(pmml_math_element)
                        pmml_failure = None

                    except Exception as e:
                        cmml_math_tokens = ''
                        pmml_math_tokens = ''
                        cmml_failure = e
                        pmml_failure = e
                else:
                    cmml_math_tokens = ''
                    pmml_math_tokens = ''
                    cmml_failure = ValueError('Formula not found in LaTeXML output')
                    pmml_failure = ValueError('Formula not found in LaTeXML output')
                cmml_list.append((cmml_failure, cmml_math_tokens))
                pmml_list.append((pmml_failure, pmml_math_tokens))
        except etree.Error as e:  # LaTeXML conversion failed, try halving latex_rows
            assert len(latex_list) > 0
            if len(latex_list) > 1:
                latex_list_head = latex_list[:len(latex_list) // 2]
                latex_list_tail = latex_list[len(latex_list) // 2:]
                cmml_list_head, pmml_list_head = get_mathmls(latex_list_head)
                cmml_list_tail, pmml_list_tail = get_mathmls(latex_list_tail)
                cmml_list.extend(cmml_list_head + cmml_list_tail)
                pmml_list.extend(pmml_list_head + pmml_list_tail)
            else:
                cmml_math_tokens = ''
                pmml_math_tokens = ''
                cmml_failure = ValueError(e.msg)
                pmml_failure = ValueError(e.msg)
                cmml_list.append((cmml_failure, cmml_math_tokens))
                pmml_list.append((pmml_failure, pmml_math_tokens))
    except subprocess.SubprocessError as e:
        cmml_math_tokens = ''
        pmml_math_tokens = ''
        cmml_failure = e
        pmml_failure = e
        for _ in latex_list:
            cmml_list.append((cmml_failure, cmml_math_tokens))
            pmml_list.append((pmml_failure, pmml_math_tokens))
    return cmml_list, pmml_list
